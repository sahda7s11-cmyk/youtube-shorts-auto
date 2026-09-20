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
    {
        "search": "football stadium match players",
        "fallback_searches": ["football match stadium", "soccer stadium players", "football players action"],
        "title": "هل تعلم لماذا أصبحت البيانات مهمة جدًا في كرة القدم؟",
        "text": "هل تعلم أن كرة القدم الحديثة أصبحت تعتمد على البيانات بشكل مذهل؟ المدربون يستطيعون تحليل سرعة اللاعب وعدد تمريراته ومساحاته داخل الملعب وحتى تحركات الفريق بالكامل. هذه البيانات تساعد المدرب على اكتشاف نقاط القوة والضعف وقد تغيّر طريقة لعب الفريق في المباراة التالية.",
        "hashtags": ["#Shorts", "#كرة_القدم", "#هل_تعلم", "#معلومات", "#Football", "#Soccer"],
    },
    {
        "search": "football player running match",
        "fallback_searches": ["soccer player running", "football fitness", "soccer match action"],
        "title": "هل تعلم كم يركض لاعب كرة القدم في المباراة؟",
        "text": "هل فكرت يومًا كم يركض لاعب كرة القدم خلال مباراة واحدة؟ اللاعب المحترف يقطع عدة كيلومترات أثناء المباراة، لكن المثير أن المسافة ليست كل شيء. فاللاعب يغيّر سرعته باستمرار بين المشي والركض والجري السريع. ولهذا تحتاج كرة القدم الحديثة إلى لياقة عالية وسرعة كبيرة في اتخاذ القرار.",
        "hashtags": ["#Shorts", "#كرة_القدم", "#هل_تعلم", "#Football", "#Soccer", "#رياضة"],
    },
    {
        "search": "football goalkeeper save",
        "fallback_searches": ["soccer goalkeeper", "goalkeeper training", "football goalkeeper action"],
        "title": "لماذا يبدو حارس المرمى أسرع مما تتوقع؟",
        "text": "هل تعلم أن حارس المرمى يحتاج إلى اتخاذ قرار في لحظة قصيرة جدًا؟ الحارس لا يعتمد على سرعة يديه فقط، بل يقرأ وضعية اللاعب واتجاه جسمه قبل التسديدة. ولهذا يبدأ أحيانًا بالتحرك قبل أن تصل الكرة إليه. في المستوى الاحترافي، جزء من الثانية قد يصنع الفرق.",
        "hashtags": ["#Shorts", "#كرة_القدم", "#حراس_المرمى", "#هل_تعلم", "#Football", "#Soccer"],
    },
    {
        "search": "football fans stadium crowd",
        "fallback_searches": ["soccer fans stadium", "football crowd", "football supporters"],
        "title": "هل تعلم لماذا تختلف أجواء ملاعب كرة القدم؟",
        "text": "هل لاحظت أن بعض ملاعب كرة القدم تبدو مختلفة تمامًا من ناحية الأجواء؟ التصميم وحجم المدرجات وطريقة توزيع الجماهير كلها تؤثر في تجربة المشجعين داخل الملعب. ولهذا أصبحت بعض الملاعب الحديثة مصممة لتكون تجربة كاملة، وليس مجرد مكان لمشاهدة المباراة.",
        "hashtags": ["#Shorts", "#كرة_القدم", "#جماهير", "#ملاعب", "#هل_تعلم", "#Football"],
    },
    {
        "search": "football training player",
        "fallback_searches": ["soccer training", "football skills training", "soccer practice"],
        "title": "لماذا يتدرب لاعبو كرة القدم على أشياء تبدو بسيطة؟",
        "text": "هل تعلم أن أبسط المهارات في كرة القدم تحتاج إلى تكرار هائل؟ التمرير واستلام الكرة والتحرك بدون كرة كلها مهارات يتدرب عليها اللاعبون باستمرار حتى تصبح تلقائية. وعندما تصل المباراة إلى لحظة حاسمة، يحتاج اللاعب إلى تنفيذ المهارة بسرعة دون تردد.",
        "hashtags": ["#Shorts", "#كرة_القدم", "#تدريب", "#هل_تعلم", "#Football", "#Soccer"],
    },
    {
        "search": "football goal scoring",
        "fallback_searches": ["soccer goal", "football striker", "soccer scoring"],
        "title": "هل تعلم لماذا يصعب تسجيل الهدف في كرة القدم؟",
        "text": "تسجيل الهدف في كرة القدم ليس مجرد تسديدة قوية. اللاعب يحتاج إلى اختيار المكان والتوقيت والزاوية المناسبة خلال ثوانٍ قليلة. ولهذا قد تكون اللمسة الأخيرة أهم من قوة التسديدة نفسها. وفي المباريات الكبيرة، قرار واحد سريع قد يغيّر النتيجة بالكامل.",
        "hashtags": ["#Shorts", "#كرة_القدم", "#أهداف", "#هل_تعلم", "#Football", "#Soccer"],
    },
    {
        "search": "space earth science",
        "fallback_searches": ["earth space", "planet earth", "solar system"],
        "title": "هل تعلم أنك تتحرك الآن رغم أنك جالس؟",
        "text": "هل تعلم أنك تتحرك الآن رغم أنك جالس في مكانك؟ الأرض تدور حول نفسها، وفي الوقت نفسه تتحرك حول الشمس. والنظام الشمسي نفسه يتحرك داخل مجرة درب التبانة. وهذا يعني أننا في حركة مستمرة، حتى عندما نشعر أننا ثابتون تمامًا.",
        "hashtags": ["#Shorts", "#هل_تعلم", "#علوم", "#معلومات", "#فضاء", "#Science"],
    },
    {
        "search": "ocean underwater marine life",
        "fallback_searches": ["deep ocean", "underwater sea", "marine animals"],
        "title": "لماذا ما زال جزء كبير من المحيط غامضًا؟",
        "text": "هل تعلم أن أعماق المحيط ما زالت تحتوي على مناطق لم نعرف عنها الكثير؟ الضغط والظلام والظروف القاسية تجعل استكشاف الأعماق صعبًا جدًا. ولهذا تستمر البعثات العلمية في اكتشاف كائنات وبيئات جديدة. المحيط الذي نراه من السطح يخفي عالمًا مختلفًا تمامًا.",
        "hashtags": ["#Shorts", "#علوم", "#محيط", "#هل_تعلم", "#Science"],
    },
    {
        "search": "lightning storm science",
        "fallback_searches": ["thunderstorm lightning", "lightning sky", "storm clouds"],
        "title": "كيف يمكن لبرق واحد أن يكون قويًا جدًا؟",
        "text": "البرق ليس مجرد وميض في السماء. إنه تفريغ كهربائي هائل يحدث عندما تتراكم شحنات كهربائية داخل السحب. ولهذا يمكن أن يظهر البرق بطاقة ضخمة خلال فترة زمنية قصيرة جدًا. والصوت الذي نسمعه بعده هو الرعد الناتج عن التسخين السريع للهواء.",
        "hashtags": ["#Shorts", "#علوم", "#برق", "#طقس", "#هل_تعلم", "#Science"],
    },
    {
        "search": "volcano eruption lava",
        "fallback_searches": ["volcano mountain", "lava volcano", "volcanic eruption"],
        "title": "ماذا يحدث داخل البركان قبل ثورانه؟",
        "text": "قبل ثوران البركان تحدث تغيرات في باطن الأرض. الصهارة والغازات يمكن أن تتحرك داخل النظام البركاني وتؤثر في الضغط الموجود تحت السطح. ولهذا يراقب العلماء الزلازل والغازات والتغيرات الأرضية لفهم نشاط البراكين بشكل أفضل.",
        "hashtags": ["#Shorts", "#براكين", "#علوم", "#هل_تعلم", "#Science"],
    },
    {
        "search": "airplane flying cockpit",
        "fallback_searches": ["aircraft flying sky", "airplane takeoff", "commercial airplane"],
        "title": "كيف يعرف الطيار مكان الطائرة في السماء؟",
        "text": "هل تساءلت كيف يعرف الطيار مكان الطائرة أثناء الرحلة؟ الطائرات تستخدم مجموعة من أنظمة الملاحة والأجهزة لتحديد الموقع والاتجاه والارتفاع والسرعة. كما يتابع الطيارون تعليمات المراقبة الجوية وخطة الرحلة. كل هذه الأنظمة تعمل معًا للحفاظ على مسار الرحلة.",
        "hashtags": ["#Shorts", "#طيران", "#طيارات", "#هل_تعلم", "#Science"],
    },
    {
        "search": "modern car technology driving",
        "fallback_searches": ["modern car road", "electric car driving", "car technology"],
        "title": "لماذا أصبحت السيارات الحديثة مليئة بالحساسات؟",
        "text": "السيارات الحديثة تحتوي على عدد كبير من الحساسات. بعضها يراقب السرعة وبعضها المسافة وبعضها يساعد أنظمة السلامة. هذه البيانات تسمح للسيارة بمراقبة ما يحدث حولها وتحسين عمل العديد من الأنظمة أثناء القيادة.",
        "hashtags": ["#Shorts", "#سيارات", "#تقنية", "#هل_تعلم", "#Cars", "#Technology"],
    },
    {
        "search": "robot technology laboratory",
        "fallback_searches": ["robotics technology", "robot machine", "future technology"],
        "title": "كيف تستطيع الروبوتات تنفيذ حركات دقيقة؟",
        "text": "الروبوت لا يتحرك بطريقة عشوائية. يستخدم محركات وحساسات وبرمجيات للتحكم في الحركة. وبحسب تصميمه يمكنه قياس موقع أجزائه وتعديل الحركة باستمرار للوصول إلى نتيجة دقيقة.",
        "hashtags": ["#Shorts", "#روبوت", "#تقنية", "#هل_تعلم", "#Technology"],
    },
    {
        "search": "computer processor technology",
        "fallback_searches": ["computer chip", "processor technology", "computer hardware"],
        "title": "ماذا يفعل المعالج داخل جهازك؟",
        "text": "المعالج هو أحد أهم المكونات داخل الكمبيوتر والهاتف. وظيفته تنفيذ التعليمات ومعالجة العمليات التي تطلبها البرامج. وكلما تطورت المعالجات أصبحت قادرة على تنفيذ عمليات أكثر بسرعة وكفاءة أعلى.",
        "hashtags": ["#Shorts", "#تقنية", "#كمبيوتر", "#هل_تعلم", "#Technology"],
    },
    {
        "search": "internet data center servers",
        "fallback_searches": ["server room", "data center", "internet servers"],
        "title": "أين تذهب بياناتك عندما تستخدم الإنترنت؟",
        "text": "عندما تستخدم تطبيقًا أو موقعًا على الإنترنت، قد تنتقل البيانات بين جهازك وخوادم موجودة في مراكز بيانات. هذه الخوادم تعالج الطلبات وتخزن أنواعًا مختلفة من المعلومات وتعيد البيانات إلى جهازك خلال وقت قصير جدًا.",
        "hashtags": ["#Shorts", "#إنترنت", "#تقنية", "#هل_تعلم", "#Technology"],
    },
    {
        "search": "rocket launch space",
        "fallback_searches": ["rocket launch", "spacecraft launch", "rocket space"],
        "title": "لماذا تحتاج الصواريخ إلى قوة هائلة عند الإطلاق؟",
        "text": "الصاروخ يحتاج إلى توليد قوة دفع كبيرة جدًا حتى يبدأ بالابتعاد عن الأرض. كلما ارتفع الصاروخ تتغير الظروف المحيطة به. ولهذا صُممت مراحل الصاروخ وأنظمة الدفع بدقة لتوفير الطاقة المطلوبة خلال أجزاء مختلفة من الرحلة.",
        "hashtags": ["#Shorts", "#فضاء", "#صواريخ", "#علوم", "#هل_تعلم", "#Science"],
    },
    {
        "search": "moon night sky",
        "fallback_searches": ["moon space", "full moon sky", "lunar surface"],
        "title": "لماذا نرى القمر بأشكال مختلفة خلال الشهر؟",
        "text": "القمر لا يغيّر شكله فعليًا خلال الشهر. الذي يتغير هو الجزء المضيء الذي نراه من الأرض مع دوران القمر حول كوكبنا. ولهذا تظهر لنا مراحل مختلفة مثل الهلال والبدر.",
        "hashtags": ["#Shorts", "#القمر", "#فضاء", "#علوم", "#هل_تعلم"],
    },
    {
        "search": "human eye vision science",
        "fallback_searches": ["eye anatomy", "human vision", "eyes science"],
        "title": "كيف تستطيع عيناك رؤية العالم من حولك؟",
        "text": "العين تستقبل الضوء من البيئة المحيطة ثم تحوله إلى إشارات عصبية تنتقل إلى الدماغ. بعد ذلك يعالج الدماغ هذه الإشارات حتى تتكون لدينا الصورة التي نراها. لذلك الرؤية ليست وظيفة العين وحدها.",
        "hashtags": ["#Shorts", "#علوم", "#جسم_الإنسان", "#هل_تعلم", "#Science"],
    },
    {
        "search": "human brain neuroscience",
        "fallback_searches": ["brain science", "neuroscience", "human brain"],
        "title": "لماذا يُعد الدماغ من أعقد أعضاء الجسم؟",
        "text": "الدماغ مسؤول عن عدد هائل من العمليات في جسم الإنسان. فهو يشارك في الحركة والتفكير والذاكرة ومعالجة المعلومات والعديد من الوظائف الأخرى. ولهذا ما زال العلماء يدرسون الكثير من أسراره لفهم طريقة عمله بشكل أدق.",
        "hashtags": ["#Shorts", "#دماغ", "#علوم", "#هل_تعلم", "#Science"],
    },
    {
        "search": "plant growth nature sunlight",
        "fallback_searches": ["plants sunlight", "plant growth", "green plants"],
        "title": "كيف تصنع النباتات غذاءها؟",
        "text": "النباتات تستخدم عملية تسمى البناء الضوئي لصنع غذائها. تستخدم الضوء والماء وثاني أكسيد الكربون لإنتاج الطاقة الكيميائية التي تحتاج إليها. ولهذا يعد ضوء الشمس جزءًا أساسيًا من حياة معظم النباتات.",
        "hashtags": ["#Shorts", "#نباتات", "#علوم", "#هل_تعلم", "#Science"],
    },
    {
        "search": "desert sand dunes landscape",
        "fallback_searches": ["desert landscape", "sand dunes", "desert nature"],
        "title": "لماذا تتحرك بعض الكثبان الرملية؟",
        "text": "الكثبان الرملية ليست ثابتة دائمًا. عندما تهب الرياح يمكنها نقل حبيبات الرمل من مكان إلى آخر. ومع استمرار حركة الرمال قد يتغير شكل الكثيب وموقعه تدريجيًا. ولهذا تبدو بعض الصحارى وكأنها تتغير مع الوقت.",
        "hashtags": ["#Shorts", "#صحراء", "#طبيعة", "#علوم", "#هل_تعلم"],
    },
    {
        "search": "waterfall river nature",
        "fallback_searches": ["river nature", "waterfall landscape", "fresh water"],
        "title": "لماذا تتحرك الأنهار باستمرار نحو مناطق منخفضة؟",
        "text": "الماء يتأثر بالجاذبية، ولهذا تتحرك الأنهار عادة من المناطق الأعلى نحو المناطق الأقل ارتفاعًا. وخلال رحلتها يمكن للمياه أن تنحت الصخور والتربة وتغيّر شكل البيئة المحيطة بها على مدى فترات طويلة.",
        "hashtags": ["#Shorts", "#أنهار", "#طبيعة", "#علوم", "#هل_تعلم"],
    },
    {
        "search": "shark underwater ocean",
        "fallback_searches": ["shark swimming", "marine predator", "ocean shark"],
        "title": "لماذا تُعد أسماك القرش مهمة للنظام البحري؟",
        "text": "أسماك القرش جزء مهم من كثير من الأنظمة البيئية البحرية. وجود المفترسات يساعد في الحفاظ على توازن أعداد الكائنات الأخرى. ولهذا فإن اختفاء نوع مهم من النظام البيئي قد يؤثر في أنواع وعمليات أخرى مرتبطة به.",
        "hashtags": ["#Shorts", "#أسماك_القرش", "#محيط", "#علوم", "#هل_تعلم"],
    },
    {
        "search": "penguin antarctica ice",
        "fallback_searches": ["penguins ice", "antarctica wildlife", "penguin colony"],
        "title": "كيف تستطيع البطاريق العيش في البرد القارس؟",
        "text": "البطاريق تمتلك تكيفات تساعدها على تحمل البيئات الباردة. ريشها الكثيف وطبقات العزل في أجسامها تساعدها على الاحتفاظ بالحرارة. كما أن بعض الأنواع تتجمع معًا لتقليل فقدان الحرارة.",
        "hashtags": ["#Shorts", "#بطاريق", "#حيوانات", "#علوم", "#هل_تعلم"],
    },
    {
        "search": "cheetah running wildlife",
        "fallback_searches": ["cheetah speed", "wild cat running", "cheetah animal"],
        "title": "لماذا يُعد الفهد من أسرع الحيوانات البرية؟",
        "text": "الفهد يمتلك جسمًا مصممًا للانطلاق السريع. أطرافه وعموده الفقري وعضلاته تساعده على زيادة سرعته خلال وقت قصير. لكن هذه السرعة العالية تحتاج إلى طاقة كبيرة ولهذا لا يستطيع الحفاظ على أقصى سرعته لفترات طويلة.",
        "hashtags": ["#Shorts", "#فهد", "#حيوانات", "#هل_تعلم", "#Science"],
    },
    {
        "search": "ancient ruins archaeology",
        "fallback_searches": ["ancient civilization ruins", "archaeology discovery", "ancient history"],
        "title": "كيف يعرف العلماء عمر الآثار القديمة؟",
        "text": "العلماء لا يعتمدون على طريقة واحدة لمعرفة عمر الآثار. يمكن استخدام أساليب مختلفة حسب نوع المادة والعينة. كما تساعد طبقات التربة والسياق الأثري والمقارنة التاريخية في بناء صورة أدق عن عمر الموقع أو القطعة.",
        "hashtags": ["#Shorts", "#تاريخ", "#آثار", "#هل_تعلم", "#History"],
    },
    {
        "search": "ancient egypt pyramids",
        "fallback_searches": ["egypt pyramids", "ancient egypt", "pyramid history"],
        "title": "كيف بُنيت الأهرامات قبل آلاف السنين؟",
        "text": "بناء الأهرامات كان مشروعًا هندسيًا ضخمًا بالنسبة لعصره. اعتمد المصريون القدماء على التخطيط والعمالة والأدوات وطرق النقل لنقل الأحجار وترتيبها بدقة. ولا تزال بعض تفاصيل تقنيات البناء القديمة محل دراسة ونقاش علمي.",
        "hashtags": ["#Shorts", "#مصر", "#أهرامات", "#تاريخ", "#هل_تعلم"],
    },
    {
        "search": "bridge engineering construction",
        "fallback_searches": ["modern bridge", "engineering bridge", "bridge construction"],
        "title": "كيف تستطيع الجسور تحمل أوزان ضخمة؟",
        "text": "الجسر لا يعتمد على مادة قوية فقط. التصميم الهندسي يوزع القوى والأحمال على أجزاء مختلفة من الهيكل. ويحسب المهندسون تأثير الوزن والرياح والاهتزازات وعوامل أخرى حتى يستطيع الجسر العمل بأمان ضمن الحدود المصممة له.",
        "hashtags": ["#Shorts", "#هندسة", "#جسور", "#تقنية", "#هل_تعلم"],
    },
    {
        "search": "train railway high speed",
        "fallback_searches": ["high speed train", "modern railway", "train technology"],
        "title": "لماذا تسير بعض القطارات بسرعة كبيرة جدًا؟",
        "text": "القطارات السريعة تعتمد على تصميمات تقلل مقاومة الهواء وأنظمة دفع متطورة ومسارات مصممة بدقة. كما تستخدم أنظمة تحكم ومراقبة تساعد على إدارة السرعة والمسار. كل هذه العناصر تعمل معًا لتحقيق رحلة سريعة ومستقرة.",
        "hashtags": ["#Shorts", "#قطارات", "#هندسة", "#تقنية", "#هل_تعلم"],
    },
    {
        "search": "smartphone technology phone",
        "fallback_searches": ["mobile phone technology", "smartphone", "phone hardware"],
        "title": "كيف يعرف هاتفك اتجاهه عندما تدور به؟",
        "text": "الهاتف يحتوي على حساسات صغيرة تقيس الحركة والتسارع والدوران. البرمجيات تجمع هذه البيانات لتقدير اتجاه الجهاز وحركته. ولهذا يستطيع الهاتف تغيير اتجاه الشاشة وتشغيل العديد من الميزات التي تعتمد على الحركة.",
        "hashtags": ["#Shorts", "#جوال", "#تقنية", "#هل_تعلم", "#Technology"],
    },
    {
        "search": "solar panels renewable energy",
        "fallback_searches": ["solar energy", "solar power panels", "renewable energy"],
        "title": "كيف تحول الألواح الشمسية ضوء الشمس إلى كهرباء؟",
        "text": "الألواح الشمسية تحتوي على خلايا قادرة على تحويل الطاقة الضوئية إلى طاقة كهربائية. عندما يصل الضوء إلى الخلايا تتحرك الشحنات داخل المادة وينتج عن ذلك تيار كهربائي يمكن استخدامه أو تخزينه.",
        "hashtags": ["#Shorts", "#طاقة_شمسية", "#علوم", "#تقنية", "#هل_تعلم"],
    },
    {
        "search": "ice glacier mountains climate",
        "fallback_searches": ["glacier ice", "mountain glacier", "frozen landscape"],
        "title": "لماذا تتحرك الأنهار الجليدية رغم أنها تبدو ثابتة؟",
        "text": "الأنهار الجليدية تتكون من كتل ضخمة من الجليد لكنها تستطيع التحرك ببطء شديد تحت تأثير الجاذبية والضغط. قد تكون الحركة غير ملحوظة خلال يوم واحد، لكنها تصبح واضحة عند دراسة التغيرات على مدى سنوات.",
        "hashtags": ["#Shorts", "#جليد", "#علوم", "#طبيعة", "#هل_تعلم"],
    },
    {
        "search": "tornado storm weather",
        "fallback_searches": ["tornado clouds", "severe weather", "storm tornado"],
        "title": "كيف تتشكل الأعاصير القمعية؟",
        "text": "الأعاصير القمعية يمكن أن تتشكل في ظروف جوية معينة عندما تتفاعل كتل هوائية مختلفة مع تغيرات في سرعة واتجاه الرياح. هذه الظروف قد تساعد على تكوين دوران قوي داخل العاصفة. لكن ليس كل اضطراب جوي يتحول إلى إعصار.",
        "hashtags": ["#Shorts", "#طقس", "#أعاصير", "#علوم", "#هل_تعلم"],
    },
    {
        "search": "volleyball basketball sports arena",
        "fallback_searches": ["basketball game", "sports arena", "volleyball match"],
        "title": "لماذا تختلف سرعة رد الفعل بين الرياضات؟",
        "text": "كل رياضة تضع اللاعب أمام مواقف مختلفة تحتاج إلى استجابة سريعة. في بعض الألعاب يجب متابعة جسم سريع جدًا، وفي ألعاب أخرى يحتاج اللاعب إلى توقع الحركة قبل حدوثها. ولهذا يتدرب الرياضيون على رد الفعل والتركيز باستمرار.",
        "hashtags": ["#Shorts", "#رياضة", "#هل_تعلم", "#Sports", "#معلومات"],
    },
    {
        "search": "stadium architecture modern",
        "fallback_searches": ["modern stadium", "sports stadium architecture", "football arena"],
        "title": "لماذا أصبحت الملاعب الحديثة أكثر تعقيدًا؟",
        "text": "الملعب الحديث لم يعد مجرد مدرجات وملعب. التصميم يشمل الإضاءة والشاشات وأنظمة الصوت والمداخل وأنظمة الأمن وإدارة الجماهير. ولهذا أصبحت الملاعب مشاريع هندسية وتقنية ضخمة.",
        "hashtags": ["#Shorts", "#ملاعب", "#هندسة", "#رياضة", "#هل_تعلم"],
    },
    {
        "search": "night city traffic lights",
        "fallback_searches": ["city night traffic", "urban technology", "city lights"],
        "title": "كيف تساعد إشارات المرور في تنظيم المدن؟",
        "text": "إشارات المرور تساعد على تنظيم حركة المركبات والمشاة وتقليل التعارض بين اتجاهات السير. وفي بعض المدن الحديثة يمكن استخدام أنظمة ذكية لمراقبة حركة المرور وتعديل توقيت الإشارات حسب الحاجة.",
        "hashtags": ["#Shorts", "#مدن", "#تقنية", "#مرور", "#هل_تعلم"],
    },
    {
        "search": "3d printing technology machine",
        "fallback_searches": ["3d printer", "3d printing", "modern manufacturing"],
        "title": "كيف تستطيع الطابعة ثلاثية الأبعاد بناء جسم كامل؟",
        "text": "الطباعة ثلاثية الأبعاد تختلف عن الطباعة التقليدية. بدل وضع الحبر على الورق، تبني الطابعة الجسم طبقة فوق طبقة اعتمادًا على نموذج رقمي. ولهذا يمكن استخدامها لصناعة أشكال معقدة يصعب تصنيعها بطرق أخرى.",
        "hashtags": ["#Shorts", "#طباعة_ثلاثية_الأبعاد", "#تقنية", "#هل_تعلم", "#Technology"],
    },
    {
        "search": "satellite earth orbit",
        "fallback_searches": ["satellite space", "earth satellite", "satellite technology"],
        "title": "كيف تبقى الأقمار الصناعية في مدارها؟",
        "text": "القمر الصناعي لا يبقى في الفضاء لأنه بعيد عن الجاذبية. الجاذبية ما زالت تؤثر فيه، لكن سرعته الجانبية تجعله في حالة سقوط مستمر حول الأرض. وهذا التوازن بين الحركة والجاذبية يسمح له بالبقاء في المدار.",
        "hashtags": ["#Shorts", "#أقمار_صناعية", "#فضاء", "#علوم", "#هل_تعلم"],
    },
    {
        "search": "earth atmosphere clouds sky",
        "fallback_searches": ["atmosphere earth", "clouds sky", "earth weather"],
        "title": "لماذا لا نشعر بالهواء رغم أنه يحيط بنا؟",
        "text": "الهواء موجود حولنا في كل مكان، لكننا لا نراه لأن معظم مكوناته غازات شفافة. ومع ذلك فإن للهواء كتلة وضغطًا ويمكنه التأثير في الأجسام. ولهذا نستطيع ملاحظة وجوده من خلال الرياح والضغط وحركة الأشياء.",
        "hashtags": ["#Shorts", "#علوم", "#هواء", "#طقس", "#هل_تعلم"],
    },
]


# =========================================================
# EXTRA UNIQUE CONTENT POOL
# =========================================================
# Additional topics are intentionally different from the original pool.
# The memory system below prevents a topic from being published twice.
EXTRA_TOPICS = [
    {"search":"football offside technology","fallback_searches":["football offside","VAR offside","football technology"],"title":"كيف تساعد تقنية التسلل في كرة القدم على تحديد اللقطة بدقة؟","text":"تستخدم أنظمة التسلل الحديثة صورًا متعددة من كاميرات الملعب لتحديد مواقع اللاعبين والكرة في لحظة التمرير. ثم تُحلل البيانات لمساعدة الحكام على اتخاذ قرار أدق.","hashtags":["#Shorts","#كرة_القدم","#تقنية","#رياضة","#هل_تعلم"]},
    {"search":"football goal net stadium","fallback_searches":["soccer goal net","football goal","stadium goal"],"title":"لماذا تتحرك شبكة المرمى عند تسجيل الهدف؟","text":"شبكة المرمى مصممة لتسمح للكرة بالدخول وتبطئ حركتها بدل أن ترتد بسرعة. كما تساعد مرونتها على امتصاص جزء من طاقة الكرة وتوضيح دخولها إلى المرمى.","hashtags":["#Shorts","#كرة_القدم","#رياضة","#هندسة","#هل_تعلم"]},
    {"search":"football ball aerodynamics","fallback_searches":["soccer ball flight","football ball spin","soccer aerodynamics"],"title":"لماذا تنحرف كرة القدم عندما تدور في الهواء؟","text":"دوران الكرة يغير طريقة مرور الهواء حولها، وقد ينتج عن ذلك قوة جانبية تجعل مسارها ينحرف. وتظهر هذه الظاهرة بوضوح في بعض التسديدات والركلات الحرة.","hashtags":["#Shorts","#كرة_القدم","#فيزياء","#رياضة","#هل_تعلم"]},
    {"search":"football stadium floodlights","fallback_searches":["soccer stadium lights","stadium lighting","football floodlights"],"title":"كيف تضيء الملاعب الكبيرة الملعب ليلًا؟","text":"تستخدم الملاعب أنظمة إضاءة قوية موزعة حول الملعب لتقليل الظلال وتحقيق إضاءة متقاربة في مختلف المناطق. وتُصمم هذه الأنظمة أيضًا لتناسب البث التلفزيوني عالي الدقة.","hashtags":["#Shorts","#ملاعب","#كرة_القدم","#هندسة","#هل_تعلم"]},
    {"search":"football referee communication technology","fallback_searches":["referee communication","football referee headset","sports communication"],"title":"كيف يتواصل حكام كرة القدم أثناء المباراة؟","text":"يستخدم الحكام أنظمة اتصال لاسلكية تسمح لهم بتبادل المعلومات بسرعة أثناء اللعب. هذا يساعدهم على التنسيق ومتابعة الأحداث التي قد تحدث في أجزاء مختلفة من الملعب.","hashtags":["#Shorts","#كرة_القدم","#تقنية","#رياضة","#هل_تعلم"]},
    {"search":"football goalkeeper gloves","fallback_searches":["soccer goalkeeper gloves","goalkeeper save","football goalkeeper"],"title":"لماذا تحتوي قفازات حارس المرمى على طبقة لاصقة؟","text":"تحتوي كثير من قفازات حراس المرمى على مادة تساعد على زيادة الاحتكاك بين القفاز والكرة. وهذا يمنح الحارس قبضة أفضل عند محاولة الإمساك بالكرة أو إبعادها.","hashtags":["#Shorts","#حارس_المرمى","#كرة_القدم","#رياضة","#هل_تعلم"]},
    {"search":"football stadium grass pitch","fallback_searches":["soccer field grass","stadium turf","football pitch"],"title":"لماذا تُقص أعشاب ملاعب كرة القدم باتجاهات مختلفة؟","text":"تغيير اتجاه قص العشب يمكن أن يعطي الملعب مظهرًا مخططًا بسبب اختلاف اتجاه انعكاس الضوء عن أوراق العشب. ولا يعني ذلك بالضرورة اختلاف لون العشب نفسه.","hashtags":["#Shorts","#ملاعب","#كرة_القدم","#طبيعة","#هل_تعلم"]},
    {"search":"sound wave physics","fallback_searches":["sound waves","acoustics science","sound vibration"],"title":"كيف يصل الصوت من شخص إلى أذنك؟","text":"عندما يهتز مصدر الصوت فإنه يسبب اهتزازات في الوسط المحيط، مثل الهواء. تنتقل هذه الاهتزازات على شكل موجات حتى تصل إلى الأذن التي تحولها إلى إشارات عصبية يفهمها الدماغ.","hashtags":["#Shorts","#صوت","#فيزياء","#علوم","#هل_تعلم"]},
    {"search":"echo canyon sound","fallback_searches":["sound echo","echo canyon","acoustics echo"],"title":"لماذا نسمع الصدى في بعض الأماكن؟","text":"يحدث الصدى عندما تصل الموجات الصوتية إلى سطح بعيد ثم تنعكس وتعود إلى المستمع بعد فترة زمنية كافية. لذلك يكون الصدى أوضح في الأماكن الكبيرة ذات الأسطح الصلبة.","hashtags":["#Shorts","#صدى","#فيزياء","#علوم","#هل_تعلم"]},
    {"search":"rain formation clouds","fallback_searches":["how rain forms","cloud precipitation","rain science"],"title":"كيف تتحول السحب إلى مطر؟","text":"داخل السحب تتجمع قطرات الماء أو بلورات الجليد وتنمو تدريجيًا. وعندما تصبح الجسيمات ثقيلة بما يكفي مقارنة بقدرة التيارات الهوائية على حملها، تهبط على شكل هطول.","hashtags":["#Shorts","#مطر","#طقس","#علوم","#هل_تعلم"]},
    {"search":"lightning thunder storm","fallback_searches":["thunderstorm lightning","thunder sound","lightning science"],"title":"لماذا نرى البرق قبل أن نسمع الرعد؟","text":"الضوء ينتقل أسرع بكثير من الصوت. لذلك يصل ضوء البرق إلى أعيننا قبل وصول موجات الرعد إلى آذاننا، رغم أن الحدثين يحدثان في الوقت نفسه تقريبًا.","hashtags":["#Shorts","#برق","#رعد","#فيزياء","#هل_تعلم"]},
    {"search":"rainbow sunlight water","fallback_searches":["rainbow formation","light refraction water","rainbow science"],"title":"كيف يظهر قوس قزح بعد المطر؟","text":"عندما يدخل ضوء الشمس إلى قطرات الماء يمكن أن ينكسر وينعكس ويتحلل إلى ألوان مختلفة. وعندما تصل هذه الأشعة إلى أعيننا من زوايا مناسبة يظهر قوس قزح.","hashtags":["#Shorts","#ضوء","#علوم","#طبيعة","#هل_تعلم"]},
    {"search":"moon surface space","fallback_searches":["moon science","lunar surface","moon crater"],"title":"لماذا توجد حفر كثيرة على سطح القمر؟","text":"سطح القمر يحمل آثار اصطدامات كثيرة بأجسام فضائية عبر تاريخ طويل. وبسبب غياب الغلاف الجوي الكثيف والعمليات الجيولوجية المشابهة للأرض، تبقى كثير من آثار الاصطدام واضحة لفترات طويلة.","hashtags":["#Shorts","#قمر","#فضاء","#علوم","#هل_تعلم"]},
    {"search":"earth rotation day night","fallback_searches":["earth rotation","day night earth","planet rotation"],"title":"كيف يتعاقب الليل والنهار على الأرض؟","text":"الأرض تدور حول محورها باستمرار. المنطقة المواجهة للشمس تكون في النهار، بينما تكون المنطقة البعيدة عنها في الليل، ومع استمرار الدوران تتغير هذه المناطق.","hashtags":["#Shorts","#الأرض","#فضاء","#علوم","#هل_تعلم"]},
    {"search":"earth magnetic field","fallback_searches":["earth magnetosphere","magnetic field earth","compass earth"],"title":"كيف يساعد المجال المغناطيسي للأرض على حمايتها؟","text":"للأرض مجال مغناطيسي يمتد حولها ويؤثر في الجسيمات المشحونة القادمة من الشمس. هذا المجال جزء من البيئة الفضائية المحيطة بالأرض ويساعد على تقليل وصول بعض الجسيمات مباشرة إلى الغلاف الجوي.","hashtags":["#Shorts","#الأرض","#مغناطيسية","#فضاء","#هل_تعلم"]},
    {"search":"volcano magma underground","fallback_searches":["magma volcano","volcanic eruption science","volcano inside"],"title":"من أين تأتي المواد المنصهرة في البركان؟","text":"توجد صخور منصهرة تسمى الصهارة في أجزاء من باطن الأرض. إذا صعدت هذه الصهارة إلى مناطق قريبة من السطح ثم خرجت أثناء ثوران بركاني، تُعرف المواد المنصهرة التي تصل إلى السطح باسم الحمم.","hashtags":["#Shorts","#براكين","#جيولوجيا","#علوم","#هل_تعلم"]},
    {"search":"earthquake seismograph","fallback_searches":["earthquake waves","seismometer","earthquake science"],"title":"كيف يقيس العلماء الزلازل؟","text":"تستخدم أجهزة قياس الزلازل لتسجيل اهتزازات الأرض الناتجة عن الموجات الزلزالية. تساعد هذه التسجيلات العلماء على دراسة قوة الزلزال ومكانه وطبيعة الموجات التي انتشرت خلال الأرض.","hashtags":["#Shorts","#زلازل","#جيولوجيا","#علوم","#هل_تعلم"]},
    {"search":"ocean waves beach physics","fallback_searches":["ocean wave formation","sea waves","wave physics"],"title":"لماذا تصل أمواج البحر إلى الشاطئ باستمرار؟","text":"تتولد كثير من أمواج البحر بسبب انتقال الطاقة عبر الماء بفعل الرياح. وعندما تقترب الموجة من المياه الضحلة يتغير سلوكها وتصبح أكثر ارتفاعًا قبل أن تصل إلى الشاطئ.","hashtags":["#Shorts","#أمواج","#محيط","#فيزياء","#هل_تعلم"]},
    {"search":"coral reef underwater","fallback_searches":["coral reef ecosystem","coral underwater","marine reef"],"title":"لماذا تُعد الشعاب المرجانية مهمة للمحيطات؟","text":"الشعاب المرجانية توفر موائل لعدد كبير من الكائنات البحرية. كما أنها تشكل أنظمة بيئية معقدة ترتبط بها أنواع كثيرة، لذلك تؤدي دورًا مهمًا في التنوع الحيوي البحري.","hashtags":["#Shorts","#شعاب_مرجانية","#محيط","#طبيعة","#هل_تعلم"]},
    {"search":"octopus underwater animal","fallback_searches":["octopus intelligence","octopus animal","octopus ocean"],"title":"لماذا يستطيع الأخطبوط تغيير مظهره؟","text":"يمتلك الأخطبوط خلايا متخصصة في الجلد تساعده على تغيير اللون والنقوش، ويمكن لبعض الأنواع أيضًا تغيير ملمس الجلد. تستخدم هذه القدرات في التواصل والتمويه والتفاعل مع البيئة.","hashtags":["#Shorts","#أخطبوط","#حيوانات","#محيط","#هل_تعلم"]},
    {"search":"owl bird night vision","fallback_searches":["owl eyes night","owl hunting","owl bird"],"title":"كيف ترى البوم في الإضاءة الضعيفة؟","text":"عيون البوم كبيرة مقارنة بحجم الرأس، وتساعد بنيتها على جمع الضوء بكفاءة في ظروف الإضاءة المنخفضة. كما تمتلك البوم تكيفات أخرى تساعدها على الصيد في الليل.","hashtags":["#Shorts","#بوم","#حيوانات","#طبيعة","#هل_تعلم"]},
    {"search":"camel desert adaptation","fallback_searches":["camel desert","camel biology","desert animal camel"],"title":"كيف يساعد الجمل جسمه على تحمل الصحراء؟","text":"يمتلك الجمل مجموعة من التكيفات التي تساعده في البيئة الصحراوية، منها القدرة على تحمل فقدان الماء لفترات وظروف الحرارة العالية. كما تساعده أقدامه وبنيته على الحركة فوق الرمال.","hashtags":["#Shorts","#جمل","#صحراء","#حيوانات","#هل_تعلم"]},
    {"search":"dolphin echolocation ocean","fallback_searches":["dolphin sonar","dolphin sound","marine mammals"],"title":"كيف تستخدم الدلافين الأصوات لمعرفة ما حولها؟","text":"تستخدم الدلافين تحديد الموقع بالصدى، حيث تطلق أصواتًا وتستقبل صداها بعد انعكاسه عن الأجسام. تساعدها هذه المعلومات على تقدير موقع الأجسام والمسافات في الماء.","hashtags":["#Shorts","#دلافين","#محيط","#حيوانات","#هل_تعلم"]},
    {"search":"bee pollination flower","fallback_searches":["bees flowers pollination","bee pollination","honeybee nature"],"title":"كيف تساعد النحل في تلقيح النباتات؟","text":"عندما ينتقل النحل بين الأزهار يلتصق حبوب اللقاح بجسمه ويمكن أن ينقل جزءًا منها إلى زهرة أخرى. هذه العملية تساعد كثيرًا من النباتات على التكاثر وإنتاج البذور.","hashtags":["#Shorts","#نحل","#نباتات","#طبيعة","#هل_تعلم"]},
    {"search":"tree rings age","fallback_searches":["tree rings science","tree age rings","dendrochronology"],"title":"كيف يمكن معرفة عمر بعض الأشجار من حلقاتها؟","text":"تضيف كثير من الأشجار طبقات نمو جديدة مع مرور السنوات. وعند فحص الحلقات في مقطع جذع مناسب يمكن للعلماء استخدامها لتقدير عمر الشجرة ودراسة ظروف نموها عبر الزمن.","hashtags":["#Shorts","#أشجار","#طبيعة","#علوم","#هل_تعلم"]},
    {"search":"photosynthesis leaf chlorophyll","fallback_searches":["chlorophyll plants","leaf photosynthesis","plant science"],"title":"لماذا تبدو أوراق النباتات خضراء؟","text":"تحتوي كثير من النباتات على صبغة تسمى الكلوروفيل تمتص أجزاء من الضوء وتشارك في البناء الضوئي. ويعكس الكلوروفيل جزءًا من الضوء الأخضر أكثر من بعض الألوان الأخرى، لذلك تبدو الأوراق خضراء.","hashtags":["#Shorts","#نباتات","#علوم","#طبيعة","#هل_تعلم"]},
    {"search":"human skeleton xray bones","fallback_searches":["human bones","skeleton science","bone structure"],"title":"لماذا لا تكون عظام الإنسان صلبة بالكامل من الداخل؟","text":"العظم نسيج حي وله بنية داخلية معقدة. كثير من العظام تحتوي على جزء داخلي مسامي يساعد على تقليل الوزن مع المحافظة على قدر جيد من القوة، كما تحتوي العظام على خلايا وأنسجة حية.","hashtags":["#Shorts","#عظام","#علوم","#جسم_الإنسان","#هل_تعلم"]},
    {"search":"human heartbeat heart anatomy","fallback_searches":["heart pumping blood","human heart","cardiovascular system"],"title":"كيف يدفع القلب الدم إلى أنحاء الجسم؟","text":"ينقبض القلب ويرتخي في دورة متكررة تدفع الدم عبر الأوعية الدموية. يعمل هذا النظام على نقل الأكسجين والمواد الغذائية إلى الأنسجة وإعادة بعض المواد إلى الأعضاء المسؤولة عن معالجتها.","hashtags":["#Shorts","#قلب","#علوم","#جسم_الإنسان","#هل_تعلم"]},
    {"search":"human lungs breathing","fallback_searches":["lungs oxygen","respiratory system","lung anatomy"],"title":"كيف يصل الأكسجين من الهواء إلى الدم؟","text":"عند التنفس يصل الهواء إلى الرئتين، وهناك ينتقل الأكسجين عبر أسطح دقيقة جدًا إلى الدم، بينما ينتقل ثاني أكسيد الكربون من الدم إلى الهواء ليخرج أثناء الزفير.","hashtags":["#Shorts","#رئتان","#علوم","#جسم_الإنسان","#هل_تعلم"]},
    {"search":"human skin temperature","fallback_searches":["skin body temperature","sweating cooling","human thermoregulation"],"title":"كيف يساعد التعرق الجسم على تبريد نفسه؟","text":"عندما يتبخر العرق من سطح الجلد فإنه يسحب جزءًا من الطاقة الحرارية من الجسم. لذلك يعد التعرق إحدى الطرق التي يستخدمها الجسم للمساعدة في تنظيم درجة حرارته.","hashtags":["#Shorts","#تعرق","#علوم","#جسم_الإنسان","#هل_تعلم"]},
    {"search":"computer binary code technology","fallback_searches":["binary computing","computer bits","digital data"],"title":"لماذا تستخدم الحواسيب النظام الثنائي؟","text":"تعتمد الدوائر الرقمية على حالات كهربائية يمكن تمثيلها بصورة مبسطة بصفر وواحد. ومن خلال ترتيب هذه الحالات تستطيع الحواسيب تمثيل البيانات وتنفيذ العمليات المنطقية والحسابية.","hashtags":["#Shorts","#حاسوب","#تقنية","#برمجة","#هل_تعلم"]},
    {"search":"computer RAM memory","fallback_searches":["RAM explained","computer memory","ram technology"],"title":"ما وظيفة ذاكرة RAM في الحاسوب؟","text":"تستخدم ذاكرة RAM لتخزين البيانات التي تحتاج إليها البرامج بسرعة أثناء عملها. وهي تختلف عن التخزين الدائم لأن محتوياتها لا تبقى عادة بعد انقطاع الطاقة.","hashtags":["#Shorts","#رام","#حاسوب","#تقنية","#هل_تعلم"]},
    {"search":"SSD storage technology","fallback_searches":["solid state drive","SSD how works","computer SSD"],"title":"لماذا تكون أقراص SSD أسرع من الأقراص التقليدية؟","text":"تعتمد أقراص SSD على شرائح ذاكرة إلكترونية ولا تحتوي عادة على أجزاء ميكانيكية متحركة مثل الأقراص الصلبة التقليدية. هذا يساعدها على الوصول إلى البيانات بسرعة وتقليل زمن الانتظار في كثير من الاستخدامات.","hashtags":["#Shorts","#SSD","#حاسوب","#تقنية","#هل_تعلم"]},
    {"search":"wifi router wireless signal","fallback_searches":["wifi technology","wireless router","wifi signal"],"title":"كيف ينتقل الإنترنت إلى هاتفك عبر Wi-Fi؟","text":"يرسل جهاز التوجيه البيانات عبر موجات راديوية باستخدام ترددات مخصصة للاتصالات اللاسلكية. يستقبل الهاتف هذه الإشارات ويحولها إلى بيانات يمكن للتطبيقات استخدامها.","hashtags":["#Shorts","#واي_فاي","#إنترنت","#تقنية","#هل_تعلم"]},
    {"search":"fiber optic cable light internet","fallback_searches":["fiber optic internet","optical fiber","internet cables"],"title":"كيف تنقل الألياف الضوئية البيانات بالضوء؟","text":"تستخدم الألياف الضوئية خيوطًا دقيقة من الزجاج أو مواد مشابهة لنقل نبضات ضوئية. يمكن ترميز البيانات داخل هذه الإشارات ونقلها لمسافات طويلة بسرعات عالية.","hashtags":["#Shorts","#ألياف_ضوئية","#إنترنت","#تقنية","#هل_تعلم"]},
    {"search":"gps satellite navigation phone","fallback_searches":["GPS technology","GPS satellites","phone navigation"],"title":"كيف يعرف هاتفك موقعك باستخدام GPS؟","text":"يستقبل الهاتف إشارات من عدة أقمار صناعية لنظام تحديد المواقع. وباستخدام فروق زمن وصول الإشارات يمكن للجهاز حساب موقع تقريبي على سطح الأرض.","hashtags":["#Shorts","#GPS","#جوال","#تقنية","#هل_تعلم"]},
    {"search":"camera image sensor smartphone","fallback_searches":["camera sensor","phone camera technology","digital camera"],"title":"كيف تحول كاميرا الهاتف الضوء إلى صورة؟","text":"يصل الضوء إلى حساس الصورة داخل الكاميرا، حيث تحوله عناصر صغيرة إلى إشارات كهربائية. ثم تعالجها البرمجيات لتكوين ملف صورة رقمي يمكن حفظه ومشاركته.","hashtags":["#Shorts","#كاميرا","#جوال","#تقنية","#هل_تعلم"]},
    {"search":"electric motor magnetic field","fallback_searches":["electric motor science","motor magnets","motor engineering"],"title":"كيف يحول المحرك الكهربائي الكهرباء إلى حركة؟","text":"يستخدم المحرك الكهربائي تفاعل المجالات المغناطيسية مع التيار الكهربائي لإنتاج قوة دوران. وتُرتب الملفات والمغناطيسات بحيث تستمر القوة في دفع الجزء الدوار.","hashtags":["#Shorts","#محرك","#كهرباء","#هندسة","#هل_تعلم"]},
    {"search":"battery lithium ion charging","fallback_searches":["lithium ion battery","battery science","battery charging"],"title":"كيف تخزن البطارية الطاقة الكهربائية؟","text":"البطارية تحول الطاقة الكيميائية إلى طاقة كهربائية عند استخدامها، ويمكن عكس العملية في البطاريات القابلة لإعادة الشحن. داخل البطارية تتحرك الأيونات والإلكترونات عبر مواد ومسارات محددة.","hashtags":["#Shorts","#بطاريات","#كهرباء","#تقنية","#هل_تعلم"]},
    {"search":"electricity power grid transmission","fallback_searches":["power grid","electric transmission","electricity network"],"title":"لماذا تُنقل الكهرباء بجهد عالٍ عبر الشبكات؟","text":"رفع جهد النقل يسمح بنقل قدرة كهربائية معينة بتيار أقل، وهذا يقلل الفاقد الحراري في خطوط النقل. لذلك تستخدم شبكات الكهرباء جهودًا عالية في مراحل النقل لمسافات طويلة.","hashtags":["#Shorts","#كهرباء","#هندسة","#طاقة","#هل_تعلم"]},
    {"search":"wind turbine renewable energy","fallback_searches":["wind power turbine","wind energy","wind turbine blades"],"title":"كيف تحول توربينات الرياح حركة الهواء إلى كهرباء؟","text":"تحرك الرياح شفرات التوربين فتدور معها أجزاء ميكانيكية متصلة بمولد. يحول المولد الطاقة الميكانيكية الناتجة عن الدوران إلى طاقة كهربائية.","hashtags":["#Shorts","#طاقة_الرياح","#هندسة","#طاقة","#هل_تعلم"]},
    {"search":"hydroelectric dam power","fallback_searches":["hydropower dam","hydroelectricity","water turbine"],"title":"كيف تنتج السدود الكهرومائية الكهرباء؟","text":"يمكن للمياه المخزنة على ارتفاع أن تمتلك طاقة وضع. عند مرورها عبر التوربينات تتحول هذه الطاقة إلى حركة دورانية، ثم يحول المولد الحركة إلى كهرباء.","hashtags":["#Shorts","#طاقة_مائية","#هندسة","#كهرباء","#هل_تعلم"]},
    {"search":"skyscraper structural engineering","fallback_searches":["skyscraper engineering","tall building structure","building design"],"title":"كيف تقاوم ناطحات السحاب الرياح؟","text":"تُصمم الأبراج العالية بحيث توزع الأحمال على الهيكل والأساسات، وتستخدم أنظمة إنشائية تساعد على التحكم في الحركة الناتجة عن الرياح. ويأخذ المهندسون أيضًا تأثير الزلازل والوزن في الحسبان حسب الموقع.","hashtags":["#Shorts","#ناطحات_السحاب","#هندسة","#بناء","#هل_تعلم"]},
    {"search":"airplane wing lift aerodynamics","fallback_searches":["airplane lift","aircraft wing","aerodynamics plane"],"title":"كيف تساعد أجنحة الطائرة على البقاء في الهواء؟","text":"عند حركة الطائرة خلال الهواء يتشكل توزيع للقوى حول الأجنحة ينتج عنه قوة رفع. يعتمد مقدار الرفع على سرعة الهواء وشكل الجناح وزاويته وعوامل أخرى.","hashtags":["#Shorts","#طائرات","#هندسة","#فيزياء","#هل_تعلم"]},
    {"search":"airplane jet engine turbine","fallback_searches":["jet engine how works","aircraft engine","jet turbine"],"title":"كيف يدفع المحرك النفاث الطائرة إلى الأمام؟","text":"يسحب المحرك الهواء ثم يضغطه ويخلطه بالوقود ويحرق الخليط لإنتاج غازات ساخنة تتمدد وتندفع إلى الخلف. ينتج عن ذلك قوة دفع تدفع الطائرة إلى الأمام.","hashtags":["#Shorts","#محركات","#طائرات","#هندسة","#هل_تعلم"]},
    {"search":"car airbags crash safety","fallback_searches":["airbag safety","car crash technology","vehicle safety"],"title":"كيف تعمل الوسائد الهوائية في السيارات؟","text":"عند اكتشاف تصادم قوي تستخدم السيارة حساسات ترسل بيانات إلى وحدة تحكم. إذا تحققت شروط معينة تنتفخ الوسادة الهوائية بسرعة لتوفير وسادة حماية إضافية للركاب.","hashtags":["#Shorts","#سيارات","#هندسة","#سلامة","#هل_تعلم"]},
    {"search":"electric car regenerative braking","fallback_searches":["regenerative braking","electric vehicle braking","EV technology"],"title":"كيف تستعيد السيارات الكهربائية جزءًا من الطاقة أثناء التباطؤ؟","text":"عند التباطؤ يمكن للمحرك الكهربائي أن يعمل بطريقة مختلفة ليعمل كمولد. فتتحول بعض الطاقة الحركية إلى طاقة كهربائية تعود إلى البطارية بدل فقدها كلها على شكل حرارة في نظام الاحتكاك.","hashtags":["#Shorts","#سيارات_كهربائية","#هندسة","#طاقة","#هل_تعلم"]},
    {"search":"robot sensors lidar camera","fallback_searches":["robot sensors","robot perception","robotics technology"],"title":"كيف تعرف الروبوتات ما يوجد حولها؟","text":"يمكن للروبوت استخدام كاميرات وحساسات مسافة ومستشعرات أخرى لجمع معلومات عن البيئة. ثم تعالج برمجياته هذه البيانات لتحديد مواقع الأشياء واتخاذ قرارات للحركة.","hashtags":["#Shorts","#روبوتات","#تقنية","#هندسة","#هل_تعلم"]},
    {"search":"3d printer layer manufacturing","fallback_searches":["additive manufacturing","3d printing layers","3d printer technology"],"title":"لماذا تسمى الطباعة ثلاثية الأبعاد تصنيعًا إضافيًا؟","text":"في التصنيع الإضافي يُبنى الجسم بإضافة المادة تدريجيًا وفق نموذج رقمي، بدل إزالة المادة من كتلة كبيرة. هذا يسمح بإنتاج أشكال هندسية معقدة في بعض التطبيقات.","hashtags":["#Shorts","#طباعة_ثلاثية_الأبعاد","#هندسة","#تقنية","#هل_تعلم"]},
    {"search":"bridge suspension cables engineering","fallback_searches":["suspension bridge","bridge cables","structural engineering"],"title":"لماذا تستخدم بعض الجسور كابلات ضخمة؟","text":"في الجسور المعلقة تحمل الكابلات الرئيسية جزءًا كبيرًا من الأحمال وتنقل القوى إلى الأبراج والمراسي. يساعد هذا النظام على تغطية مسافات واسعة دون الحاجة إلى دعامات كثيرة في المنتصف.","hashtags":["#Shorts","#جسور","#هندسة","#بناء","#هل_تعلم"]},
    {"search":"tunnel boring machine underground","fallback_searches":["tunnel boring machine","underground construction","tunnel engineering"],"title":"كيف تحفر الآلات الأنفاق تحت الأرض؟","text":"تستخدم آلات حفر الأنفاق رأس قطع دوارًا لإزالة الصخور أو التربة تدريجيًا. وفي الوقت نفسه يمكن تركيب دعامات أو بطانات خلف الآلة للمساعدة على تثبيت النفق.","hashtags":["#Shorts","#أنفاق","#هندسة","#بناء","#هل_تعلم"]},
    {"search":"dam engineering concrete water","fallback_searches":["dam structure","concrete dam","water engineering"],"title":"لماذا تكون بعض السدود سميكة جدًا عند قاعدتها؟","text":"ضغط المياه على السد يزداد مع العمق، لذلك تحتاج بعض تصميمات السدود إلى قاعدة قوية وعريضة لمقاومة القوى المؤثرة. يعتمد الشكل النهائي على نوع السد والمواد والظروف الجيولوجية.","hashtags":["#Shorts","#سدود","#هندسة","#مياه","#هل_تعلم"]},
    {"search":"ancient roman roads engineering","fallback_searches":["roman roads","ancient roman engineering","roman infrastructure"],"title":"لماذا بقيت بعض الطرق الرومانية القديمة لقرون؟","text":"اعتمد الرومان في كثير من الطرق على طبقات متعددة من المواد وتصريف المياه وتنظيم مسار الطريق. ساعدت هذه الأساليب الهندسية على زيادة متانة بعض الطرق وتقليل تأثير تجمع المياه.","hashtags":["#Shorts","#رومان","#تاريخ","#هندسة","#هل_تعلم"]},
    {"search":"ancient aqueduct engineering","fallback_searches":["roman aqueduct","ancient water systems","aqueduct engineering"],"title":"كيف نقلت القنوات الرومانية المياه لمسافات طويلة؟","text":"استخدم الرومان قنوات مصممة بانحدار مناسب لنقل المياه بفعل الجاذبية من مصادرها إلى المدن. وتضمنت بعض الأنظمة جسورًا وقنوات تحت الأرض وخزانات لتوزيع المياه.","hashtags":["#Shorts","#رومان","#مياه","#هندسة","#هل_تعلم"]},
    {"search":"ancient compass navigation","fallback_searches":["magnetic compass history","compass navigation","ancient navigation"],"title":"كيف ساعدت البوصلة على تطوير الملاحة؟","text":"تعتمد البوصلة المغناطيسية على إبرة تتأثر بالمجال المغناطيسي للأرض. سمحت هذه الأداة للبحارة بتحديد اتجاهات عامة حتى عندما تكون المعالم المرئية محدودة.","hashtags":["#Shorts","#بوصلة","#ملاحة","#تاريخ","#هل_تعلم"]},
    {"search":"printing press history books","fallback_searches":["printing press history","Gutenberg press","old printing"],"title":"كيف غيرت الطباعة انتشار الكتب؟","text":"سمحت تقنيات الطباعة بإنتاج نسخ كثيرة من النصوص بطريقة أسرع من نسخها يدويًا واحدة تلو الأخرى. ساعد ذلك على زيادة انتشار الكتب والمعلومات في المجتمعات التي استخدمت هذه التقنيات.","hashtags":["#Shorts","#طباعة","#تاريخ","#كتب","#هل_تعلم"]},
    {"search":"ancient astronomy observatory stars","fallback_searches":["ancient astronomy","old observatory","star observation history"],"title":"لماذا راقب القدماء حركة النجوم والكواكب؟","text":"استخدمت حضارات قديمة مراقبة السماء لفهم دورات الزمن والمواسم والملاحة وبناء تقاويمها. وساعد تسجيل الحركات السماوية عبر فترات طويلة على تطوير المعرفة الفلكية.","hashtags":["#Shorts","#فلك","#تاريخ","#فضاء","#هل_تعلم"]},
    {"search":"meteorite desert rock space","fallback_searches":["meteorite discovery","space rock desert","meteorite rock"],"title":"كيف يعرف العلماء أن بعض الصخور جاءت من الفضاء؟","text":"يمكن أن تحمل بعض النيازك خصائص وتركيبات معدنية تختلف عن الصخور الشائعة على الأرض. يدرس العلماء تركيبها ونظائرها وبنيتها للمساعدة على تحديد أصلها وتاريخها.","hashtags":["#Shorts","#نيازك","#فضاء","#جيولوجيا","#هل_تعلم"]},
    {"search":"stars nuclear fusion space","fallback_searches":["star fusion","sun nuclear fusion","stellar energy"],"title":"من أين تحصل النجوم على طاقتها؟","text":"في النجوم تحدث تفاعلات اندماج نووي في درجات حرارة وضغوط هائلة. في نجوم مثل الشمس تتحول نوى الهيدروجين تدريجيًا إلى هيليوم وتتحرر طاقة كبيرة.","hashtags":["#Shorts","#نجوم","#فضاء","#فيزياء","#هل_تعلم"]},
    {"search":"sunlight earth energy solar","fallback_searches":["sun energy earth","solar radiation","sun science"],"title":"لماذا تعد الشمس مصدر الطاقة الرئيسي لكثير من أنظمة الأرض؟","text":"تصل طاقة الشمس إلى الأرض على شكل إشعاع، وتستخدم النباتات جزءًا منها في البناء الضوئي. كما تسهم الطاقة الشمسية في تسخين سطح الأرض وتحريك دورة المياه والرياح.","hashtags":["#Shorts","#الشمس","#طاقة","#علوم","#هل_تعلم"]},
    {"search":"ocean currents global circulation","fallback_searches":["ocean currents","sea circulation","ocean science"],"title":"كيف تتحرك التيارات البحرية لمسافات طويلة؟","text":"تتحرك مياه المحيطات بسبب الرياح واختلاف الكثافة الناتج عن الحرارة والملوحة وشكل الأحواض البحرية. وتساهم هذه الحركة في نقل الحرارة والمواد عبر أجزاء واسعة من المحيطات.","hashtags":["#Shorts","#محيطات","#تيارات_بحرية","#علوم","#هل_تعلم"]},
    {"search":"water cycle evaporation clouds","fallback_searches":["water cycle","evaporation condensation","water science"],"title":"كيف تعود المياه من الأرض إلى السماء؟","text":"تتبخر المياه من البحار والأنهار والأسطح الرطبة، ثم يبرد بخار الماء ويتكاثف في الغلاف الجوي لتتكون السحب. بعد ذلك يعود الماء إلى السطح على شكل هطول.","hashtags":["#Shorts","#دورة_المياه","#علوم","#طقس","#هل_تعلم"]},
    {"search":"snowflake formation microscope","fallback_searches":["snow crystal","snowflake science","ice crystal"],"title":"لماذا تختلف أشكال بلورات الثلج؟","text":"تتكون بلورات الثلج عندما يتجمد بخار الماء في ظروف جوية معينة. وتتأثر طريقة نمو البلورة بدرجة الحرارة والرطوبة أثناء سقوطها، لذلك يمكن أن تظهر أشكال كثيرة مختلفة.","hashtags":["#Shorts","#ثلج","#علوم","#طقس","#هل_تعلم"]},
    {"search":"desert oasis water nature","fallback_searches":["oasis desert","desert water","oasis landscape"],"title":"كيف تتكون الواحات في بعض الصحارى؟","text":"تظهر الواحات في أماكن يصل فيها الماء الجوفي إلى قرب سطح الأرض أو يتوفر فيها مصدر مائي مستمر. وجود الماء يسمح بنمو النباتات وقيام تجمعات بشرية في مناطق صحراوية.","hashtags":["#Shorts","#واحات","#صحراء","#طبيعة","#هل_تعلم"]},
    {"search":"mangrove forest coast roots","fallback_searches":["mangrove ecosystem","mangrove roots","coastal forest"],"title":"كيف تستطيع أشجار المانغروف النمو قرب مياه البحر؟","text":"تمتلك أشجار المانغروف تكيفات تساعدها على العيش في البيئات الساحلية المالحة والمغمورة دوريًا. وتشكل جذورها المعقدة موائل مهمة لكائنات كثيرة وتساعد في تثبيت الرواسب.","hashtags":["#Shorts","#مانغروف","#طبيعة","#محيط","#هل_تعلم"]},
    {"search":"bamboo plant growth nature","fallback_searches":["bamboo growth","bamboo plant","fast growing plants"],"title":"لماذا يمكن لبعض أنواع الخيزران أن تنمو بسرعة كبيرة؟","text":"تمتلك بعض أنواع الخيزران مناطق نمو نشطة تسمح للساق بالاستطالة بسرعة خلال ظروف مناسبة. وتختلف سرعة النمو كثيرًا بين الأنواع والبيئات، لذلك لا تنطبق الأرقام نفسها على كل أنواع الخيزران.","hashtags":["#Shorts","#خيزران","#نباتات","#طبيعة","#هل_تعلم"]},
    {"search":"ant colony insect teamwork","fallback_searches":["ants colony","ant teamwork","insect behavior"],"title":"كيف تتعاون مستعمرات النمل في العثور على الغذاء؟","text":"تستطيع بعض أنواع النمل ترك إشارات كيميائية على المسارات، ويمكن لغيرها تتبع هذه الإشارات للوصول إلى مصادر الغذاء. هذا السلوك يساعد المستعمرة على تنظيم البحث والنقل.","hashtags":["#Shorts","#نمل","#حشرات","#طبيعة","#هل_تعلم"]},
    {"search":"spider web silk macro","fallback_searches":["spider silk","spider web science","spider web"],"title":"لماذا تتميز خيوط العنكبوت بقوة ملحوظة؟","text":"خيوط العنكبوت مصنوعة من بروتينات تنتجها الغدد الخاصة بالعنكبوت. تمتلك بعض أنواع الحرير توازنًا مميزًا بين القوة والمرونة، وتختلف خصائص الخيوط حسب نوع العنكبوت ووظيفتها.","hashtags":["#Shorts","#عناكب","#حشرات","#علوم","#هل_تعلم"]},
    {"search":"butterfly metamorphosis life cycle","fallback_searches":["butterfly life cycle","metamorphosis butterfly","caterpillar butterfly"],"title":"كيف تتحول اليرقة إلى فراشة؟","text":"تمر الفراشات بمراحل مختلفة في دورة حياتها، تبدأ عادة بالبيضة ثم اليرقة فالطور العذري ثم الحشرة البالغة. خلال التحول تتغير بنية الجسم ووظائفه بشكل كبير.","hashtags":["#Shorts","#فراشات","#حشرات","#طبيعة","#هل_تعلم"]},
    {"search":"penguin swimming underwater","fallback_searches":["penguin swimming","penguin feathers","penguin ocean"],"title":"لماذا تستطيع البطاريق السباحة بكفاءة رغم أنها طيور؟","text":"أجنحة البطاريق تحورت لتعمل بطريقة تشبه الزعانف أثناء السباحة، كما يساعد شكل الجسم والريش على الحركة في الماء. وهي لا تطير في الهواء مثل معظم الطيور لكنها متخصصة جدًا في السباحة.","hashtags":["#Shorts","#بطاريق","#حيوانات","#محيط","#هل_تعلم"]},
    {"search":"elephant ears cooling","fallback_searches":["elephant ears temperature","elephant cooling","elephant biology"],"title":"كيف تساعد آذان الفيل الكبيرة على تبريد جسمه؟","text":"تحتوي آذان الفيل على شبكة واسعة من الأوعية الدموية. عندما يمر الدم بالقرب من سطح الأذن يمكن أن يفقد جزءًا من الحرارة، وتساعد حركة الأذن في زيادة تبادل الحرارة مع الهواء.","hashtags":["#Shorts","#فيل","#حيوانات","#علوم","#هل_تعلم"]},
    {"search":"polar bear fur insulation","fallback_searches":["polar bear cold adaptation","polar bear fur","arctic animal"],"title":"كيف يحافظ الدب القطبي على حرارته في البرد؟","text":"يمتلك الدب القطبي طبقات من العزل تشمل الفراء والدهون، ما يقلل فقدان الحرارة في البيئة الباردة. كما يساعد شكل جسمه على تقليل مساحة السطح مقارنة بحجمه.","hashtags":["#Shorts","#دب_قطبي","#حيوانات","#طبيعة","#هل_تعلم"]},
    {"search":"whale ocean breathing surface","fallback_searches":["whale breathing","whale ocean","marine mammal"],"title":"لماذا تصعد الحيتان إلى سطح الماء؟","text":"الحيتان ثدييات وتحتاج إلى تنفس الهواء من الغلاف الجوي، لذلك تصعد إلى السطح للتنفس. ثم تستطيع بعض الأنواع الغوص لفترات طويلة قبل العودة إلى السطح مرة أخرى.","hashtags":["#Shorts","#حيتان","#محيط","#حيوانات","#هل_تعلم"]},
    {"search":"gecko feet adhesion macro","fallback_searches":["gecko feet science","gecko climbing","animal adhesion"],"title":"كيف تستطيع بعض الوزغات المشي على الأسطح الملساء؟","text":"تحتوي أقدام بعض الوزغات على ملايين التراكيب الدقيقة التي تزيد مساحة التلامس مع السطح. تنتج عن هذه البنية قوى سطحية تسمح لها بالالتصاق والتسلق دون مادة لاصقة سائلة.","hashtags":["#Shorts","#وزغ","#حيوانات","#علوم","#هل_تعلم"]},
    {"search":"magnet attraction iron science","fallback_searches":["magnetism iron","magnetic field","magnet science"],"title":"لماذا يجذب المغناطيس الحديد ولا يجذب كل المعادن؟","text":"تتأثر المواد المختلفة بالمجالات المغناطيسية بدرجات مختلفة. الحديد وبعض المواد المشابهة تمتلك بنية تسمح باستجابة مغناطيسية قوية نسبيًا، بينما تكون استجابة كثير من المعادن الأخرى أضعف بكثير.","hashtags":["#Shorts","#مغناطيس","#فيزياء","#علوم","#هل_تعلم"]},
    {"search":"prism light spectrum","fallback_searches":["prism rainbow light","light spectrum","refraction prism"],"title":"كيف يكشف المنشور الزجاجي ألوان الضوء؟","text":"عندما يمر الضوء عبر منشور زجاجي ينكسر، وتختلف زاوية الانحراف قليلًا بين الألوان المختلفة. لذلك يمكن فصل الضوء الأبيض إلى طيف من الألوان المرئية.","hashtags":["#Shorts","#ضوء","#فيزياء","#علوم","#هل_تعلم"]},
    {"search":"laser beam technology","fallback_searches":["laser science","laser light","laser technology"],"title":"لماذا يكون ضوء الليزر مركزًا جدًا؟","text":"الليزر ينتج ضوءًا له خصائص مميزة من حيث الترابط والاتجاهية مقارنة بالضوء العادي. تسمح هذه الخصائص باستخدامه في الاتصالات والقياس والطب والصناعة وتطبيقات أخرى.","hashtags":["#Shorts","#ليزر","#فيزياء","#تقنية","#هل_تعلم"]},
    {"search":"hydraulic pressure machine","fallback_searches":["hydraulic system","hydraulic press","fluid pressure"],"title":"كيف تستطيع الأنظمة الهيدروليكية رفع أوزان كبيرة؟","text":"تعتمد الأنظمة الهيدروليكية على ضغط سائل محصور. يمكن للقوة المؤثرة على مساحة صغيرة أن تنتج قوة أكبر على مساحة أكبر وفق مبدأ انتقال الضغط في السائل.","hashtags":["#Shorts","#هيدروليك","#هندسة","#فيزياء","#هل_تعلم"]},
    {"search":"gear mechanism mechanical engineering","fallback_searches":["gears how work","gear ratio","mechanical gears"],"title":"لماذا تستخدم الآلات التروس بأحجام مختلفة؟","text":"تسمح نسب أحجام التروس بتغيير العلاقة بين السرعة وعزم الدوران. يمكن لنظام تروس مناسب أن يزيد العزم أو السرعة بحسب التصميم والوظيفة المطلوبة.","hashtags":["#Shorts","#تروس","#هندسة","#ميكانيكا","#هل_تعلم"]},
    {"search":"crane construction lifting","fallback_searches":["tower crane","construction crane","crane engineering"],"title":"كيف ترفع الرافعات البرجية الأحمال إلى ارتفاعات كبيرة؟","text":"تستخدم الرافعات البرجية أذرعًا وأنظمة بكرات ومحركات لرفع الأحمال وتحريكها. ويُحسب توزيع الوزن ونصف قطر الحركة وحدود الرفع لضمان بقاء الرافعة مستقرة ضمن ظروف التشغيل.","hashtags":["#Shorts","#رافعات","#هندسة","#بناء","#هل_تعلم"]},
    {"search":"escalator mechanism engineering","fallback_searches":["escalator how works","moving stairs mechanism","escalator technology"],"title":"كيف تتحرك درجات السلم الكهربائي باستمرار؟","text":"ترتبط درجات السلم الكهربائي بسلسلة متحركة تدور حول مسار مغلق. يحرك محرك كهربائي هذه السلسلة عبر نظام تروس، بينما توجه المسارات الدرجات للحفاظ على وضعها أثناء الحركة.","hashtags":["#Shorts","#سلالم_كهربائية","#هندسة","#تقنية","#هل_تعلم"]},
    {"search":"elevator counterweight cable","fallback_searches":["elevator mechanism","lift counterweight","elevator engineering"],"title":"لماذا تحتوي المصاعد على ثقل موازن؟","text":"يساعد الثقل الموازن على موازنة جزء كبير من وزن الكابينة والحمل. هذا يقلل القوة التي يحتاج إليها المحرك لتحريك المصعد ويجعل النظام أكثر كفاءة.","hashtags":["#Shorts","#مصاعد","#هندسة","#بناء","#هل_تعلم"]},
    {"search":"thermal insulation building wall","fallback_searches":["building insulation","thermal insulation","energy efficient building"],"title":"كيف تقلل العوازل الحرارية انتقال الحرارة في المباني؟","text":"تحتوي مواد العزل على بنية تقلل انتقال الحرارة مقارنة بمواد البناء الموصلة. وضع العزل في الجدران والأسقف والأرضيات يمكن أن يساعد على تقليل انتقال الحرارة إلى الداخل أو الخارج.","hashtags":["#Shorts","#عزل_حراري","#هندسة","#بناء","#هل_تعلم"]},
    {"search":"refrigerator cooling cycle","fallback_searches":["refrigerator how works","refrigeration cycle","fridge technology"],"title":"كيف يحافظ الثلاجة على برودة الطعام؟","text":"تستخدم الثلاجات دورة تبريد تنقل الحرارة من داخل الحجرة إلى الخارج. يمر وسيط التبريد بمراحل ضغط وتمدد وتبادل حراري تسمح باستخراج الحرارة من الداخل.","hashtags":["#Shorts","#ثلاجة","#هندسة","#تقنية","#هل_تعلم"]},
    {"search":"air conditioner cooling system","fallback_searches":["air conditioning cycle","AC how works","cooling technology"],"title":"كيف يبرد المكيف هواء الغرفة؟","text":"يسحب المكيف الحرارة من هواء الغرفة عبر دورة تبريد، ثم يطرح هذه الحرارة إلى الخارج. لذلك لا يختفي heat من الغرفة، بل تنتقل الطاقة الحرارية إلى مكان آخر.","hashtags":["#Shorts","#مكيف","#هندسة","#فيزياء","#هل_تعلم"]},
    {"search":"microwave electromagnetic waves food","fallback_searches":["microwave oven science","microwave heating","microwave technology"],"title":"كيف يسخن الميكروويف الطعام؟","text":"يولد فرن الميكروويف موجات كهرومغناطيسية بتردد مناسب للتسخين. تتفاعل هذه الموجات مع الجزيئات القطبية في الطعام، ما يزيد حركة الجزيئات ويساهم في رفع درجة الحرارة.","hashtags":["#Shorts","#ميكروويف","#فيزياء","#تقنية","#هل_تعلم"]},
    {"search":"induction cooker electromagnetic","fallback_searches":["induction cooking","induction stove science","electromagnetic cooking"],"title":"كيف يعمل موقد الحث الكهربائي؟","text":"ينتج موقد الحث مجالًا مغناطيسيًا متغيرًا يمكنه توليد تيارات كهربائية داخل أواني مناسبة. تتحول هذه الطاقة إلى حرارة داخل الوعاء نفسه، بدل تسخين سطح الموقد بالطريقة التقليدية.","hashtags":["#Shorts","#طبخ","#كهرباء","#فيزياء","#هل_تعلم"]},
    {"search":"traffic roundabout engineering","fallback_searches":["roundabout traffic","road engineering","intersection design"],"title":"لماذا تستخدم بعض الطرق الدوارات بدل الإشارات؟","text":"الدوارات تغير طريقة تقاطع المركبات وتقلل نقاط التعارض المباشر في بعض أنواع التقاطعات. يعتمد نجاحها على التصميم وحجم الحركة وقواعد الأولوية وسلوك السائقين.","hashtags":["#Shorts","#طرق","#هندسة","#مرور","#هل_تعلم"]},
    {"search":"airport runway engineering","fallback_searches":["airport runway","runway design","airport engineering"],"title":"لماذا تكون مدارج المطارات طويلة ومحددة الاتجاه؟","text":"طول المدرج يعتمد على نوع الطائرات ووزنها ودرجة الحرارة والارتفاع وعوامل أخرى. أما اتجاه المدرج فيرتبط جزئيًا بالرياح السائدة لتقليل تأثير الرياح الجانبية أثناء الإقلاع والهبوط.","hashtags":["#Shorts","#مطارات","#هندسة","#طيران","#هل_تعلم"]},
    {"search":"satellite solar panels space","fallback_searches":["satellite solar panels","spacecraft power","satellite technology"],"title":"لماذا تحمل الأقمار الصناعية ألواحًا شمسية كبيرة؟","text":"تحتاج الأقمار الصناعية إلى مصدر كهرباء لتشغيل أجهزتها وأنظمة الاتصال والحاسوب. تستخدم كثير من الأقمار ألواحًا شمسية لتحويل ضوء الشمس إلى كهرباء، مع بطاريات للاستخدام عندما لا تكون الألواح مضاءة.","hashtags":["#Shorts","#أقمار_صناعية","#فضاء","#طاقة","#هل_تعلم"]},
    {"search":"space telescope stars galaxy","fallback_searches":["space telescope","astronomy telescope","galaxy telescope"],"title":"لماذا توضع بعض التلسكوبات في الفضاء؟","text":"وجود التلسكوب فوق الغلاف الجوي يمكن أن يقلل تأثير بعض اضطرابات الغلاف الجوي على الرصد. كما يسمح لبعض التلسكوبات بدراسة أطوال موجية يحجبها الغلاف الجوي جزئيًا أو كليًا.","hashtags":["#Shorts","#تلسكوبات","#فضاء","#فلك","#هل_تعلم"]},
    {"search":"mars rover wheels science","fallback_searches":["Mars rover","rover wheels","Mars exploration"],"title":"كيف تتحرك المركبات الجوالة على سطح المريخ؟","text":"تستخدم المركبات الجوالة عجلات وأنظمة تعليق مصممة للتعامل مع سطح غير مستوٍ. وتُرسل أوامر الحركة من الأرض، بينما تستخدم المركبة حساسات وكاميرات لمساعدتها على التنقل وجمع البيانات.","hashtags":["#Shorts","#المريخ","#فضاء","#هندسة","#هل_تعلم"]},
    {"search":"rocket stages space launch","fallback_searches":["rocket staging","space rocket","launch vehicle"],"title":"لماذا تحتوي بعض الصواريخ على مراحل متعددة؟","text":"تفصل بعض الصواريخ أجزاءً من المركبة بعد استهلاك وقودها لتقليل الكتلة التي يجب دفعها لاحقًا. يسمح ذلك باستخدام الوقود المتبقي بكفاءة أكبر أثناء الصعود إلى المدار.","hashtags":["#Shorts","#صواريخ","#فضاء","#هندسة","#هل_تعلم"]},
    {"search":"astronaut spacesuit technology","fallback_searches":["spacesuit technology","astronaut suit","space suit"],"title":"لماذا تحتاج بدلة رائد الفضاء إلى أنظمة كثيرة؟","text":"بدلة الفضاء تساعد على توفير ضغط مناسب وحماية حرارية ووسائل اتصال وإدارة للبيئة المحيطة بالرائد. تختلف وظائف البدلة حسب المهمة ومكان استخدامها داخل المركبة أو خارجها.","hashtags":["#Shorts","#رواد_الفضاء","#فضاء","#تقنية","#هل_تعلم"]},
    {"search":"black hole gravity space","fallback_searches":["black hole science","event horizon","space black hole"],"title":"لماذا يصعب رؤية الثقب الأسود مباشرة؟","text":"الثقب الأسود لا يبعث ضوءًا يمكننا رؤيته بالطريقة المعتادة، لذلك يُدرس من خلال تأثيره في المادة والضوء المحيط به. يمكن لآثاره الجاذبية والقرائن الناتجة عن البيئة المحيطة أن تكشف وجوده.","hashtags":["#Shorts","#ثقوب_سوداء","#فضاء","#فيزياء","#هل_تعلم"]},
    {"search":"neutron star dense space","fallback_searches":["neutron star","dense star","space physics"],"title":"لماذا تُعد النجوم النيوترونية شديدة الكثافة؟","text":"تتكون النجوم النيوترونية من بقايا نجم ضخم بعد حدث نجمي عنيف. تنهار مادتها تحت تأثير الجاذبية إلى حالة شديدة الكثافة، فتتركز كتلة كبيرة في جسم صغير نسبيًا.","hashtags":["#Shorts","#نجوم_نيوترونية","#فضاء","#فيزياء","#هل_تعلم"]},
    {"search":"galaxy milky way stars space","fallback_searches":["Milky Way galaxy","galaxy structure","galaxy stars"],"title":"ما الذي يجعل مجرة درب التبانة تبدو كقرص ضخم؟","text":"تحتوي مجرة درب التبانة على عدد هائل من النجوم والغاز والغبار، وتدور مكوناتها ضمن بنية واسعة. يظهر جزء كبير من مادتها المرئية في قرص مجري مع مناطق أكثر كثافة في الوسط.","hashtags":["#Shorts","#درب_التبانة","#مجرة","#فضاء","#هل_تعلم"]},
    {"search":"aurora northern lights atmosphere","fallback_searches":["aurora borealis","aurora science","polar lights"],"title":"كيف تتكون الأضواء القطبية في السماء؟","text":"تحدث الأضواء القطبية عندما تتفاعل جسيمات قادمة من الشمس مع الغازات في الغلاف الجوي العلوي قرب المناطق القطبية. ينتج عن هذه التفاعلات ضوء بألوان مختلفة حسب نوع الغاز والارتفاع.","hashtags":["#Shorts","#أضواء_قطبية","#فضاء","#علوم","#هل_تعلم"]},
    {"search":"fossil rock paleontology","fallback_searches":["fossils science","fossil formation","paleontology"],"title":"كيف تتحول بقايا الكائنات إلى أحافير؟","text":"في ظروف مناسبة يمكن أن تُدفن بقايا الكائنات بسرعة داخل الرواسب، ثم تتغير تدريجيًا بفعل الضغط والعمليات الكيميائية. لا تتحول كل البقايا إلى أحافير، ولهذا تعد الأحافير سجلًا محدودًا لكنه مهم للحياة القديمة.","hashtags":["#Shorts","#أحافير","#جيولوجيا","#تاريخ_طبيعي","#هل_تعلم"]},
    {"search":"cave stalactite stalagmite geology","fallback_searches":["cave formations","stalactite stalagmite","cave geology"],"title":"كيف تتكون التكوينات داخل الكهوف؟","text":"يمكن للمياه التي تمر عبر الصخور أن تحمل مواد مذابة، ثم تترسب هذه المواد تدريجيًا داخل الكهوف. ومع مرور زمن طويل قد تتشكل تراكيب مثل الهوابط والصواعد.","hashtags":["#Shorts","#كهوف","#جيولوجيا","#طبيعة","#هل_تعلم"]},
    {"search":"mountain formation tectonic plates","fallback_searches":["mountain formation","tectonic plates mountains","geology mountains"],"title":"كيف تتكون بعض السلاسل الجبلية؟","text":"تتشكل بعض السلاسل الجبلية عندما تتحرك الصفائح التكتونية وتتقارب، فتتعرض الصخور للضغط والرفع والتشوه. وتختلف طريقة تشكل الجبال حسب نوع الحدود التكتونية والعمليات الجيولوجية.","hashtags":["#Shorts","#جبال","#جيولوجيا","#علوم","#هل_تعلم"]},
    {"search":"river delta satellite","fallback_searches":["river delta formation","delta geography","river sediment"],"title":"كيف تتكون دلتا الأنهار عند السواحل؟","text":"عندما يصل النهر إلى منطقة أبطأ حركة مثل البحر أو بحيرة، يمكن أن تترسب بعض الرواسب التي يحملها. ومع تراكمها عبر الزمن قد تتكون منطقة دلتا بأشكال متعددة.","hashtags":["#Shorts","#أنهار","#دلتا","#جغرافيا","#هل_تعلم"]},
    {"search":"sand dune wind desert","fallback_searches":["dune formation","wind sand dunes","desert dunes"],"title":"كيف تصنع الرياح أشكالًا مختلفة للكثبان الرملية؟","text":"تدفع الرياح حبيبات الرمل وتحركها بطرق تعتمد على سرعتها واتجاهها وكمية الرواسب. اختلاف هذه العوامل يؤدي إلى أشكال مختلفة من الكثبان واتجاهات متنوعة لحركتها.","hashtags":["#Shorts","#كثبان","#صحراء","#جيولوجيا","#هل_تعلم"]},
    {"search":"iceberg ocean floating","fallback_searches":["iceberg science","iceberg floating","polar ocean"],"title":"لماذا تطفو الجبال الجليدية فوق الماء؟","text":"الجليد أقل كثافة من الماء السائل، لذلك يمكن لقطعة جليد كبيرة أن تطفو. يبقى جزء منها تحت سطح الماء لأن الطفو يعتمد على توازن وزن الجليد مع قوة دفع الماء.","hashtags":["#Shorts","#جبال_جليدية","#محيط","#فيزياء","#هل_تعلم"]},
    {"search":"salt crystallization sea salt","fallback_searches":["salt crystals","salt evaporation","sea salt science"],"title":"كيف تتكون بلورات الملح عند تبخر الماء؟","text":"عندما يتبخر الماء من محلول ملحي ترتفع نسبة الملح فيه تدريجيًا. وعند الوصول إلى حالة مناسبة يمكن للأيونات أن تنتظم في بنية بلورية فتتكون بلورات الملح.","hashtags":["#Shorts","#ملح","#كيمياء","#علوم","#هل_تعلم"]},
    {"search":"rust iron oxidation","fallback_searches":["iron rust science","rust oxidation","metal corrosion"],"title":"لماذا يصدأ الحديد عند تعرضه للهواء والرطوبة؟","text":"الصدأ ينتج عن تفاعلات كيميائية بين الحديد والأكسجين والماء. تتغير بنية الحديد تدريجيًا وتتكون مركبات أكسدة على سطحه، وتسرع الرطوبة بعض عمليات التآكل.","hashtags":["#Shorts","#صدأ","#كيمياء","#علوم","#هل_تعلم"]},
    {"search":"vinegar baking soda reaction","fallback_searches":["acid base reaction","baking soda chemistry","chemical reaction"],"title":"لماذا يحدث فوران عند خلط الخل مع بيكربونات الصوديوم؟","text":"الخل يحتوي على حمض الأسيتيك، وبيكربونات الصوديوم تتفاعل معه في تفاعل ينتج غاز ثاني أكسيد الكربون. فقاعات الغاز هي السبب الرئيسي في ظهور الفوران.","hashtags":["#Shorts","#كيمياء","#تجارب","#علوم","#هل_تعلم"]},
    {"search":"soap bubbles surface tension","fallback_searches":["soap bubble science","surface tension bubbles","bubble physics"],"title":"لماذا تأخذ فقاعات الصابون شكلًا قريبًا من الكرة؟","text":"تحاول طبقة الصابون تقليل مساحة سطحها قدر الإمكان بسبب التوتر السطحي. الشكل الكروي يحقق مساحة سطح صغيرة مقارنة بالحجم، لذلك تميل الفقاعة الحرة إلى هذا الشكل.","hashtags":["#Shorts","#فقاعات","#فيزياء","#علوم","#هل_تعلم"]},
    {"search":"oil water separation chemistry","fallback_searches":["oil and water","density oil water","liquids chemistry"],"title":"لماذا لا يمتزج الزيت بالماء بسهولة؟","text":"تختلف طبيعة الجزيئات في الماء والزيت، لذلك لا تتوزع جزيئات الزيت داخل الماء بالطريقة نفسها التي تتوزع بها جزيئات الماء. كما أن كثافة كثير من الزيوت أقل من كثافة الماء، فتتجمع عادة في طبقة أعلى.","hashtags":["#Shorts","#كيمياء","#ماء","#علوم","#هل_تعلم"]},
    {"search":"ice melting temperature physics","fallback_searches":["melting ice","phase change water","ice physics"],"title":"لماذا يبقى الجليد باردًا أثناء ذوبانه؟","text":"أثناء تغير الحالة من صلب إلى سائل تُستخدم الطاقة الحرارية الداخلة في عملية الانصهار بدل رفع درجة الحرارة مباشرة. لذلك يمكن أن تبقى درجة حرارة خليط الجليد والماء قريبة من درجة الانصهار حتى يذوب جزء كبير من الجليد.","hashtags":["#Shorts","#جليد","#فيزياء","#علوم","#هل_تعلم"]},
]

TOPICS.extend(EXTRA_TOPICS)


def validate_topic_pool():
    seen_titles = set()
    seen_texts = set()
    seen_searches = set()
    duplicates = []

    for index, topic in enumerate(TOPICS, start=1):
        title = normalize_content(topic.get("title", ""))
        text = normalize_content(topic.get("text", ""))
        search = normalize_content(topic.get("search", ""))

        if title and title in seen_titles:
            duplicates.append(f"duplicate title at #{index}: {topic.get('title', '')}")
        if text and text in seen_texts:
            duplicates.append(f"duplicate text at #{index}: {topic.get('title', '')}")
        if search and search in seen_searches:
            duplicates.append(f"duplicate search at #{index}: {topic.get('title', '')}")

        seen_titles.add(title)
        seen_texts.add(text)
        seen_searches.add(search)

    if duplicates:
        raise RuntimeError(
            "DUPLICATE TOPICS FOUND IN TOPICS: " + " | ".join(duplicates)
        )

    print(f"Unique content pool verified: {len(TOPICS)} topics")


# =========================================================
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


def select_new_topic(used_content):
    # Never reuse a published topic. The comparison checks the title, full
    # script, and Pexels search phrase, including legacy memory records.
    available = [
        topic for topic in TOPICS
        if not content_already_used(topic, used_content)
    ]

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
    """
    Use Azure Neural Speech when configured; otherwise preserve the existing
    Edge-TTS fallback so the workflow does not become dependent on a paid API.
    """
    if AZURE_SPEECH_KEY and AZURE_SPEECH_REGION:
        print("Creating voice with Azure Neural Speech...")

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
