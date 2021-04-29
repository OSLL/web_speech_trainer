#! /bin/bash

apache_config_filename=${1}
apache_ssl_mod=${2:-''}
sudo scripts/setup_apache_config.sh $apache_config_filename $apache_ssl_mod

mkdir -p ../mongo_data
docker-compose build
docker-compose APP_CONF=../app_conf/config.ini up -d --remove-orphans
