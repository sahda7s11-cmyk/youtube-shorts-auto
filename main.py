import asyncio
import os
import random
import shutil
import subprocess
from pathlib import Path

import requests
import edge_tts


# =========================================================
# SETTINGS
# =========================================================

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

OUTPUT_VIDEO = Path("short.mp4")
VOICE_FILE = Path("voice.mp3")
WORK_DIR = Path("clips")

# ملف الترجمة
SUBTITLE_FILE = Path("subtitles.ass")

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# عدد اللقطات
NUMBER_OF_CLIPS = 8

# مدة كل لقطة تقريبية
CLIP_DURATION = 6


# =========================================================
# TOPICS
# =========================================================

TOPICS = [
    {
        "search": "technology artificial intelligence",
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
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY is missing")

    WORK_DIR.mkdir(
        exist_ok=True
    )


def clean_previous_files():
    print("Cleaning previous files...")

    if OUTPUT_VIDEO.exists():
        OUTPUT_VIDEO.unlink()

    if VOICE_FILE.exists():
        VOICE_FILE.unlink()

    if SUBTITLE_FILE.exists():
        SUBTITLE_FILE.unlink()

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

        # نفضل الفيديو العمودي
        if height >= width and width >= 500:
            usable.append(file)

    if usable:
        return max(
            usable,
            key=lambda x:
                (x.get("width") or 0)
                *
                (x.get("height") or 0)
        )

    # إذا لم نجد عموديًا نستخدم أفضل ملف متاح
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
    print(f"Downloading: {destination}")

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
# SUBTITLE FUNCTIONS
# =========================================================

def split_text_for_subtitles(text):
    """
    يقسم النص إلى أجزاء قصيرة مناسبة للعرض على الشاشة.
    """

    # تقسيم أولي حسب الجمل
    sentences = []

    current = ""

    for word in text.split():

        if not current:
            current = word
            continue

        # الحد الأقصى لعدد الأحرف في السطر
        if len(current) + len(word) + 1 <= 34:
            current += " " + word

        else:
            sentences.append(current)
            current = word

    if current:
        sentences.append(current)

    return sentences


def ass_time(seconds):
    """
    تحويل الثواني إلى صيغة ASS:
    H:MM:SS.cc
    """

    hours = int(seconds // 3600)

    minutes = int(
        (seconds % 3600) // 60
    )

    secs = seconds % 60

    whole_seconds = int(secs)

    centiseconds = int(
        round(
            (secs - whole_seconds) * 100
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
    """
    إنشاء ترجمة عربية متزامنة تقريبياً مع الصوت.
    """

    parts = split_text_for_subtitles(text)

    if not parts:
        return

    total_characters = sum(
        len(part)
        for part in parts
    )

    current_time = 0.0

    # -----------------------------------------------------
    # شكل الترجمة
    # -----------------------------------------------------

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

        for index, part in enumerate(parts):

            # مدة هذا الجزء حسب عدد الأحرف
            if total_characters > 0:
                part_duration = (
                    len(part)
                    /
                    total_characters
                ) * duration
            else:
                part_duration = (
                    duration / len(parts)
                )

            start = current_time

            end = (
                current_time
                +
                part_duration
            )

            # منع تجاوز مدة الصوت
            end = min(
                end,
                duration
            )

            # تنظيف بعض الرموز التي قد تسبب مشكلة في ASS
            subtitle_text = (
                part
                .replace(
                    "\n",
                    " "
                )
                .replace(
                    "{",
                    "\\{"
                )
                .replace(
                    "}",
                    "\\}"
                )
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
    """
    يحول كل لقطة إلى فيديو عمودي موحد.
    يتم استخدام crop بدل تمديد الصورة حتى لا يبدو الفيديو مشوهًا.
    """

    # بداية عشوائية بسيطة للقطعة
    start_time = random.uniform(
        0,
        1.5
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
        (
            "scale="
            f"{VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
            "force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
            "setsar=1"
        ),

        "-r",
        "30",

        "-an",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "21",

        "-pix_fmt",
        "yuv420p",

        str(output_file),
    ]

    run_command(
        command
    )


def create_concat_file(clips):

    concat_file = WORK_DIR / "concat.txt"

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

    concat_file = create_concat_file(
        clips
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
        "21",

        "-pix_fmt",
        "yuv420p",

        "-r",
        "30",

        "-an",

        str(silent_video),
    ]

    run_command(
        command
    )

    return silent_video


# =========================================================
# AUDIO + VIDEO + SUBTITLES
# =========================================================

def create_final_video(
    silent_video,
    text,
):
    """
    يضيف الصوت والترجمة إلى الفيديو.

    الصوت هو المرجع النهائي للمدة.
    """

    # -----------------------------------------------------
    # معرفة مدة الصوت
    # -----------------------------------------------------

    audio_duration = get_audio_duration()

    print(
        f"Audio duration: "
        f"{audio_duration:.2f} seconds"
    )

    # -----------------------------------------------------
    # إنشاء ملف الترجمة
    # -----------------------------------------------------

    print(
        "Creating Arabic subtitles..."
    )

    create_subtitle_file(
        text,
        audio_duration
    )

    # -----------------------------------------------------
    # إضافة الترجمة والصوت
    # -----------------------------------------------------

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

        # حرق الترجمة داخل الفيديو
        "-vf",
        f"ass={SUBTITLE_FILE.as_posix()}",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "21",

        "-pix_fmt",
        "yuv420p",

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
# MAIN
# =========================================================

def main():

    check_environment()

    clean_previous_files()

    # اختيار موضوع
    topic = random.choice(
        TOPICS
    )

    print(
        f"Selected topic: "
        f"{topic['search']}"
    )

    # -----------------------------------------------------
    # SEARCH
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

        video_file = choose_video_file(
            video
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
            "Not enough usable video files found"
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
        "Preparing realistic Short clips..."
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

    silent_video = create_silent_video(
        prepared_clips
    )

    # -----------------------------------------------------
    # ADD VOICE + SUBTITLES
    # -----------------------------------------------------

    print(
        "Adding narration and subtitles..."
    )

    create_final_video(
        silent_video,
        topic["text"]
    )

    # -----------------------------------------------------
    # RESULT
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
    print(
        "================================"
    )
    print(
        "SUCCESS"
    )
    print(
        f"Video: {OUTPUT_VIDEO}"
    )
    print(
        f"Size: {file_size:.2f} MB"
    )
    print(
        "Arabic subtitles added"
    )
    print(
        "================================"
    )


if __name__ == "__main__":
    main()
