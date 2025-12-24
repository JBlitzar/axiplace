import time
from flask import Flask, Response, json, request

import dotenv
import os
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import redis
from flask import send_from_directory

dotenv.load_dotenv()

app = Flask(__name__)
CORS(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

TIMEOUT_S = 300


r = redis.Redis(
    host="smart-squirrel-31858.upstash.io",
    port=6379,
    password=os.getenv("REDIS_PASSWORD"),
    ssl=True,
)

COMMAND_QUEUE_KEY = "command_queue"


# is ts auth skib??
@app.get("/command")
def get_command():
    source_ip = os.getenv("SOURCE_IP")
    if not source_ip:
        return {"error": "SOURCE_IP not set"}
    if source_ip != request.remote_addr:
        return {"error": "Unauthorized"}

    command = r.lpop(COMMAND_QUEUE_KEY)
    if command:
        return {"command": command.decode("utf-8")}
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

    stream_url = stream_url.strip().rstrip("/") + "/stream"

    r.set("stream_url", stream_url)
    return {"status": "success"}


@app.get("/stream-url")
def get_stream_url():
    url = r.get("stream_url")
    if not url:
        return {"error": "No stream URL set"}
    return {"stream_url": url.decode("utf-8")}


@app.post("/command_complete")
def command_complete():
    source_ip = os.getenv("SOURCE_IP")
    if not source_ip:
        return {"error": "SOURCE_IP not set"}
    if source_ip != request.remote_addr:
        return {"error": "Unauthorized"}

    return {"status": "success"}


@app.post("/add_command")
def add_command():
    ip = request.remote_addr
    rate_limit_key = f"rate_limit:{ip}"

    # Check rate limit in Redis
    last_time = r.get(rate_limit_key)
    if last_time:
        last_time = float(last_time.decode("utf-8"))
        time_left = TIMEOUT_S - (time.time() - last_time)
        if time_left > 0:
            return Response(
                json.dumps(
                    {
                        "status": "error",
                        "message": f"you need to wait haha; Time left: {time_left:.1f}s",
                    }
                ),
                status=429,
                mimetype="application/json",
            )

    data = request.get_json()
    command = data.get("command")
    if not command:
        return {"error": "No command provided"}
    command = json.dumps(command)

    r.rpush(COMMAND_QUEUE_KEY, command)

    r.set(rate_limit_key, str(time.time()), ex=TIMEOUT_S)
    return {"status": "success"}


@app.route("/")
def index():
    return send_from_directory("frontend", "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)  # TODO different port
