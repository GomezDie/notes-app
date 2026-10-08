"""Download generated media listed in a JSON file: [{"name": "img02_car_a", "url": "https://..."}].

    python3 fetch.py list.json out_dir
"""
import json
import os
import subprocess
import sys


def main():
    items, out = json.load(open(sys.argv[1])), sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for it in items:
        url = it["url"]
        ext = os.path.splitext(url.split("?")[0])[1] or ".bin"
        path = os.path.join(out, it["name"] + ext)
        r = subprocess.run(["curl", "-sS", "-o", path, "-w", "%{http_code}", url], capture_output=True, text=True)
        print(f"{r.stdout} {path} {os.path.getsize(path) if os.path.exists(path) else 0}")


if __name__ == "__main__":
    main()
