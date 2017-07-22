#!/bin/bash
#release_version: 1.0.03
#release_date   : Wed Mar  8 15:11:02 PST 2017

set -x

APACHE_CONFIG_DIR="/etc/apache2/sites-available/"
APACHE_CONFIG_ENABLE_DIR="/etc/apache2/sites-enabled/"

APACHE_MOD_CONFIG_DIR="/etc/apache2/mods-available/"
APACHE_MOD_CONFIG_ENABLE_DIR="/etc/apache2/mods-enabled/"

SYS_CONF="system.conf"
CGI_LOG_DIR=${CGI_LOG_FILE%/*}

function install_package()
{
    apt-get install gcc -y
    apt-get install apache2 -y
    apt-get install librrd-dev -y
    apt-get install rrdtool -y
    apt-get install libpython-dev -y
    apt-get install libconfuse-dev -y
    apt-get install libapr1-dev  -y
    apt-get install libaprutil1-dev -y
    apt-get install python-requests -y
    apt-get install python-pip -y
    pip install --upgrade pip
    pip install ConcurrentLogHandler


    apt-get install libconfuse0 -y
    apt-get install libpcre3-dev -y
    apt-get install zlib1g-dev -y
    apt-get install libmemcache0  -y
    apt-get install libmemcached-dev -y
    apt-get install php7.0 -y
    apt-get install php7.0-xml -y
    apt-get install libapache2-mod-php7.0 -y

    apt-get install pkg-config

}

function additional_dir()
{
    mkdir -p  /usr/local/var/run

    # where RRD database file saved
    mkdir -p /var/lib/ganglia/rrds

    mkdir -p /usr/local/lib64/ganglia/python_modules

}


function dir_privilege()
{
    chown nobody /var/lib/ganglia/rrds
    chown -R www-data:www-data /var/www/html/ganglia  
}

function install_ganglia()
{
    cd ganglia-src
    tar zxvf ganglia-3.7.2.tar.gz
    cd ganglia-3.7.2
    ./configure --enable-debug -enable-status --with-gmetad --with-memcached
    make
    make install
    cp -f gmond/gmond.service /etc/systemd/system/
    cp -f gmetad/gmetad.service /etc/systemd/system/
    cd ../..
    cp ganglia-conf/gmond.conf /usr/local/etc/gmond.conf
    # generate BST metrics groups
    python generators.py
    cp -fr output/* /usr/local/etc/conf.d/
}

function uninstall_ganglia()
{
    cd ganglia-src
    cd ganglia-3.7.2
    make uninstall
    rm /usr/local/etc/gmond.conf
}


function install_gweb()
{
    cd ganglia-src
    tar zxvf ganglia-web-3.7.2.tar.gz
    cd ganglia-web-3.7.2
    cp -f ../../ganglia-conf/gweb.Makefile ./Makefile
    make install
    cd ../..
}

function uninstall_gweb()
{
    rm -fr /var/www/html/ganglia
}

function uninstall_cgi()
{
    rm -fr $CGI_DIR
    rm -fr $CGI_LOG_DIR
}

function install_apache_conf()
{
    cp -f apache-conf/apache_ganglia_web.conf $APACHE_CONFIG_DIR
    ln -sf $APACHE_CONFIG_DIR/apache_ganglia_web.conf $APACHE_CONFIG_ENABLE_DIR/apache_ganglia_web.conf
    ln -sf $APACHE_MOD_CONFIG_DIR/cgi.load $APACHE_MOD_CONFIG_ENABLE_DIR/cgi.load
    apache2ctl restart 
}
function uninstall_apache_conf()
{
    rm -f $APACHE_CONFIG_DIR/apache_ganglia_web.conf
    rm -f $APACHE_CONFIG_ENABLE_DIR/apache_ganglia_web.conf
}

function install_lenovo_telemetry()
{
    install_package
    install_ganglia
    install_gweb
    additional_dir
    dir_privilege
    install_apache_conf
}


function uninstall_lenovo_telemetry()
{
    uninstall_ganglia
    uninstall_gweb
    uninstall_apache_conf
}


case "$1" in
   install)
     install_lenovo_telemetry
     ;;
   uninstall)
     uninstall_lenovo_telemetry
     ;;
   *)
    echo "Usage: $0 { install | uninstall }"
    exit 1
esac

exit 0
