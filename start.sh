#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
docker run --rm -d \
           -e FLASK_APP=tgbot.py \
           -p 5000:5000 \
           -v /var/run/redis/redis.sock:/tmp/redis.sock \
           -v $DIR/keys/:/keys \
           -l tiltbot tiltbot
