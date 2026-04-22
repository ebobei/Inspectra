#!/bin/sh
set -eu

exec rq worker inspectra --url "$REDIS_URL"
