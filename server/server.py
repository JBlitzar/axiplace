import socket
import subprocess
import threading
from flask import Flask, Response
import dotenv

dotenv.load_dotenv()
import os

app = Flask(__name__)

latest = None
lock = threading.Lock()
SECRET = f"AUTH {os.environ['STREAM_SECRET']}\n".encode("utf-8")


# function is made by ai because idk ffmpeg / tcp
def ffmpeg_reader():
    global latest

    s = socket.socket()
    s.bind(("0.0.0.0", 5123))
    s.listen(1)
    conn, addr = s.accept()

    header = conn.recv(len(SECRET))
    if header != SECRET:
        print(f"Rejected connection from {addr}")
        conn.close()
        return

    proc = subprocess.Popen(
        [
            "ffmpeg",
            "-fflags",
            "nobuffer",
            "-flags",
            "low_delay",
            "-i",
            "pipe:0",
            "-vf",
            "fps=10",
            "-q:v",
            "5",
            "-f",
            "mjpeg",
            "pipe:1",
        ],
        stdin=conn.makefile("rb"),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )

    buf = b""
    while True:
        chunk = proc.stdout.read(4096)
        if not chunk:
            break
        buf += chunk
        while b"\xff\xd8" in buf and b"\xff\xd9" in buf:
            s = buf.index(b"\xff\xd8")
            e = buf.index(b"\xff\xd9") + 2
            frame = buf[s:e]
            buf = buf[e:]
            with lock:
                latest = frame


def mjpeg():
    while True:
        with lock:
            frame = latest
        if frame:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"


@app.route("/stream")
def stream():
    return Response(mjpeg(), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    threading.Thread(target=ffmpeg_reader, daemon=True).start()
    app.run(host="0.0.0.0", port=8000, threaded=True)
