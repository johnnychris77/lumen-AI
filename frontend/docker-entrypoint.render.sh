#!/bin/sh
set -eu

# Substitute ONLY $API_UPSTREAM (leave nginx's own $host, $remote_addr, etc.
# intact) into the config template, then hand off to nginx.
: "${API_UPSTREAM:?API_UPSTREAM must be set (internal URL of the backend, e.g. http://lumen-ai-api:8000)}"

envsubst '${API_UPSTREAM}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
