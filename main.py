import os
import requests

api_key = os.getenv("PEXELS_API_KEY")

if not api_key:
    raise RuntimeError("PEXELS_API_KEY is missing")

url = "https://api.pexels.com/v1/videos/search"

params = {
    "query": "cars",
    "orientation": "portrait",
    "per_page": 3,
}

headers = {
    "Authorization": api_key
}

response = requests.get(
    url,
    headers=headers,
    params=params,
    timeout=30
)

response.raise_for_status()

data = response.json()

videos = data.get("videos", [])

print(f"Pexels connection: OK")
print(f"Videos found: {len(videos)}")

for video in videos:
    print(video["url"])
