#!/bin/bash

cleanup() {
  echo "Cleaning up..."
  echo "killing cf"
  kill "$CF_PID" 2>/dev/null
  echo "killing uv"
  kill "$UV_PID" 2>/dev/null
  echo "axi off, up"
  axi goto 0 0
  axi off
  axi up

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

url=""
restarts=0
max_restarts=5
while [ -z "$url" ]; do
  # If cloudflared died before producing a URL, restart it.
  if ! kill -0 "$CF_PID" 2>/dev/null; then
    restarts=$((restarts + 1))
    if [ "$restarts" -gt "$max_restarts" ]; then
      echo "cloudflared failed to start a tunnel after $max_restarts restarts"
      cleanup
    fi
    echo "cloudflared exited; restarting ($restarts/$max_restarts)..."
    cloudflared tunnel --url http://localhost:8000 > "$logfile" 2>&1 &
    CF_PID=$!
  fi

  url=$(grep -Eo 'https://[^[:space:]]+\.trycloudflare\.com' /tmp/tunnel.log | head -n 1)
  if [ -z "$url" ]; then
    sleep 1
  fi
done

uv run upstream.py "$url" &

# curl -X POST https://axiplace.vercel.app/update-stream-url \
#   -H "Content-Type: application/json" \
#   -d "{\"stream_url\": \"$url\"}"

echo "Stream available at: $url"

wait

cleanup