# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "flask",
#     "numpy",
#     "opencv-python",
#     "requests",
# ]
# ///
from flask import Flask, Response
import subprocess
import threading
import time
import requests
import cv2
import numpy as np

app = Flask(__name__)

camera_process = None
current_frame = b""
frame_lock = threading.Lock()
frame_ready = threading.Event()


def fake_callback(c):  # ts had better be blocking upon implementation
    print(f"Fake callback: {c}")


API_BASE = "https://axiplace.vercel.app"


def unskew(img):
    """ul 714 156
    ur 2795 156
    dl 622 1790
    dr 2831 1790
    should be:
    ul 714 156
    ur 2795 156
    dl 714 1790
    dr 2795 1790"""
    h, w = img.shape[:2]
    src_pts = np.float32([[714, 156], [2795, 156], [622, 1790], [2831, 1790]])
    dst_pts = np.float32([[714, 156], [2795, 156], [714, 1790], [2795, 1790]])
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    unskewed = cv2.warpPerspective(img, matrix, (w, h))
    return unskewed


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


def camera_thread():
    global camera_process, current_frame

    camera_process = subprocess.Popen(
        [
            "rpicam-vid",
            "-t",
            "0",
            "--codec",
            "mjpeg",
            "--width",
            "1920",
            "--height",
            "1080",
            "--framerate",
            "30",
            "--denoise",
            "off",
            "--awb",
            "auto",
            "-o",
            "-",
        ],
        stdout=subprocess.PIPE,
        bufsize=0,
        stderr=subprocess.DEVNULL,
    )

    buffer = b""
    while True:
        chunk = camera_process.stdout.read(65536)
        if not chunk:
            break

        buffer += chunk

        while True:
            start = buffer.find(b"\xff\xd8")
            end = buffer.find(b"\xff\xd9")

            if start != -1 and end != -1 and end > start:
                frame = buffer[start : end + 2]
                buffer = buffer[end + 2 :]

                with frame_lock:
                    current_frame = frame
                    frame_ready.set()
            else:
                break


def generate_frames():
    while True:
        frame_ready.wait()
        with frame_lock:
            frame = current_frame
            frame_ready.clear()

        frame_array = cv2.imdecode(np.frombuffer(frame, np.uint8), cv2.IMREAD_COLOR)

        unskewed_frame = unskew(frame_array)

        _, encoded_frame = cv2.imencode(".jpg", unskewed_frame)
        frame = encoded_frame.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Content-Length: "
            + str(len(frame)).encode()
            + b"\r\n\r\n"
            + frame
            + b"\r\n"
        )


@app.route("/stream")
def stream():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


def poll_loop():
    while True:
        poll()
        time.sleep(2)


if __name__ == "__main__":
    thread = threading.Thread(target=camera_thread, daemon=True)
    thread.start()

    poller_thread = threading.Thread(target=poll_loop, daemon=True)
    poller_thread.start()

    app.run(host="0.0.0.0", port=8000, threaded=True)
