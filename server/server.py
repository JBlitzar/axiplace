import subprocess
import threading
from flask import Flask, Response, json, request
import dotenv
import os
import queue
import time
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

dotenv.load_dotenv()

app = Flask(__name__)
CORS(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
STREAM_URL = ""
lock = threading.Lock()

commandQueue = queue.Queue()

ipTimes = {}
TIMEOUT_S = 300


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


@app.post("/update-stream-url")
def update_stream_url():
    source_ip = os.getenv("SOURCE_IP")
    if not source_ip:
        return {"error": "SOURCE_IP not set"}
    if source_ip != request.remote_addr:
        return {"error": "Unauthorized"}
    data = request.get_json()
    stream_url = data.get("stream_url")
    if not stream_url:
        return {"error": "No stream_url provided"}
    global latest
    with lock:
        latest = stream_url
    return {"status": "success"}


@app.get("/stream-url")
def get_stream_url():
    global STREAM_URL
    with lock:
        url = STREAM_URL
    if not url:
        return {"error": "No stream URL set"}
    return {"stream_url": url}


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
    # try:
    if request.remote_addr not in ipTimes:
        ipTimes[request.remote_addr] = 0
    if (
        request.remote_addr in ipTimes
        and time.time() - ipTimes[request.remote_addr] > TIMEOUT_S
    ):
        data = request.get_json()
        command = data.get("command")
        if not command:
            return {"error": "No command provided"}
        commandQueue.put(command)
        ipTimes[request.remote_addr] = time.time()
        return {"status": "success"}
    else:
        return Response(
            json.dumps(
                {
                    "status": "error",
                    "message": f"you need to wait haha; Time left: {TIMEOUT_S - (time.time() - ipTimes[request.remote_addr])}",
                }
            ),
            status=429,
            mimetype="application/json",
        )
    # except Exception as e:
    #     return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)  # TODO different port
