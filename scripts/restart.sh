#! /bin/bash

set -e

VERSION_FILE_NAME="VERSION.json"

VERSION_FILE_PATH="$(dirname $(dirname $(readlink -f $0)))/$VERSION_FILE_NAME"
./scripts/version.sh > $VERSION_FILE_PATH

docker-compose stop

docker-compose --project-name wst_test_build build --no-cache
docker-compose build

APP_CONF=../app_conf/config.ini docker-compose up -d --remove-orphans
