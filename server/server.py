import subprocess
import threading
from flask import Flask, Response

app = Flask(__name__)

latest = None
lock = threading.Lock()


# function is made by ai because idk ffmpeg / tcp
def ffmpeg_reader():
    global latest
    proc = subprocess.Popen(
        [
            "ffmpeg",
            "-fflags",
            "nobuffer",
            "-listen",
            "1",
            "-flags",
            "low_delay",
            "-i",
            "tcp://0.0.0.0:5123",
            "-vf",
            "fps=10",
            "-q:v",
            "5",
            "-f",
            "mjpeg",
            "pipe:1",
        ],
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
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")


@app.route("/stream")
def stream():
    return Response(mjpeg(), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    threading.Thread(target=ffmpeg_reader, daemon=True).start()
    app.run(host="0.0.0.0", port=8000, threaded=True)
