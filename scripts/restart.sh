#! /bin/bash
VERSION_FILE_NAME="VERSION.json"
new_image="base_image"
old_image="base_image:old"


apache_config_filename=${1}
apache_ssl_mod=${2:-''}
sudo scripts/setup_apache_config.sh $apache_config_filename $apache_ssl_mod

VERSION_FILE_PATH="$(dirname $(dirname $(readlink -f $0)))/$VERSION_FILE_NAME"
scripts/version.sh > $VERSION_FILE_PATH

mkdir -p ../mongo_data

docker-compose down
docker tag $new_image $old_image
docker-compose build --no-cache
docker rmi $old_image

APP_CONF=../app_conf/config.ini docker-compose up -d --remove-orphans
