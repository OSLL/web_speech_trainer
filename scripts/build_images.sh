#!/bin/bash

set -e

# build vosk
./scripts/build_images/build_vosk.sh

# build base image
./scripts/build_images/build_base.sh
