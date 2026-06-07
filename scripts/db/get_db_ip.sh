#!/bin/bash

set -e

container_id=`docker ps --quiet --filter "ancestor=mongo:4.4.1" --filter "name=_db_1"`
container_ip=`docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' ${container_id}`

echo ${container_ip}
