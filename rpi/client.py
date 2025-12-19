import os
import socket
import subprocess
import time
import requests
import threading

API_BASE = "https://192.168.7.188:8000"
STREAM_HOST = "192.168.7.188"
STREAM_PORT = 5123
STREAM_SECRET = os.environ.get("STREAM_SECRET", "default_secret")


def fake_callback(c):
    print(f"Fake callback: {c}")


def poll():
    try:
        resp = requests.get(f"{API_BASE}/command")
        if resp.status_code == 200:
            val = resp.json()
            if val.get("command"):
                fake_callback(val["command"])
                requests.post(f"{API_BASE}/command_complete", json={"status": "done"})
    except Exception as e:
        print("Polling error:", e)


def start_stream():
    try:
        s = socket.create_connection((STREAM_HOST, STREAM_PORT))
        s.sendall(f"AUTH {STREAM_SECRET}\n".encode())
        print("AUTH sent, starting video stream...")

        rpicam_cmd = [
            "rpicam-vid",
            "-t",
            "0",
            "--codec",
            "yuv420",
            "--width",
            "1280",
            "--height",
            "720",
            "--framerate",
            "20",
            "-o",
            "-",
        ]

        ffmpeg_cmd = [
            "ffmpeg",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "yuv420p",
            "-s",
            "1280x720",
            "-r",
            "20",
            "-i",
            "-",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-tune",
            "zerolatency",
            "-profile:v",
            "baseline",
            "-x264-params",
            "keyint=20:min-keyint=20:scenecut=0:sync-lookahead=0:rc-lookahead=0",
            "-g",
            "20",
            "-bf",
            "0",
            "-f",
            "mpegts",
            "pipe:1",
        ]

        rpicam = subprocess.Popen(rpicam_cmd, stdout=subprocess.PIPE)

        ffmpeg = subprocess.Popen(ffmpeg_cmd, stdin=rpicam.stdout, stdout=s)

        ffmpeg.wait()
    except Exception as e:
        print("Streaming error:", e)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    threading.Thread(target=start_stream, daemon=True).start()

    while True:
        poll()
        time.sleep(5)


if __name__ == "__main__":
    main()
