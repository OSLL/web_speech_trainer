#!/bin/bash

set -e

tag=${1:-'v0.2'}

# build base image
./scripts/build_image.sh Dockerfile_base dvivanov/wst-base:$tag
