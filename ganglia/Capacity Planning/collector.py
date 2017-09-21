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
import pdb
from pdb import Pdb
from cloghandler import ConcurrentRotatingFileHandler
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL

_Worker_Thread = None
_Lock = threading.Lock() # synchronization lock

class LogHandler():
    """log wrapper class for  log """
    def __init__(self, logfile, log_size_limit, log_rotate_num, log_level):
        self.logger = logging.getLogger()
        try:
            self.rotateHandler = ConcurrentRotatingFileHandler(logfile, "a", log_size_limit, log_rotate_num)
        except Exception, e:
            print 'INTERNAL_ERR'
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
        self.ip           = params['ip']
        self.metric       = {}
        self.cookie       = ''

        # Initialize the HTTPs connnection and save the cookie
        # Step 1 - Login and get the auth cookie
        url='http://'+self.ip +':8090'+'/nos/api/login/'
        ret = requests.get(url,auth=('admin','admin'),verify=False)
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
        tmp_url='http://'+self.ip+':8090'+ '/nos/api/info/telemetry/bst/report'
        payload = { }
        payload['include-ingress-port-priority-group'] = 1
        payload['include-ingress-port-service-pool'] = 1
        payload['include-ingress-service-pool'] = 1
        payload['include-egress-port-service-pool'] = 1
        payload['include-egress-service-pool'] = 1
        payload['include-device'] = 1
        ret = requests.post(tmp_url, headers=hdr, auth=('admin','admin'),
                    json= payload, verify=False)
        json_report = ret.json()
        m = { }
        m['time_max'] = 3
        m['value_type'] = 'uint32'
        m['units'] = 'C'
        m['format'] = '%u',
        m['slope'] = 'both'
        send_list = []
        realm_list = json_report['report']
        for i in range(len(realm_list)):
            realm =  realm_list[i]
            if not realm.has_key('realm'):
               break
            if realm['realm'] == 'device':
                print "device realm"
                m['value'] = (int) (realm['data'])
                m['description'] = 'Device Realm'
                m['groups'] = 'Device Realm' 
                m['name'] = '_Device'
                print m
                send_list.append(m.copy()) 
            if realm['realm'] == 'ingress-port-priority-group':
                data_list = realm['data']
                val = 0
                for j in range(len(data_list)):
                     data = data_list[j]
                     arr = data['data']
                     pg = arr[0][0]
                     val = val + (int) (arr[0][1])
                m['value'] = (int) (val/len(data_list))
                m['description'] = 'Ingress port priority group'
                m['groups'] = 'Ingress Port Priority Group' 
                m['name'] = '_aggregate_ingress_port_priority_group_' + str(pg)
                print m
                send_list.append(m.copy()) 
            elif realm['realm'] == 'ingress-port-service-pool':
                data_list = realm['data']
                val = 0
                for j in range(len(data_list)):
                     data = data_list[j]
                     arr = data['data']
                     service_pool = arr[0][0]
                     val = val + (int) (arr[0][1])
                m['value'] = (int) (val/len(data_list))
                m['description'] = 'Ingress port service pool'
                m['groups'] = 'Ingress Port Service Pool' 
                m['name'] = '_aggregate_ingress-port-service_pool_' + str(service_pool)
                send_list.append(m.copy()) 
            elif realm['realm'] == 'ingress-service-pool':
                data_list = realm['data']
                service_pool = data_list[0][0]
                m['value'] = (int) (data_list[0][1])
                m['description'] = 'Ingress service pool'
                m['groups'] = 'Ingress Service Pool' 
                m['name'] = '_ingress-service-pool_' + str(service_pool)
                send_list.append(m.copy()) 
            elif realm['realm'] == 'egress-port-service-pool':
                data_list = realm['data']
                val = 0
                for j in range(len(data_list)):
                     data = data_list[j]
                     arr = data['data']
                     service_pool = arr[0][0]
                     val = val + (int) (arr[0][1])
                m['value'] = (int) (val/len(data_list))
                m['description'] = 'Egress port service pool'
                m['groups'] = 'Egress Port Service Pool' 
                m['name'] = '_aggregate_egress-port-service-pool_' + str(service_pool)
                send_list.append(m.copy()) 
            elif realm['realm'] == 'egress-service-pool':
                data_list = realm['data']
                service_pool = data_list[0][0]
                m['value'] = (int) (data_list[0][1])
                m['description'] = 'Egress service pool'
                m['groups'] = 'Egress Service Pool' 
                m['name'] = '_egress-service-pool_' + str(service_pool)
                send_list.append(m.copy()) 

	    #pdb.set_trace()
            
	pull.logger.debug("input json report %s" % json.dumps(json_report))
        if send_list is None or len(send_list) == 0:
           pull.logger.debug("no metrics find")
           return 
        pull.logger.debug("%d metrics generated" % (len(send_list)))

        g = Gmetric('239.2.11.71', '8649', 'multicast')
        for m in send_list:
            s = self.ip
            fake_host = s.replace(".", "_")
            m['name'] = self.ip + m['name'] 
            g.send(m['name'], m['value'], m['value_type'], m['units'], m['slope'],m['time_max'], 0, m['groups'], '%s:%s' %(self.ip, fake_host))
            pull.logger.debug("Switch IP: %-15s updating metric %s, metric value: %d (%s:%s)" % (self.ip, m['name'], int(m['value']), self.ip, fake_host))
            print("Switch IP: %-15s updating metric %s, metric value: %d (%s:%s)" % (self.ip, m['name'], int(m['value']), self.ip, fake_host))

def metric_of(self, name):
        val = 0
        if name in self.metric:
            #_Lock.acquire()
            val = self.metric[name]
            #_Lock.release()
        return val

def monitor_init(params):
    global descriptors
    t = init_thread(params)
    return t

def init_thread(params):
    thread = UpdateMetricThread(params)
    thread.start()
    #thread.update_metric()
    return thread

def init_switch_monitors():
    switch_monitors = []
    for s in conf.switches:
        print "init monitor for %s" % s
        switch_monitors.append((s, monitor_init({"ip": s})))
    return switch_monitors

if __name__ == '__main__':

    pull = LogHandler("telemetry.log", 1024*1024*50, 5, "DEBUG")
    switch_monitors = init_switch_monitors()
    #g = Gmetric('239.2.11.71', '8649', 'multicast')

    try:
        while True:
            for s in switch_monitors:
                print "============================================================================"
                print "updating metrics of switch %s" % s[0]
                '''
                for d in metric_descriptors:
                    v = s[1].metric_of(d['name'])
                    print ("    '%s'" + (55-len(d['name']))*'.' + d['format']) % (d['name'], v)
                    g.send(d['name'], v, d['value_type'], d['units'], d['slope'], d['time_max'], 0, d['groups'], '%s:%s'%(s[0],s[0]))
                '''
            
            # sleep 5 seconds before the next query
            pull.logger.debug("I'm sleeping") 
            time.sleep(5)

    except KeyboardInterrupt:
        time.sleep(0.2)
        os._exit(1)
    except StandardError:
        traceback.print_exc()
        os._exit(1)

