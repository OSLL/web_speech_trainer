#!/bin/bash

set -e

tag=${1:-'v0.1'}

# build vosk
./scripts/build_image.sh "Dockerfile.kaldi-ru" osll/vosk:$tag

# build base image
./scripts/build_image.sh Dockerfile_base osll/wst_base:$tag
