import asyncio
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont
from moviepy import AudioFileClip, ImageClip

TEXT = (
    "هل تعلم أن بعض السيارات الحديثة تستطيع تحديث أنظمتها "
    "وبرامجها عن بُعد دون الحاجة إلى زيارة مركز الصيانة؟ "
    "هذه التقنية أصبحت جزءًا مهمًا من تطور السيارات الذكية."
)

VOICE = "ar-SA-HamedNeural"

AUDIO_FILE = Path("voice.mp3")
IMAGE_FILE = Path("short.png")
VIDEO_FILE = Path("short.mp4")


async def create_voice():
    communicate = edge_tts.Communicate(TEXT, VOICE)
    await communicate.save(str(AUDIO_FILE))


def create_image():
    width, height = 1080, 1920

    image = Image.new("RGB", (width, height), "black")
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            58,
        )
    except Exception:
        font = ImageFont.load_default()

    lines = [
        "هل تعلم؟",
        "",
        "بعض السيارات الحديثة",
        "تستطيع تحديث أنظمتها",
        "وبرامجها عن بُعد!",
        "",
        "هذه التقنية أصبحت",
        "جزءًا من تطور",
        "السيارات الذكية."
    ]

    y = 500

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]

        x = (width - text_width) // 2

        draw.text(
            (x, y),
            line,
            font=font,
            fill="white",
        )

        y += 100

    image.save(IMAGE_FILE)


def create_video():
    audio = AudioFileClip(str(AUDIO_FILE))

    video = ImageClip(str(IMAGE_FILE)).with_duration(
        audio.duration
    ).with_audio(audio)

    video.write_videofile(
        str(VIDEO_FILE),
        fps=30,
        codec="libx264",
        audio_codec="aac",
    )

    audio.close()
    video.close()


async def main():
    print("Creating Arabic voice...")
    await create_voice()

    print("Creating vertical image...")
    create_image()

    print("Creating Short video...")
    create_video()

    print(f"Video created successfully: {VIDEO_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
