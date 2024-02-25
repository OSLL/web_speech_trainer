#!/bin/bash

set -e

tag=${1:-'v0.1'}

# build base image
./scripts/build_image.sh Dockerfile_base osll/wst_base:$tag
