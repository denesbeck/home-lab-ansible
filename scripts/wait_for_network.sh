#!/bin/bash

ipServerAddress=$(ip route | awk '/default/ {print $3; exit}')
cycleLength=1 # The length of a wait cycle in seconds
timeout=15    # Maximum number of seconds to wait before giving up

if [ -z "$ipServerAddress" ]; then
    sleep $timeout
    exit 1
fi

elapsedTime=0
ping -c 1 $ipServerAddress > /dev/null 2>&1
while [ $? -ne 0 ]; do
    if [ "$elapsedTime" -ge "$timeout" ]; then
        # Timeout
        exit 1
    fi

    elapsedTime=$((elapsedTime + cycleLength))
    sleep $cycleLength
    ping -c 1 $ipServerAddress > /dev/null 2>&1
done
