#!/bin/bash
uv run client.py &

rm -f /tmp/tunnel.log

cloudflared tunnel --url http://localhost:8000 > /tmp/tunnel.log 2>&1 &


while [ ! -s /tmp/tunnel.log ]; do sleep 0.5; done
sleep 10


url=$(grep -Eo 'https://[^[:space:]]+\.trycloudflare\.com' /tmp/tunnel.log | head -n 1)


curl -X POST https://axiplace.vercel.app/update-stream-url \
  -H "Content-Type: application/json" \
  -d "{\"stream_url\": \"$url\"}"

echo "Stream available at: $url"


wait

killall cloudflared