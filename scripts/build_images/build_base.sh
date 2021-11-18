#!/bin/bash

set -e

# build base image
docker build -f Dockerfile_base -t osll/wst_base .
