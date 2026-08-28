import asyncio
import os
import random
import shutil
import subprocess
from pathlib import Path

import requests
import edge_tts

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# =========================================================
# SETTINGS
# =========================================================

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN")

OUTPUT_VIDEO = Path("short.mp4")
VOICE_FILE = Path("voice.mp3")
WORK_DIR = Path("clips")
SUBTITLE_FILE = Path("subtitles.ass")

# Shorts الحقيقي
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# عدد اللقطات
NUMBER_OF_CLIPS = 8

# مدة كل لقطة
CLIP_DURATION = 6


# =========================================================
# TOPICS
# =========================================================

TOPICS = [
    {
        "search": "technology artificial intelligence",
        "title": "هل تعلم كيف أصبح الذكاء الاصطناعي جزءًا من حياتنا؟",
        "text": (
            "هل تعلم أن الذكاء الاصطناعي أصبح جزءًا من حياتنا اليومية أكثر مما نتوقع؟ "
            "فهو يستخدم اليوم في تحليل كميات ضخمة من المعلومات، ومساعدة الشركات على اتخاذ القرارات، "
            "وتطوير التطبيقات والخدمات التي نستخدمها كل يوم. "
            "والأمر المثير للاهتمام أن تطور هذه التقنية لا يعتمد فقط على سرعة أجهزة الكمبيوتر، "
            "بل يعتمد أيضًا على قدرتها على فهم الأنماط الموجودة في البيانات. "
            "ولهذا السبب أصبح الذكاء الاصطناعي من أكثر التقنيات تأثيرًا في العالم."
        ),
    },
    {
        "search": "football stadium players",
        "title": "هل تعلم كيف أصبحت البيانات جزءًا من كرة القدم؟",
        "text": (
            "هل تعلم أن كرة القدم الحديثة أصبحت تعتمد على البيانات بشكل كبير؟ "
            "فالفرق المحترفة لا تكتفي بمشاهدة المباراة فقط، "
            "بل تستخدم أنظمة تحليل متقدمة لدراسة حركة اللاعبين وسرعة الجري ودقة التمرير. "
            "ويمكن للمدربين استخدام هذه المعلومات لمعرفة نقاط القوة والضعف، "
            "وتحسين طريقة اللعب قبل المباريات القادمة. "
            "ولهذا أصبحت البيانات عنصرًا مهمًا في كرة القدم الحديثة إلى جانب المهارة والخبرة."
        ),
    },
    {
        "search": "modern cars driving road",
        "title": "هل تعلم أن السيارة الحديثة أصبحت جهازًا ذكيًا؟",
        "text": (
            "هل تعلم أن السيارة الحديثة أصبحت أقرب إلى جهاز ذكي متحرك؟ "
            "فالعديد من السيارات الجديدة تحتوي على أنظمة تستطيع مراقبة الطريق، "
            "وتنبيه السائق عند وجود خطر، ومساعدته في مواقف مختلفة أثناء القيادة. "
            "وتستخدم هذه الأنظمة مجموعة من الكاميرات والمستشعرات لمعرفة ما يحدث حول السيارة. "
            "ومع استمرار تطور التقنية، أصبحت أنظمة مساعدة السائق أكثر انتشارًا في السيارات الجديدة."
        ),
    },
    {
        "search": "science laboratory technology",
        "title": "لماذا تبدأ الاكتشافات العلمية بسؤال بسيط؟",
        "text": (
            "من المثير للاهتمام أن كثيرًا من الاكتشافات العلمية بدأت بملاحظة بسيطة جدًا. "
            "فالعلماء لا يبحثون دائمًا عن إجابة جاهزة، بل يبدأون غالبًا بسؤال: لماذا يحدث هذا؟ "
            "ثم تأتي مرحلة التجارب وجمع البيانات ومقارنة النتائج. "
            "ومع تطور الأجهزة والتقنيات، أصبح بإمكان العلماء دراسة أشياء كانت مستحيلة المراقبة في الماضي. "
            "ولهذا فإن الفضول وطرح الأسئلة ما زالا من أهم أسباب التقدم العلمي."
        ),
    },
    {
        "search": "modern city night people",
        "title": "كم نظامًا يعمل خلف المدن الحديثة؟",
        "text": (
            "هل فكرت يومًا في كمية الأنظمة التي تعمل خلف المدن الحديثة؟ "
            "إشارات المرور، وشبكات الاتصال، وأنظمة المواصلات، والخدمات الرقمية، "
            "كلها تعمل معًا بشكل مستمر حتى تبدو الحياة اليومية طبيعية وسلسة. "
            "والأغرب أن معظم هذه الأنظمة تعمل في الخلفية دون أن نلاحظها. "
            "ومع زيادة عدد السكان وتطور المدن، أصبحت التقنية عنصرًا أساسيًا في إدارة الحياة اليومية."
        ),
    },
]


# =========================================================
# BASIC FUNCTIONS
# =========================================================

def run_command(command):
    print("Running:", " ".join(str(x) for x in command))

    subprocess.run(
        command,
        check=True,
    )


def check_environment():

    required = {
        "PEXELS_API_KEY": PEXELS_API_KEY,
        "YOUTUBE_CLIENT_ID": YOUTUBE_CLIENT_ID,
        "YOUTUBE_CLIENT_SECRET": YOUTUBE_CLIENT_SECRET,
        "YOUTUBE_REFRESH_TOKEN": YOUTUBE_REFRESH_TOKEN,
    }

    for name, value in required.items():

        if not value:
            raise RuntimeError(
                f"{name} is missing"
            )

    WORK_DIR.mkdir(
        exist_ok=True
    )


def clean_previous_files():

    print("Cleaning previous files...")

    for file in [
        OUTPUT_VIDEO,
        VOICE_FILE,
        SUBTITLE_FILE,
    ]:

        if file.exists():
            file.unlink()

    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)

    WORK_DIR.mkdir(
        exist_ok=True
    )


# =========================================================
# PEXELS
# =========================================================

def search_pexels(query):

    url = "https://api.pexels.com/v1/videos/search"

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    params = {
        "query": query,
        "orientation": "portrait",
        "size": "medium",
        "per_page": 20,
        "locale": "en-US",
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json().get(
        "videos",
        []
    )


def choose_video_file(video):

    files = video.get(
        "video_files",
        []
    )

    usable = []

    for file in files:

        width = file.get("width") or 0
        height = file.get("height") or 0
        link = file.get("link")

        if not link:
            continue

        # نفضّل الفيديو العمودي الحقيقي
        if height > width and width >= 500:
            usable.append(file)

    if usable:

        return max(
            usable,
            key=lambda x:
                (x.get("width") or 0)
                *
                (x.get("height") or 0)
        )

    # إذا لم يوجد عمودي، نأخذ أفضل ملف متاح
    if files:

        return max(
            files,
            key=lambda x:
                (x.get("width") or 0)
                *
                (x.get("height") or 0)
        )

    return None


def download_video(url, destination):

    print(
        f"Downloading: {destination}"
    )

    response = requests.get(
        url,
        stream=True,
        timeout=60,
    )

    response.raise_for_status()

    with open(
        destination,
        "wb"
    ) as file:

        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):

            if chunk:
                file.write(chunk)


# =========================================================
# VOICE
# =========================================================

def create_voice(text):

    async def generate():

        communicate = edge_tts.Communicate(
            text,
            "ar-SA-HamedNeural",
            rate="-6%",
            volume="+0%",
            pitch="+0Hz",
        )

        await communicate.save(
            str(VOICE_FILE)
        )

    asyncio.run(
        generate()
    )


# =========================================================
# AUDIO DURATION
# =========================================================

def get_audio_duration():

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(VOICE_FILE),
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )

    return float(
        result.stdout.strip()
    )


# =========================================================
# SUBTITLES
# =========================================================

def split_text_for_subtitles(text):

    sentences = []

    current = ""

    for word in text.split():

        if not current:

            current = word
            continue

        if (
            len(current)
            + len(word)
            + 1
            <= 34
        ):

            current += " " + word

        else:

            sentences.append(
                current
            )

            current = word

    if current:
        sentences.append(
            current
        )

    return sentences


def ass_time(seconds):

    hours = int(seconds // 3600)

    minutes = int(
        (seconds % 3600) // 60
    )

    secs = seconds % 60

    whole_seconds = int(secs)

    centiseconds = int(
        round(
            (secs - whole_seconds)
            * 100
        )
    )

    if centiseconds >= 100:

        whole_seconds += 1
        centiseconds = 0

    if whole_seconds >= 60:

        minutes += 1
        whole_seconds = 0

    if minutes >= 60:

        hours += 1
        minutes = 0

    return (
        f"{hours}:"
        f"{minutes:02d}:"
        f"{whole_seconds:02d}."
        f"{centiseconds:02d}"
    )


def create_subtitle_file(text, duration):

    parts = split_text_for_subtitles(text)

    if not parts:
        return

    total_characters = sum(
        len(part)
        for part in parts
    )

    current_time = 0.0

    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Arabic,Arial,58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,70,70,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    with open(
        SUBTITLE_FILE,
        "w",
        encoding="utf-8-sig",
    ) as file:

        file.write(
            ass_header
        )

        for part in parts:

            part_duration = (
                len(part)
                / total_characters
            ) * duration

            start = current_time

            end = min(
                current_time + part_duration,
                duration
            )

            subtitle_text = (
                part
                .replace("\n", " ")
                .replace("{", "\\{")
                .replace("}", "\\}")
            )

            line = (
                "Dialogue: 0,"
                f"{ass_time(start)},"
                f"{ass_time(end)},"
                "Arabic,,"
                "0,0,0,,"
                f"{subtitle_text}\n"
            )

            file.write(
                line
            )

            current_time = end


# =========================================================
# VIDEO PROCESSING
# =========================================================

def prepare_clip(
    input_file,
    output_file,
    duration,
):

    # بداية عشوائية بسيطة حتى لا نأخذ نفس الجزء دائمًا
    start_time = random.uniform(
        0,
        1.5
    )

    # =====================================================
    # مهم جدًا:
    #
    # لا نستخدم scale=1080:1920 مباشرة
    # لأنه قد يشوّه الفيديو إذا كانت أبعاده مختلفة.
    #
    # نكبّر الفيديو مع الحفاظ على نسبة العرض/الارتفاع،
    # ثم نقص الزائد فقط.
    #
    # النتيجة دائمًا:
    # 1080x1920
    # 9:16
    # بدون ضغط للصورة.
    # =====================================================

    video_filter = (
        "scale="
        f"{VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
        "force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
        "(in_w-out_w)/2:"
        "(in_h-out_h)/2,"
        "setsar=1,"
        "setdar=9/16"
    )

    command = [
        "ffmpeg",
        "-y",

        "-ss",
        str(start_time),

        "-i",
        str(input_file),

        "-t",
        str(duration),

        "-vf",
        video_filter,

        # FPS ثابت مناسب لليوتيوب
        "-r",
        "30",

        "-an",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "20",

        "-pix_fmt",
        "yuv420p",

        "-movflags",
        "+faststart",

        str(output_file),
    ]

    run_command(
        command
    )


def create_concat_file(clips):

    concat_file = (
        WORK_DIR /
        "concat.txt"
    )

    with open(
        concat_file,
        "w",
        encoding="utf-8"
    ) as file:

        for clip in clips:

            absolute_path = clip.resolve()

            safe_path = str(
                absolute_path
            ).replace(
                "'",
                "'\\''"
            )

            file.write(
                f"file '{safe_path}'\n"
            )

    return concat_file


def create_silent_video(clips):

    concat_file = (
        create_concat_file(
            clips
        )
    )

    silent_video = (
        WORK_DIR /
        "silent.mp4"
    )

    command = [
        "ffmpeg",
        "-y",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        str(concat_file),

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "20",

        "-pix_fmt",
        "yuv420p",

        "-r",
        "30",

        "-an",

        "-movflags",
        "+faststart",

        str(silent_video),
    ]

    run_command(
        command
    )

    return silent_video


# =========================================================
# FINAL VIDEO
# =========================================================

def create_final_video(
    silent_video,
    text,
):

    audio_duration = (
        get_audio_duration()
    )

    print(
        f"Audio duration: "
        f"{audio_duration:.2f} seconds"
    )

    print(
        "Creating Arabic subtitles..."
    )

    create_subtitle_file(
        text,
        audio_duration
    )

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

        "-vf",
        f"ass={SUBTITLE_FILE.as_posix()}",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        # جودة أعلى من النسخة السابقة
        "-crf",
        "20",

        "-pix_fmt",
        "yuv420p",

        "-r",
        "30",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-ar",
        "44100",

        "-af",
        (
            "loudnorm="
            "I=-16:"
            "TP=-1.5:"
            "LRA=11"
        ),

        "-shortest",

        "-movflags",
        "+faststart",

        str(OUTPUT_VIDEO),
    ]

    run_command(
        final_command
    )


# =========================================================
# YOUTUBE UPLOAD
# =========================================================

def upload_to_youtube(
    title,
    description,
):

    print()
    print("================================")
    print("Uploading Short to YouTube...")
    print("================================")

    scopes = [
        "https://www.googleapis.com/auth/youtube.upload"
    ]

    credentials = Credentials(
        token=None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        scopes=scopes,
    )

    youtube = build(
        "youtube",
        "v3",
        credentials=credentials
    )

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "22",
        },

        "status": {
            # PUBLIC
            "privacyStatus": "public",

            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(OUTPUT_VIDEO),
        mimetype="video/mp4",
        resumable=True,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None

    while response is None:

        status, response = (
            request.next_chunk()
        )

        if status:

            progress = int(
                status.progress()
                * 100
            )

            print(
                f"Upload progress: "
                f"{progress}%"
            )

    video_id = response.get(
        "id"
    )

    if not video_id:

        raise RuntimeError(
            "YouTube upload completed "
            "but no video ID was returned."
        )

    print()
    print("================================")
    print("YOUTUBE UPLOAD SUCCESS")
    print(f"Video ID: {video_id}")
    print("Privacy: PUBLIC")
    print(
        f"https://www.youtube.com/watch?v={video_id}"
    )
    print("================================")

    return video_id


# =========================================================
# MAIN
# =========================================================

def main():

    check_environment()

    clean_previous_files()

    # -----------------------------------------------------
    # اختيار موضوع
    # -----------------------------------------------------

    topic = random.choice(
        TOPICS
    )

    print(
        f"Selected topic: "
        f"{topic['search']}"
    )

    # -----------------------------------------------------
    # SEARCH PEXELS
    # -----------------------------------------------------

    print(
        "Searching Pexels..."
    )

    videos = search_pexels(
        topic["search"]
    )

    if not videos:

        raise RuntimeError(
            "No Pexels videos found"
        )

    random.shuffle(
        videos
    )

    # -----------------------------------------------------
    # SELECT
    # -----------------------------------------------------

    selected = []

    used_ids = set()

    for video in videos:

        video_id = video.get(
            "id"
        )

        if video_id in used_ids:
            continue

        video_file = (
            choose_video_file(
                video
            )
        )

        if not video_file:
            continue

        selected.append(
            video_file["link"]
        )

        used_ids.add(
            video_id
        )

        if len(selected) >= NUMBER_OF_CLIPS:
            break

    if len(selected) < 4:

        raise RuntimeError(
            "Not enough usable "
            "video files found"
        )

    print(
        f"Selected {len(selected)} clips"
    )

    # -----------------------------------------------------
    # DOWNLOAD
    # -----------------------------------------------------

    downloaded = []

    for index, url in enumerate(
        selected
    ):

        destination = (
            WORK_DIR /
            f"source_{index}.mp4"
        )

        download_video(
            url,
            destination
        )

        downloaded.append(
            destination
        )

    # -----------------------------------------------------
    # VOICE
    # -----------------------------------------------------

    print(
        "Creating Arabic narration..."
    )

    create_voice(
        topic["text"]
    )

    # -----------------------------------------------------
    # PREPARE CLIPS
    # -----------------------------------------------------

    print(
        "Preparing 9:16 Shorts clips..."
    )

    prepared_clips = []

    for index, source in enumerate(
        downloaded
    ):

        output = (
            WORK_DIR /
            f"clip_{index}.mp4"
        )

        prepare_clip(
            source,
            output,
            CLIP_DURATION
        )

        prepared_clips.append(
            output
        )

    # -----------------------------------------------------
    # BUILD VIDEO
    # -----------------------------------------------------

    print(
        "Joining clips..."
    )

    silent_video = (
        create_silent_video(
            prepared_clips
        )
    )

    # -----------------------------------------------------
    # AUDIO + SUBTITLES
    # -----------------------------------------------------

    print(
        "Adding narration and subtitles..."
    )

    create_final_video(
        silent_video,
        topic["text"]
    )

    # -----------------------------------------------------
    # CHECK
    # -----------------------------------------------------

    if not OUTPUT_VIDEO.exists():

        raise RuntimeError(
            "Video was not created"
        )

    file_size = (
        OUTPUT_VIDEO.stat().st_size
        /
        (1024 * 1024)
    )

    print()
    print("================================")
    print("VIDEO CREATED SUCCESSFULLY")
    print(f"Video: {OUTPUT_VIDEO}")
    print(f"Size: {file_size:.2f} MB")
    print("Format: 1080x1920 (9:16)")
    print("Arabic subtitles added")
    print("================================")

    # -----------------------------------------------------
    # YOUTUBE UPLOAD
    # -----------------------------------------------------

    description = (
        topic["text"]
        +
        "\n\n"
        "#Shorts #معلومات #هل_تعلم"
    )

    upload_to_youtube(
        topic["title"],
        description
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    main()
