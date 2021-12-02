#!/bin/bash

set -e

dockerfile=${1}
image_tag=${2}

# build base image
docker build -f $dockerfile -t $image_tag --no-cache .
