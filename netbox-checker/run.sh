#!/bin/bash
#
# Usage with `netbox-community/netbox-docker`
#
# ./run.sh <netbox-docker-path>

set -e

if [[ $1 == "inside-docker" ]]; then
  echo "Running inside container"

  pip install -e /netbox-checker

  /opt/netbox/netbox/manage.py nbshell \
      --command='from netbox_checker import check_netbox; check_netbox()'
else
  echo "Running docker compose"

  export NETBOX_CHECKER_PATH="$PWD"
  export NETBOX_DOCKER_PATH=${1:-$NETBOX_CHECKER_PATH/../netbox-docker}

  cd "$NETBOX_DOCKER_PATH"

  docker compose run \
    --user=root \
    --env NETBOX_CHECKER_MAX_OUTPUTS \
    --env NETBOX_CHECKER_BASE_URL \
    --volume "$NETBOX_CHECKER_PATH:/netbox-checker" \
    netbox /netbox-checker/run.sh inside-docker
fi
