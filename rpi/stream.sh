#!/bin/bash 
source .env
(
printf "AUTH ${STREAM_SECRET}\n"
rpicam-vid -t 0 \
  --codec yuv420 \
  --width 1280 --height 720 --framerate 20 \
  -o -
) | ffmpeg \
  -f rawvideo \
  -pix_fmt yuv420p \
  -s 1280x720 \
  -r 20 \
  -re \
  -i - \
  -c:v libx264 \
  -preset ultrafast \
  -tune zerolatency \
  -profile:v baseline \
  -x264-params keyint=20:min-keyint=20:scenecut=0:sync-lookahead=0:rc-lookahead=0 \
  -g 20 -bf 0 \
  -f mpegts \
  pipe:1 | nc 192.168.7.188 5123
