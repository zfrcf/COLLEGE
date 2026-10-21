#!/bin/bash
cd "$(dirname "$0")/../srv"
python3 -c "import socket;socket.create_connection(('127.0.0.1',25575),1)" 2>/dev/null && { echo already; exit 0; }
: > log.txt
setsid nohup java -Xmx2G -jar server.jar nogui > log.txt 2>&1 < /dev/null &
for i in $(seq 1 90); do sleep 2; grep -q "RCON running" log.txt && break; done
cd ../tools && python3 rcon.py "forceload add -64 -64 63 63" "tick freeze" "gamerule randomTickSpeed 0" >/dev/null
echo up
