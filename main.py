import os

print("=== YouTube Shorts Automation ===")

required = [
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "YOUTUBE_CLIENT_ID",
    "YOUTUBE_CLIENT_SECRET",
    "YOUTUBE_REFRESH_TOKEN",
]

missing = []

for name in required:
    if os.getenv(name):
        print(f"{name}: OK")
    else:
        print(f"{name}: MISSING")
        missing.append(name)

if missing:
    raise RuntimeError(
        "Missing GitHub Secrets: " + ", ".join(missing)
    )

print("All YouTube credentials are available.")
print("Next step: video generation and upload.")
