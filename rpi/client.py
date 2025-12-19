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


def fake_callback(c): # ts had better be blocking upon implementation
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
       os.system("bash stream.sh &")
    except Exception as e:
        print("Streaming error:", e)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__))) # excellent syntactic sugar

    start_stream()

    while True:
        poll()
        time.sleep(5)


if __name__ == "__main__":
    main()
