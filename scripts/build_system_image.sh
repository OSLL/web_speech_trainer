#!/bin/bash

set -e

# build vosk
./scripts/build_image.sh "Dockerfile.kaldi-ru" OSLL/vosk

# build base image
./scripts/build_image.sh Dockerfile_base OSLL/wst_base
