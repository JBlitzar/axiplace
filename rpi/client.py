# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "flask",
# ]
# ///
from flask import Flask, Response
import subprocess
import threading
import time

app = Flask(__name__)

camera_process = None
current_frame = b""
frame_lock = threading.Lock()
frame_ready = threading.Event()


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
            "640",
            "--height",
            "480",
            "--framerate",
            "30",  # Higher FPS
            "--denoise",
            "off",  # Disable processing
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


if __name__ == "__main__":
    thread = threading.Thread(target=camera_thread, daemon=True)
    thread.start()

    app.run(host="0.0.0.0", port=8000, threaded=True)
