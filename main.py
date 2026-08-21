import asyncio
from pathlib import Path
import edge_tts

TEXT = """
هل تعلم أن بعض السيارات الحديثة تستطيع تحديث أنظمتها وبرامجها
عن بُعد دون الحاجة إلى زيارة مركز الصيانة؟
هذه التقنية أصبحت جزءًا مهمًا من تطور السيارات الذكية.
"""

OUTPUT = Path("voice.mp3")


async def create_voice():
    voice = "ar-SA-HamedNeural"
    communicate = edge_tts.Communicate(TEXT, voice)
    await communicate.save(str(OUTPUT))


asyncio.run(create_voice())

print(f"Voice created: {OUTPUT}")
