# -*- coding: utf-8 -*-
#!/usr/bin/env python
#release_version: 1.0.03
#release_date   : Wed Mar  8 15:11:02 PST 2017

import sys
import traceback
import os
import threading
import time
import random
import json
import logging
import requests
import json
from gmetric import Gmetric
from pprint import pprint
import conf
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
from cloghandler import ConcurrentRotatingFileHandler
#from receiver import LogHandler
#import receiver

_Worker_Thread = None
_Lock = threading.Lock() # synchronization lock
'''
logger = logging.getLogger("telemetry")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler("telemetry.log")
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
fh.setFormatter(formatter)
logger.addHandler(ch)
logger.addHandler(fh)
'''
''' use concurrency support, rationtion support logger'''

class LogHandler():
    """log wrapper class for CGI log """
    def __init__(self, logfile, log_size_limit, log_rotate_num, log_level):
        self.logger = logging.getLogger()
        try:
            self.rotateHandler = ConcurrentRotatingFileHandler(logfile, "a", log_size_limit, log_rotate_num)
        except Exception, e:
            print_result('INTERNAL_ERR')
        formatter = logging.Formatter('%(asctime)-25s %(funcName)-25s %(levelname)-6s %(message)s')
        self.rotateHandler.setFormatter(formatter)
        self.logger.addHandler(self.rotateHandler)

        self.serverhandler = logging.handlers.SysLogHandler(address = ('10.240.176.203',514))
        self.serverhandler.setFormatter(formatter)
        self.logger.addHandler(self.serverhandler)

        if log_level == "DEBUG":
            self.logger.setLevel(DEBUG)
        elif log_level =="INFO":
            self.logger.setLevel(INFO)
        elif log_level =="WARNING":
            self.logger.setLevel(WARNING)
        elif log_level =="ERROR":
            self.logger.setLevel(ERROR)
        elif log_level =="CRITICAL":
            self.logger.setLevel(CRITICAL)
        else:
            self.logger.setLevel(INFO)

class UpdateMetricThread(threading.Thread):
    def __init__(self, params):
        threading.Thread.__init__(self)
        self.running      = False
        self.shuttingdown = False
        self.refresh_rate = 10
        self.ip           = params['sw_intf']['switch']
        self.intf         = params['sw_intf']['interface']
        self.metric       = {}
        self.prev_ctr     = [0,0,0,0,0,0,0]
        self.prev_tx_ctr     = [0,0,0,0,0,0,0]
        self.prev_rx_ctr     = [0,0,0,0,0,0,0]
        self.cookie       = ''

        a =  params['sw_intf']['interface']

        # Initialize the HTTPs connnection and save the cookie
        # Step 1 - Login and get the auth cookie
        url='http://'+self.ip +':8090'+'/nos/api/login/'
        ret = requests.get(url,auth=('admin','admin'),verify=False, timeout=20)
        print ret.elapsed
        self.cookie=ret.cookies['auth_cookie']

        # Step 2 - Login with valid cookie
        tmp_ckie = 'auth_cookie=' + self.cookie + ';user=admin; Max-Age=3600; Path=/'
        hdr=dict()
        hdr['Cookie']=tmp_ckie
 
        ret = requests.get(url, headers=hdr, auth=('admin','admin'),verify=False)
        self.cookie=ret.cookies['auth_cookie']

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        self.running = True
        while not self.shuttingdown:
            #_Lock.acquire()
            self.update_metric()
            #_Lock.release()
            time.sleep(self.refresh_rate)

        self.running = False

    def update_metric(self):
        tmp_ckie = 'auth_cookie='+self.cookie+';user=admin; Max-Age=3600; Path=/'
        hdr=dict()
        hdr['Cookie']=tmp_ckie
        hdr['Content-Type']='application/json'

        agg_rx = 0
        agg_tx = 0
        send_list = [] 
        i = 0
        for b in self.intf:
             url_intf = b.replace("/", "%2F")
             tmp_url='http://'+self.ip+':8090'+ '/nos/api/info/statistics/interface/' + url_intf
             print tmp_url
             ret = requests.get(tmp_url, headers=hdr, auth=('admin','admin'),
                     verify=False, timeout=10)
             json_report = ret.json()
             m = { }
             infstr = json_report['if_name']
             intfname = infstr.replace("/","_")
             m['name'] = self.ip + '_Rxrate_' + intfname
             if self.prev_rx_ctr[i] is 0:
                 m['value'] = 0 
             else:
                 m['value'] =  (int) (((int) (json_report['rx_pkts']) -   self.prev_rx_ctr[i]) / (self.refresh_rate))
                 
             self.prev_rx_ctr[i] = (int) (json_report['rx_pkts'])
             agg_rx = (int) (m['value']) + agg_rx
             m['time_max'] = 3
             m['value_type'] = 'uint32'
             m['units'] = 'C'
             m['format'] = '%u',
             m['slope'] = 'both'
             m['description'] = 'rx rate'
             m['groups'] = 'rx_rate'
             send_list.append(m.copy())
             m['name'] = self.ip  + '_Txrate_' + intfname
             if self.prev_tx_ctr[i] is 0:
                 m['value'] = 0 
             else:
                 m['value'] =  (int) (((int) (json_report['tx_pkts']) -   self.prev_tx_ctr[i]) / (self.refresh_rate))
             self.prev_tx_ctr[i] = (int) (json_report['tx_pkts'])
             agg_tx = (int) (m['value']) + agg_tx
             m['description'] = 'txrate'
             m['groups'] = 'tx_rate'
             send_list.append(m.copy())
             i = i + 1
        
        m['name'] = self.ip + '_Agg_Rxrate'
        m['value'] = agg_rx
        m['description'] = 'device_rx rate'
        m['groups'] = 'device_rx_rate'
        send_list.append(m.copy())
        
        m['name'] = self.ip + '_Agg_Txrate'
        m['value'] = agg_tx
        m['description'] = 'device_tx rate'
        m['groups'] = 'device_tx_rate'
        send_list.append(m.copy())
                 
        payload = {}
        payload['req-id'] = 1
        payload['request-type'] = 'port-drops'
        intf_list_dict = {}
        intf_list_dict['interface-list'] = self.intf
        payload['request-params'] = intf_list_dict
        tmp_url='http://'+self.ip+':8090'+ '/nos/api/info/telemetry/bst/congestion-drop-counters' 
        ret = requests.post(tmp_url, headers=hdr, auth=('admin','admin'), json = payload, verify=False)
        json_report =  ret.json()
        mylist = json_report['congestion-ctr']
        i = 0
        agg_cdrops = 0
        for b in mylist:
              mystr = b['interface']
              myname = mystr.replace("/","_")
              m['name'] = 'CDrp' + myname
              if self.prev_ctr[i] is 0:
                  m['value'] = 0 
              else:
                  m['value'] =  (int) (((int) (b['ctr']) -   self.prev_ctr[i]) / (self.refresh_rate))
                 
              agg_cdrops = m['value'] + agg_cdrops
              self.prev_ctr[i] = (int) (b['ctr'])
              m['description'] = 'Congestion drop rate'
              m['groups'] = 'cgsn_drop_rate'
              send_list.append(m.copy())
              i = i + 1
        m['name'] = self.ip + '_Agg_CgsnRate'
        m['value'] = agg_cdrops
        m['description'] = 'device_cgsn rate'
        m['groups'] = 'device_cgsn_rate'

        send_list.append(m.copy())
        pull.logger.info("input json report %s" % json.dumps(json_report))
        if send_list is None or len(send_list) == 0:
              pull.logger.debug("no metrics find")
              pull.logger.debug("%d metrics generated" % (len(send_list)))
        g = Gmetric('239.2.11.71', '8649', 'multicast')
        for m in send_list:
              s = self.ip
              fake_host = s.replace(".", "_")
              g.send(m['name'], m['value'], m['value_type'], m['units'], m['slope'],m['time_max'], 0, m['groups'], '%s:%s' %(self.ip, fake_host))
              print("IP: %-15s updating metric %s %u (%s:%s)" % (self.ip, m['name'], int(m['value']), self.ip, fake_host))

	      '''
	      if m['splunk_field'] is None:
	          cgilog.logger.info("no splunk forward")
	      else:
	          splunk_msg = 'ganglia-to-splunk: switch_ip=%s,' % (self.ip)
	          for f in m['splunk_field']:
	              if f['value'] != 'unknown_yet':
	              splunk_msg = splunk_msg + " %s=%s," % (f['name'], f['value'])
	          cgilog.logger.info(splunk_msg)
	      '''

    def metric_of(self, name):
        val = 0
        if name in self.metric:
            #_Lock.acquire()
            val = self.metric[name]
            #_Lock.release()
        return val

def monitor_init(params):
    t = init_thread(params)
    return t

def init_thread(params):
    thread = UpdateMetricThread(params)
    thread.start()
    return thread

def init_switch_monitors():
    switch_monitors = []
    for s in conf.switches_interface:
        switch_monitors.append((s, monitor_init({"sw_intf" : s})))
    return switch_monitors

if __name__ == '__main__':

    pull = LogHandler("telemetry.log", 1024*1024*50, 5, "INFO")
    switch_monitors = init_switch_monitors()
    g = Gmetric('239.2.11.71', '8649', 'multicast')

    try:
        while True:
            for s in switch_monitors:
                print "============================================================================"
                print "updating metrics of switch %s" % s[0]
            
            # sleep 5 seconds before the next query
            time.sleep(5)

    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except StandardError:
        traceback.print_exc()
        os._exit(1)




