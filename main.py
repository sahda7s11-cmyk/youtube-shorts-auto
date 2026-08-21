import asyncio
import os
import random
import subprocess
from pathlib import Path

import requests
import edge_tts

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

OUTPUT_VIDEO = Path("short.mp4")
VOICE_FILE = Path("voice.mp3")
WORK_DIR = Path("clips")

TOPICS = [
    {
        "search": "technology artificial intelligence",
        "text": "هل تعلم أن الذكاء الاصطناعي أصبح قادرًا على تحليل كميات ضخمة من المعلومات خلال وقت قصير؟ هذه التقنية تغيّر طريقة عمل كثير من الشركات والمجالات."
    },
    {
        "search": "sports football stadium",
        "text": "هل تعلم أن تحليل البيانات أصبح جزءًا أساسيًا من الرياضة الحديثة؟ الفرق تستخدم البيانات لفهم أداء اللاعبين وتحسين القرارات داخل الملعب."
    },
    {
        "search": "modern cars driving",
        "text": "هل تعلم أن السيارات الحديثة تحتوي على أنظمة ذكية تستطيع مراقبة الطريق ومساعدة السائق في مواقف مختلفة؟ هذه التقنيات تتطور بسرعة كبيرة."
    },
    {
        "search": "interesting science",
        "text": "من أغرب الأشياء في العلم أن بعض الاكتشافات المهمة بدأت بملاحظات بسيطة جدًا. الفضول وطرح الأسئلة كانا دائمًا جزءًا من التقدم العلمي."
    },
    {
        "search": "city night people",
        "text": "هل تعلم أن المدن الحديثة تعتمد على آلاف الأنظمة الرقمية التي تعمل في الخلفية كل يوم؟ من إشارات المرور إلى شبكات الاتصال، التقنية أصبحت جزءًا أساسيًا من الحياة اليومية."
    },
]


def check_environment():
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY is missing")

    WORK_DIR.mkdir(exist_ok=True)


def search_pexels(query):
    url = "https://api.pexels.com/v1/videos/search"

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    params = {
        "query": query,
        "orientation": "portrait",
        "size": "medium",
        "per_page": 10,
        "locale": "en-US",
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json().get("videos", [])


def choose_video_file(video):
    files = video.get("video_files", [])

    portrait_files = []

    for file in files:
        width = file.get("width") or 0
        height = file.get("height") or 0

        if height >= width and width >= 500:
            portrait_files.append(file)

    if portrait_files:
        return max(
            portrait_files,
            key=lambda x: (x.get("width") or 0) * (x.get("height") or 0),
        )

    if files:
        return max(
            files,
            key=lambda x: (x.get("width") or 0) * (x.get("height") or 0),
        )

    return None


def download_video(url, destination):
    response = requests.get(
        url,
        stream=True,
        timeout=60,
    )

    response.raise_for_status()

    with open(destination, "wb") as file:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                file.write(chunk)


def create_voice(text):
    async def generate():
        communicate = edge_tts.Communicate(
            text,
            "ar-SA-HamedNeural",
        )
        await communicate.save(str(VOICE_FILE))

    asyncio.run(generate())


def create_video_with_ffmpeg(clips):
    concat_file = WORK_DIR / "concat.txt"

    with open(concat_file, "w", encoding="utf-8") as file:
        for clip in clips:
            absolute_path = clip.resolve()
            file.write(
                "file '" +
                str(absolute_path).replace("'", "'\\''") +
                "'\n"
            )

    silent_video = WORK_DIR / "silent.mp4"

    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-vf",
        (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920"
        ),
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        str(silent_video),
    ]

    subprocess.run(command, check=True)

    final_command = [
        "ffmpeg",
        "-y",
        "-i",
        str(silent_video),
        "-i",
        str(VOICE_FILE),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(OUTPUT_VIDEO),
    ]

    subprocess.run(final_command, check=True)


def main():
    check_environment()

    topic = random.choice(TOPICS)

    print(f"Selected topic: {topic['search']}")

    videos = search_pexels(topic["search"])

    if not videos:
        raise RuntimeError("No Pexels videos found")

    random.shuffle(videos)

    selected = []

    for video in videos:
        video_file = choose_video_file(video)

        if not video_file:
            continue

        selected.append(video_file["link"])

        if len(selected) == 4:
            break

    if not selected:
        raise RuntimeError("No usable video files found")

    clips = []

    for index, url in enumerate(selected):
        destination = WORK_DIR / f"clip_{index}.mp4"

        print(f"Downloading clip {index + 1}/{len(selected)}")

        download_video(url, destination)

        clips.append(destination)

    print("Creating Arabic narration...")
    create_voice(topic["text"])

    print("Creating vertical Short...")
    create_video_with_ffmpeg(clips)

    print(f"SUCCESS: {OUTPUT_VIDEO}")


if __name__ == "__main__":
    main()
