#!/bin/bash

source ~/.bashrc
shopt -s extglob

F1=$1
F2=$2

DEJAVU_RESULT=$(python compare_files.py $F1 $F2)

readarray -t lines <<< "$DEJAVU_RESULT"
echo ${lines[-1]}
