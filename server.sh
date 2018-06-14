#!/bin/bash
set -xeuo pipefail

dbname=${DBNAME:-}
dbhost=${DBHOST:-}
dbuser=${DBUSER:-}
dbpasswd=${DBPASSWD:-}
cacert_url=${CACERT_URL:-}

project_dir=$(dirname "$0")
cd "$project_dir"

cat <<EOD > config.py
dbname = '$dbname'
dbhost = '$dbhost'
dbuser = '$dbuser'
dbpasswd = '$dbpasswd'
EOD

if [ -n "$cacert_url" ]; then
    (
        cd /etc/pki/ca-trust/source/anchors
        curl -o --insecure "$cacert_url"
    )
    update-ca-trust extract
fi

exec gunicorn \
    --bind=0.0.0.0:5000 \
    --access-logfile=- \
    --enable-stdio-inheritance \
    product_listings_manager.wsgi
