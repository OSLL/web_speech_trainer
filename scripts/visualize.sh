#!/bin/bash

db_url="`./scripts/db/get_db_ip.sh`:27017"

cd visualization

python3 -m pip install -r requirements.txt
python3 visualization.py --mongo $db_url

cd -