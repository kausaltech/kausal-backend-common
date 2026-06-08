#!/bin/bash

set -e

python manage.py clearsessions
python manage.py cleartokens --skip-checks
# It's uncertain if we should run rebuild_references_index and when/how often
# python manage.py rebuild_references_index
