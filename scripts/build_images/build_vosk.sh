#!/bin/bash

set -e

# build vosk
docker build -f "Dockerfile.kaldi-ru" -t osll/vosk .
