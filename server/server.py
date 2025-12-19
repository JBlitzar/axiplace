import subprocess
import threading
from flask import Flask, Response, request
import dotenv
import os
import queue
import time

dotenv.load_dotenv()

app = Flask(__name__)

latest = None
lock = threading.Lock()

commandQueue = queue.Queue()

ipTimes = {}
TIMEOUT_S = 300


# function is made by ai because idk ffmpeg / tcp
def ffmpeg_reader():
    global latest
    source_ip = os.getenv("SOURCE_IP")
    if not source_ip:
        print("SOURCE_IP not set !!")
        return

    proc = subprocess.Popen(
        [
            "ffmpeg",
            "-fflags",
            "nobuffer",
            "-listen",
            "1",
            "-flags",
            "low_delay",
            "-allowed_ips",
            source_ip,
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




# is ts auth skib??
@app.get("/command")
def get_command():
    source_ip = os.getenv("SOURCE_IP")
    if not source_ip:
        return {"error": "SOURCE_IP not set"}
    if source_ip != request.remote_addr:
        return {"error": "Unauthorized"}
    try:
        command = commandQueue.get_nowait()
        return {"command": command}
    except queue.Empty:
        return {"command": None}
    
@app.post("/command_complete")
def command_complete():
    source_ip = os.getenv("SOURCE_IP")
    if not source_ip:
        return {"error": "SOURCE_IP not set"}
    if source_ip != request.remote_addr:
        return {"error": "Unauthorized"}
    try:
        commandQueue.task_done()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    

@app.post("/add_command")
def add_command():
    try:
        if request.remote_addr in ipTimes and time.time() - ipTimes[request.remote_addr] > TIMEOUT_S:
            data = request.get_json()
            command = data.get("command")
            if not command:
                return {"error": "No command provided"}
            commandQueue.put(command)
            ipTimes[request.remote_addr] = time.time()
            return {"status": "success"}
        else:
            return {"status": "error", "message": f"you need to wait haha; Time left: {TIMEOUT_S - (time.time() - ipTimes[request.remote_addr])}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}




if __name__ == "__main__":
    threading.Thread(target=ffmpeg_reader, daemon=True).start()
    app.run(host="0.0.0.0", port=8000, threaded=True) # TODO different port
