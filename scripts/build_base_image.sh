#!/bin/bash

set -e

tag=${1:-'v0.2'}

# build base image
docker build -f Dockerfile_base -t dvivanov/wst-base:$tag --no-cache .
