import asyncio
import json
import os
import random
import re
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
SUBTITLE_FILE = Path("subtitles.ass")
WORK_DIR = Path("clips")

# ذاكرة المقاطع المستخدمة سابقًا
USED_CLIPS_FILE = Path("used_pexels.json")

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# عدد اللقطات
NUMBER_OF_CLIPS = 7

# مدة كل لقطة
CLIP_DURATION = 3.2


# =========================================================
# TOPICS
# =========================================================

TOPICS = [
    {
        "search": "football stadium match players",
        "fallback_searches": [
            "football match stadium",
            "soccer stadium players",
            "football players action",
            "soccer game",
        ],
        "title": "هل تعلم لماذا أصبحت البيانات مهمة جدًا في كرة القدم؟",
        "text": (
            "هل تعلم أن كرة القدم الحديثة أصبحت تعتمد على البيانات بشكل مذهل؟ "
            "المدربون اليوم يستطيعون تحليل سرعة اللاعب وعدد تمريراته "
            "ومساحاته داخل الملعب وحتى تحركات الفريق بالكامل. "
            "هذه البيانات تساعد المدرب على اكتشاف نقاط القوة والضعف "
            "وقد تغيّر طريقة لعب الفريق في المباراة التالية. "
            "كرة القدم لم تعد تعتمد على المهارة فقط، "
            "بل أصبحت البيانات جزءًا مهمًا منها."
        ),
        "hashtags": [
            "#Shorts",
            "#كرة_القدم",
            "#هل_تعلم",
            "#معلومات",
            "#Football",
            "#Soccer",
            "#رياضة",
        ],
    },

    {
        "search": "football player training stadium",
        "fallback_searches": [
            "soccer training",
            "football training",
            "football player running",
            "soccer players training",
        ],
        "title": "هل تعلم كم يركض لاعب كرة القدم في المباراة؟",
        "text": (
            "هل فكرت يومًا كم يركض لاعب كرة القدم خلال مباراة واحدة؟ "
            "اللاعب المحترف قد يقطع عدة كيلومترات أثناء المباراة، "
            "لكن المثير أن المسافة ليست كل شيء. "
            "فاللاعب يغيّر سرعته باستمرار بين المشي والركض والجري السريع. "
            "ولهذا تحتاج كرة القدم الحديثة إلى لياقة عالية "
            "وسرعة كبيرة في اتخاذ القرار."
        ),
        "hashtags": [
            "#Shorts",
            "#كرة_القدم",
            "#هل_تعلم",
            "#معلومات_رياضية",
            "#Football",
            "#Soccer",
            "#رياضة",
        ],
    },

    {
        "search": "football goalkeeper goal match",
        "fallback_searches": [
            "soccer goalkeeper save",
            "football goalkeeper",
            "goalkeeper training",
            "soccer goal keeper",
        ],
        "title": "لماذا يبدو حارس المرمى أسرع مما تتوقع؟",
        "text": (
            "هل تعلم أن رد فعل حارس المرمى يحدث خلال جزء صغير جدًا من الثانية؟ "
            "الحارس لا يعتمد على سرعة يديه فقط، "
            "بل يقرأ وضعية اللاعب واتجاه جسمه قبل التسديدة. "
            "ولهذا يبدأ أحيانًا بالتحرك قبل أن تصل الكرة إليه. "
            "في المستوى الاحترافي، جزء من الثانية قد يصنع الفرق."
        ),
        "hashtags": [
            "#Shorts",
            "#كرة_القدم",
            "#حراس_المرمى",
            "#هل_تعلم",
            "#Football",
            "#Soccer",
            "#رياضة",
        ],
    },

    {
        "search": "football fans stadium crowd",
        "fallback_searches": [
            "soccer fans stadium",
            "football crowd",
            "football stadium fans",
            "soccer supporters",
        ],
        "title": "هل تعلم لماذا تختلف أجواء ملاعب كرة القدم؟",
        "text": (
            "هل لاحظت أن بعض ملاعب كرة القدم تبدو مختلفة تمامًا من ناحية الأجواء؟ "
            "التصميم وحجم المدرجات وطريقة توزيع الجماهير "
            "كلها تؤثر في تجربة المشجعين داخل الملعب. "
            "ولهذا أصبحت بعض الملاعب الحديثة مصممة لتكون تجربة كاملة، "
            "وليس مجرد مكان لمشاهدة المباراة."
        ),
        "hashtags": [
            "#Shorts",
            "#كرة_القدم",
            "#جماهير",
            "#ملاعب",
            "#هل_تعلم",
            "#Football",
            "#Soccer",
        ],
    },

    {
        "search": "football training player running",
        "fallback_searches": [
            "soccer training player",
            "football skills training",
            "soccer ball training",
            "football practice",
        ],
        "title": "لماذا يتدرب لاعبو كرة القدم على أشياء تبدو بسيطة؟",
        "text": (
            "هل تعلم أن أبسط المهارات في كرة القدم تحتاج إلى تكرار هائل؟ "
            "التمرير واستلام الكرة والتحرك بدون كرة "
            "كلها مهارات يتدرب عليها اللاعبون باستمرار حتى تصبح تلقائية. "
            "وعندما تصل المباراة إلى لحظة حاسمة، "
            "يحتاج اللاعب إلى تنفيذ المهارة بسرعة دون تردد."
        ),
        "hashtags": [
            "#Shorts",
            "#كرة_القدم",
            "#تدريب",
            "#هل_تعلم",
            "#Football",
            "#Soccer",
            "#رياضة",
        ],
    },

    {
        "search": "football goal stadium match",
        "fallback_searches": [
            "soccer goal",
            "football scoring goal",
            "soccer striker",
            "football match goal",
        ],
        "title": "هل تعلم لماذا يصعب تسجيل الهدف في كرة القدم؟",
        "text": (
            "تسجيل الهدف في كرة القدم ليس مجرد تسديدة قوية. "
            "اللاعب يحتاج إلى اختيار المكان والتوقيت والزاوية المناسبة "
            "خلال ثوانٍ قليلة. "
            "ولهذا قد تكون اللمسة الأخيرة أهم من قوة التسديدة نفسها. "
            "وفي المباريات الكبيرة، قرار واحد سريع قد يغيّر النتيجة بالكامل."
        ),
        "hashtags": [
            "#Shorts",
            "#كرة_القدم",
            "#أهداف",
            "#هل_تعلم",
            "#Football",
            "#Soccer",
            "#رياضة",
        ],
    },

    {
        "search": "space earth science",
        "fallback_searches": [
            "earth space",
            "planet earth",
            "space universe",
            "solar system",
        ],
        "title": "هل تعلم أنك تتحرك الآن رغم أنك جالس؟",
        "text": (
            "هل تعلم أنك تتحرك الآن بسرعة هائلة رغم أنك جالس في مكانك؟ "
            "الأرض تدور حول نفسها، وفي الوقت نفسه تتحرك حول الشمس. "
            "والنظام الشمسي نفسه يتحرك داخل مجرة درب التبانة. "
            "وهذا يعني أننا في حركة مستمرة، "
            "حتى عندما نشعر أننا ثابتون تمامًا."
        ),
        "hashtags": [
            "#Shorts",
            "#هل_تعلم",
            "#علوم",
            "#معلومات",
            "#فضاء",
            "#Science",
        ],
    },
]


# =========================================================
# BASIC FUNCTIONS
# =========================================================

def run_command(command):

    print(
        "Running:",
        " ".join(str(x) for x in command)
    )

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

    print(
        "Cleaning previous files..."
    )

    for file in [
        OUTPUT_VIDEO,
        VOICE_FILE,
        SUBTITLE_FILE,
    ]:

        if file.exists():

            file.unlink()

    if WORK_DIR.exists():

        shutil.rmtree(
            WORK_DIR
        )

    WORK_DIR.mkdir(
        exist_ok=True
    )


# =========================================================
# MEMORY
# =========================================================

def load_used_clips():

    if not USED_CLIPS_FILE.exists():

        return set()

    try:

        with open(
            USED_CLIPS_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if isinstance(
            data,
            list
        ):

            return set(
                str(x)
                for x in data
            )

    except Exception as error:

        print(
            "Warning: Could not read "
            "used_pexels.json:",
            error
        )

    return set()


def save_used_clips(
    used_clips
):

    with open(
        USED_CLIPS_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            sorted(
                list(
                    used_clips
                )
            ),
            file,
            ensure_ascii=False,
            indent=2,
        )


# =========================================================
# PEXELS
# =========================================================

def search_pexels(
    query,
    page=1,
):

    url = (
        "https://api.pexels.com/v1/videos/search"
    )

    headers = {
        "Authorization":
        PEXELS_API_KEY
    }

    params = {
        "query": query,
        "orientation": "portrait",
        "size": "medium",
        "per_page": 80,
        "page": page,
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


def choose_video_file(
    video
):

    files = video.get(
        "video_files",
        []
    )

    vertical = []

    for video_file in files:

        width = (
            video_file.get("width")
            or 0
        )

        height = (
            video_file.get("height")
            or 0
        )

        link = video_file.get(
            "link"
        )

        if not link:
            continue

        if (
            height > width
            and width >= 500
            and height >= 800
        ):

            vertical.append(
                video_file
            )

    if vertical:

        return max(
            vertical,
            key=lambda item:
            (
                item.get("width")
                or 0
            )
            *
            (
                item.get("height")
                or 0
            )
        )

    return None


def select_unique_videos(
    topic,
    used_clips
):

    search_queries = [
        topic["search"]
    ] + topic.get(
        "fallback_searches",
        []
    )

    candidates = {}

    for query in search_queries:

        print(
            f"Searching Pexels: {query}"
        )

        for page in range(
            1,
            4
        ):

            try:

                videos = search_pexels(
                    query,
                    page
                )

            except Exception as error:

                print(
                    "Pexels search error:",
                    error
                )

                continue

            for video in videos:

                video_id = str(
                    video.get(
                        "id",
                        ""
                    )
                )

                if not video_id:
                    continue

                # منع استخدام أي مقطع سابق
                if video_id in used_clips:
                    continue

                video_file = choose_video_file(
                    video
                )

                if not video_file:
                    continue

                candidates[
                    video_id
                ] = {
                    "id": video_id,
                    "link": video_file[
                        "link"
                    ],
                }

            if len(candidates) >= 30:
                break

        if len(candidates) >= 14:
            break

    candidates_list = list(
        candidates.values()
    )

    random.shuffle(
        candidates_list
    )

    if len(candidates_list) < NUMBER_OF_CLIPS:

        raise RuntimeError(
            "Not enough NEW Pexels clips found. "
            f"Found {len(candidates_list)}, "
            f"need {NUMBER_OF_CLIPS}."
        )

    selected = candidates_list[
        :NUMBER_OF_CLIPS
    ]

    print(
        "Selected NEW Pexels IDs:"
    )

    for item in selected:

        print(
            f"  {item['id']}"
        )

    return selected


# =========================================================
# DOWNLOAD
# =========================================================

def download_video(
    url,
    destination
):

    print(
        f"Downloading: {destination}"
    )

    response = requests.get(
        url,
        stream=True,
        timeout=90,
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

                file.write(
                    chunk
                )


# =========================================================
# VOICE
# =========================================================

def create_voice(
    text
):

    async def generate():

        communicate = edge_tts.Communicate(
            text,
            "ar-SA-HamedNeural",
            rate="+5%",
            volume="+0%",
            pitch="+0Hz",
        )

        await communicate.save(
            str(
                VOICE_FILE
            )
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

def clean_text(
    text
):

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def split_text_for_subtitles(
    text
):

    words = clean_text(
        text
    ).split()

    parts = []
    current = []

    for word in words:

        candidate = " ".join(
            current + [word]
        )

        if len(candidate) <= 27:

            current.append(
                word
            )

        else:

            if current:

                parts.append(
                    " ".join(
                        current
                    )
                )

            current = [
                word
            ]

    if current:

        parts.append(
            " ".join(
                current
            )
        )

    return parts


def ass_time(
    seconds
):

    hours = int(
        seconds // 3600
    )

    minutes = int(
        (seconds % 3600)
        // 60
    )

    remaining = (
        seconds
        - hours * 3600
        - minutes * 60
    )

    whole_seconds = int(
        remaining
    )

    centiseconds = int(
        round(
            (
                remaining
                - whole_seconds
            )
            * 100
        )
    )

    if centiseconds >= 100:

        whole_seconds += 1
        centiseconds = 0

    return (
        f"{hours}:"
        f"{minutes:02d}:"
        f"{whole_seconds:02d}."
        f"{centiseconds:02d}"
    )


def create_subtitle_file(
    text,
    duration,
):

    parts = split_text_for_subtitles(
        text
    )

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
Style: Arabic,Arial,64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,5,2,2,60,60,270,1

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
                /
                total_characters
            ) * duration

            start = current_time

            end = min(
                current_time
                + part_duration,
                duration
            )

            subtitle_text = (
                part
                .replace(
                    "{",
                    "\\{"
                )
                .replace(
                    "}",
                    "\\}"
                )
            )

            file.write(
                "Dialogue: 0,"
                f"{ass_time(start)},"
                f"{ass_time(end)},"
                "Arabic,,"
                "0,0,0,,"
                f"{subtitle_text}\n"
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

    start_time = random.uniform(
        0,
        1.2
    )

    # =====================================================
    # IMPORTANT FIX
    #
    # نجعل الفيديو يغطي كامل مساحة 1080x1920 أولًا،
    # ثم نقص الزائد.
    #
    # هذا يمنع خطأ:
    # Invalid too big or non positive size
    #
    # مع المقاطع التي نسبتها ليست 9:16 بالضبط.
    # =====================================================

    video_filter = (
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
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

        "-an",

        "-r",
        "30",

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "18",

        "-pix_fmt",
        "yuv420p",

        "-movflags",
        "+faststart",

        str(output_file),
    ]

    run_command(
        command
    )


def create_concat_file(
    clips
):

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

            absolute_path = (
                clip.resolve()
            )

            safe_path = (
                str(
                    absolute_path
                )
                .replace(
                    "'",
                    "'\\''"
                )
            )

            file.write(
                f"file '{safe_path}'\n"
            )

    return concat_file


def create_silent_video(
    clips
):

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
        str(
            concat_file
        ),

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "18",

        "-pix_fmt",
        "yuv420p",

        "-r",
        "30",

        "-an",

        "-movflags",
        "+faststart",

        str(
            silent_video
        ),
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
        f"{audio_duration:.2f}s"
    )

    create_subtitle_file(
        text,
        audio_duration
    )

    # =====================================================
    # AUDIO
    # بدون موسيقى
    # =====================================================

    audio_filter = (
        "highpass=f=70,"
        "lowpass=f=14000,"
        "acompressor="
        "threshold=-18dB:"
        "ratio=2:"
        "attack=15:"
        "release=120,"
        "loudnorm="
        "I=-15:"
        "TP=-1.5:"
        "LRA=8"
    )

    final_command = [
        "ffmpeg",
        "-y",

        "-i",
        str(
            silent_video
        ),

        "-i",
        str(
            VOICE_FILE
        ),

        "-map",
        "0:v:0",

        "-map",
        "1:a:0",

        "-vf",
        f"ass={SUBTITLE_FILE.as_posix()}",

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "18",

        "-pix_fmt",
        "yuv420p",

        "-r",
        "30",

        "-c:a",
        "aac",

        "-b:a",
        "160k",

        "-ar",
        "44100",

        "-af",
        audio_filter,

        "-shortest",

        "-movflags",
        "+faststart",

        str(
            OUTPUT_VIDEO
        ),
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
    print(
        "================================"
    )
    print(
        "Uploading to YouTube..."
    )
    print(
        "================================"
    )

    scopes = [
        "https://www.googleapis.com/auth/youtube.upload"
    ]

    credentials = Credentials(
        token=None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        token_uri=(
            "https://oauth2.googleapis.com/token"
        ),
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
            "categoryId": "17",
        },

        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(
            OUTPUT_VIDEO
        ),
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
    print(
        "================================"
    )
    print(
        "YOUTUBE UPLOAD SUCCESS"
    )
    print(
        f"Video ID: {video_id}"
    )
    print(
        "Privacy: PUBLIC"
    )
    print(
        "================================"
    )

    return video_id


# =========================================================
# MAIN
# =========================================================

def main():

    check_environment()

    clean_previous_files()

    # -----------------------------------------------------
    # تحميل ذاكرة المقاطع السابقة
    # -----------------------------------------------------

    used_clips = load_used_clips()

    print(
        f"Previously used Pexels clips: "
        f"{len(used_clips)}"
    )

    # -----------------------------------------------------
    # اختيار موضوع
    # -----------------------------------------------------

    topic = random.choice(
        TOPICS
    )

    print()
    print(
        "Selected topic:"
    )

    print(
        topic["title"]
    )

    # -----------------------------------------------------
    # PEXELS SEARCH
    # -----------------------------------------------------

    print()
    print(
        "Searching for NEW Pexels clips..."
    )

    selected = select_unique_videos(
        topic,
        used_clips
    )

    # -----------------------------------------------------
    # IDs التي سيستخدمها هذا الفيديو
    #
    # لا نضيفها للذاكرة الدائمة الآن.
    # سيتم حفظها فقط بعد نجاح الرفع.
    # -----------------------------------------------------

    current_video_ids = set(
        item["id"]
        for item in selected
    )

    # -----------------------------------------------------
    # DOWNLOAD
    # -----------------------------------------------------

    downloaded = []

    for index, item in enumerate(
        selected
    ):

        destination = (
            WORK_DIR /
            f"source_{index}.mp4"
        )

        download_video(
            item["link"],
            destination
        )

        downloaded.append(
            destination
        )

    # -----------------------------------------------------
    # VOICE
    # -----------------------------------------------------

    print()
    print(
        "Creating Arabic narration..."
    )

    create_voice(
        topic["text"]
    )

    # -----------------------------------------------------
    # PREPARE CLIPS
    # -----------------------------------------------------

    print()
    print(
        "Preparing professional "
        "vertical clips..."
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
    # JOIN
    # -----------------------------------------------------

    print()
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

    print()
    print(
        "Adding narration and subtitles..."
    )

    create_final_video(
        silent_video,
        topic["text"]
    )

    # -----------------------------------------------------
    # FINAL CHECK
    # -----------------------------------------------------

    if not OUTPUT_VIDEO.exists():

        raise RuntimeError(
            "short.mp4 was not created."
        )

    file_size = (
        OUTPUT_VIDEO.stat().st_size
        /
        (1024 * 1024)
    )

    print()
    print(
        "================================"
    )
    print(
        "VIDEO CREATED SUCCESSFULLY"
    )
    print(
        f"Size: {file_size:.2f} MB"
    )
    print(
        "Resolution: 1080x1920"
    )
    print(
        "Aspect ratio: 9:16"
    )
    print(
        "FPS: 30"
    )
    print(
        "CRF: 18"
    )
    print(
        "Music: OFF"
    )
    print(
        "Arabic subtitles: ON"
    )
    print(
        "NEW PEXELS CLIPS: YES"
    )
    print(
        "================================"
    )

    # -----------------------------------------------------
    # DESCRIPTION
    # -----------------------------------------------------

    hashtags = " ".join(
        topic["hashtags"]
    )

    description = (
        topic["text"]
        + "\n\n"
        + hashtags
    )

    # -----------------------------------------------------
    # UPLOAD
    # -----------------------------------------------------

    video_id = upload_to_youtube(
        topic["title"],
        description
    )

    # -----------------------------------------------------
    # حفظ الذاكرة بعد نجاح الرفع فقط
    # -----------------------------------------------------

    if video_id:

        used_clips.update(
            current_video_ids
        )

        save_used_clips(
            used_clips
        )

        print()
        print(
            "Pexels memory updated "
            "after successful YouTube upload."
        )

        print(
            f"Total remembered clips: "
            f"{len(used_clips)}"
        )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    main()
