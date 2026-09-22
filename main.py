import asyncio
import json
import os
import random
import re
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

import requests
import edge_tts

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
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

USED_CLIPS_FILE = Path("used_pexels.json")
USED_CONTENT_FILE = Path("used_content.json")

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

NUMBER_OF_CLIPS = 9
CLIP_DURATION = 2.8
FPS = 30

VOICE_NAME = "ar-SA-HamedNeural"
VOICE_RATE = "+2%"
VOICE_VOLUME = "+0%"
VOICE_PITCH = "+0Hz"


YOUTUBE_PRIVACY = "public"
YOUTUBE_CATEGORY_ID = "17"
YOUTUBE_MADE_FOR_KIDS = False

# =========================================================
# CONTENT
# =========================================================

TOPICS = []

WIKIPEDIA_API = "https://ar.wikipedia.org/w/api.php"
WIKIPEDIA_RANDOM_BATCH = 20
WIKIPEDIA_MAX_ATTEMPTS = 12
WIKIPEDIA_MIN_EXTRACT_CHARS = 180
WIKIPEDIA_MAX_EXTRACT_CHARS = 650

# Conservative blacklist. Ambiguous candidates are rejected rather than published.
FORBIDDEN_TOPIC_TERMS = [
    "جنس", "جنسية", "جنسي", "إباحية", "اباحية", "إباحي", "عري", "عاري",
    "بورن", "دعارة", "بغاء", "اتجار جنسي", "اغتصاب", "تحرش جنسي",
    "استغلال جنسي", "مثلية", "مثلي", "مثليون", "شذوذ", "شاذ",
    "متحول جنسيا", "متحول جنسيًا", "تغيير الجنس", "هوية جنسية", "توجه جنسي",
    "ميول جنسية", "امرأة", "امرأه", "نساء", "النساء", "مرأة", "أنثى", "انثى",
    "أنثوية", "نسائي", "نسائية", "فتاة", "بنات", "زوجة", "زوجات", "حمل",
    "ولادة", "رضاعة", "حيض", "دورة شهرية",
    "سياسة", "سياسي", "سياسية", "حكومة", "برلمان", "انتخابات", "انتخاب",
    "رئيس الجمهورية", "رئيس الوزراء", "وزير", "حزب سياسي", "أحزاب", "حزب",
    "ديمقراطية", "ديموقراطية", "جمهورية", "مرشح", "مرشحة", "مجلس الشورى",
    "الكونغرس", "البيت الأبيض", "السلطة", "انقلاب", "ثورة سياسية", "أيديولوجيا",
    "سياسة خارجية", "علاقات دولية", "تصويت",
    "انتحار", "انتحاري", "إيذاء النفس", "ايذاء النفس", "إيذاء ذاتي", "جرح النفس",
    "محاولة انتحار", "تفكير انتحاري",
    "مخدر", "مخدرات", "هيروين", "كوكايين", "فنتانيل", "ميثامفيتامين", "ماريجوانا",
    "قنب هندي", "حشيش", "أفيون", "ترامادول", "إكستاسي", "كراك",
    "قمار", "مراهنات", "رهان", "كازينو", "يانصيب", "مقامرة",
    "سلاح ناري", "أسلحة نارية", "مسدس", "بندقية", "رشاش", "مدفع", "صاروخ",
    "قنبلة", "متفجرات", "تفجير", "عبوة ناسفة", "ذخيرة", "لغم", "سلاح كيميائي",
    "سلاح بيولوجي", "سلاح نووي", "أسلحة دمار شامل",
    "مجزرة", "مذبحة", "تعذيب", "قتل متسلسل", "قاتل متسلسل", "جريمة قتل",
    "تشويه جثث", "جثة", "جثث", "دماء", "بتر", "إعدام", "إعدامات",
    "سرقة", "سطو", "اختطاف", "خطف", "تهريب", "غسيل أموال", "تزوير", "قرصنة",
    "اختراق", "برمجيات خبيثة", "فيروس حاسوبي", "فدية إلكترونية", "ابتزاز",
    "تلوث إشعاعي", "مادة سامة", "سم قاتل", "سموم", "مواد سامة", "تحدي خطير",
]
FORBIDDEN_TOPIC_STEMS = [
    "إباح", "اباح", "جنس", "شذوذ", "مثلي", "متحول", "سياس", "انتخاب", "حكوم",
    "برلمان", "حزب", "مخدر", "قمار", "مراهن", "انتحار", "إيذاء", "ايذاء",
    "سلاح", "قنبلة", "متفجر", "تعذيب", "مجزرة", "مذبحة", "اختطاف", "خطف",
    "تهريب", "ابتزاز", "قرصنة", "سموم", "إعدام",
]


# GENERAL HELPERS
# =========================================================

def run_command(command):
    print("Running:", " ".join(str(x) for x in command))
    subprocess.run(command, check=True)


def command_output(command):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def check_binary(name):
    if shutil.which(name) is None:
        raise RuntimeError(f"Required program not found: {name}")


def check_environment():
    required = {
        "PEXELS_API_KEY": PEXELS_API_KEY,
        "YOUTUBE_CLIENT_ID": YOUTUBE_CLIENT_ID,
        "YOUTUBE_CLIENT_SECRET": YOUTUBE_CLIENT_SECRET,
        "YOUTUBE_REFRESH_TOKEN": YOUTUBE_REFRESH_TOKEN,
    }

    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError("Missing environment variables: " + ", ".join(missing))

    check_binary("ffmpeg")
    check_binary("ffprobe")

    WORK_DIR.mkdir(parents=True, exist_ok=True)


def clean_previous_files():
    print("Cleaning previous generated files...")

    for file in [OUTPUT_VIDEO, VOICE_FILE, SUBTITLE_FILE]:
        if file.exists():
            file.unlink()

    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)

    WORK_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# JSON MEMORY
# =========================================================

def load_json_list(path):
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except Exception as error:
        print(f"Warning: Could not read {path}: {error}")
        return []


def save_json_list(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")

    with open(temporary, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    temporary.replace(path)


def load_used_clips():
    return set(str(x) for x in load_json_list(USED_CLIPS_FILE))


def save_used_clips(used_clips):
    save_json_list(USED_CLIPS_FILE, sorted(used_clips))


def load_used_content():
    return load_json_list(USED_CONTENT_FILE)


def save_used_content(used_content):
    save_json_list(USED_CONTENT_FILE, used_content)


# =========================================================
# CONTENT MEMORY
# =========================================================

def normalize_content(text):
    text = str(text).lower()
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
    text = re.sub(r"[^\w\s\u0600-\u06FF]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def content_fingerprint(topic):
    return (
        normalize_content(topic.get("title", "")),
        normalize_content(topic.get("text", "")),
        normalize_content(topic.get("search", "")),
    )


def content_already_used(topic, used_content):
    title = normalize_content(topic.get("title", ""))
    text = normalize_content(topic.get("text", ""))
    search = normalize_content(topic.get("search", ""))

    for old in used_content:
        old_title = normalize_content(old.get("title", ""))
        old_text = normalize_content(old.get("text", ""))
        old_search = normalize_content(old.get("search", ""))

        if title and title == old_title:
            return True

        if text and text == old_text:
            return True

        if search and search == old_search:
            return True

    return False


def _topic_text_blob(topic):
    return normalize_content(" ".join([
        str(topic.get("title", "")), str(topic.get("text", "")),
        str(topic.get("search", "")),
        " ".join(str(x) for x in topic.get("fallback_searches", [])),
    ]))


def is_forbidden_topic(topic):
    """Conservative safety gate for every generated topic."""
    blob = _topic_text_blob(topic)
    if not blob:
        return True
    for term in FORBIDDEN_TOPIC_TERMS:
        if normalize_content(term) in blob:
            return True
    for stem in FORBIDDEN_TOPIC_STEMS:
        if normalize_content(stem) in blob:
            return True
    return False


def _topic_tokens(text):
    return {x for x in normalize_content(text).split() if len(x) >= 3}


def _topic_similarity(a, b):
    aa = _topic_tokens(_topic_text_blob(a))
    bb = _topic_tokens(_topic_text_blob(b))
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / len(aa | bb)


def topic_is_new(topic, used_content):
    if is_forbidden_topic(topic) or content_already_used(topic, used_content):
        return False
    for old in used_content:
        old_topic = {
            "title": old.get("title", ""), "text": old.get("text", ""),
            "search": old.get("search", ""),
            "fallback_searches": old.get("fallback_searches", []),
        }
        if _topic_similarity(topic, old_topic) >= 0.78:
            return False
    return True


def _clean_wikipedia_extract(text):
    text = re.sub(r"\[[^\]]*\]", "", str(text))
    return re.sub(r"\s+", " ", text).strip()


def _wikipedia_random_articles():
    params = {
        "action": "query", "format": "json", "generator": "random",
        "grnnamespace": 0, "grnlimit": WIKIPEDIA_RANDOM_BATCH,
        "prop": "extracts|info", "exintro": 1, "explaintext": 1,
        "exchars": WIKIPEDIA_MAX_EXTRACT_CHARS, "inprop": "url",
        "formatversion": 2,
    }
    response = requests.get(
        WIKIPEDIA_API, params=params,
        headers={"User-Agent": "YouTubeShortsAutomation/1.0"}, timeout=30,
    )
    response.raise_for_status()
    return response.json().get("query", {}).get("pages", [])


def _make_topic_from_wikipedia(page):
    title = _clean_wikipedia_extract(page.get("title", ""))
    extract = _clean_wikipedia_extract(page.get("extract", ""))
    if not title or len(extract) < WIKIPEDIA_MIN_EXTRACT_CHARS:
        return None
    sentences = [x.strip() for x in re.split(r"(?<=[.!؟])\s+", extract) if x.strip()]
    text = " ".join(sentences[:3]).strip()
    if len(text) > WIKIPEDIA_MAX_EXTRACT_CHARS:
        text = text[:WIKIPEDIA_MAX_EXTRACT_CHARS].rsplit(" ", 1)[0] + "."
    return {
        "search": title,
        "fallback_searches": [title, f"{title} documentary", f"{title} science"],
        "title": f"هل تعلم ما قصة {title}؟",
        "text": f"هل تعلم؟ {text}",
        "hashtags": ["#Shorts", "#هل_تعلم", "#معلومات", "#ويكيبيديا"],
        "wikipedia_title": title,
        "wikipedia_url": page.get("fullurl", ""),
    }


def get_fresh_wikipedia_topic(used_content):
    for attempt in range(1, WIKIPEDIA_MAX_ATTEMPTS + 1):
        print(f"Wikipedia search {attempt}/{WIKIPEDIA_MAX_ATTEMPTS}")
        try:
            pages = _wikipedia_random_articles()
        except Exception as error:
            print("Wikipedia request error:", error)
            continue
        random.shuffle(pages)
        for page in pages:
            topic = _make_topic_from_wikipedia(page)
            if topic is None:
                continue
            if not wikipedia_source_is_acceptable(topic):
                print("Rejected unsuitable Wikipedia page:", topic.get("title", ""))
                continue
            if not audit_and_accept_topic(topic, used_content):
                print("Rejected unsafe/duplicate Wikipedia topic:", topic.get("title", ""))
                continue
            return topic
    raise RuntimeError("NO SAFE NEW WIKIPEDIA TOPIC FOUND. No video will be published.")


def final_topic_safety_audit(topic):
    """Run every safety rule again immediately before the topic enters the pipeline."""
    required = ["title", "text", "search"]
    if any(not str(topic.get(key, "")).strip() for key in required):
        return False, "missing required topic field"
    if is_forbidden_topic(topic):
        return False, "forbidden subject detected"
    if len(normalize_content(topic.get("text", ""))) < 120:
        return False, "topic text too short"
    if len(normalize_content(topic.get("title", ""))) > 140:
        return False, "topic title too long"
    return True, "ok"


def wikipedia_source_is_acceptable(topic):
    """Reject pages that are not suitable factual source material."""
    title = normalize_content(topic.get("wikipedia_title", ""))
    url = str(topic.get("wikipedia_url", "")).lower()
    if not title:
        return False
    if url and "ar.wikipedia.org" not in url:
        return False
    blocked_namespace_terms = [
        "قائمة", "تصنيف", "بوابة", "مقالة توضيح", "صفحة توضيح",
        "سنوات", "أحداث جارية", "وفيات",
    ]
    return not any(term in title for term in blocked_namespace_terms)


def audit_and_accept_topic(topic, used_content):
    if not wikipedia_source_is_acceptable(topic):
        return False
    ok, reason = final_topic_safety_audit(topic)
    if not ok:
        print("Topic safety audit rejected candidate:", reason)
        return False
    if not topic_is_new(topic, used_content):
        print("Topic duplicate audit rejected candidate")
        return False
    return True


def select_new_topic(used_content):
    topic = get_fresh_wikipedia_topic(used_content)
    if not audit_and_accept_topic(topic, used_content):
        raise RuntimeError("FINAL SAFETY AUDIT FAILED. No video will be published.")
    print("\n================================")
    print("NEW SAFE WIKIPEDIA CONTENT SELECTED")
    print(topic["title"])
    print("Source: Arabic Wikipedia")
    print("================================\n")
    return topic


def remember_content(topic, video_id, used_content):
    used_content.append({
        "title": topic["title"],
        "text": topic["text"],
        "search": topic["search"],
        "fingerprint": list(content_fingerprint(topic)),
        "video_id": video_id,
        "saved_at": int(time.time()),
    })

    save_used_content(used_content)
    print(f"Content memory updated. Total: {len(used_content)}")


# =========================================================
# PEXELS
# =========================================================

def search_pexels(query, page=1):
    url = "https://api.pexels.com/v1/videos/search"

    headers = {"Authorization": PEXELS_API_KEY}

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

    return response.json().get("videos", [])


def choose_video_file(video):
    files = video.get("video_files", [])
    vertical = []

    for item in files:
        width = item.get("width") or 0
        height = item.get("height") or 0
        link = item.get("link")

        if not link:
            continue

        if height > width and width >= 500 and height >= 800:
            vertical.append(item)

    if vertical:
        return max(
            vertical,
            key=lambda item: (item.get("width") or 0) * (item.get("height") or 0),
        )

    # If Pexels returns no vertical file, accept a good landscape source.
    usable = [
        item for item in files
        if item.get("link") and (item.get("width") or 0) >= 640
    ]

    if usable:
        return max(
            usable,
            key=lambda item: (item.get("width") or 0) * (item.get("height") or 0),
        )

    return None


def build_visual_queries(topic):
    """Build concept-focused Pexels queries instead of generic repeated searches."""
    primary = clean_text(topic.get("search", ""))
    fallbacks = [
        clean_text(x)
        for x in topic.get("fallback_searches", [])
        if clean_text(x)
    ]

    queries = []
    for query in [primary] + fallbacks:
        if query and query.lower() not in {q.lower() for q in queries}:
            queries.append(query)

    # Ask for a few additional visual variants using the same subject.
    words = primary.split()
    if words:
        queries.extend([
            " ".join(words) + " close up",
            " ".join(words) + " slow motion",
            " ".join(words) + " cinematic",
        ])

    unique = []
    seen = set()
    for query in queries:
        key = query.lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(query)

    return unique[:7]


def select_unique_videos(topic, used_clips):
    search_queries = build_visual_queries(topic)
    candidates = {}

    for query in search_queries:
        print(f"Searching Pexels: {query}")

        for page in range(1, 4):
            try:
                videos = search_pexels(query, page)
            except Exception as error:
                print("Pexels search error:", error)
                continue

            for video in videos:
                video_id = str(video.get("id", ""))
                if not video_id or video_id in used_clips:
                    continue

                video_file = choose_video_file(video)
                if not video_file:
                    continue

                width = int(video_file.get("width") or video.get("width") or 0)
                height = int(video_file.get("height") or video.get("height") or 0)

                # Prefer large portrait sources. Keep a landscape fallback,
                # because forcing only portrait results can fail for niche topics.
                portrait = height > width
                resolution_score = min(width, 1080) * min(height, 1920)

                candidates[video_id] = {
                    "id": video_id,
                    "link": video_file["link"],
                    "width": width,
                    "height": height,
                    "portrait": portrait,
                    "score": (1000000000 if portrait else 0) + resolution_score,
                }

            if len(candidates) >= 60:
                break

        if len(candidates) >= max(NUMBER_OF_CLIPS * 4, 36):
            break

    candidates_list = list(candidates.values())

    # Keep variety: first rank by quality, then sample from the strongest pool
    # rather than blindly shuffling all results.
    candidates_list.sort(key=lambda item: item["score"], reverse=True)
    quality_pool = candidates_list[:max(NUMBER_OF_CLIPS * 4, 36)]
    random.shuffle(quality_pool)

    if len(quality_pool) < NUMBER_OF_CLIPS:
        raise RuntimeError(
            f"Not enough NEW Pexels clips. Found {len(quality_pool)}, "
            f"need {NUMBER_OF_CLIPS}."
        )

    selected = quality_pool[:NUMBER_OF_CLIPS]

    print("Selected NEW Pexels IDs:")
    for item in selected:
        print(" ", item["id"])

    return selected


def download_video(url, destination):
    print(f"Downloading: {destination}")

    response = requests.get(
        url,
        stream=True,
        timeout=120,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()

    with open(destination, "wb") as file:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                file.write(chunk)


# =========================================================
# NATURAL ARABIC SCRIPT STYLE
# =========================================================
# The project does not currently use an external generative-AI API for text.
# These rules make the existing verified scripts sound lighter and more
# conversational before they are sent to the voice engine, without changing
# the factual idea or the topic title.
NATURAL_ARABIC_STYLE = """
استخدم العربية السعودية الخفيفة والطبيعية، كأن شخصًا سعوديًا يتكلم مع المشاهد مباشرة.
خلك عفوي وواضح، واستخدم تعبيرات خفيفة مثل: تدري، تخيل، الغريب إن، والأغرب إن، بدون مبالغة.
تجنب الفصحى الرسمية والكلمات المعقدة قدر الإمكان.
خلي الكلام مفهومًا لجميع العرب، وليس بلهجة محلية صعبة.
الجمل قصيرة وسهلة النطق.
لا تستخدم إيموجي أو رموز داخل النص.
حافظ على المعلومة العلمية أو الواقعية كما هي، ولا تضف معلومة جديدة.
"""


def make_natural_arabic_script(text):
    """Lightly convert the existing Arabic script to a natural Saudi-style delivery."""
    text = clean_text(text)

    replacements = [
        ("هل تعلم أن", "تدري إن"),
        ("هل تعلم أن", "تدري إن"),
        ("هل تعلم", "تدري"),
        ("هل فكرت يومًا", "قد سألت نفسك"),
        ("هل تساءلت", "قد سألت نفسك"),
        ("هل لاحظت أن", "لاحظت إن"),
        ("هل لاحظت", "لاحظت"),
        ("يمكن أن", "ممكن"),
        ("لا يمكن", "ما يقدر"),
        ("يستطيع", "يقدر"),
        ("تستطيع", "تقدر"),
        ("يستطيعون", "يقدرون"),
        ("تستطيعون", "يقدرون"),
        ("يحتاج إلى", "يحتاج"),
        ("تحتاج إلى", "تحتاج"),
        ("ولهذا", "وعشان كذا"),
        ("لذلك", "وعشان كذا"),
        ("بسبب ذلك", "وعشان كذا"),
        ("بالنسبة إلى", "بالنسبة لـ"),
        ("داخل الجسم", "داخل الجسم"),
        ("في الوقت نفسه", "بنفس الوقت"),
        ("بشكل مستمر", "باستمرار"),
        ("بشكل كبير", "بشكل كبير"),
        ("بشكل مختلف", "بطريقة مختلفة"),
        ("بشكل أفضل", "بطريقة أفضل"),
        ("تدري أن", "تدري إن"),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    # Small spoken-language cleanup; do not rewrite facts or numbers.
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("، و", "، و")

    return text


def prepare_topic_for_voice(topic):
    """Return a copy with natural delivery text while preserving the original topic."""
    prepared = dict(topic)
    prepared["text"] = make_natural_arabic_script(topic.get("text", ""))
    return prepared


def create_voice(text):
    """Create the narration with free Edge Neural TTS."""
    print(f"Creating Edge Neural TTS voice: {VOICE_NAME}")

    async def generate():
        communicate = edge_tts.Communicate(
            text,
            VOICE_NAME,
            rate=VOICE_RATE,
            volume=VOICE_VOLUME,
            pitch=VOICE_PITCH,
        )
        await communicate.save(str(VOICE_FILE))

    asyncio.run(generate())

    if not VOICE_FILE.exists() or VOICE_FILE.stat().st_size < 1000:
        raise RuntimeError("Voice file was not created correctly.")

def get_audio_duration():
    result = command_output([
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(VOICE_FILE),
    ])

    duration = float(result)
    if duration <= 0:
        raise RuntimeError("Invalid audio duration.")

    return duration


# =========================================================
# SUBTITLES
# =========================================================

def clean_text(text):
    text = re.sub(r"\s+", " ", str(text))
    return text.strip()


def split_text_for_subtitles(text):
    """Split Arabic captions into balanced 1-2 line blocks like modern Shorts captions."""
    words = clean_text(text).split()
    parts = []
    current = []

    for word in words:
        candidate = " ".join(current + [word])

        if len(candidate) <= 23:
            current.append(word)
        else:
            if current:
                parts.append(" ".join(current))
            current = [word]

    if current:
        parts.append(" ".join(current))

    # Merge very short neighboring blocks when the result still fits.
    merged = []
    for part in parts:
        if merged and len(merged[-1]) + 1 + len(part) <= 23:
            merged[-1] = merged[-1] + " " + part
        else:
            merged.append(part)

    return merged


def make_caption_lines(text):
    """Create a balanced two-line caption without awkwardly splitting words."""
    text = clean_text(text)
    if len(text) <= 23:
        return text

    words = text.split()
    best = None
    best_score = None

    for i in range(1, len(words)):
        left = " ".join(words[:i])
        right = " ".join(words[i:])

        if len(left) > 23 or len(right) > 23:
            continue

        # Prefer two lines with similar visual length.
        score = abs(len(left) - len(right))
        if best_score is None or score < best_score:
            best = left + r"\N" + right
            best_score = score

    if best:
        return best

    # Fallback for unusually long text.
    return text


def highlight_caption(text):
    """Emphasize the final meaningful phrase in yellow, matching the reference style."""
    plain = text.replace(r"\N", " ")
    words = plain.split()
    if len(words) < 3:
        return text

    # Highlight the final 1-3 words; keep punctuation attached naturally.
    count = 2 if len(words) >= 4 else 1
    prefix = " ".join(words[:-count])
    emphasis = " ".join(words[-count:])

    if r"\N" in text:
        # Prefer highlighting the final line when it is already split.
        lines = text.split(r"\N", 1)
        last_line = lines[1].strip()
        last_words = last_line.split()
        if len(last_words) >= 2:
            count = min(2, len(last_words))
            normal_last = " ".join(last_words[:-count])
            yellow_last = " ".join(last_words[-count:])
            lines[1] = (
                normal_last + " " if normal_last else ""
            ) + r"{\c&H0000FFFF&}" + yellow_last + r"{\c&H00FFFFFF&}"
            return r"\N".join(lines)

    return (
        prefix + " " if prefix else ""
    ) + r"{\c&H0000FFFF&}" + emphasis + r"{\c&H00FFFFFF&}"


def ass_time(seconds):
    total_cs = max(0, int(round(seconds * 100)))
    hours, remainder = divmod(total_cs, 360000)
    minutes, remainder = divmod(remainder, 6000)
    seconds_value, centiseconds = divmod(remainder, 100)

    return f"{hours}:{minutes:02d}:{seconds_value:02d}.{centiseconds:02d}"


def escape_ass_text(text):
    return (
        str(text)
        .replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", " ")
    )


def create_subtitle_file(text, duration):
    parts = split_text_for_subtitles(text)

    if not parts:
        raise RuntimeError("Subtitle text is empty.")

    total_characters = sum(max(1, len(part)) for part in parts)

    # Modern Arabic Shorts caption style:
    # bold, large white text, thick black outline, subtle shadow,
    # semi-transparent black caption box, centered in the lower-safe area.
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Arabic,Noto Sans Arabic,68,&H00FFFFFF,&H00FFFFFF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,3,2,1,2,90,90,430,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    with open(SUBTITLE_FILE, "w", encoding="utf-8-sig") as file:
        file.write(ass_header)

        current_time = 0.0

        for index, part in enumerate(parts):
            part_duration = (max(1, len(part)) / total_characters) * duration

            start = current_time
            end = duration if index == len(parts) - 1 else min(
                duration,
                current_time + part_duration,
            )

            caption = make_caption_lines(part)
            caption = highlight_caption(caption)

            file.write(
                "Dialogue: 0,"
                f"{ass_time(start)},"
                f"{ass_time(end)},"
                "Arabic,,0,0,0,,"
                f"{caption}\n"
            )

            current_time = end


# =========================================================
# VIDEO PROCESSING
# =========================================================

def probe_video_duration(path):
    try:
        return float(command_output([
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]))
    except Exception:
        return 0.0


def prepare_clip(input_file, output_file, duration):
    source_duration = probe_video_duration(input_file)

    if source_duration <= duration + 0.2:
        start_time = 0
    else:
        max_start = max(0.0, source_duration - duration - 0.1)
        start_time = random.uniform(0, min(max_start, max(0.0, source_duration - duration)))

    # Very subtle crop/scale motion. It avoids the old static-photo feeling
    # while remaining natural on real footage.
    motion = random.choice([
        "scale=1120:1991:force_original_aspect_ratio=increase,crop=1080:1920:(iw-1080)/2:(ih-1920)/2",
        "scale=1160:2062:force_original_aspect_ratio=increase,crop=1080:1920:(iw-1080)/2:(ih-1920)/2",
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
    ])

    video_filter = (
        motion + ","
        "setsar=1,"
        "setdar=9/16,"
        "fps=30,"
        "format=yuv420p"
    )

    command = [
        "ffmpeg",
        "-y",
        "-ss", f"{start_time:.3f}",
        "-i", str(input_file),
        "-t", str(duration),
        "-vf", video_filter,
        "-an",
        "-r", str(FPS),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_file),
    ]

    run_command(command)


def create_concat_file(clips):
    concat_file = WORK_DIR / "concat.txt"

    with open(concat_file, "w", encoding="utf-8") as file:
        for clip in clips:
            path = clip.resolve()
            path_string = str(path).replace("'", "'\\''")
            file.write(f"file '{path_string}'\n")

    return concat_file


def create_silent_video(clips):
    concat_file = create_concat_file(clips)
    silent_video = WORK_DIR / "silent.mp4"

    command = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-an",
        "-movflags", "+faststart",
        str(silent_video),
    ]

    run_command(command)
    return silent_video


def create_final_video(silent_video, text):
    audio_duration = get_audio_duration()

    print(f"Audio duration: {audio_duration:.2f}s")

    # Make sure the visual track is never shorter than the voice.
    silent_duration = probe_video_duration(silent_video)

    if silent_duration < audio_duration:
        extra = audio_duration - silent_duration + 0.2
        print(f"Extending visual track by {extra:.2f}s")

        extended = WORK_DIR / "silent_extended.mp4"

        command = [
            "ffmpeg",
            "-y",
            "-stream_loop", "-1",
            "-i", str(silent_video),
            "-t", f"{audio_duration + 0.2:.3f}",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-r", str(FPS),
            str(extended),
        ]

        run_command(command)
        silent_video = extended

    create_subtitle_file(text, audio_duration)

    audio_filter = (
        "highpass=f=70,"
        "lowpass=f=15000,"
        "acompressor=threshold=-20dB:ratio=2.2:attack=10:release=100:makeup=1,"
        "loudnorm=I=-14:TP=-1.5:LRA=7"
    )

    subtitle_path = SUBTITLE_FILE.resolve().as_posix().replace(":", r"\:")
    subtitle_filter = f"ass='{subtitle_path}'"

    final_command = [
        "ffmpeg",
        "-y",
        "-i", str(silent_video),
        "-i", str(VOICE_FILE),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-vf", subtitle_filter,
        "-af", audio_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "160k",
        "-ar", "48000",
        "-shortest",
        "-movflags", "+faststart",
        str(OUTPUT_VIDEO),
    ]

    run_command(final_command)

    if not OUTPUT_VIDEO.exists() or OUTPUT_VIDEO.stat().st_size < 10000:
        raise RuntimeError("Final video was not created correctly.")

    print(f"Final video created: {OUTPUT_VIDEO}")


# =========================================================
# YOUTUBE AUTHENTICATION
# =========================================================

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
]


def get_youtube_credentials():
    credentials = Credentials(
        token=None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        scopes=YOUTUBE_SCOPES,
    )

    try:
        credentials.refresh(Request())
    except Exception as error:
        raise RuntimeError(
            "YouTube OAuth refresh failed. "
            "The refresh token may be expired/revoked or belong to a different OAuth client. "
            f"Original error: {error}"
        ) from error

    return credentials


def get_youtube_service():
    credentials = get_youtube_credentials()

    return build(
        "youtube",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )


# =========================================================
# YOUTUBE UPLOAD
# =========================================================

def build_video_title(topic):
    return topic["title"]


def build_video_description(topic):
    hashtags = " ".join(topic.get("hashtags", []))

    return (
        f"{topic['text']}\n\n"
        f"{hashtags}\n\n"
        "معلومات قصيرة وحقائق متنوعة بشكل مبسط.\n"
        "اشترك للمزيد من المقاطع."
    )


def upload_to_youtube(topic):
    if not OUTPUT_VIDEO.exists():
        raise RuntimeError("Output video does not exist.")

    youtube = get_youtube_service()

    title = build_video_title(topic)
    description = build_video_description(topic)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "categoryId": YOUTUBE_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": YOUTUBE_PRIVACY,
            "selfDeclaredMadeForKids": YOUTUBE_MADE_FOR_KIDS,
        },
    }

    print("Uploading to YouTube...")

    last_error = None

    for attempt in range(1, 4):
        try:
            media = MediaFileUpload(
                str(OUTPUT_VIDEO),
                mimetype="video/mp4",
                resumable=True,
                chunksize=4 * 1024 * 1024,
            )

            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            response = None

            while response is None:
                status, response = request.next_chunk()

                if status:
                    print(
                        f"Upload progress: "
                        f"{int(status.progress() * 100)}%"
                    )

            video_id = response.get("id")

            if not video_id:
                raise RuntimeError(
                    f"YouTube upload returned no video ID: {response}"
                )

            print(f"YouTube upload successful: {video_id}")
            print(f"https://www.youtube.com/shorts/{video_id}")

            return video_id

        except Exception as error:
            last_error = error
            print(f"Upload attempt {attempt}/3 failed: {error}")

            if attempt < 3:
                time.sleep(5 * attempt)

    raise RuntimeError(
        f"YouTube upload failed after 3 attempts: {last_error}"
    )


# =========================================================
# VALIDATION
# =========================================================

def validate_final_video():
    if not OUTPUT_VIDEO.exists():
        raise RuntimeError("short.mp4 does not exist.")

    duration = probe_video_duration(OUTPUT_VIDEO)

    if duration <= 0:
        raise RuntimeError("Could not read final video duration.")

    size_mb = OUTPUT_VIDEO.stat().st_size / (1024 * 1024)

    print("\nVIDEO CHECK")
    print(f"Duration: {duration:.2f}s")
    print(f"Size: {size_mb:.2f} MB")

    if duration < 1:
        raise RuntimeError("Video is too short.")

    return duration


# =========================================================
# MAIN PIPELINE
# =========================================================

def validate_topic_pool():
    """Compatibility check: static topic pool is disabled."""
    print("Static topic pool disabled: fresh topics come from Arabic Wikipedia.")
    print("Conservative safety blacklist enabled.")


def main():
    print("\n========================================")
    print("YOUTUBE SHORTS AUTOMATION - PROFESSIONAL MODE")
    print("========================================\n")

    check_environment()
    validate_topic_pool()

    used_content = load_used_content()
    used_clips = load_used_clips()

    topic = select_new_topic(used_content)

    clean_previous_files()

    selected_videos = select_unique_videos(
        topic,
        used_clips,
    )

    downloaded = []

    print("\nDownloading clips...")

    for index, item in enumerate(selected_videos, start=1):
        raw_file = WORK_DIR / f"raw_{index:02d}.mp4"
        prepared_file = WORK_DIR / f"clip_{index:02d}.mp4"

        download_video(
            item["link"],
            raw_file,
        )

        prepare_clip(
            raw_file,
            prepared_file,
            CLIP_DURATION,
        )

        downloaded.append(prepared_file)

    if len(downloaded) != NUMBER_OF_CLIPS:
        raise RuntimeError("Clip preparation count is incorrect.")

    print("\nCreating silent video...")
    silent_video = create_silent_video(downloaded)

    # Keep the stored topic unchanged for duplicate detection and YouTube metadata,
    # but use a lighter Saudi conversational version for narration and captions.
    voice_topic = prepare_topic_for_voice(topic)

    print("\nCreating Arabic voice...")
    create_voice(voice_topic["text"])

    print("\nCreating final Short...")
    create_final_video(
        silent_video,
        voice_topic["text"],
    )

    validate_final_video()

    print("\nUploading...")
    video_id = upload_to_youtube(topic)

    # Only remember the content and Pexels clips AFTER a successful upload.
    for item in selected_videos:
        used_clips.add(str(item["id"]))

    save_used_clips(used_clips)
    remember_content(
        topic,
        video_id,
        used_content,
    )

    print("\n========================================")
    print("DONE")
    print(f"Video ID: {video_id}")
    print(f"Used Pexels clips remembered: {len(used_clips)}")
    print(f"Used content items remembered: {len(used_content)}")
    print("========================================")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.")
        raise
    except Exception as error:
        print("\n========================================")
        print("AUTOMATION FAILED")
        print("========================================")
        print(type(error).__name__ + ":", error)
        raise
