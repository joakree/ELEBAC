#!/bin/bash

PI5_IP="192.168.3.1"  ## Change to correct IP
INTERFACE="usb0"

FAIL_COUNT=0
MAX_FAIL=40

sleep 60

while true; do
    echo "loop kjører"
    echo "$FAIL_COUNT feil"
    # Sjekk om interface er oppe
    if ! ip link show "$INTERFACE" | grep -q "state UP"; then
        echo "$(date) Interface nede" >> /home/cameranode3/watchdog.log.    #CHANGE cameranodeX to correct number
        FAIL_COUNT=$((FAIL_COUNT+1))

    # Sjekk ping
    elif /bin/ping -c1 -W1 "$PI5_IP" > /dev/null; then
        echo "$(date) Connection OK" >> /home/cameranode3/watchdog.log.       #CHANGE cameranodeX to correct number
        FAIL_COUNT=0

    else
        echo "$(date) Ping feilet ($FAIL_COUNT)" >> /home/cameranode3/watchdog.log. #CHANGE cameranodeX to correct number
        FAIL_COUNT=$((FAIL_COUNT+1))
    fi

    if [ "$FAIL_COUNT" -ge "$MAX_FAIL" ]; then
        echo "$(date) Rebooter!" >> /home/cameranode3/watchdog.log  #CHANGE cameranodeX to correct number
        /sbin/reboot
    fi

    sleep 3
done
