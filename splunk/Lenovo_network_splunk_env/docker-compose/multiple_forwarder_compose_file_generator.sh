#/bin/bash
#
#	1.  Memory/CPU
#       2.  Storage check
#	2.  Default port availability which docker containers wille expose to host OS
#

version=7.0.3
FORWARDERS=""

function usage() {
    echo "Command Usage:"
    echo "multiple_forwarder_compose_file_generator.sh <forwarder_num> <dest_compose_file>"
    echo ""
} 

function check_memory() {
	# Enterprise server 4G,  forwarder  300M 
	# Rough estimation :  4 * 1024  + FORWARDER_NUM * 300M  < 80% of HOST_MEMORY

	HOST_MEMORY=`free -m | grep ^Mem: | awk '{ print $2 }'` 

	let "NEED=4*1024 + FORWARDERS*300"
	
	let "LIMIT=4*HOST_MEMORY/5"
	
	if [ $NEED -gt $LIMIT ]; then
		printf "= Host OS memory is not enougth! \n"
		printf "= Expect 4G for Splunk Enterprise Server, 300M for every forwarder \n"
		printf "= Need memory %s M \n" "$NEED"
		printf "= Host OS 80 percent memory limiation  %s M \n" "$LIMIT"
		printf "\n"
		printf "\n"
                exit 1
        fi
}

function check_storage() {
	#printf "= Skip storage check!"
	echo ""
}

function service_port_check() {
	# Only those port need to be exposed to Host OS, if only used within docker internal private network,  it does not 
	# conflict with Host OS port. 
	# default splunk WEB GUI http service port  	8000		Must	
	SPLUNK_WEB_PORT=8000
	# default splunk mangement purpose service port 8089		Optional 
	SPLUNK_MGMT_PORT=8089
	# default Splunk server recieving port 		9997		Optional  Not need in Phase 1
	SPLUNK_REV_PORT_DEF=9997

	HOST_PORT_USED=`netstat -tuln  | grep ^[t,u] | awk '{ print $4 }' | sed  's/:/ /g' | awk '{ print $NF }'`

	for PORT in $HOST_PORT_USED
	do
		if [ $PORT -eq $SPLUNK_WEB_PORT ]; then
			printf "= Port 8000 has been used.  Splunk Enterprise server need 8000 for WEB GUI access"
			printf "\n"
			printf "\n"
			exit 1
		fi
		if [ $PORT -eq $SPLUNK_MGMT_PORT ]; then
			printf "= Port 8089 has been used.  Splunk Enterprise server need 8089 for deployment service"
			printf "\n"
			printf "\n"
			exit 1
		fi
		if [ $PORT -eq $SPLUNK_REV_PORT_DEF ]; then
			printf "= Port 9997 has been used.  Splunk Enterprise server need 9997 to receive data"
			printf "\n"
			printf "\n"
			exit 1
		fi


	done
}

function volumes_compose() {
	printf "version: \'2.0\' \n" 
	printf "volumes: \n" 
	printf "    Startup-Order: \n"
	printf "    opt-splunk-etc: \n"
	printf "    opt-splunk-var: \n"

	for(( index=1; index<=FORWARDERS ; index++))
	do
		printf "    opt-forwarder-%s-etc: \n"  "$index"
		printf "    opt-forwarder-%s-var: \n"  "$index"
	done

	printf "services: \n" 
}

function splunkenterprise_compose() {
	printf "    splunkenterprise: \n"
	printf "        image: splunk/splunk:%s \n" "$version"
	printf "        container_name: server \n" 
    	printf "        hostname: splunkenterprise-docker \n"
    	printf "        environment: \n"
    	printf "          SPLUNK_START_ARGS: --accept-license --answer-yes \n"
      	printf "          SPLUNK_ENABLE_DEPLOY_SERVER: 'true' \n"
	printf "          SPLUNK_ENABLE_LISTEN: 9997 \n"
    	printf "        volumes: \n"
      	printf "          - /data/splunk/opt-splunk-etc:/opt/splunk/etc \n"
        printf "          - /data/splunk/opt-splunk-var:/opt/splunk/var \n"
        printf "          - /data/Startup-Order:/Startup-Order \n"
	printf "        command: |\n"
        printf "          /bin/bash -c '\n"
        printf "          rm -fr /Start-Order/*;\n"
        printf "          echo Service splunkenterprise  Start;\n"
	printf "          sleep 25;\n"
        printf "          touch /Startup-Order/splunkenterprise;\n"
        printf "          /sbin/entrypoint.sh start-service'\n"
    	printf "        ports: \n"
	printf "          - \"8000:8000\" \n"
	printf "          - \"9997:9997\" \n"
	printf "          - \"8089:8089\" \n"
}


function forwarder_compose() {
	index=$1
	printf "    forwarder-%s: \n" "$index"
	printf "        image: ospost/lenovo-splunk-forwarder:%s \n" "$version"
	printf "        container_name: forwarder-%s \n" "$index"
    	printf "        hostname: forwarder-%s-docker \n" "$index"
	if [ $index -eq 1 ]; then
    		#printf "        depends_on: \n"
    		#printf "          - \"splunkenterprise\" \n"
		printf "        command: |\n"
        	printf "          /bin/bash -c '\n"
      		printf "          while [[ ! -f /Startup-Order/splunkenterprise ]]; do sleep 1; done;\n"
        	printf "          echo Service forwarder-1 Start;\n"
        	printf "          sleep 45;\n"
        	printf "          touch /Startup-Order/forwarder-1;\n"
        	printf "          /sbin/entrypoint.sh start-service'\n"

	else 
		#let "depend = index - 1"
		#printf "        depends_on: \n"
    		#printf "          - \"forwarder-%s\" \n" "$depend"
		printf "        command: |\n"
        	printf "          /bin/bash -c '\n"
      		printf "          while [[ ! -f /Startup-Order/splunkenterprise ]]; do sleep 1; done;\n"
		for(( i=1; i<index ; i++))
		#for i in $(seq 1 $index)
		do
      			printf "          while [[ ! -f /Startup-Order/forwarder-%s ]]; do sleep 1; done;\n" "$i"
		done
        	printf "          echo Service forwarder-%s Start;\n" "$index"
		let "wait_time = 50 + index*5"
        	printf "          sleep %s;\n" "$wait_time"
        	printf "          touch /Startup-Order/forwarder-%s;\n" "$index"
        	printf "          /sbin/entrypoint.sh start-service'\n"

	fi	
    	printf "        environment: \n"
    	printf "          SPLUNK_START_ARGS: --accept-license --answer-yes \n"
      	printf "          SPLUNK_FORWARD_SERVER_ARGS: '-method clone' \n"
	printf "          SPLUNK_FORWARD_SERVER: 'splunkenterprise:9997' \n"
	printf "          SPLUNK_DEPLOYMENT_SERVER: 'splunkenterprise:8089' \n"

	let "forwarder_port = 1000 + index"

	printf "          SPLUNK_ENABLE_LISTEN: %s \n" "$forwarder_port"
    	printf "        volumes: \n"
      	printf "          - /data/forwarder-%s/opt-forwarder-%s-etc:/opt/splunk/etc \n" "$index" "$index"
        printf "          - /data/forwarder-%s/opt-forwarder-%s-var:/opt/splunk/var \n" "$index" "$index"
        printf "          - /data/Startup-Order:/Startup-Order \n"
    	printf "        ports: \n"
	printf "          - \"%s:%s\" \n" "$forwarder_port" "$forwarder_port"
}


if [ $# -ne 2 ]; then
	usage
	exit 1
fi

expr $1 "+" 10 &> /dev/null
if [ $? -ne 0 ]; then
  echo "$1 not number"
  usage
  exit 1
fi

FORWARDERS=$1

if [ -e $2 ]; then
  echo "$2 already exsit, plesae choose different name"
  exit 1
fi


printf  "\n1 Splunk Enterprise Server, %s forwarder(s) docker compose file \'%s\' generating ...  \n" "$1" "$2"

check_memory
check_storage
service_port_check
volumes_compose > $2
splunkenterprise_compose >> $2

for(( forwarder=1; forwarder<=FORWARDERS ; forwarder++))
do
	forwarder_compose $forwarder >> $2
done

printf  "docker compose file \'%s\' generating ...  Done \n\n"  "$2"



