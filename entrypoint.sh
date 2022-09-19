#!/bin/bash -xue

UID=${AIRFLOW_UID:-9001}

# Adds user "user" and executes the Dockerfile's command as "user"
echo "Starting with UID: $UID"
id -u user &>/dev/null || useradd --shell /bin/bash -u $UID -o -c "" -m user

chown -R user:user /home/user

exec gosu user "$@"