import redis
import os
import dotenv
import argparse

dotenv.load_dotenv()

r = redis.Redis(
    host="smart-squirrel-31858.upstash.io",
    port=6379,
    password=os.getenv("REDIS_PASSWORD"),
    ssl=True,
)

def set_stream_url(stream_url: str):
    if not stream_url.endswith("/stream"):
        stream_url = stream_url.rstrip("/") + "/stream"
    r.set("stream_url", stream_url)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set the stream URL in Redis.")
    parser.add_argument("stream_url", type=str, help="The stream URL to set.")
    args = parser.parse_args()
    set_stream_url(args.stream_url)
    print(f"Stream URL set to: {args.stream_url}")
