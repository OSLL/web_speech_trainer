#!/bin/bash

set -e

# build base image
docker build -f Dockerfile_ubuntu_python3 -t osll/wst_base .
