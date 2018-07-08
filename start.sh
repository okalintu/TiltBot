#!/bin/bash
docker run --rm -d \
           -e FLASK_APP=tgbot.py \
           -p 5000:5000 \
           -v /var/run/redis/redis.sock:/tmp/redis.sock \
           -l tiltbot tiltbot
