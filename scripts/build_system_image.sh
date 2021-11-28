#!/bin/bash

set -e

# build vosk
./scripts/build_image.sh "Dockerfile.kaldi-ru" osll/vosk

# build base image
./scripts/build_image.sh Dockerfile_base osll/wst_base
