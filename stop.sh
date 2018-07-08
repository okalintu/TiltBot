#!/bin/bash
docker stop $(docker ps -f label=tiltbot -q)
