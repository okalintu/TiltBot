#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
docker run -d \
           -e FLASK_APP=tgbot.py \
           -e FLASK_ENV=development \
           -p 127.0.0.1:5000:5000 \
           -v /var/run/redis/redis.sock:/tmp/redis.sock \
           -v $DIR/keys/:/keys \
           -v $DIR/:/code \
           --restart=always \
           --name tiltbot tiltbot
