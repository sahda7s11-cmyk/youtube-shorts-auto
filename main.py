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
VOICE_RATE = "+0%"
VOICE_VOLUME = "+0%"
VOICE_PITCH = "+0Hz"

# Strict automotive-mechanics visual mode. Generic car footage is never accepted.
AUTOMOTIVE_MECHANICS_ONLY = True
STRICT_VISUAL_MIN_SCORE = 7
# Optional professional voice. If these two secrets exist, Azure Neural Speech
# is used directly; otherwise the existing Edge-TTS voice remains the fallback.
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
AZURE_VOICE_NAME = os.getenv("AZURE_VOICE_NAME", "ar-SA-HamedNeural")

YOUTUBE_PRIVACY = "public"
YOUTUBE_CATEGORY_ID = "17"
YOUTUBE_MADE_FOR_KIDS = False

# =========================================================
# CONTENT
# =========================================================

TOPICS = [
    {'search': 'piston engine cylinder', 'fallback_searches': ['piston engine cylinder close up', 'piston engine cylinder internal mechanism'], 'title': 'كيف يعمل المكبس', 'text': 'كيف يعمل المكبس داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'piston engine cylinder', 'fallback_searches': ['piston engine cylinder close up', 'piston engine cylinder internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق المكبس', 'text': 'يحتاج المكبس إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'piston engine cylinder', 'fallback_searches': ['piston engine cylinder close up', 'piston engine cylinder internal mechanism'], 'title': 'كيف تنتقل القوة فيه المكبس', 'text': 'توضح آلية المكبس كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'piston engine cylinder', 'fallback_searches': ['piston engine cylinder close up', 'piston engine cylinder internal mechanism'], 'title': 'كيف تتأثر حرارته المكبس', 'text': 'تتأثر حرارة المكبس بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'piston engine cylinder', 'fallback_searches': ['piston engine cylinder close up', 'piston engine cylinder internal mechanism'], 'title': 'ما الذي يحدث داخله المكبس', 'text': 'داخل المكبس تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'piston rings engine', 'fallback_searches': ['piston rings engine close up', 'piston rings engine internal mechanism'], 'title': 'كيف يعمل حلقات المكبس', 'text': 'كيف يعمل حلقات المكبس داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'piston rings engine', 'fallback_searches': ['piston rings engine close up', 'piston rings engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق حلقات المكبس', 'text': 'يحتاج حلقات المكبس إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'piston rings engine', 'fallback_searches': ['piston rings engine close up', 'piston rings engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه حلقات المكبس', 'text': 'توضح آلية حلقات المكبس كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'piston rings engine', 'fallback_searches': ['piston rings engine close up', 'piston rings engine internal mechanism'], 'title': 'كيف تتأثر حرارته حلقات المكبس', 'text': 'تتأثر حرارة حلقات المكبس بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'piston rings engine', 'fallback_searches': ['piston rings engine close up', 'piston rings engine internal mechanism'], 'title': 'ما الذي يحدث داخله حلقات المكبس', 'text': 'داخل حلقات المكبس تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'connecting rod engine', 'fallback_searches': ['connecting rod engine close up', 'connecting rod engine internal mechanism'], 'title': 'كيف يعمل ذراع التوصيل', 'text': 'كيف يعمل ذراع التوصيل داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'connecting rod engine', 'fallback_searches': ['connecting rod engine close up', 'connecting rod engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق ذراع التوصيل', 'text': 'يحتاج ذراع التوصيل إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'connecting rod engine', 'fallback_searches': ['connecting rod engine close up', 'connecting rod engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه ذراع التوصيل', 'text': 'توضح آلية ذراع التوصيل كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'connecting rod engine', 'fallback_searches': ['connecting rod engine close up', 'connecting rod engine internal mechanism'], 'title': 'كيف تتأثر حرارته ذراع التوصيل', 'text': 'تتأثر حرارة ذراع التوصيل بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'connecting rod engine', 'fallback_searches': ['connecting rod engine close up', 'connecting rod engine internal mechanism'], 'title': 'ما الذي يحدث داخله ذراع التوصيل', 'text': 'داخل ذراع التوصيل تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'crankshaft engine', 'fallback_searches': ['crankshaft engine close up', 'crankshaft engine internal mechanism'], 'title': 'كيف يعمل عمود المرفق', 'text': 'كيف يعمل عمود المرفق داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'crankshaft engine', 'fallback_searches': ['crankshaft engine close up', 'crankshaft engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق عمود المرفق', 'text': 'يحتاج عمود المرفق إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'crankshaft engine', 'fallback_searches': ['crankshaft engine close up', 'crankshaft engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه عمود المرفق', 'text': 'توضح آلية عمود المرفق كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'crankshaft engine', 'fallback_searches': ['crankshaft engine close up', 'crankshaft engine internal mechanism'], 'title': 'كيف تتأثر حرارته عمود المرفق', 'text': 'تتأثر حرارة عمود المرفق بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'crankshaft engine', 'fallback_searches': ['crankshaft engine close up', 'crankshaft engine internal mechanism'], 'title': 'ما الذي يحدث داخله عمود المرفق', 'text': 'داخل عمود المرفق تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'crankshaft bearings engine', 'fallback_searches': ['crankshaft bearings engine close up', 'crankshaft bearings engine internal mechanism'], 'title': 'كيف يعمل محامل عمود المرفق', 'text': 'كيف يعمل محامل عمود المرفق داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'crankshaft bearings engine', 'fallback_searches': ['crankshaft bearings engine close up', 'crankshaft bearings engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق محامل عمود المرفق', 'text': 'يحتاج محامل عمود المرفق إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'crankshaft bearings engine', 'fallback_searches': ['crankshaft bearings engine close up', 'crankshaft bearings engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه محامل عمود المرفق', 'text': 'توضح آلية محامل عمود المرفق كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'crankshaft bearings engine', 'fallback_searches': ['crankshaft bearings engine close up', 'crankshaft bearings engine internal mechanism'], 'title': 'كيف تتأثر حرارته محامل عمود المرفق', 'text': 'تتأثر حرارة محامل عمود المرفق بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'crankshaft bearings engine', 'fallback_searches': ['crankshaft bearings engine close up', 'crankshaft bearings engine internal mechanism'], 'title': 'ما الذي يحدث داخله محامل عمود المرفق', 'text': 'داخل محامل عمود المرفق تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'flywheel engine', 'fallback_searches': ['flywheel engine close up', 'flywheel engine internal mechanism'], 'title': 'كيف يعمل دولاب الموازنة', 'text': 'كيف يعمل دولاب الموازنة داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'flywheel engine', 'fallback_searches': ['flywheel engine close up', 'flywheel engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق دولاب الموازنة', 'text': 'يحتاج دولاب الموازنة إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'flywheel engine', 'fallback_searches': ['flywheel engine close up', 'flywheel engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه دولاب الموازنة', 'text': 'توضح آلية دولاب الموازنة كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'flywheel engine', 'fallback_searches': ['flywheel engine close up', 'flywheel engine internal mechanism'], 'title': 'كيف تتأثر حرارته دولاب الموازنة', 'text': 'تتأثر حرارة دولاب الموازنة بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'flywheel engine', 'fallback_searches': ['flywheel engine close up', 'flywheel engine internal mechanism'], 'title': 'ما الذي يحدث داخله دولاب الموازنة', 'text': 'داخل دولاب الموازنة تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'camshaft engine', 'fallback_searches': ['camshaft engine close up', 'camshaft engine internal mechanism'], 'title': 'كيف يعمل عمود الكامات', 'text': 'كيف يعمل عمود الكامات داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'camshaft engine', 'fallback_searches': ['camshaft engine close up', 'camshaft engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق عمود الكامات', 'text': 'يحتاج عمود الكامات إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'camshaft engine', 'fallback_searches': ['camshaft engine close up', 'camshaft engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه عمود الكامات', 'text': 'توضح آلية عمود الكامات كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'camshaft engine', 'fallback_searches': ['camshaft engine close up', 'camshaft engine internal mechanism'], 'title': 'كيف تتأثر حرارته عمود الكامات', 'text': 'تتأثر حرارة عمود الكامات بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'camshaft engine', 'fallback_searches': ['camshaft engine close up', 'camshaft engine internal mechanism'], 'title': 'ما الذي يحدث داخله عمود الكامات', 'text': 'داخل عمود الكامات تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine valves cylinder head', 'fallback_searches': ['engine valves cylinder head close up', 'engine valves cylinder head internal mechanism'], 'title': 'كيف يعمل الصمامات', 'text': 'كيف يعمل الصمامات داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine valves cylinder head', 'fallback_searches': ['engine valves cylinder head close up', 'engine valves cylinder head internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق الصمامات', 'text': 'يحتاج الصمامات إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine valves cylinder head', 'fallback_searches': ['engine valves cylinder head close up', 'engine valves cylinder head internal mechanism'], 'title': 'كيف تنتقل القوة فيه الصمامات', 'text': 'توضح آلية الصمامات كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine valves cylinder head', 'fallback_searches': ['engine valves cylinder head close up', 'engine valves cylinder head internal mechanism'], 'title': 'كيف تتأثر حرارته الصمامات', 'text': 'تتأثر حرارة الصمامات بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine valves cylinder head', 'fallback_searches': ['engine valves cylinder head close up', 'engine valves cylinder head internal mechanism'], 'title': 'ما الذي يحدث داخله الصمامات', 'text': 'داخل الصمامات تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'valve seats cylinder head', 'fallback_searches': ['valve seats cylinder head close up', 'valve seats cylinder head internal mechanism'], 'title': 'كيف يعمل مقاعد الصمامات', 'text': 'كيف يعمل مقاعد الصمامات داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'valve seats cylinder head', 'fallback_searches': ['valve seats cylinder head close up', 'valve seats cylinder head internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق مقاعد الصمامات', 'text': 'يحتاج مقاعد الصمامات إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'valve seats cylinder head', 'fallback_searches': ['valve seats cylinder head close up', 'valve seats cylinder head internal mechanism'], 'title': 'كيف تنتقل القوة فيه مقاعد الصمامات', 'text': 'توضح آلية مقاعد الصمامات كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'valve seats cylinder head', 'fallback_searches': ['valve seats cylinder head close up', 'valve seats cylinder head internal mechanism'], 'title': 'كيف تتأثر حرارته مقاعد الصمامات', 'text': 'تتأثر حرارة مقاعد الصمامات بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'valve seats cylinder head', 'fallback_searches': ['valve seats cylinder head close up', 'valve seats cylinder head internal mechanism'], 'title': 'ما الذي يحدث داخله مقاعد الصمامات', 'text': 'داخل مقاعد الصمامات تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'valve guides cylinder head', 'fallback_searches': ['valve guides cylinder head close up', 'valve guides cylinder head internal mechanism'], 'title': 'كيف يعمل أدلة الصمامات', 'text': 'كيف يعمل أدلة الصمامات داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'valve guides cylinder head', 'fallback_searches': ['valve guides cylinder head close up', 'valve guides cylinder head internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق أدلة الصمامات', 'text': 'يحتاج أدلة الصمامات إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'valve guides cylinder head', 'fallback_searches': ['valve guides cylinder head close up', 'valve guides cylinder head internal mechanism'], 'title': 'كيف تنتقل القوة فيه أدلة الصمامات', 'text': 'توضح آلية أدلة الصمامات كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'valve guides cylinder head', 'fallback_searches': ['valve guides cylinder head close up', 'valve guides cylinder head internal mechanism'], 'title': 'كيف تتأثر حرارته أدلة الصمامات', 'text': 'تتأثر حرارة أدلة الصمامات بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'valve guides cylinder head', 'fallback_searches': ['valve guides cylinder head close up', 'valve guides cylinder head internal mechanism'], 'title': 'ما الذي يحدث داخله أدلة الصمامات', 'text': 'داخل أدلة الصمامات تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'hydraulic lifters engine', 'fallback_searches': ['hydraulic lifters engine close up', 'hydraulic lifters engine internal mechanism'], 'title': 'كيف يعمل رافعات الصمامات', 'text': 'كيف يعمل رافعات الصمامات داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'hydraulic lifters engine', 'fallback_searches': ['hydraulic lifters engine close up', 'hydraulic lifters engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق رافعات الصمامات', 'text': 'يحتاج رافعات الصمامات إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'hydraulic lifters engine', 'fallback_searches': ['hydraulic lifters engine close up', 'hydraulic lifters engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه رافعات الصمامات', 'text': 'توضح آلية رافعات الصمامات كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'hydraulic lifters engine', 'fallback_searches': ['hydraulic lifters engine close up', 'hydraulic lifters engine internal mechanism'], 'title': 'كيف تتأثر حرارته رافعات الصمامات', 'text': 'تتأثر حرارة رافعات الصمامات بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'hydraulic lifters engine', 'fallback_searches': ['hydraulic lifters engine close up', 'hydraulic lifters engine internal mechanism'], 'title': 'ما الذي يحدث داخله رافعات الصمامات', 'text': 'داخل رافعات الصمامات تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'rocker arms engine', 'fallback_searches': ['rocker arms engine close up', 'rocker arms engine internal mechanism'], 'title': 'كيف يعمل أذرع الروكر', 'text': 'كيف يعمل أذرع الروكر داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'rocker arms engine', 'fallback_searches': ['rocker arms engine close up', 'rocker arms engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق أذرع الروكر', 'text': 'يحتاج أذرع الروكر إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'rocker arms engine', 'fallback_searches': ['rocker arms engine close up', 'rocker arms engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه أذرع الروكر', 'text': 'توضح آلية أذرع الروكر كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'rocker arms engine', 'fallback_searches': ['rocker arms engine close up', 'rocker arms engine internal mechanism'], 'title': 'كيف تتأثر حرارته أذرع الروكر', 'text': 'تتأثر حرارة أذرع الروكر بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'rocker arms engine', 'fallback_searches': ['rocker arms engine close up', 'rocker arms engine internal mechanism'], 'title': 'ما الذي يحدث داخله أذرع الروكر', 'text': 'داخل أذرع الروكر تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'timing chain engine', 'fallback_searches': ['timing chain engine close up', 'timing chain engine internal mechanism'], 'title': 'كيف يعمل سلسلة التوقيت', 'text': 'كيف يعمل سلسلة التوقيت داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'timing chain engine', 'fallback_searches': ['timing chain engine close up', 'timing chain engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق سلسلة التوقيت', 'text': 'يحتاج سلسلة التوقيت إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'timing chain engine', 'fallback_searches': ['timing chain engine close up', 'timing chain engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه سلسلة التوقيت', 'text': 'توضح آلية سلسلة التوقيت كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'timing chain engine', 'fallback_searches': ['timing chain engine close up', 'timing chain engine internal mechanism'], 'title': 'كيف تتأثر حرارته سلسلة التوقيت', 'text': 'تتأثر حرارة سلسلة التوقيت بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'timing chain engine', 'fallback_searches': ['timing chain engine close up', 'timing chain engine internal mechanism'], 'title': 'ما الذي يحدث داخله سلسلة التوقيت', 'text': 'داخل سلسلة التوقيت تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'timing belt engine', 'fallback_searches': ['timing belt engine close up', 'timing belt engine internal mechanism'], 'title': 'كيف يعمل سير التوقيت', 'text': 'كيف يعمل سير التوقيت داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'timing belt engine', 'fallback_searches': ['timing belt engine close up', 'timing belt engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق سير التوقيت', 'text': 'يحتاج سير التوقيت إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'timing belt engine', 'fallback_searches': ['timing belt engine close up', 'timing belt engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه سير التوقيت', 'text': 'توضح آلية سير التوقيت كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'timing belt engine', 'fallback_searches': ['timing belt engine close up', 'timing belt engine internal mechanism'], 'title': 'كيف تتأثر حرارته سير التوقيت', 'text': 'تتأثر حرارة سير التوقيت بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'timing belt engine', 'fallback_searches': ['timing belt engine close up', 'timing belt engine internal mechanism'], 'title': 'ما الذي يحدث داخله سير التوقيت', 'text': 'داخل سير التوقيت تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'timing tensioner engine', 'fallback_searches': ['timing tensioner engine close up', 'timing tensioner engine internal mechanism'], 'title': 'كيف يعمل شداد التوقيت', 'text': 'كيف يعمل شداد التوقيت داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'timing tensioner engine', 'fallback_searches': ['timing tensioner engine close up', 'timing tensioner engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق شداد التوقيت', 'text': 'يحتاج شداد التوقيت إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'timing tensioner engine', 'fallback_searches': ['timing tensioner engine close up', 'timing tensioner engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه شداد التوقيت', 'text': 'توضح آلية شداد التوقيت كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'timing tensioner engine', 'fallback_searches': ['timing tensioner engine close up', 'timing tensioner engine internal mechanism'], 'title': 'كيف تتأثر حرارته شداد التوقيت', 'text': 'تتأثر حرارة شداد التوقيت بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'timing tensioner engine', 'fallback_searches': ['timing tensioner engine close up', 'timing tensioner engine internal mechanism'], 'title': 'ما الذي يحدث داخله شداد التوقيت', 'text': 'داخل شداد التوقيت تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine oil pump', 'fallback_searches': ['engine oil pump close up', 'engine oil pump internal mechanism'], 'title': 'كيف يعمل مضخة الزيت', 'text': 'كيف يعمل مضخة الزيت داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine oil pump', 'fallback_searches': ['engine oil pump close up', 'engine oil pump internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق مضخة الزيت', 'text': 'يحتاج مضخة الزيت إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine oil pump', 'fallback_searches': ['engine oil pump close up', 'engine oil pump internal mechanism'], 'title': 'كيف تنتقل القوة فيه مضخة الزيت', 'text': 'توضح آلية مضخة الزيت كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine oil pump', 'fallback_searches': ['engine oil pump close up', 'engine oil pump internal mechanism'], 'title': 'كيف تتأثر حرارته مضخة الزيت', 'text': 'تتأثر حرارة مضخة الزيت بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine oil pump', 'fallback_searches': ['engine oil pump close up', 'engine oil pump internal mechanism'], 'title': 'ما الذي يحدث داخله مضخة الزيت', 'text': 'داخل مضخة الزيت تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'oil filter engine', 'fallback_searches': ['oil filter engine close up', 'oil filter engine internal mechanism'], 'title': 'كيف يعمل فلتر الزيت', 'text': 'كيف يعمل فلتر الزيت داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'oil filter engine', 'fallback_searches': ['oil filter engine close up', 'oil filter engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق فلتر الزيت', 'text': 'يحتاج فلتر الزيت إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'oil filter engine', 'fallback_searches': ['oil filter engine close up', 'oil filter engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه فلتر الزيت', 'text': 'توضح آلية فلتر الزيت كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'oil filter engine', 'fallback_searches': ['oil filter engine close up', 'oil filter engine internal mechanism'], 'title': 'كيف تتأثر حرارته فلتر الزيت', 'text': 'تتأثر حرارة فلتر الزيت بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'oil filter engine', 'fallback_searches': ['oil filter engine close up', 'oil filter engine internal mechanism'], 'title': 'ما الذي يحدث داخله فلتر الزيت', 'text': 'داخل فلتر الزيت تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine oil cooler', 'fallback_searches': ['engine oil cooler close up', 'engine oil cooler internal mechanism'], 'title': 'كيف يعمل مبرد الزيت', 'text': 'كيف يعمل مبرد الزيت داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine oil cooler', 'fallback_searches': ['engine oil cooler close up', 'engine oil cooler internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق مبرد الزيت', 'text': 'يحتاج مبرد الزيت إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine oil cooler', 'fallback_searches': ['engine oil cooler close up', 'engine oil cooler internal mechanism'], 'title': 'كيف تنتقل القوة فيه مبرد الزيت', 'text': 'توضح آلية مبرد الزيت كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine oil cooler', 'fallback_searches': ['engine oil cooler close up', 'engine oil cooler internal mechanism'], 'title': 'كيف تتأثر حرارته مبرد الزيت', 'text': 'تتأثر حرارة مبرد الزيت بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine oil cooler', 'fallback_searches': ['engine oil cooler close up', 'engine oil cooler internal mechanism'], 'title': 'ما الذي يحدث داخله مبرد الزيت', 'text': 'داخل مبرد الزيت تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'oil pan engine', 'fallback_searches': ['oil pan engine close up', 'oil pan engine internal mechanism'], 'title': 'كيف يعمل حوض الزيت', 'text': 'كيف يعمل حوض الزيت داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'oil pan engine', 'fallback_searches': ['oil pan engine close up', 'oil pan engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق حوض الزيت', 'text': 'يحتاج حوض الزيت إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'oil pan engine', 'fallback_searches': ['oil pan engine close up', 'oil pan engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه حوض الزيت', 'text': 'توضح آلية حوض الزيت كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'oil pan engine', 'fallback_searches': ['oil pan engine close up', 'oil pan engine internal mechanism'], 'title': 'كيف تتأثر حرارته حوض الزيت', 'text': 'تتأثر حرارة حوض الزيت بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'oil pan engine', 'fallback_searches': ['oil pan engine close up', 'oil pan engine internal mechanism'], 'title': 'ما الذي يحدث داخله حوض الزيت', 'text': 'داخل حوض الزيت تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'oil pressure relief valve', 'fallback_searches': ['oil pressure relief valve close up', 'oil pressure relief valve internal mechanism'], 'title': 'كيف يعمل صمام ضغط الزيت', 'text': 'كيف يعمل صمام ضغط الزيت داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'oil pressure relief valve', 'fallback_searches': ['oil pressure relief valve close up', 'oil pressure relief valve internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق صمام ضغط الزيت', 'text': 'يحتاج صمام ضغط الزيت إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'oil pressure relief valve', 'fallback_searches': ['oil pressure relief valve close up', 'oil pressure relief valve internal mechanism'], 'title': 'كيف تنتقل القوة فيه صمام ضغط الزيت', 'text': 'توضح آلية صمام ضغط الزيت كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'oil pressure relief valve', 'fallback_searches': ['oil pressure relief valve close up', 'oil pressure relief valve internal mechanism'], 'title': 'كيف تتأثر حرارته صمام ضغط الزيت', 'text': 'تتأثر حرارة صمام ضغط الزيت بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'oil pressure relief valve', 'fallback_searches': ['oil pressure relief valve close up', 'oil pressure relief valve internal mechanism'], 'title': 'ما الذي يحدث داخله صمام ضغط الزيت', 'text': 'داخل صمام ضغط الزيت تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'PCV valve engine', 'fallback_searches': ['PCV valve engine close up', 'PCV valve engine internal mechanism'], 'title': 'كيف يعمل نظام التهوية', 'text': 'كيف يعمل نظام التهوية داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'PCV valve engine', 'fallback_searches': ['PCV valve engine close up', 'PCV valve engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق نظام التهوية', 'text': 'يحتاج نظام التهوية إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'PCV valve engine', 'fallback_searches': ['PCV valve engine close up', 'PCV valve engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه نظام التهوية', 'text': 'توضح آلية نظام التهوية كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'PCV valve engine', 'fallback_searches': ['PCV valve engine close up', 'PCV valve engine internal mechanism'], 'title': 'كيف تتأثر حرارته نظام التهوية', 'text': 'تتأثر حرارة نظام التهوية بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'PCV valve engine', 'fallback_searches': ['PCV valve engine close up', 'PCV valve engine internal mechanism'], 'title': 'ما الذي يحدث داخله نظام التهوية', 'text': 'داخل نظام التهوية تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'water pump engine cooling', 'fallback_searches': ['water pump engine cooling close up', 'water pump engine cooling internal mechanism'], 'title': 'كيف يعمل مضخة الماء', 'text': 'كيف يعمل مضخة الماء داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'water pump engine cooling', 'fallback_searches': ['water pump engine cooling close up', 'water pump engine cooling internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق مضخة الماء', 'text': 'يحتاج مضخة الماء إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'water pump engine cooling', 'fallback_searches': ['water pump engine cooling close up', 'water pump engine cooling internal mechanism'], 'title': 'كيف تنتقل القوة فيه مضخة الماء', 'text': 'توضح آلية مضخة الماء كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'water pump engine cooling', 'fallback_searches': ['water pump engine cooling close up', 'water pump engine cooling internal mechanism'], 'title': 'كيف تتأثر حرارته مضخة الماء', 'text': 'تتأثر حرارة مضخة الماء بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'water pump engine cooling', 'fallback_searches': ['water pump engine cooling close up', 'water pump engine cooling internal mechanism'], 'title': 'ما الذي يحدث داخله مضخة الماء', 'text': 'داخل مضخة الماء تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine thermostat cooling', 'fallback_searches': ['engine thermostat cooling close up', 'engine thermostat cooling internal mechanism'], 'title': 'كيف يعمل الثرموستات', 'text': 'كيف يعمل الثرموستات داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine thermostat cooling', 'fallback_searches': ['engine thermostat cooling close up', 'engine thermostat cooling internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق الثرموستات', 'text': 'يحتاج الثرموستات إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine thermostat cooling', 'fallback_searches': ['engine thermostat cooling close up', 'engine thermostat cooling internal mechanism'], 'title': 'كيف تنتقل القوة فيه الثرموستات', 'text': 'توضح آلية الثرموستات كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine thermostat cooling', 'fallback_searches': ['engine thermostat cooling close up', 'engine thermostat cooling internal mechanism'], 'title': 'كيف تتأثر حرارته الثرموستات', 'text': 'تتأثر حرارة الثرموستات بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine thermostat cooling', 'fallback_searches': ['engine thermostat cooling close up', 'engine thermostat cooling internal mechanism'], 'title': 'ما الذي يحدث داخله الثرموستات', 'text': 'داخل الثرموستات تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'radiator engine cooling', 'fallback_searches': ['radiator engine cooling close up', 'radiator engine cooling internal mechanism'], 'title': 'كيف يعمل الرديتر', 'text': 'كيف يعمل الرديتر داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'radiator engine cooling', 'fallback_searches': ['radiator engine cooling close up', 'radiator engine cooling internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق الرديتر', 'text': 'يحتاج الرديتر إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'radiator engine cooling', 'fallback_searches': ['radiator engine cooling close up', 'radiator engine cooling internal mechanism'], 'title': 'كيف تنتقل القوة فيه الرديتر', 'text': 'توضح آلية الرديتر كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'radiator engine cooling', 'fallback_searches': ['radiator engine cooling close up', 'radiator engine cooling internal mechanism'], 'title': 'كيف تتأثر حرارته الرديتر', 'text': 'تتأثر حرارة الرديتر بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'radiator engine cooling', 'fallback_searches': ['radiator engine cooling close up', 'radiator engine cooling internal mechanism'], 'title': 'ما الذي يحدث داخله الرديتر', 'text': 'داخل الرديتر تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'radiator pressure cap', 'fallback_searches': ['radiator pressure cap close up', 'radiator pressure cap internal mechanism'], 'title': 'كيف يعمل غطاء الرديتر', 'text': 'كيف يعمل غطاء الرديتر داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'radiator pressure cap', 'fallback_searches': ['radiator pressure cap close up', 'radiator pressure cap internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق غطاء الرديتر', 'text': 'يحتاج غطاء الرديتر إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'radiator pressure cap', 'fallback_searches': ['radiator pressure cap close up', 'radiator pressure cap internal mechanism'], 'title': 'كيف تنتقل القوة فيه غطاء الرديتر', 'text': 'توضح آلية غطاء الرديتر كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'radiator pressure cap', 'fallback_searches': ['radiator pressure cap close up', 'radiator pressure cap internal mechanism'], 'title': 'كيف تتأثر حرارته غطاء الرديتر', 'text': 'تتأثر حرارة غطاء الرديتر بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'radiator pressure cap', 'fallback_searches': ['radiator pressure cap close up', 'radiator pressure cap internal mechanism'], 'title': 'ما الذي يحدث داخله غطاء الرديتر', 'text': 'داخل غطاء الرديتر تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'coolant expansion tank', 'fallback_searches': ['coolant expansion tank close up', 'coolant expansion tank internal mechanism'], 'title': 'كيف يعمل خزان التمدد', 'text': 'كيف يعمل خزان التمدد داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'coolant expansion tank', 'fallback_searches': ['coolant expansion tank close up', 'coolant expansion tank internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق خزان التمدد', 'text': 'يحتاج خزان التمدد إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'coolant expansion tank', 'fallback_searches': ['coolant expansion tank close up', 'coolant expansion tank internal mechanism'], 'title': 'كيف تنتقل القوة فيه خزان التمدد', 'text': 'توضح آلية خزان التمدد كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'coolant expansion tank', 'fallback_searches': ['coolant expansion tank close up', 'coolant expansion tank internal mechanism'], 'title': 'كيف تتأثر حرارته خزان التمدد', 'text': 'تتأثر حرارة خزان التمدد بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'coolant expansion tank', 'fallback_searches': ['coolant expansion tank close up', 'coolant expansion tank internal mechanism'], 'title': 'ما الذي يحدث داخله خزان التمدد', 'text': 'داخل خزان التمدد تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine cooling fan', 'fallback_searches': ['engine cooling fan close up', 'engine cooling fan internal mechanism'], 'title': 'كيف يعمل مروحة التبريد', 'text': 'كيف يعمل مروحة التبريد داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine cooling fan', 'fallback_searches': ['engine cooling fan close up', 'engine cooling fan internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق مروحة التبريد', 'text': 'يحتاج مروحة التبريد إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine cooling fan', 'fallback_searches': ['engine cooling fan close up', 'engine cooling fan internal mechanism'], 'title': 'كيف تنتقل القوة فيه مروحة التبريد', 'text': 'توضح آلية مروحة التبريد كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine cooling fan', 'fallback_searches': ['engine cooling fan close up', 'engine cooling fan internal mechanism'], 'title': 'كيف تتأثر حرارته مروحة التبريد', 'text': 'تتأثر حرارة مروحة التبريد بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine cooling fan', 'fallback_searches': ['engine cooling fan close up', 'engine cooling fan internal mechanism'], 'title': 'ما الذي يحدث داخله مروحة التبريد', 'text': 'داخل مروحة التبريد تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'intercooler automotive engine', 'fallback_searches': ['intercooler automotive engine close up', 'intercooler automotive engine internal mechanism'], 'title': 'كيف يعمل المبرد البيني', 'text': 'كيف يعمل المبرد البيني داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'intercooler automotive engine', 'fallback_searches': ['intercooler automotive engine close up', 'intercooler automotive engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق المبرد البيني', 'text': 'يحتاج المبرد البيني إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'intercooler automotive engine', 'fallback_searches': ['intercooler automotive engine close up', 'intercooler automotive engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه المبرد البيني', 'text': 'توضح آلية المبرد البيني كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'intercooler automotive engine', 'fallback_searches': ['intercooler automotive engine close up', 'intercooler automotive engine internal mechanism'], 'title': 'كيف تتأثر حرارته المبرد البيني', 'text': 'تتأثر حرارة المبرد البيني بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'intercooler automotive engine', 'fallback_searches': ['intercooler automotive engine close up', 'intercooler automotive engine internal mechanism'], 'title': 'ما الذي يحدث داخله المبرد البيني', 'text': 'داخل المبرد البيني تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'turbocharger automotive engine', 'fallback_searches': ['turbocharger automotive engine close up', 'turbocharger automotive engine internal mechanism'], 'title': 'كيف يعمل الشاحن التوربيني', 'text': 'كيف يعمل الشاحن التوربيني داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'turbocharger automotive engine', 'fallback_searches': ['turbocharger automotive engine close up', 'turbocharger automotive engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق الشاحن التوربيني', 'text': 'يحتاج الشاحن التوربيني إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'turbocharger automotive engine', 'fallback_searches': ['turbocharger automotive engine close up', 'turbocharger automotive engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه الشاحن التوربيني', 'text': 'توضح آلية الشاحن التوربيني كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'turbocharger automotive engine', 'fallback_searches': ['turbocharger automotive engine close up', 'turbocharger automotive engine internal mechanism'], 'title': 'كيف تتأثر حرارته الشاحن التوربيني', 'text': 'تتأثر حرارة الشاحن التوربيني بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'turbocharger automotive engine', 'fallback_searches': ['turbocharger automotive engine close up', 'turbocharger automotive engine internal mechanism'], 'title': 'ما الذي يحدث داخله الشاحن التوربيني', 'text': 'داخل الشاحن التوربيني تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'turbo wastegate', 'fallback_searches': ['turbo wastegate close up', 'turbo wastegate internal mechanism'], 'title': 'كيف يعمل صمام ويست غيت', 'text': 'كيف يعمل صمام ويست غيت داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'turbo wastegate', 'fallback_searches': ['turbo wastegate close up', 'turbo wastegate internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق صمام ويست غيت', 'text': 'يحتاج صمام ويست غيت إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'turbo wastegate', 'fallback_searches': ['turbo wastegate close up', 'turbo wastegate internal mechanism'], 'title': 'كيف تنتقل القوة فيه صمام ويست غيت', 'text': 'توضح آلية صمام ويست غيت كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'turbo wastegate', 'fallback_searches': ['turbo wastegate close up', 'turbo wastegate internal mechanism'], 'title': 'كيف تتأثر حرارته صمام ويست غيت', 'text': 'تتأثر حرارة صمام ويست غيت بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'turbo wastegate', 'fallback_searches': ['turbo wastegate close up', 'turbo wastegate internal mechanism'], 'title': 'ما الذي يحدث داخله صمام ويست غيت', 'text': 'داخل صمام ويست غيت تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'turbo diverter valve', 'fallback_searches': ['turbo diverter valve close up', 'turbo diverter valve internal mechanism'], 'title': 'كيف يعمل صمام التفريغ', 'text': 'كيف يعمل صمام التفريغ داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'turbo diverter valve', 'fallback_searches': ['turbo diverter valve close up', 'turbo diverter valve internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق صمام التفريغ', 'text': 'يحتاج صمام التفريغ إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'turbo diverter valve', 'fallback_searches': ['turbo diverter valve close up', 'turbo diverter valve internal mechanism'], 'title': 'كيف تنتقل القوة فيه صمام التفريغ', 'text': 'توضح آلية صمام التفريغ كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'turbo diverter valve', 'fallback_searches': ['turbo diverter valve close up', 'turbo diverter valve internal mechanism'], 'title': 'كيف تتأثر حرارته صمام التفريغ', 'text': 'تتأثر حرارة صمام التفريغ بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'turbo diverter valve', 'fallback_searches': ['turbo diverter valve close up', 'turbo diverter valve internal mechanism'], 'title': 'ما الذي يحدث داخله صمام التفريغ', 'text': 'داخل صمام التفريغ تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'supercharger automotive engine', 'fallback_searches': ['supercharger automotive engine close up', 'supercharger automotive engine internal mechanism'], 'title': 'كيف يعمل الشاحن الفائق', 'text': 'كيف يعمل الشاحن الفائق داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'supercharger automotive engine', 'fallback_searches': ['supercharger automotive engine close up', 'supercharger automotive engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق الشاحن الفائق', 'text': 'يحتاج الشاحن الفائق إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'supercharger automotive engine', 'fallback_searches': ['supercharger automotive engine close up', 'supercharger automotive engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه الشاحن الفائق', 'text': 'توضح آلية الشاحن الفائق كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'supercharger automotive engine', 'fallback_searches': ['supercharger automotive engine close up', 'supercharger automotive engine internal mechanism'], 'title': 'كيف تتأثر حرارته الشاحن الفائق', 'text': 'تتأثر حرارة الشاحن الفائق بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'supercharger automotive engine', 'fallback_searches': ['supercharger automotive engine close up', 'supercharger automotive engine internal mechanism'], 'title': 'ما الذي يحدث داخله الشاحن الفائق', 'text': 'داخل الشاحن الفائق تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine air filter', 'fallback_searches': ['engine air filter close up', 'engine air filter internal mechanism'], 'title': 'كيف يعمل فلتر الهواء', 'text': 'كيف يعمل فلتر الهواء داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine air filter', 'fallback_searches': ['engine air filter close up', 'engine air filter internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق فلتر الهواء', 'text': 'يحتاج فلتر الهواء إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine air filter', 'fallback_searches': ['engine air filter close up', 'engine air filter internal mechanism'], 'title': 'كيف تنتقل القوة فيه فلتر الهواء', 'text': 'توضح آلية فلتر الهواء كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine air filter', 'fallback_searches': ['engine air filter close up', 'engine air filter internal mechanism'], 'title': 'كيف تتأثر حرارته فلتر الهواء', 'text': 'تتأثر حرارة فلتر الهواء بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'engine air filter', 'fallback_searches': ['engine air filter close up', 'engine air filter internal mechanism'], 'title': 'ما الذي يحدث داخله فلتر الهواء', 'text': 'داخل فلتر الهواء تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'throttle body engine', 'fallback_searches': ['throttle body engine close up', 'throttle body engine internal mechanism'], 'title': 'كيف يعمل بوابة الخانق', 'text': 'كيف يعمل بوابة الخانق داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'throttle body engine', 'fallback_searches': ['throttle body engine close up', 'throttle body engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق بوابة الخانق', 'text': 'يحتاج بوابة الخانق إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'throttle body engine', 'fallback_searches': ['throttle body engine close up', 'throttle body engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه بوابة الخانق', 'text': 'توضح آلية بوابة الخانق كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'throttle body engine', 'fallback_searches': ['throttle body engine close up', 'throttle body engine internal mechanism'], 'title': 'كيف تتأثر حرارته بوابة الخانق', 'text': 'تتأثر حرارة بوابة الخانق بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'throttle body engine', 'fallback_searches': ['throttle body engine close up', 'throttle body engine internal mechanism'], 'title': 'ما الذي يحدث داخله بوابة الخانق', 'text': 'داخل بوابة الخانق تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'intake manifold engine', 'fallback_searches': ['intake manifold engine close up', 'intake manifold engine internal mechanism'], 'title': 'كيف يعمل مشعب السحب', 'text': 'كيف يعمل مشعب السحب داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'intake manifold engine', 'fallback_searches': ['intake manifold engine close up', 'intake manifold engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق مشعب السحب', 'text': 'يحتاج مشعب السحب إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'intake manifold engine', 'fallback_searches': ['intake manifold engine close up', 'intake manifold engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه مشعب السحب', 'text': 'توضح آلية مشعب السحب كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'intake manifold engine', 'fallback_searches': ['intake manifold engine close up', 'intake manifold engine internal mechanism'], 'title': 'كيف تتأثر حرارته مشعب السحب', 'text': 'تتأثر حرارة مشعب السحب بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'intake manifold engine', 'fallback_searches': ['intake manifold engine close up', 'intake manifold engine internal mechanism'], 'title': 'ما الذي يحدث داخله مشعب السحب', 'text': 'داخل مشعب السحب تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'fuel injectors engine', 'fallback_searches': ['fuel injectors engine close up', 'fuel injectors engine internal mechanism'], 'title': 'كيف يعمل البخاخات', 'text': 'كيف يعمل البخاخات داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'fuel injectors engine', 'fallback_searches': ['fuel injectors engine close up', 'fuel injectors engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق البخاخات', 'text': 'يحتاج البخاخات إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'fuel injectors engine', 'fallback_searches': ['fuel injectors engine close up', 'fuel injectors engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه البخاخات', 'text': 'توضح آلية البخاخات كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'fuel injectors engine', 'fallback_searches': ['fuel injectors engine close up', 'fuel injectors engine internal mechanism'], 'title': 'كيف تتأثر حرارته البخاخات', 'text': 'تتأثر حرارة البخاخات بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'fuel injectors engine', 'fallback_searches': ['fuel injectors engine close up', 'fuel injectors engine internal mechanism'], 'title': 'ما الذي يحدث داخله البخاخات', 'text': 'داخل البخاخات تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'fuel pump automotive', 'fallback_searches': ['fuel pump automotive close up', 'fuel pump automotive internal mechanism'], 'title': 'كيف يعمل مضخة الوقود', 'text': 'كيف يعمل مضخة الوقود داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'fuel pump automotive', 'fallback_searches': ['fuel pump automotive close up', 'fuel pump automotive internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق مضخة الوقود', 'text': 'يحتاج مضخة الوقود إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'fuel pump automotive', 'fallback_searches': ['fuel pump automotive close up', 'fuel pump automotive internal mechanism'], 'title': 'كيف تنتقل القوة فيه مضخة الوقود', 'text': 'توضح آلية مضخة الوقود كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'fuel pump automotive', 'fallback_searches': ['fuel pump automotive close up', 'fuel pump automotive internal mechanism'], 'title': 'كيف تتأثر حرارته مضخة الوقود', 'text': 'تتأثر حرارة مضخة الوقود بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'fuel pump automotive', 'fallback_searches': ['fuel pump automotive close up', 'fuel pump automotive internal mechanism'], 'title': 'ما الذي يحدث داخله مضخة الوقود', 'text': 'داخل مضخة الوقود تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'fuel pressure regulator', 'fallback_searches': ['fuel pressure regulator close up', 'fuel pressure regulator internal mechanism'], 'title': 'كيف يعمل منظم ضغط الوقود', 'text': 'كيف يعمل منظم ضغط الوقود داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'fuel pressure regulator', 'fallback_searches': ['fuel pressure regulator close up', 'fuel pressure regulator internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق منظم ضغط الوقود', 'text': 'يحتاج منظم ضغط الوقود إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'fuel pressure regulator', 'fallback_searches': ['fuel pressure regulator close up', 'fuel pressure regulator internal mechanism'], 'title': 'كيف تنتقل القوة فيه منظم ضغط الوقود', 'text': 'توضح آلية منظم ضغط الوقود كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'fuel pressure regulator', 'fallback_searches': ['fuel pressure regulator close up', 'fuel pressure regulator internal mechanism'], 'title': 'كيف تتأثر حرارته منظم ضغط الوقود', 'text': 'تتأثر حرارة منظم ضغط الوقود بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'fuel pressure regulator', 'fallback_searches': ['fuel pressure regulator close up', 'fuel pressure regulator internal mechanism'], 'title': 'ما الذي يحدث داخله منظم ضغط الوقود', 'text': 'داخل منظم ضغط الوقود تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'spark plug engine', 'fallback_searches': ['spark plug engine close up', 'spark plug engine internal mechanism'], 'title': 'كيف يعمل شمعة الاحتراق', 'text': 'كيف يعمل شمعة الاحتراق داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'spark plug engine', 'fallback_searches': ['spark plug engine close up', 'spark plug engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق شمعة الاحتراق', 'text': 'يحتاج شمعة الاحتراق إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'spark plug engine', 'fallback_searches': ['spark plug engine close up', 'spark plug engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه شمعة الاحتراق', 'text': 'توضح آلية شمعة الاحتراق كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'spark plug engine', 'fallback_searches': ['spark plug engine close up', 'spark plug engine internal mechanism'], 'title': 'كيف تتأثر حرارته شمعة الاحتراق', 'text': 'تتأثر حرارة شمعة الاحتراق بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'spark plug engine', 'fallback_searches': ['spark plug engine close up', 'spark plug engine internal mechanism'], 'title': 'ما الذي يحدث داخله شمعة الاحتراق', 'text': 'داخل شمعة الاحتراق تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'ignition coil engine', 'fallback_searches': ['ignition coil engine close up', 'ignition coil engine internal mechanism'], 'title': 'كيف يعمل ملف الإشعال', 'text': 'كيف يعمل ملف الإشعال داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'ignition coil engine', 'fallback_searches': ['ignition coil engine close up', 'ignition coil engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق ملف الإشعال', 'text': 'يحتاج ملف الإشعال إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'ignition coil engine', 'fallback_searches': ['ignition coil engine close up', 'ignition coil engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه ملف الإشعال', 'text': 'توضح آلية ملف الإشعال كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'ignition coil engine', 'fallback_searches': ['ignition coil engine close up', 'ignition coil engine internal mechanism'], 'title': 'كيف تتأثر حرارته ملف الإشعال', 'text': 'تتأثر حرارة ملف الإشعال بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'ignition coil engine', 'fallback_searches': ['ignition coil engine close up', 'ignition coil engine internal mechanism'], 'title': 'ما الذي يحدث داخله ملف الإشعال', 'text': 'داخل ملف الإشعال تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'exhaust manifold engine', 'fallback_searches': ['exhaust manifold engine close up', 'exhaust manifold engine internal mechanism'], 'title': 'كيف يعمل مشعب العادم', 'text': 'كيف يعمل مشعب العادم داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'exhaust manifold engine', 'fallback_searches': ['exhaust manifold engine close up', 'exhaust manifold engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق مشعب العادم', 'text': 'يحتاج مشعب العادم إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'exhaust manifold engine', 'fallback_searches': ['exhaust manifold engine close up', 'exhaust manifold engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه مشعب العادم', 'text': 'توضح آلية مشعب العادم كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'exhaust manifold engine', 'fallback_searches': ['exhaust manifold engine close up', 'exhaust manifold engine internal mechanism'], 'title': 'كيف تتأثر حرارته مشعب العادم', 'text': 'تتأثر حرارة مشعب العادم بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'exhaust manifold engine', 'fallback_searches': ['exhaust manifold engine close up', 'exhaust manifold engine internal mechanism'], 'title': 'ما الذي يحدث داخله مشعب العادم', 'text': 'داخل مشعب العادم تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'catalytic converter exhaust', 'fallback_searches': ['catalytic converter exhaust close up', 'catalytic converter exhaust internal mechanism'], 'title': 'كيف يعمل المحول الحفاز', 'text': 'كيف يعمل المحول الحفاز داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'catalytic converter exhaust', 'fallback_searches': ['catalytic converter exhaust close up', 'catalytic converter exhaust internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق المحول الحفاز', 'text': 'يحتاج المحول الحفاز إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'catalytic converter exhaust', 'fallback_searches': ['catalytic converter exhaust close up', 'catalytic converter exhaust internal mechanism'], 'title': 'كيف تنتقل القوة فيه المحول الحفاز', 'text': 'توضح آلية المحول الحفاز كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'catalytic converter exhaust', 'fallback_searches': ['catalytic converter exhaust close up', 'catalytic converter exhaust internal mechanism'], 'title': 'كيف تتأثر حرارته المحول الحفاز', 'text': 'تتأثر حرارة المحول الحفاز بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'catalytic converter exhaust', 'fallback_searches': ['catalytic converter exhaust close up', 'catalytic converter exhaust internal mechanism'], 'title': 'ما الذي يحدث داخله المحول الحفاز', 'text': 'داخل المحول الحفاز تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'muffler exhaust system', 'fallback_searches': ['muffler exhaust system close up', 'muffler exhaust system internal mechanism'], 'title': 'كيف يعمل كاتم الصوت', 'text': 'كيف يعمل كاتم الصوت داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'muffler exhaust system', 'fallback_searches': ['muffler exhaust system close up', 'muffler exhaust system internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق كاتم الصوت', 'text': 'يحتاج كاتم الصوت إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'muffler exhaust system', 'fallback_searches': ['muffler exhaust system close up', 'muffler exhaust system internal mechanism'], 'title': 'كيف تنتقل القوة فيه كاتم الصوت', 'text': 'توضح آلية كاتم الصوت كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'muffler exhaust system', 'fallback_searches': ['muffler exhaust system close up', 'muffler exhaust system internal mechanism'], 'title': 'كيف تتأثر حرارته كاتم الصوت', 'text': 'تتأثر حرارة كاتم الصوت بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'muffler exhaust system', 'fallback_searches': ['muffler exhaust system close up', 'muffler exhaust system internal mechanism'], 'title': 'ما الذي يحدث داخله كاتم الصوت', 'text': 'داخل كاتم الصوت تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'EGR valve engine', 'fallback_searches': ['EGR valve engine close up', 'EGR valve engine internal mechanism'], 'title': 'كيف يعمل صمام إعادة العادم', 'text': 'كيف يعمل صمام إعادة العادم داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'EGR valve engine', 'fallback_searches': ['EGR valve engine close up', 'EGR valve engine internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق صمام إعادة العادم', 'text': 'يحتاج صمام إعادة العادم إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'EGR valve engine', 'fallback_searches': ['EGR valve engine close up', 'EGR valve engine internal mechanism'], 'title': 'كيف تنتقل القوة فيه صمام إعادة العادم', 'text': 'توضح آلية صمام إعادة العادم كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'EGR valve engine', 'fallback_searches': ['EGR valve engine close up', 'EGR valve engine internal mechanism'], 'title': 'كيف تتأثر حرارته صمام إعادة العادم', 'text': 'تتأثر حرارة صمام إعادة العادم بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'EGR valve engine', 'fallback_searches': ['EGR valve engine close up', 'EGR valve engine internal mechanism'], 'title': 'ما الذي يحدث داخله صمام إعادة العادم', 'text': 'داخل صمام إعادة العادم تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'diesel particulate filter exhaust', 'fallback_searches': ['diesel particulate filter exhaust close up', 'diesel particulate filter exhaust internal mechanism'], 'title': 'كيف يعمل فلتر الجسيمات', 'text': 'كيف يعمل فلتر الجسيمات داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'diesel particulate filter exhaust', 'fallback_searches': ['diesel particulate filter exhaust close up', 'diesel particulate filter exhaust internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق فلتر الجسيمات', 'text': 'يحتاج فلتر الجسيمات إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'diesel particulate filter exhaust', 'fallback_searches': ['diesel particulate filter exhaust close up', 'diesel particulate filter exhaust internal mechanism'], 'title': 'كيف تنتقل القوة فيه فلتر الجسيمات', 'text': 'توضح آلية فلتر الجسيمات كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'diesel particulate filter exhaust', 'fallback_searches': ['diesel particulate filter exhaust close up', 'diesel particulate filter exhaust internal mechanism'], 'title': 'كيف تتأثر حرارته فلتر الجسيمات', 'text': 'تتأثر حرارة فلتر الجسيمات بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'diesel particulate filter exhaust', 'fallback_searches': ['diesel particulate filter exhaust close up', 'diesel particulate filter exhaust internal mechanism'], 'title': 'ما الذي يحدث داخله فلتر الجسيمات', 'text': 'داخل فلتر الجسيمات تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'clutch transmission automotive', 'fallback_searches': ['clutch transmission automotive close up', 'clutch transmission automotive internal mechanism'], 'title': 'كيف يعمل القابض', 'text': 'كيف يعمل القابض داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'clutch transmission automotive', 'fallback_searches': ['clutch transmission automotive close up', 'clutch transmission automotive internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق القابض', 'text': 'يحتاج القابض إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'clutch transmission automotive', 'fallback_searches': ['clutch transmission automotive close up', 'clutch transmission automotive internal mechanism'], 'title': 'كيف تنتقل القوة فيه القابض', 'text': 'توضح آلية القابض كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'clutch transmission automotive', 'fallback_searches': ['clutch transmission automotive close up', 'clutch transmission automotive internal mechanism'], 'title': 'كيف تتأثر حرارته القابض', 'text': 'تتأثر حرارة القابض بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'clutch transmission automotive', 'fallback_searches': ['clutch transmission automotive close up', 'clutch transmission automotive internal mechanism'], 'title': 'ما الذي يحدث داخله القابض', 'text': 'داخل القابض تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'clutch disc automotive', 'fallback_searches': ['clutch disc automotive close up', 'clutch disc automotive internal mechanism'], 'title': 'كيف يعمل قرص القابض', 'text': 'كيف يعمل قرص القابض داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'clutch disc automotive', 'fallback_searches': ['clutch disc automotive close up', 'clutch disc automotive internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق قرص القابض', 'text': 'يحتاج قرص القابض إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'clutch disc automotive', 'fallback_searches': ['clutch disc automotive close up', 'clutch disc automotive internal mechanism'], 'title': 'كيف تنتقل القوة فيه قرص القابض', 'text': 'توضح آلية قرص القابض كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'clutch disc automotive', 'fallback_searches': ['clutch disc automotive close up', 'clutch disc automotive internal mechanism'], 'title': 'كيف تتأثر حرارته قرص القابض', 'text': 'تتأثر حرارة قرص القابض بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'clutch disc automotive', 'fallback_searches': ['clutch disc automotive close up', 'clutch disc automotive internal mechanism'], 'title': 'ما الذي يحدث داخله قرص القابض', 'text': 'داخل قرص القابض تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'pressure plate clutch', 'fallback_searches': ['pressure plate clutch close up', 'pressure plate clutch internal mechanism'], 'title': 'كيف يعمل صحن الضغط', 'text': 'كيف يعمل صحن الضغط داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'pressure plate clutch', 'fallback_searches': ['pressure plate clutch close up', 'pressure plate clutch internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق صحن الضغط', 'text': 'يحتاج صحن الضغط إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'pressure plate clutch', 'fallback_searches': ['pressure plate clutch close up', 'pressure plate clutch internal mechanism'], 'title': 'كيف تنتقل القوة فيه صحن الضغط', 'text': 'توضح آلية صحن الضغط كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'pressure plate clutch', 'fallback_searches': ['pressure plate clutch close up', 'pressure plate clutch internal mechanism'], 'title': 'كيف تتأثر حرارته صحن الضغط', 'text': 'تتأثر حرارة صحن الضغط بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'pressure plate clutch', 'fallback_searches': ['pressure plate clutch close up', 'pressure plate clutch internal mechanism'], 'title': 'ما الذي يحدث داخله صحن الضغط', 'text': 'داخل صحن الضغط تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'clutch release bearing', 'fallback_searches': ['clutch release bearing close up', 'clutch release bearing internal mechanism'], 'title': 'كيف يعمل رمان القابض', 'text': 'كيف يعمل رمان القابض داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'clutch release bearing', 'fallback_searches': ['clutch release bearing close up', 'clutch release bearing internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق رمان القابض', 'text': 'يحتاج رمان القابض إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'clutch release bearing', 'fallback_searches': ['clutch release bearing close up', 'clutch release bearing internal mechanism'], 'title': 'كيف تنتقل القوة فيه رمان القابض', 'text': 'توضح آلية رمان القابض كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'clutch release bearing', 'fallback_searches': ['clutch release bearing close up', 'clutch release bearing internal mechanism'], 'title': 'كيف تتأثر حرارته رمان القابض', 'text': 'تتأثر حرارة رمان القابض بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'clutch release bearing', 'fallback_searches': ['clutch release bearing close up', 'clutch release bearing internal mechanism'], 'title': 'ما الذي يحدث داخله رمان القابض', 'text': 'داخل رمان القابض تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'manual transmission gearbox', 'fallback_searches': ['manual transmission gearbox close up', 'manual transmission gearbox internal mechanism'], 'title': 'كيف يعمل ناقل الحركة اليدوي', 'text': 'كيف يعمل ناقل الحركة اليدوي داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'manual transmission gearbox', 'fallback_searches': ['manual transmission gearbox close up', 'manual transmission gearbox internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق ناقل الحركة اليدوي', 'text': 'يحتاج ناقل الحركة اليدوي إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'manual transmission gearbox', 'fallback_searches': ['manual transmission gearbox close up', 'manual transmission gearbox internal mechanism'], 'title': 'كيف تنتقل القوة فيه ناقل الحركة اليدوي', 'text': 'توضح آلية ناقل الحركة اليدوي كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'manual transmission gearbox', 'fallback_searches': ['manual transmission gearbox close up', 'manual transmission gearbox internal mechanism'], 'title': 'كيف تتأثر حرارته ناقل الحركة اليدوي', 'text': 'تتأثر حرارة ناقل الحركة اليدوي بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'manual transmission gearbox', 'fallback_searches': ['manual transmission gearbox close up', 'manual transmission gearbox internal mechanism'], 'title': 'ما الذي يحدث داخله ناقل الحركة اليدوي', 'text': 'داخل ناقل الحركة اليدوي تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'transmission synchronizer', 'fallback_searches': ['transmission synchronizer close up', 'transmission synchronizer internal mechanism'], 'title': 'كيف يعمل المزامن', 'text': 'كيف يعمل المزامن داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'transmission synchronizer', 'fallback_searches': ['transmission synchronizer close up', 'transmission synchronizer internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق المزامن', 'text': 'يحتاج المزامن إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'transmission synchronizer', 'fallback_searches': ['transmission synchronizer close up', 'transmission synchronizer internal mechanism'], 'title': 'كيف تنتقل القوة فيه المزامن', 'text': 'توضح آلية المزامن كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'transmission synchronizer', 'fallback_searches': ['transmission synchronizer close up', 'transmission synchronizer internal mechanism'], 'title': 'كيف تتأثر حرارته المزامن', 'text': 'تتأثر حرارة المزامن بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'transmission synchronizer', 'fallback_searches': ['transmission synchronizer close up', 'transmission synchronizer internal mechanism'], 'title': 'ما الذي يحدث داخله المزامن', 'text': 'داخل المزامن تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'torque converter transmission', 'fallback_searches': ['torque converter transmission close up', 'torque converter transmission internal mechanism'], 'title': 'كيف يعمل محول العزم', 'text': 'كيف يعمل محول العزم داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'torque converter transmission', 'fallback_searches': ['torque converter transmission close up', 'torque converter transmission internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق محول العزم', 'text': 'يحتاج محول العزم إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'torque converter transmission', 'fallback_searches': ['torque converter transmission close up', 'torque converter transmission internal mechanism'], 'title': 'كيف تنتقل القوة فيه محول العزم', 'text': 'توضح آلية محول العزم كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'torque converter transmission', 'fallback_searches': ['torque converter transmission close up', 'torque converter transmission internal mechanism'], 'title': 'كيف تتأثر حرارته محول العزم', 'text': 'تتأثر حرارة محول العزم بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'torque converter transmission', 'fallback_searches': ['torque converter transmission close up', 'torque converter transmission internal mechanism'], 'title': 'ما الذي يحدث داخله محول العزم', 'text': 'داخل محول العزم تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'planetary gears transmission', 'fallback_searches': ['planetary gears transmission close up', 'planetary gears transmission internal mechanism'], 'title': 'كيف يعمل التروس الكوكبية', 'text': 'كيف يعمل التروس الكوكبية داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'planetary gears transmission', 'fallback_searches': ['planetary gears transmission close up', 'planetary gears transmission internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق التروس الكوكبية', 'text': 'يحتاج التروس الكوكبية إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'planetary gears transmission', 'fallback_searches': ['planetary gears transmission close up', 'planetary gears transmission internal mechanism'], 'title': 'كيف تنتقل القوة فيه التروس الكوكبية', 'text': 'توضح آلية التروس الكوكبية كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'planetary gears transmission', 'fallback_searches': ['planetary gears transmission close up', 'planetary gears transmission internal mechanism'], 'title': 'كيف تتأثر حرارته التروس الكوكبية', 'text': 'تتأثر حرارة التروس الكوكبية بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'planetary gears transmission', 'fallback_searches': ['planetary gears transmission close up', 'planetary gears transmission internal mechanism'], 'title': 'ما الذي يحدث داخله التروس الكوكبية', 'text': 'داخل التروس الكوكبية تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'CVT transmission mechanism', 'fallback_searches': ['CVT transmission mechanism close up', 'CVT transmission mechanism internal mechanism'], 'title': 'كيف يعمل ناقل الحركة المتغير', 'text': 'كيف يعمل ناقل الحركة المتغير داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'CVT transmission mechanism', 'fallback_searches': ['CVT transmission mechanism close up', 'CVT transmission mechanism internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق ناقل الحركة المتغير', 'text': 'يحتاج ناقل الحركة المتغير إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'CVT transmission mechanism', 'fallback_searches': ['CVT transmission mechanism close up', 'CVT transmission mechanism internal mechanism'], 'title': 'كيف تنتقل القوة فيه ناقل الحركة المتغير', 'text': 'توضح آلية ناقل الحركة المتغير كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'CVT transmission mechanism', 'fallback_searches': ['CVT transmission mechanism close up', 'CVT transmission mechanism internal mechanism'], 'title': 'كيف تتأثر حرارته ناقل الحركة المتغير', 'text': 'تتأثر حرارة ناقل الحركة المتغير بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'CVT transmission mechanism', 'fallback_searches': ['CVT transmission mechanism close up', 'CVT transmission mechanism internal mechanism'], 'title': 'ما الذي يحدث داخله ناقل الحركة المتغير', 'text': 'داخل ناقل الحركة المتغير تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'dual clutch transmission', 'fallback_searches': ['dual clutch transmission close up', 'dual clutch transmission internal mechanism'], 'title': 'كيف يعمل القابض المزدوج', 'text': 'كيف يعمل القابض المزدوج داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'dual clutch transmission', 'fallback_searches': ['dual clutch transmission close up', 'dual clutch transmission internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق القابض المزدوج', 'text': 'يحتاج القابض المزدوج إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'dual clutch transmission', 'fallback_searches': ['dual clutch transmission close up', 'dual clutch transmission internal mechanism'], 'title': 'كيف تنتقل القوة فيه القابض المزدوج', 'text': 'توضح آلية القابض المزدوج كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'dual clutch transmission', 'fallback_searches': ['dual clutch transmission close up', 'dual clutch transmission internal mechanism'], 'title': 'كيف تتأثر حرارته القابض المزدوج', 'text': 'تتأثر حرارة القابض المزدوج بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'dual clutch transmission', 'fallback_searches': ['dual clutch transmission close up', 'dual clutch transmission internal mechanism'], 'title': 'ما الذي يحدث داخله القابض المزدوج', 'text': 'داخل القابض المزدوج تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'driveshaft automotive', 'fallback_searches': ['driveshaft automotive close up', 'driveshaft automotive internal mechanism'], 'title': 'كيف يعمل عمود الإدارة', 'text': 'كيف يعمل عمود الإدارة داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'driveshaft automotive', 'fallback_searches': ['driveshaft automotive close up', 'driveshaft automotive internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق عمود الإدارة', 'text': 'يحتاج عمود الإدارة إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'driveshaft automotive', 'fallback_searches': ['driveshaft automotive close up', 'driveshaft automotive internal mechanism'], 'title': 'كيف تنتقل القوة فيه عمود الإدارة', 'text': 'توضح آلية عمود الإدارة كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'driveshaft automotive', 'fallback_searches': ['driveshaft automotive close up', 'driveshaft automotive internal mechanism'], 'title': 'كيف تتأثر حرارته عمود الإدارة', 'text': 'تتأثر حرارة عمود الإدارة بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'driveshaft automotive', 'fallback_searches': ['driveshaft automotive close up', 'driveshaft automotive internal mechanism'], 'title': 'ما الذي يحدث داخله عمود الإدارة', 'text': 'داخل عمود الإدارة تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'universal joint driveshaft', 'fallback_searches': ['universal joint driveshaft close up', 'universal joint driveshaft internal mechanism'], 'title': 'كيف يعمل المفصل العام', 'text': 'كيف يعمل المفصل العام داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'universal joint driveshaft', 'fallback_searches': ['universal joint driveshaft close up', 'universal joint driveshaft internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق المفصل العام', 'text': 'يحتاج المفصل العام إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'universal joint driveshaft', 'fallback_searches': ['universal joint driveshaft close up', 'universal joint driveshaft internal mechanism'], 'title': 'كيف تنتقل القوة فيه المفصل العام', 'text': 'توضح آلية المفصل العام كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'universal joint driveshaft', 'fallback_searches': ['universal joint driveshaft close up', 'universal joint driveshaft internal mechanism'], 'title': 'كيف تتأثر حرارته المفصل العام', 'text': 'تتأثر حرارة المفصل العام بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'universal joint driveshaft', 'fallback_searches': ['universal joint driveshaft close up', 'universal joint driveshaft internal mechanism'], 'title': 'ما الذي يحدث داخله المفصل العام', 'text': 'داخل المفصل العام تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'CV joint axle', 'fallback_searches': ['CV joint axle close up', 'CV joint axle internal mechanism'], 'title': 'كيف يعمل المفصل المتجانس', 'text': 'كيف يعمل المفصل المتجانس داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'CV joint axle', 'fallback_searches': ['CV joint axle close up', 'CV joint axle internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق المفصل المتجانس', 'text': 'يحتاج المفصل المتجانس إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'CV joint axle', 'fallback_searches': ['CV joint axle close up', 'CV joint axle internal mechanism'], 'title': 'كيف تنتقل القوة فيه المفصل المتجانس', 'text': 'توضح آلية المفصل المتجانس كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'CV joint axle', 'fallback_searches': ['CV joint axle close up', 'CV joint axle internal mechanism'], 'title': 'كيف تتأثر حرارته المفصل المتجانس', 'text': 'تتأثر حرارة المفصل المتجانس بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'CV joint axle', 'fallback_searches': ['CV joint axle close up', 'CV joint axle internal mechanism'], 'title': 'ما الذي يحدث داخله المفصل المتجانس', 'text': 'داخل المفصل المتجانس تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'differential gears automotive', 'fallback_searches': ['differential gears automotive close up', 'differential gears automotive internal mechanism'], 'title': 'كيف يعمل الدفرنس', 'text': 'كيف يعمل الدفرنس داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'differential gears automotive', 'fallback_searches': ['differential gears automotive close up', 'differential gears automotive internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق الدفرنس', 'text': 'يحتاج الدفرنس إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'differential gears automotive', 'fallback_searches': ['differential gears automotive close up', 'differential gears automotive internal mechanism'], 'title': 'كيف تنتقل القوة فيه الدفرنس', 'text': 'توضح آلية الدفرنس كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'differential gears automotive', 'fallback_searches': ['differential gears automotive close up', 'differential gears automotive internal mechanism'], 'title': 'كيف تتأثر حرارته الدفرنس', 'text': 'تتأثر حرارة الدفرنس بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'differential gears automotive', 'fallback_searches': ['differential gears automotive close up', 'differential gears automotive internal mechanism'], 'title': 'ما الذي يحدث داخله الدفرنس', 'text': 'داخل الدفرنس تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'wheel bearing automotive', 'fallback_searches': ['wheel bearing automotive close up', 'wheel bearing automotive internal mechanism'], 'title': 'كيف يعمل محمل العجلة', 'text': 'كيف يعمل محمل العجلة داخل منظومة السيارة، وما الحركة أو القوة التي ينقلها؟ فهم هذه الآلية يوضح لماذا يعتمد الجزء على تصميمه الهندسي وطريقة ارتباطه ببقية المنظومة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'wheel bearing automotive', 'fallback_searches': ['wheel bearing automotive close up', 'wheel bearing automotive internal mechanism'], 'title': 'لماذا يحتاج إلى تصميم دقيق محمل العجلة', 'text': 'يحتاج محمل العجلة إلى تصميم وأبعاد دقيقة لأن أي تغير في الحركة أو الخلوص أو الضغط يغير طريقة عمل المنظومة. لذلك ترتبط كفاءته مباشرة بالهندسة الميكانيكية للجزء.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'wheel bearing automotive', 'fallback_searches': ['wheel bearing automotive close up', 'wheel bearing automotive internal mechanism'], 'title': 'كيف تنتقل القوة فيه محمل العجلة', 'text': 'توضح آلية محمل العجلة كيف تنتقل القوة داخل مجموعة الحركة أو المنظومة الميكانيكية. تتوزع الأحمال بين الأسطح والمحاور والمفاصل بحسب اتجاه القوة وسرعة الحركة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'wheel bearing automotive', 'fallback_searches': ['wheel bearing automotive close up', 'wheel bearing automotive internal mechanism'], 'title': 'كيف تتأثر حرارته محمل العجلة', 'text': 'تتأثر حرارة محمل العجلة بالاحتكاك وتدفق السوائل أو الهواء والحمل الميكانيكي. زيادة الحمل ترفع الطاقة المتحولة إلى حرارة، لذلك يعتمد التصميم على تبديدها بطريقة محسوبة.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
    {'search': 'wheel bearing automotive', 'fallback_searches': ['wheel bearing automotive close up', 'wheel bearing automotive internal mechanism'], 'title': 'ما الذي يحدث داخله محمل العجلة', 'text': 'داخل محمل العجلة تحدث حركة ميكانيكية مستمرة بين أجزاء مترابطة. اختلاف السرعة والضغط والاحتكاك بين هذه الأجزاء هو الذي يحدد أداء المنظومة وكفاءتها.', 'hashtags': ['#Shorts', '#ميكانيكا_السيارات', '#هندسة', '#علوم']},
]
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

# =========================================================
# HARD CONTENT BLOCKLIST
# =========================================================
# These are hard filters: a topic is rejected before generation if its
# title/script contains one of these prohibited subjects.
# The Pexels search phrase is intentionally NOT scanned because it is an
# internal English search query and must not be confused with spoken text.
BLOCKED_CONTENT_TERMS = [
    # Politics / elections / political actors
    "سياسة", "سياسي", "السياسة", "انتخابات", "انتخاب", "حزب سياسي",
    "حكومة", "رئيس", "وزير", "برلمان", "مجلس الشورى", "تصويت",
    "مرشح", "مرشحة", "حملة انتخابية", "انتخابي",

    # Sexual / explicit content
    "جنس", "جنسي", "إباحية", "اباحي", "إباحي", "محتوى إباحي",
    "علاقة جنسية", "ممارسة جنسية", "اعتداء جنسي",

    # Sexual-orientation topics
    "مثلية", "المثلية", "مثلي", "مثلية جنسية", "شذوذ", "شاذ جنسيا",

    # Drugs / intoxication
    "مخدرات", "مخدر", "هيروين", "كوكايين", "كريستال ميث", "الميثامفيتامين",
    "حشيش", "ماريجوانا", "قنب", "تعاطي المخدرات",

    # Gambling / betting
    "قمار", "مقامرة", "مراهنات", "مراهنة", "رهان", "كازينو",

    # Weapons / explosives
    "أسلحة", "سلاح", "بندقية", "مسدس", "رصاص", "ذخيرة", "متفجرات",
    "قنبلة", "قنابل", "تفجير", "متفجر",

    # Crime / violent or graphic subjects
    "جريمة", "جرائم", "قتل", "قاتل", "اغتيال", "مجرم", "مجرمين",
    "اختطاف", "خطف", "ابتزاز", "سطو", "سرقة", "عصابة", "إرهاب",
    "إرهابي", "تعذيب", "دماء", "دموي", "مذبحة", "مجزرة",

    # Actors / actresses / singers / entertainers
    "ممثل", "ممثلة", "ممثلين", "ممثلات", "فنان", "فنانة", "فنانين",
    "مغني", "مغنية", "مغنين", "موسيقي", "مشاهير", "مشهور", "مشاهيرة",

    # Women/female-focused subjects, as requested for this channel
    "نساء", "النساء", "امرأة", "المرأة", "نساءً", "أنثى", "أنثوية",

    # Historical / geographic subjects
    "تاريخ", "تاريخي", "التاريخ", "جغرافيا", "جغرافي", "الجغرافيا",
    "عاصمة", "عواصم", "دولة", "دول", "خريطة", "خرائط",

    # Western-centric cultural topics to avoid
    "هوليوود", "أمريكا", "الولايات المتحدة", "بريطانيا", "بريطانيا العظمى",
    "إنجلترا", "فرنسا", "ألمانيا", "إيطاليا", "إسبانيا", "كندا",
    "أوروبا", "الغرب", "الغربي", "الغربية",
]


def find_blocked_content_terms(*texts):
    """Return hard-blocked terms without substring false positives."""
    combined = normalize_content(" ".join(str(x or "") for x in texts))
    found = []

    for term in BLOCKED_CONTENT_TERMS:
        normalized_term = normalize_content(term)
        if not normalized_term:
            continue

        # Match complete Arabic/word tokens, not arbitrary substrings.
        # This prevents false positives such as: رئيس داخل رئيسية، دول داخل الدورة،
        # سطو داخل السطوح، or خريطة داخل كلمة أطول.
        pattern = r"(?<![\w\u0600-\u06FF])" + re.escape(normalized_term) + r"(?![\w\u0600-\u06FF])"
        if re.search(pattern, combined, flags=re.IGNORECASE):
            found.append(term)

    return sorted(set(found), key=len, reverse=True)


def topic_is_allowed(topic):
    """Hard content gate used before a topic can be selected or published."""
    blocked = find_blocked_content_terms(
        topic.get("title", ""),
        topic.get("text", ""),
    )
    return not blocked, blocked



def validate_topic_pool():
    """Validate the active pool before generation.

    The pool intentionally contains automotive mechanics topics only. General car,
    driving, street, people, history, geography, and unrelated subjects are excluded.
    """
    if not TOPICS:
        raise RuntimeError("TOPICS is empty.")

    seen = set()
    for index, topic in enumerate(TOPICS, start=1):
        # Validate the actual stored fields first. Sanitizing must never make a
        # valid topic appear empty just because it contains punctuation/symbols.
        raw_title = str(topic.get("title", "") or "").strip()
        raw_text = str(topic.get("text", "") or "").strip()
        if not raw_title or not raw_text:
            raise RuntimeError(f"Topic {index} has an empty title or script.")

        # Clean for TTS/subtitles, but safely fall back to the original field
        # if an over-aggressive cleanup ever removes everything.
        title = sanitize_script(raw_title) if "sanitize_script" in globals() else raw_title
        text = sanitize_script(raw_text) if "sanitize_script" in globals() else raw_text
        if not title:
            title = raw_title
        if not text:
            text = raw_text

        allowed, blocked = topic_is_allowed({"title": title, "text": text})
        if not allowed:
            raise RuntimeError(
                f"Blocked topic detected at index {index}: {blocked}. "
                "Remove the prohibited subject from TOPICS."
            )

        key = normalize_content(title + " " + text)
        if key in seen:
            raise RuntimeError(f"Duplicate topic detected at index {index}.")
        seen.add(key)

    print(f"Unique content pool verified: {len(TOPICS)} topics")


def select_new_topic(used_content):
    # Never reuse a published topic. The comparison checks the title, full
    # script, and Pexels search phrase, including legacy memory records.
    available = []
    blocked_count = 0

    for topic in TOPICS:
        allowed, blocked = topic_is_allowed(topic)
        if not allowed:
            blocked_count += 1
            print(f"BLOCKED TOPIC SKIPPED: {topic.get('title', '')} -> {blocked}")
            continue

        if not content_already_used(topic, used_content):
            available.append(topic)

    if not available:
        raise RuntimeError(
            "ALL UNIQUE CONTENT TOPICS HAVE BEEN USED. Add new genuinely different topics to TOPICS."
        )

    topic = random.choice(available)

    print("\n================================")
    print("NEW CONTENT SELECTED")
    print(topic["title"])
    print(f"Remaining unused topics: {len(available) - 1}")
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


def choose_video_file(video, allow_landscape=True):
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

    if not allow_landscape:
        return None

    usable = [item for item in files if item.get("link") and (item.get("width") or 0) >= 640]
    if usable:
        return max(usable,key=lambda item:(item.get("width") or 0)*(item.get("height") or 0))
    return None


# =========================================================
# STRICT AUTOMOTIVE VISUAL FILTER
# =========================================================

AUTO_ALLOWED_VISUAL_TERMS = {
    "engine","piston","cylinder","crankshaft","camshaft","valve","turbocharger",
    "turbo","wastegate","supercharger","radiator","cooling","thermostat","water pump",
    "oil pump","oil filter","oil pan","oil cooler","timing chain","timing belt","tensioner",
    "intake manifold","throttle body","air filter","fuel injector","fuel pump","fuel rail",
    "spark plug","ignition coil","exhaust manifold","catalytic converter","muffler","egr",
    "clutch","flywheel","pressure plate","manual transmission","gearbox","synchronizer",
    "torque converter","planetary gear","cvt","dual clutch","driveshaft","universal joint",
    "cv joint","differential","axle","wheel bearing","brake rotor","brake disc","brake pad",
    "brake caliper","master cylinder","brake booster","drum brake","abs","steering rack",
    "pinion","power steering","ball joint","control arm","shock absorber","strut","coil spring",
    "sway bar","air suspension","wheel hub","wheel rim","tire","serpentine belt","alternator",
    "starter motor","compressor","vacuum pump","bearing","oil seal","gasket","heat shield",
    "combustion chamber","fuel injection","glow plug","intercooler","boost pressure","gear teeth",
}
AUTO_BANNED_VISUAL_TERMS = {
    "person","people","man","woman","human","mechanic","technician","driver","face","hand",
    "street","road","highway","traffic","city","building","landscape","mountain","beach",
    "parking","showroom","dealership","race","racing","motorsport","drift","drifting","track",
    "car exterior","car driving","driving","road trip","travel","vehicle exterior","car commercial",
    "portrait","selfie","crowd","garage door","dealership","logo","advertisement","showcase",
}

def _visual_query_key(text):
    return re.sub(r"[^a-z0-9 ]+"," ",str(text).lower()).strip()

def _visual_has_banned_term(text):
    words=set(_visual_query_key(text).split())
    return any(term in words for term in AUTO_BANNED_VISUAL_TERMS)

def build_visual_queries(topic):
    """Only generate highly specific mechanical-part searches; never generic car searches."""
    primary=clean_text(topic.get("search",""))
    queries=[]
    for q in [primary]+topic.get("fallback_searches",[]):
        q=clean_text(q)
        if not q: continue
        low=_visual_query_key(q)
        if _visual_has_banned_term(q): continue
        if not any(a in low for a in AUTO_ALLOWED_VISUAL_TERMS): continue
        if low not in {_visual_query_key(x) for x in queries}: queries.append(q)
    # Add only mechanical close-ups, never cinematic/general-car variants.
    if primary:
        for suffix in ["close up mechanism","internal mechanical parts","engine component close up"]:
            q=f"{primary} {suffix}"
            low=_visual_query_key(q)
            if _visual_has_banned_term(q): continue
            queries.append(q)
    return list(dict.fromkeys(queries))[:8]

def _strict_video_metadata_ok(video, topic):
    """Reject weak metadata, non-portrait files, and generic visual results."""
    vf=choose_video_file(video, allow_landscape=False)
    if not vf: return None
    width=int(vf.get("width") or 0); height=int(vf.get("height") or 0)
    if height <= width or width < 600 or height < 1000: return None
    hay=" ".join(str(video.get(k,"")) for k in ["url","image","type"]).lower()
    hay += " " + " ".join(str(x) for x in video.get("tags",[]) if x)
    if _visual_has_banned_term(hay): return None
    query_words=set(re.findall(r"[a-z]+",_visual_query_key(topic.get("search",""))))
    allowed_words=set(re.findall(r"[a-z]+",hay)) & AUTO_ALLOWED_VISUAL_TERMS
    # Pexels often omits semantic tags; in that case the exact query is still the gate.
    return {"file":vf,"width":width,"height":height,"semantic_count":len(allowed_words),"query_words":query_words}

def select_unique_videos(topic, used_clips):
    queries=build_visual_queries(topic)
    candidates={}
    for query in queries:
        print(f"STRICT Pexels search: {query}")
        for page in range(1,5):
            try: videos=search_pexels(query,page)
            except Exception as error:
                print("Pexels search error:",error); continue
            for video in videos:
                vid=str(video.get("id",""))
                if not vid or vid in used_clips: continue
                checked=_strict_video_metadata_ok(video,topic)
                if not checked: continue
                score=checked["width"]*checked["height"] + checked["semantic_count"]*10_000_000
                candidates[vid]={"id":vid,"link":checked["file"]["link"],"width":checked["width"],"height":checked["height"],"portrait":True,"score":score}
            if len(candidates)>=80: break
        if len(candidates)>=max(NUMBER_OF_CLIPS*6,54): break
    pool=sorted(candidates.values(),key=lambda x:x["score"],reverse=True)
    if len(pool)<NUMBER_OF_CLIPS:
        raise RuntimeError(f"STRICT VISUAL FILTER: only {len(pool)} verified mechanical clips found; need {NUMBER_OF_CLIPS}. No unrelated fallback is allowed.")
    # Prefer top quality while retaining clip diversity.
    top=pool[:max(NUMBER_OF_CLIPS*3,27)]
    random.shuffle(top)
    selected=top[:NUMBER_OF_CLIPS]
    print("STRICT VERIFIED NEW Pexels IDs:")
    for x in selected: print(" ",x["id"])
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
# SCRIPT SANITIZATION
# =========================================================
def sanitize_script(text):
    """Prepare one Arabic script for BOTH TTS and subtitles."""
    text = str(text or "")

    # Remove common introductory filler so the fact starts immediately.
    text = re.sub(
        r"^\s*(?:هل\s+تعلم(?:\s+أن)?|تدري(?:\s+أن)?|هل\s+كنت\s+تعلم(?:\s+أن)?|هل\s+فكرت\s+يومًا\s+أن?|هل\s+تساءلت\s+كيف)\s*[:،؟?!.\-—]*\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove URLs, email-like strings, hashtags, mentions and code-like fragments.
    text = re.sub(r"https?://\S+|www\.\S+|\S+@\S+", " ", text)
    text = re.sub(r"(?<!\w)[#@][\w\u0600-\u06FF_-]+", " ", text)

    # Remove Latin-script words/abbreviations from the spoken/caption script.
    # Arabic letters/numbers and normal Arabic punctuation remain.
    text = re.sub(r"[A-Za-z]+(?:[-_][A-Za-z0-9]+)*", " ", text)

    # Remove technical/special symbols; keep Arabic punctuation.
    text = re.sub(r"[`~!$%^&*_=+<>|{}\[\]\\/:;\"'“”‘’…•·]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Remove leading/trailing punctuation left by the cleanup.
    text = re.sub(r"^[،؛:؟?.،\-—\s]+|[،؛:؟?.،\-—\s]+$", "", text)

    return text.strip()


def prepare_topic_script(topic):
    """Return a copy whose title/script are cleaned consistently."""
    cleaned = dict(topic)
    cleaned["text"] = sanitize_script(topic.get("text", ""))
    cleaned["title"] = sanitize_script(topic.get("title", ""))
    return cleaned

# =========================================================
# VOICE
# =========================================================

def create_voice(text):
    """
    Use Azure Neural Speech when configured; otherwise preserve the existing
    Edge-TTS fallback so the workflow does not become dependent on a paid API.
    """
    if False and AZURE_SPEECH_KEY and AZURE_SPEECH_REGION:
        print("Azure disabled: exact Edge word-boundary timing is required.")

        url = (
            f"https://{AZURE_SPEECH_REGION}.tts.speech.microsoft.com/"
            "cognitiveservices/v1"
        )

        headers = {
            "Ocp-Apim-Subscription-Key": AZURE_SPEECH_KEY,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-160kbitrate-mono-mp3",
            "User-Agent": "youtube-shorts-automation",
        }

        safe_text = (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

        ssml = f"""<speak version="1.0"
xmlns="http://www.w3.org/2001/10/synthesis"
xml:lang="ar-SA">
<voice name="{AZURE_VOICE_NAME}">
<prosody rate="0%" pitch="0%">
{safe_text}
</prosody>
</voice>
</speak>"""

        response = requests.post(
            url,
            headers=headers,
            data=ssml.encode("utf-8"),
            timeout=60,
        )
        response.raise_for_status()
        VOICE_FILE.write_bytes(response.content)

    else:
        print("Azure Speech secrets not found; using Edge Neural TTS fallback.")

        async def generate():
            # Stream Edge-TTS so we capture its real word-boundary timestamps.
            # These timestamps are later used directly for ASS highlighting.
            communicate = edge_tts.Communicate(
                text, VOICE_NAME, rate=VOICE_RATE,
                volume=VOICE_VOLUME, pitch=VOICE_PITCH,
            )
            audio_parts = []
            boundaries = []
            async for item in communicate.stream():
                if item["type"] == "audio":
                    audio_parts.append(item["data"])
                elif item["type"] == "WordBoundary":
                    data = item.get("offset", 0)
                    duration = item.get("duration", 0)
                    word = str(item.get("text", "")).strip()
                    if word:
                        boundaries.append({
                            "word": word,
                            "start": float(data) / 10_000_000,
                            "end": float(data + duration) / 10_000_000,
                        })
            VOICE_FILE.write_bytes(b"".join(audio_parts))
            with open(WORK_DIR / "word_timings.json", "w", encoding="utf-8") as f:
                json.dump(boundaries, f, ensure_ascii=False, indent=2)

        last_error = None
        for attempt in range(1, 4):
            try:
                if VOICE_FILE.exists():
                    VOICE_FILE.unlink()
                asyncio.run(generate())
                if VOICE_FILE.exists() and VOICE_FILE.stat().st_size >= 1000:
                    break
            except Exception as error:
                last_error = error
                print(f"Edge TTS attempt {attempt}/3 failed: {error}")
                if attempt < 3:
                    time.sleep(2 * attempt)
        else:
            raise RuntimeError(f"Edge TTS failed after 3 attempts: {last_error}")

    if not VOICE_FILE.exists() or VOICE_FILE.stat().st_size < 1000:
        raise RuntimeError("Voice file was not created correctly.")

    # Verify that the generated file really contains an audio stream before
    # the video pipeline starts. This prevents silent/corrupt voice files from
    # reaching the final render.
    try:
        command_output([
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(VOICE_FILE),
        ])
    except Exception as error:
        raise RuntimeError(f"Generated voice file is not a valid audio file: {error}") from error


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


def load_word_timings(text, duration):
    """Load Edge-TTS word boundaries and align them to the cleaned script."""
    path = WORK_DIR / "word_timings.json"
    if not path.exists():
        raise RuntimeError("Word timing data was not created by Edge-TTS.")
    data = json.loads(path.read_text(encoding="utf-8"))
    words = clean_text(text).split()
    observed = [str(x.get("word", "")).strip() for x in data if str(x.get("word", "")).strip()]
    # Edge can attach punctuation differently. Compare normalized tokens first.
    norm = lambda x: re.sub(r"[،؛:؟?!.,\"'()\[\]{}]", "", x).strip()
    if [norm(x) for x in observed] != [norm(x) for x in words]:
        raise RuntimeError("Edge word boundaries do not match the narration text exactly; subtitles were refused.")
    cleaned=[]
    for i,x in enumerate(data):
        st=max(0.0,float(x["start"]))
        en=max(st+0.03,float(x["end"]))
        if i and st < cleaned[-1]["start"]:
            raise RuntimeError("Invalid non-monotonic Edge word timing detected.")
        cleaned.append({"word":words[i],"start":st,"end":en})
    if cleaned:
        cleaned[0]["start"]=max(0.0,cleaned[0]["start"]-0.03)
        cleaned[-1]["end"]=min(duration,cleaned[-1]["end"]+0.04)
    return cleaned


def create_subtitle_file(text, duration):
    """Create word-accurate Arabic ASS captions; no guessed character timing."""
    words = load_word_timings(text, duration)
    if not words:
        raise RuntimeError("No word timings available for subtitles.")

    # New visual style: modern Arabic font, white base text, cyan active word.
    # ASS uses explicit RTL mark to keep Arabic logical order stable in libass.
    ass_header = """[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\nWrapStyle: 2\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Arabic,Noto Sans Arabic,66,&H00FFFFFF,&H00FFFFFF,&H00181818,&H99000000,-1,0,0,0,100,100,1,0,3,2,1,2,90,90,420,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""
    rlm='\u200f'
    def esc(w): return escape_ass_text(w)
    with open(SUBTITLE_FILE,"w",encoding="utf-8-sig") as file:
        file.write(ass_header)
        # Display up to 5 words at a time, but every event uses actual Edge timing.
        group_size=5
        for i in range(0,len(words),group_size):
            group=words[i:i+group_size]
            start=group[0]["start"]
            end=min(duration,group[-1]["end"]+0.02)
            for j,w in enumerate(group):
                parts=[]
                for k,x in enumerate(group):
                    word=esc(x["word"])
                    if k==j:
                        word=r'{\c&H00FFFF00&}'+word+r'{\c&H00FFFFFF&}'
                    parts.append(word)
                # Reverse visual token order because libass Arabic bidi otherwise
                # produced the user's reported reversed on-screen sequence.
                caption=rlm+" ".join(reversed(parts))
                # The logical order remains the narration order; only the ASS
                # visual token order is reversed for stable Arabic rendering.
                file.write(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Arabic,,0,0,0,,{caption}\n")


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

    # Voice polish: remove inaudible rumble, gently limit the upper band,
    # control sharp level changes, then normalize for consistent Shorts volume.
    # The chain is intentionally conservative so it improves clarity without
    # making the neural voice sound metallic or over-processed.
    audio_filter = (
        "highpass=f=70,"
        "lowpass=f=15500,"
        "acompressor=threshold=-20dB:ratio=2.0:attack=12:release=110:makeup=1,"
        "aresample=48000:resampler=soxr:precision=28,"
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
        "-b:a", "192k",
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

def main():
    print("\n========================================")
    print("YOUTUBE SHORTS AUTOMATION - PROFESSIONAL MODE")
    print("========================================\n")

    check_environment()
    validate_topic_pool()

    used_content = load_used_content()
    used_clips = load_used_clips()

    topic = select_new_topic(used_content)
    topic = prepare_topic_script(topic)

    if not topic["text"]:
        raise RuntimeError("The selected topic became empty after Arabic text cleanup.")

    print("Clean Arabic script:")
    print(topic["text"])

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

    print("\nCreating Arabic voice with exact word timing...")
    create_voice(topic["text"])

    print("\nCreating final Short...")
    create_final_video(
        silent_video,
        topic["text"],
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
