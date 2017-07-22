Plugins for Lenovo CNOS Telemetry
===
Introduction
---
Network telemetry is used by organizations to monitor their network devices (e.g. switches,routers) and provide this data to software controllers to  analyze the data for condition of the network. Network Telemetry Agents running on Lenovo CNOS monitor the buffer statistics and network interface counters on the switch. Extenal Montoring and Analytical tools like Ganglia and Splunk can be used to monitor and analyse the telemetry agent data pulled from switches running Lenovo CNOS. The plugins to do capacity planning and congestion detection are presented here.

Preparation for running the Ganglia plugins
---
**Server Installation**

Install  Ubuntu latest stable release 16.04 on a server machine and do the following

1. mkdir lenovo-ganglia
2. cd lenovo-ganglia
3. mkdir ganglia-src
4. cd ganglia-src
5. wget  https://sourceforge.net/projects/ganglia/files/ganglia-web/3.7.2/ganglia-web-3.7.2.tar.gz
6. wget  https://sourceforge.net/projects/ganglia/files/ganglia%20monitoring%20core/3.7.2/ganglia-3.7.2.tar.gz
7. cd ..
8. copy the file install.sh from the ganglia directory of the plugin to this directory
9. sudo ./install.sh install

**Lenovo Switch Configuration**

Execute the following command on the Lenovo switch
G8272#config
Enter configuration commands, one per line.  End with CNTL/Z.
G8272(config)#
G8272(config)#feature telemetry
G8272(config)#no feature restApi
G8272(config)#feature restApi http
G8272(config)#exit

Copy the contents of the plugin directories into the server

Running the plugins
---
The plugin has a sample conf.py file.
