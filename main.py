import os

print("YouTube Shorts automation started!")

required = [
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "YOUTUBE_CLIENT_ID",
    "YOUTUBE_CLIENT_SECRET",
    "YOUTUBE_REFRESH_TOKEN",
]

for name in required:
    if os.getenv(name):
        print(f"{name}: OK")
    else:
        print(f"{name}: MISSING")
