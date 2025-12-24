#!/bin/bash

cleanup() {
  echo "Cleaning up..."
  echo "killing cf"
  kill "$CF_PID" 2>/dev/null
  echo "killing uv"
  kill "$UV_PID" 2>/dev/null
  echo "exited"
  exit 0
}

trap cleanup SIGINT SIGTERM

uv run client.py &
UV_PID=$!

rm -f /tmp/tunnel.log
logfile="/tmp/tunnel.log"
touch "$logfile"

cloudflared tunnel --url http://localhost:8000 > "$logfile" 2>&1 &
CF_PID=$!

while [ ! -s "$logfile" ]; do sleep 0.5; done
sleep 10

url=$(grep -Eo 'https://[^[:space:]]+\.trycloudflare\.com' /tmp/tunnel.log | head -n 1)

curl -X POST https://axiplace.vercel.app/update-stream-url \
  -H "Content-Type: application/json" \
  -d "{\"stream_url\": \"$url\"}"

echo "Stream available at: $url"

wait

cleanup