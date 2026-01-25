import time
from flask import Flask, Response, json, request, url_for, redirect, session

import dotenv
import os
from flask_cors import CORS
import requests
from werkzeug.middleware.proxy_fix import ProxyFix
import redis
from flask import send_from_directory

from requests_oauthlib import OAuth2Session

app = Flask(__name__)
dotenv.load_dotenv()

HACKCLUB_CLIENT_ID = os.getenv("HACKCLUB_CLIENT_ID")
HACKCLUB_CLIENT_SECRET = os.getenv("HACKCLUB_CLIENT_SECRET")
HACKCLUB_AUTHORIZE_URL = "https://auth.hackclub.com/oauth/authorize"
HACKCLUB_TOKEN_URL = "https://auth.hackclub.com/oauth/token"
HACKCLUB_API_BASE_URL = "https://auth.hackclub.com/api/v1/"


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))
CORS(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

TIMEOUT_S = 60


r = redis.Redis(
    host="smart-squirrel-31858.upstash.io",
    port=6379,
    password=os.getenv("REDIS_PASSWORD"),
    ssl=True,
)

COMMAND_QUEUE_KEY = "command_queue"


@app.route("/login")
def login():
    redirect_uri = url_for("callback", _external=True)
    oauth = OAuth2Session(
        HACKCLUB_CLIENT_ID,
        scope=["openid"],
        redirect_uri=redirect_uri,
    )
    authorization_url, state = oauth.authorization_url(HACKCLUB_AUTHORIZE_URL)
    session["oauth_state"] = state
    return redirect(authorization_url)


@app.route("/oauth/callback")
def callback():
    redirect_uri = url_for("callback", _external=True)
    oauth = OAuth2Session(
        HACKCLUB_CLIENT_ID,
        state=session.get("oauth_state"),
        redirect_uri=redirect_uri,
    )
    token = oauth.fetch_token(
        HACKCLUB_TOKEN_URL,
        client_secret=HACKCLUB_CLIENT_SECRET,
        authorization_response=request.url,
    )
    session["oauth_token"] = token
    user = oauth.get(HACKCLUB_API_BASE_URL + "me").json()
    # print("USER", user)
    session["user_id"] = user["identity"]["id"]
    return redirect("/")


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
    cftoken = request.json.get("token")
    # verify
    if not cftoken:
        return {"error": "No token provided"}, 400
    secret = os.getenv("CF_SECRET_KEY")
    verify_url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    payload = {
        "secret": secret,
        "response": cftoken,
        "remoteip": request.remote_addr,
    }
    resp = requests.post(verify_url, data=payload)
    result = resp.json()
    if not result.get("success"):
        return {"error": "Invalid CAPTCHA; try reloading?"}, 400

    ip = request.remote_addr
    # rate_limit_key = f"rate_limit:{ip}"

    rate_limit_key = session.get("user_id")
    if not rate_limit_key:
        return {"error": "Unauthorized; please log in!"}, 401

    go_anyways = ip == os.getenv("SOURCE_IP")

    # Check rate limit in Redis
    last_time = r.get(rate_limit_key)
    if last_time:
        last_time = float(last_time.decode("utf-8"))
        time_left = TIMEOUT_S - (time.time() - last_time)
        if time_left > 0 and not go_anyways:
            return Response(
                json.dumps(
                    {
                        "status": "error",
                        "message": f"you need to wait (60s timeout); Time left: {time_left:.1f}s",
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


def stream_url_is_reachable(url):
    try:
        resp = requests.head(url, timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False


@app.route("/")
def index():
    stream_url = r.get("stream_url")
    if stream_url:
        stream_url = stream_url.decode("utf-8")
        if stream_url_is_reachable(stream_url):
            return send_from_directory("frontend", "index.html")

    return send_from_directory("frontend", "offline.html")


@app.route("/video.mov")
def video():
    return send_from_directory("frontend", "video.mov")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)  # TODO different port
