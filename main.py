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

NUMBER_OF_CLIPS = 7
CLIP_DURATION = 3.2
FPS = 30

VOICE_NAME = "ar-SA-HamedNeural"
VOICE_RATE = "+5%"
VOICE_VOLUME = "+0%"
VOICE_PITCH = "+0Hz"

YOUTUBE_PRIVACY = "public"
YOUTUBE_CATEGORY_ID = "17"
YOUTUBE_MADE_FOR_KIDS = False


# =========================================================
# CONTENT
# =========================================================

TOPICS = [
    {
        "search": "football stadium match players",
        "fallback_searches": [
            "football match stadium",
            "soccer stadium players",
            "football players action"
        ],
        "title": "هل تعلم لماذا أصبحت البيانات مهمة جدًا في كرة القدم؟",
        "text": "هل تعلم أن كرة القدم الحديثة أصبحت تعتمد على البيانات بشكل مذهل؟ المدربون يستطيعون تحليل سرعة اللاعب وعدد تمريراته ومساحاته داخل الملعب وحتى تحركات الفريق بالكامل. هذه البيانات تساعد المدرب على اكتشاف نقاط القوة والضعف وقد تغيّر طريقة لعب الفريق في المباراة التالية.",
        "hashtags": [
            "#Shorts",
            "#كرة_القدم",
            "#هل_تعلم",
            "#معلومات",
            "#Football",
            "#Soccer"
        ],
    },
    {
        "search": "football player running match",
        "fallback_searches": [
            "soccer player running",
            "football fitness",
            "soccer match action"
        ],
        "title": "هل تعلم كم يركض لاعب كرة القدم في المباراة؟",
        "text": "هل فكرت يومًا كم يركض لاعب كرة القدم خلال مباراة واحدة؟ اللاعب المحترف يقطع عدة كيلومترات أثناء المباراة، لكن المثير أن المسافة ليست كل شيء. فاللاعب يغيّر سرعته باستمرار بين المشي والركض والجري السريع. ولهذا تحتاج كرة القدم الحديثة إلى لياقة عالية وسرعة كبيرة في اتخاذ القرار.",
        "hashtags": [
            "#Shorts",
            "#كرة_القدم",
            "#هل_تعلم",
            "#Football",
            "#Soccer",
            "#رياضة"
        ],
    },
    {
        "search": "football goalkeeper save",
        "fallback_searches": [
            "soccer goalkeeper",
            "goalkeeper training",
            "football goalkeeper action"
        ],
        "title": "لماذا يبدو حارس المرمى أسرع مما تتوقع؟",
        "text": "هل تعلم أن حارس المرمى يحتاج إلى اتخاذ قرار في لحظة قصيرة جدًا؟ الحارس لا يعتمد على سرعة يديه فقط، بل يقرأ وضعية اللاعب واتجاه جسمه قبل التسديدة. ولهذا يبدأ أحيانًا بالتحرك قبل أن تصل الكرة إليه. في المستوى الاحترافي، جزء من الثانية قد يصنع الفرق.",
        "hashtags": [
            "#Shorts",
            "#كرة_القدم",
            "#حراس_المرمى",
            "#هل_تعلم",
            "#Football",
            "#Soccer"
        ],
    },
    {
        "search": "football fans stadium crowd",
        "fallback_searches": [
            "soccer fans stadium",
            "football crowd",
            "football supporters"
        ],
        "title": "هل تعلم لماذا تختلف أجواء ملاعب كرة القدم؟",
        "text": "هل لاحظت أن بعض ملاعب كرة القدم تبدو مختلفة تمامًا من ناحية الأجواء؟ التصميم وحجم المدرجات وطريقة توزيع الجماهير كلها تؤثر في تجربة المشجعين داخل الملعب. ولهذا أصبحت بعض الملاعب الحديثة مصممة لتكون تجربة كاملة، وليس مجرد مكان لمشاهدة المباراة.",
        "hashtags": [
            "#Shorts",
            "#كرة_القدم",
            "#جماهير",
            "#ملاعب",
            "#هل_تعلم",
            "#Football"
        ],
    },
    {
        "search": "football training player",
        "fallback_searches": [
            "soccer training",
            "football skills training",
            "soccer practice"
        ],
        "title": "لماذا يتدرب لاعبو كرة القدم على أشياء تبدو بسيطة؟",
        "text": "هل تعلم أن أبسط المهارات في كرة القدم تحتاج إلى تكرار هائل؟ التمرير واستلام الكرة والتحرك بدون كرة كلها مهارات يتدرب عليها اللاعبون باستمرار حتى تصبح تلقائية. وعندما تصل المباراة إلى لحظة حاسمة، يحتاج اللاعب إلى تنفيذ المهارة بسرعة دون تردد.",
        "hashtags": [
            "#Shorts",
            "#كرة_القدم",
            "#تدريب",
            "#هل_تعلم",
            "#Football",
            "#Soccer"
        ],
    },
    {
        "search": "football goal scoring",
        "fallback_searches": [
            "soccer goal",
            "football striker",
            "soccer scoring"
        ],
        "title": "هل تعلم لماذا يصعب تسجيل الهدف في كرة القدم؟",
        "text": "تسجيل الهدف في كرة القدم ليس مجرد تسديدة قوية. اللاعب يحتاج إلى اختيار المكان والتوقيت والزاوية المناسبة خلال ثوانٍ قليلة. ولهذا قد تكون اللمسة الأخيرة أهم من قوة التسديدة نفسها. وفي المباريات الكبيرة، قرار واحد سريع قد يغيّر النتيجة بالكامل.",
        "hashtags": [
            "#Shorts",
            "#كرة_القدم",
            "#أهداف",
            "#هل_تعلم",
            "#Football",
            "#Soccer"
        ],
    },
    {
        "search": "space earth science",
        "fallback_searches": [
            "earth space",
            "planet earth",
            "solar system"
        ],
        "title": "هل تعلم أنك تتحرك الآن رغم أنك جالس؟",
        "text": "هل تعلم أنك تتحرك الآن رغم أنك جالس في مكانك؟ الأرض تدور حول نفسها، وفي الوقت نفسه تتحرك حول الشمس. والنظام الشمسي نفسه يتحرك داخل مجرة درب التبانة. وهذا يعني أننا في حركة مستمرة، حتى عندما نشعر أننا ثابتون تمامًا.",
        "hashtags": [
            "#Shorts",
            "#هل_تعلم",
            "#علوم",
            "#معلومات",
            "#فضاء",
            "#Science"
        ],
    },
    {
        "search": "ocean underwater marine life",
        "fallback_searches": [
            "deep ocean",
            "underwater sea",
            "marine animals"
        ],
        "title": "لماذا ما زال جزء كبير من المحيط غامضًا؟",
        "text": "هل تعلم أن أعماق المحيط ما زالت تحتوي على مناطق لم نعرف عنها الكثير؟ الضغط والظلام والظروف القاسية تجعل استكشاف الأعماق صعبًا جدًا. ولهذا تستمر البعثات العلمية في اكتشاف كائنات وبيئات جديدة. المحيط الذي نراه من السطح يخفي عالمًا مختلفًا تمامًا.",
        "hashtags": [
            "#Shorts",
            "#علوم",
            "#محيط",
            "#هل_تعلم",
            "#Science"
        ],
    },
    {
        "search": "lightning storm science",
        "fallback_searches": [
            "thunderstorm lightning",
            "lightning sky",
            "storm clouds"
        ],
        "title": "كيف يمكن لبرق واحد أن يكون قويًا جدًا؟",
        "text": "البرق ليس مجرد وميض في السماء. إنه تفريغ كهربائي هائل يحدث عندما تتراكم شحنات كهربائية داخل السحب. ولهذا يمكن أن يظهر البرق بطاقة ضخمة خلال فترة زمنية قصيرة جدًا. والصوت الذي نسمعه بعده هو الرعد الناتج عن التسخين السريع للهواء.",
        "hashtags": [
            "#Shorts",
            "#علوم",
            "#برق",
            "#طقس",
            "#هل_تعلم",
            "#Science"
        ],
    },
    {
        "search": "volcano eruption lava",
        "fallback_searches": [
            "volcano mountain",
            "lava volcano",
            "volcanic eruption"
        ],
        "title": "ماذا يحدث داخل البركان قبل ثورانه؟",
        "text": "قبل ثوران البركان تحدث تغيرات في باطن الأرض. الصهارة والغازات يمكن أن تتحرك داخل النظام البركاني وتؤثر في الضغط الموجود تحت السطح. ولهذا يراقب العلماء الزلازل والغازات والتغيرات الأرضية لفهم نشاط البراكين بشكل أفضل.",
        "hashtags": [
            "#Shorts",
            "#براكين",
            "#علوم",
            "#هل_تعلم",
            "#Science"
        ],
    },
    {
        "search": "airplane flying cockpit",
        "fallback_searches": [
            "aircraft flying sky",
            "airplane takeoff",
            "commercial airplane"
        ],
        "title": "كيف يعرف الطيار مكان الطائرة في السماء؟",
        "text": "هل تساءلت كيف يعرف الطيار مكان الطائرة أثناء الرحلة؟ الطائرات تستخدم مجموعة من أنظمة الملاحة والأجهزة لتحديد الموقع والاتجاه والارتفاع والسرعة. كما يتابع الطيارون تعليمات المراقبة الجوية وخطة الرحلة. كل هذه الأنظمة تعمل معًا للحفاظ على مسار الرحلة.",
        "hashtags": [
            "#Shorts",
            "#طيران",
            "#طيارات",
            "#هل_تعلم",
            "#Science"
        ],
    },
    {
        "search": "modern car technology driving",
        "fallback_searches": [
            "modern car road",
            "electric car driving",
            "car technology"
        ],
        "title": "لماذا أصبحت السيارات الحديثة مليئة بالحساسات؟",
        "text": "السيارات الحديثة تحتوي على عدد كبير من الحساسات. بعضها يراقب السرعة وبعضها المسافة وبعضها يساعد أنظمة السلامة. هذه البيانات تسمح للسيارة بمراقبة ما يحدث حولها وتحسين عمل العديد من الأنظمة أثناء القيادة.",
        "hashtags": [
            "#Shorts",
            "#سيارات",
            "#تقنية",
            "#هل_تعلم",
            "#Cars",
            "#Technology"
        ],
    },
    {
        "search": "robot technology laboratory",
        "fallback_searches": [
            "robotics technology",
            "robot machine",
            "future technology"
        ],
        "title": "كيف تستطيع الروبوتات تنفيذ حركات دقيقة؟",
        "text": "الروبوت لا يتحرك بطريقة عشوائية. يستخدم محركات وحساسات وبرمجيات للتحكم في الحركة. وبحسب تصميمه يمكنه قياس موقع أجزائه وتعديل الحركة باستمرار للوصول إلى نتيجة دقيقة.",
        "hashtags": [
            "#Shorts",
            "#روبوت",
            "#تقنية",
            "#هل_تعلم",
            "#Technology"
        ],
    },
    {
        "search": "computer processor technology",
        "fallback_searches": [
            "computer chip",
            "processor technology",
            "computer hardware"
        ],
        "title": "ماذا يفعل المعالج داخل جهازك؟",
        "text": "المعالج هو أحد أهم المكونات داخل الكمبيوتر والهاتف. وظيفته تنفيذ التعليمات ومعالجة العمليات التي تطلبها البرامج. وكلما تطورت المعالجات أصبحت قادرة على تنفيذ عمليات أكثر بسرعة وكفاءة أعلى.",
        "hashtags": [
            "#Shorts",
            "#تقنية",
            "#كمبيوتر",
            "#هل_تعلم",
            "#Technology"
        ],
    },
    {
        "search": "internet data center servers",
        "fallback_searches": [
            "server room",
            "data center",
            "internet servers"
        ],
        "title": "أين تذهب بياناتك عندما تستخدم الإنترنت؟",
        "text": "عندما تستخدم تطبيقًا أو موقعًا على الإنترنت، قد تنتقل البيانات بين جهازك وخوادم موجودة في مراكز بيانات. هذه الخوادم تعالج الطلبات وتخزن أنواعًا مختلفة من المعلومات وتعيد البيانات إلى جهازك خلال وقت قصير جدًا.",
        "hashtags": [
            "#Shorts",
            "#إنترنت",
            "#تقنية",
            "#هل_تعلم",
            "#Technology"
        ],
    },
    {
        "search": "rocket launch space",
        "fallback_searches": [
            "rocket launch",
            "spacecraft launch",
            "rocket space"
        ],
        "title": "لماذا تحتاج الصواريخ إلى قوة هائلة عند الإطلاق؟",
        "text": "الصاروخ يحتاج إلى توليد قوة دفع كبيرة جدًا حتى يبدأ بالابتعاد عن الأرض. كلما ارتفع الصاروخ تتغير الظروف المحيطة به. ولهذا صُممت مراحل الصاروخ وأنظمة الدفع بدقة لتوفير الطاقة المطلوبة خلال أجزاء مختلفة من الرحلة.",
        "hashtags": [
            "#Shorts",
            "#فضاء",
            "#صواريخ",
            "#علوم",
            "#هل_تعلم",
            "#Science"
        ],
    },
    {
        "search": "moon night sky",
        "fallback_searches": [
            "moon space",
            "full moon sky",
            "lunar surface"
        ],
        "title": "لماذا نرى القمر بأشكال مختلفة خلال الشهر؟",
        "text": "القمر لا يغيّر شكله فعليًا خلال الشهر. الذي يتغير هو الجزء المضيء الذي نراه من الأرض مع دوران القمر حول كوكبنا. ولهذا تظهر لنا مراحل مختلفة مثل الهلال والبدر.",
        "hashtags": [
            "#Shorts",
            "#القمر",
            "#فضاء",
            "#علوم",
            "#هل_تعلم"
        ],
    },
    {
        "search": "human eye vision science",
        "fallback_searches": [
            "eye anatomy",
            "human vision",
            "eyes science"
        ],
        "title": "كيف تستطيع عيناك رؤية العالم من حولك؟",
        "text": "العين تستقبل الضوء من البيئة المحيطة ثم تحوله إلى إشارات عصبية تنتقل إلى الدماغ. بعد ذلك يعالج الدماغ هذه الإشارات حتى تتكون لدينا الصورة التي نراها. لذلك الرؤية ليست وظيفة العين وحدها.",
        "hashtags": [
            "#Shorts",
            "#علوم",
            "#جسم_الإنسان",
            "#هل_تعلم",
            "#Science"
        ],
    },
    {
        "search": "human brain neuroscience",
        "fallback_searches": [
            "brain science",
            "neuroscience",
            "human brain"
        ],
        "title": "لماذا يُعد الدماغ من أعقد أعضاء الجسم؟",
        "text": "الدماغ مسؤول عن عدد هائل من العمليات في جسم الإنسان. فهو يشارك في الحركة والتفكير والذاكرة ومعالجة المعلومات والعديد من الوظائف الأخرى. ولهذا ما زال العلماء يدرسون الكثير من أسراره لفهم طريقة عمله بشكل أدق.",
        "hashtags": [
            "#Shorts",
            "#دماغ",
            "#علوم",
            "#هل_تعلم",
            "#Science"
        ],
    },
    {
        "search": "plant growth nature sunlight",
        "fallback_searches": [
            "plants sunlight",
            "plant growth",
            "green plants"
        ],
        "title": "كيف تصنع النباتات غذاءها؟",
        "text": "النباتات تستخدم عملية تسمى البناء الضوئي لصنع غذائها. تستخدم الضوء والماء وثاني أكسيد الكربون لإنتاج الطاقة الكيميائية التي تحتاج إليها. ولهذا يعد ضوء الشمس جزءًا أساسيًا من حياة معظم النباتات.",
        "hashtags": [
            "#Shorts",
            "#نباتات",
            "#علوم",
            "#هل_تعلم",
            "#Science"
        ],
    },
    {
        "search": "desert sand dunes landscape",
        "fallback_searches": [
            "desert landscape",
            "sand dunes",
            "desert nature"
        ],
        "title": "لماذا تتحرك بعض الكثبان الرملية؟",
        "text": "الكثبان الرملية ليست ثابتة دائمًا. عندما تهب الرياح يمكنها نقل حبيبات الرمل من مكان إلى آخر. ومع استمرار حركة الرمال قد يتغير شكل الكثيب وموقعه تدريجيًا. ولهذا تبدو بعض الصحارى وكأنها تتغير مع الوقت.",
        "hashtags": [
            "#Shorts",
            "#صحراء",
            "#طبيعة",
            "#علوم",
            "#هل_تعلم"
        ],
    },
    {
        "search": "waterfall river nature",
        "fallback_searches": [
            "river nature",
            "waterfall landscape",
            "fresh water"
        ],
        "title": "لماذا تتحرك الأنهار باستمرار نحو مناطق منخفضة؟",
        "text": "الماء يتأثر بالجاذبية، ولهذا تتحرك الأنهار عادة من المناطق الأعلى نحو المناطق الأقل ارتفاعًا. وخلال رحلتها يمكن للمياه أن تنحت الصخور والتربة وتغيّر شكل البيئة المحيطة بها على مدى فترات طويلة.",
        "hashtags": [
            "#Shorts",
            "#أنهار",
            "#طبيعة",
            "#علوم",
            "#هل_تعلم"
        ],
    },
    {
        "search": "shark underwater ocean",
        "fallback_searches": [
            "shark swimming",
            "marine predator",
            "ocean shark"
        ],
        "title": "لماذا تُعد أسماك القرش مهمة للنظام البحري؟",
        "text": "أسماك القرش جزء مهم من كثير من الأنظمة البيئية البحرية. وجود المفترسات يساعد في الحفاظ على توازن أعداد الكائنات الأخرى. ولهذا فإن اختفاء نوع مهم من النظام البيئي قد يؤثر في أنواع وعمليات أخرى مرتبطة به.",
        "hashtags": [
            "#Shorts",
            "#أسماك_القرش",
            "#محيط",
            "#علوم",
            "#هل_تعلم"
        ],
    },
    {
        "search": "penguin antarctica ice",
        "fallback_searches": [
            "penguins ice",
            "antarctica wildlife",
            "penguin colony"
        ],
        "title": "كيف تستطيع البطاريق العيش في البرد القارس؟",
        "text": "البطاريق تمتلك تكيفات تساعدها على تحمل البيئات الباردة. ريشها الكثيف وطبقات العزل في أجسامها تساعدها على الاحتفاظ بالحرارة. كما أن بعض الأنواع تتجمع معًا لتقليل فقدان الحرارة.",
        "hashtags": [
            "#Shorts",
            "#بطاريق",
            "#حيوانات",
            "#علوم",
            "#هل_تعلم"
        ],
    },
    {
        "search": "cheetah running wildlife",
        "fallback_searches": [
            "cheetah speed",
            "wild cat running",
            "cheetah animal"
        ],
        "title": "لماذا يُعد الفهد من أسرع الحيوانات البرية؟",
        "text": "الفهد يمتلك جسمًا مصممًا للانطلاق السريع. أطرافه وعموده الفقري وعضلاته تساعده على زيادة سرعته خلال وقت قصير. لكن هذه السرعة العالية تحتاج إلى طاقة كبيرة ولهذا لا يستطيع الحفاظ على أقصى سرعته لفترات طويلة.",
        "hashtags": [
            "#Shorts",
            "#فهد",
            "#حيوانات",
            "#هل_تعلم",
            "#Science"
        ],
    },
    {
        "search": "ancient ruins archaeology",
        "fallback_searches": [
            "ancient civilization ruins",
            "archaeology discovery",
            "ancient history"
        ],
        "title": "كيف يعرف العلماء عمر الآثار القديمة؟",
        "text": "العلماء لا يعتمدون على طريقة واحدة لمعرفة عمر الآثار. يمكن استخدام أساليب مختلفة حسب نوع المادة والعينة. كما تساعد طبقات التربة والسياق الأثري والمقارنة التاريخية في بناء صورة أدق عن عمر الموقع أو القطعة.",
        "hashtags": [
            "#Shorts",
            "#تاريخ",
            "#آثار",
            "#هل_تعلم",
            "#History"
        ],
    },
    {
        "search": "ancient egypt pyramids",
        "fallback_searches": [
            "egypt pyramids",
            "ancient egypt",
            "pyramid history"
        ],
        "title": "كيف بُنيت الأهرامات قبل آلاف السنين؟",
        "text": "بناء الأهرامات كان مشروعًا هندسيًا ضخمًا بالنسبة لعصره. اعتمد المصريون القدماء على التخطيط والعمالة والأدوات وطرق النقل لنقل الأحجار وترتيبها بدقة. ولا تزال بعض تفاصيل تقنيات البناء القديمة محل دراسة ونقاش علمي.",
        "hashtags": [
            "#Shorts",
            "#مصر",
            "#أهرامات",
            "#تاريخ",
            "#هل_تعلم"
        ],
    },
    {
        "search": "bridge engineering construction",
        "fallback_searches": [
            "modern bridge",
            "engineering bridge",
            "bridge construction"
        ],
        "title": "كيف تستطيع الجسور تحمل أوزان ضخمة؟",
        "text": "الجسر لا يعتمد على مادة قوية فقط. التصميم الهندسي يوزع القوى والأحمال على أجزاء مختلفة من الهيكل. ويحسب المهندسون تأثير الوزن والرياح والاهتزازات وعوامل أخرى حتى يستطيع الجسر العمل بأمان ضمن الحدود المصممة له.",
        "hashtags": [
            "#Shorts",
            "#هندسة",
            "#جسور",
            "#تقنية",
            "#هل_تعلم"
        ],
    },
    {
        "search": "train railway high speed",
        "fallback_searches": [
            "high speed train",
            "modern railway",
            "train technology"
        ],
        "title": "لماذا تسير بعض القطارات بسرعة كبيرة جدًا؟",
        "text": "القطارات السريعة تعتمد على تصميمات تقلل مقاومة الهواء وأنظمة دفع متطورة ومسارات مصممة بدقة. كما تستخدم أنظمة تحكم ومراقبة تساعد على إدارة السرعة والمسار. كل هذه العناصر تعمل معًا لتحقيق رحلة سريعة ومستقرة.",
        "hashtags": [
            "#Shorts",
            "#قطارات",
            "#هندسة",
            "#تقنية",
            "#هل_تعلم"
        ],
    },
    {
        "search": "smartphone technology phone",
        "fallback_searches": [
            "mobile phone technology",
            "smartphone",
            "phone hardware"
        ],
        "title": "كيف يعرف هاتفك اتجاهه عندما تدور به؟",
        "text": "الهاتف يحتوي على حساسات صغيرة تقيس الحركة والتسارع والدوران. البرمجيات تجمع هذه البيانات لتقدير اتجاه الجهاز وحركته. ولهذا يستطيع الهاتف تغيير اتجاه الشاشة وتشغيل العديد من الميزات التي تعتمد على الحركة.",
        "hashtags": [
            "#Shorts",
            "#جوال",
            "#تقنية",
            "#هل_تعلم",
            "#Technology"
        ],
    },
    {
        "search": "solar panels renewable energy",
        "fallback_searches": [
            "solar energy",
            "solar power panels",
            "renewable energy"
        ],
        "title": "كيف تحول الألواح الشمسية ضوء الشمس إلى كهرباء؟",
        "text": "الألواح الشمسية تحتوي على خلايا قادرة على تحويل الطاقة الضوئية إلى طاقة كهربائية. عندما يصل الضوء إلى الخلايا تتحرك الشحنات داخل المادة وينتج عن ذلك تيار كهربائي يمكن استخدامه أو تخزينه.",
        "hashtags": [
            "#Shorts",
            "#طاقة_شمسية",
            "#علوم",
            "#تقنية",
            "#هل_تعلم"
        ],
    },
    {
        "search": "ice glacier mountains climate",
        "fallback_searches": [
            "glacier ice",
            "mountain glacier",
            "frozen landscape"
        ],
        "title": "لماذا تتحرك الأنهار الجليدية رغم أنها تبدو ثابتة؟",
        "text": "الأنهار الجليدية تتكون من كتل ضخمة من الجليد لكنها تستطيع التحرك ببطء شديد تحت تأثير الجاذبية والضغط. قد تكون الحركة غير ملحوظة خلال يوم واحد، لكنها تصبح واضحة عند دراسة التغيرات على مدى سنوات.",
        "hashtags": [
            "#Shorts",
            "#جليد",
            "#علوم",
            "#طبيعة",
            "#هل_تعلم"
        ],
    },
    {
        "search": "tornado storm weather",
        "fallback_searches": [
            "tornado clouds",
            "severe weather",
            "storm tornado"
        ],
        "title": "كيف تتشكل الأعاصير القمعية؟",
        "text": "الأعاصير القمعية يمكن أن تتشكل في ظروف جوية معينة عندما تتفاعل كتل هوائية مختلفة مع تغيرات في سرعة واتجاه الرياح. هذه الظروف قد تساعد على تكوين دوران قوي داخل العاصفة. لكن ليس كل اضطراب جوي يتحول إلى إعصار.",
        "hashtags": [
            "#Shorts",
            "#طقس",
            "#أعاصير",
            "#علوم",
            "#هل_تعلم"
        ],
    },
    {
        "search": "volleyball basketball sports arena",
        "fallback_searches": [
            "basketball game",
            "sports arena",
            "volleyball match"
        ],
        "title": "لماذا تختلف سرعة رد الفعل بين الرياضات؟",
        "text": "كل رياضة تضع اللاعب أمام مواقف مختلفة تحتاج إلى استجابة سريعة. في بعض الألعاب يجب متابعة جسم سريع جدًا، وفي ألعاب أخرى يحتاج اللاعب إلى توقع الحركة قبل حدوثها. ولهذا يتدرب الرياضيون على رد الفعل والتركيز باستمرار.",
        "hashtags": [
            "#Shorts",
            "#رياضة",
            "#هل_تعلم",
            "#Sports",
            "#معلومات"
        ],
    },
    {
        "search": "stadium architecture modern",
        "fallback_searches": [
            "modern stadium",
            "sports stadium architecture",
            "football arena"
        ],
        "title": "لماذا أصبحت الملاعب الحديثة أكثر تعقيدًا؟",
        "text": "الملعب الحديث لم يعد مجرد مدرجات وملعب. التصميم يشمل الإضاءة والشاشات وأنظمة الصوت والمداخل وأنظمة الأمن وإدارة الجماهير. ولهذا أصبحت الملاعب مشاريع هندسية وتقنية ضخمة.",
        "hashtags": [
            "#Shorts",
            "#ملاعب",
            "#هندسة",
            "#رياضة",
            "#هل_تعلم"
        ],
    },
    {
        "search": "night city traffic lights",
        "fallback_searches": [
            "city night traffic",
            "urban technology",
            "city lights"
        ],
        "title": "كيف تساعد إشارات المرور في تنظيم المدن؟",
        "text": "إشارات المرور تساعد على تنظيم حركة المركبات والمشاة وتقليل التعارض بين اتجاهات السير. وفي بعض المدن الحديثة يمكن استخدام أنظمة ذكية لمراقبة حركة المرور وتعديل توقيت الإشارات حسب الحاجة.",
        "hashtags": [
            "#Shorts",
            "#مدن",
            "#تقنية",
            "#مرور",
            "#هل_تعلم"
        ],
    },
    {
        "search": "3d printing technology machine",
        "fallback_searches": [
            "3d printer",
            "3d printing",
            "modern manufacturing"
        ],
        "title": "كيف تستطيع الطابعة ثلاثية الأبعاد بناء جسم كامل؟",
        "text": "الطباعة ثلاثية الأبعاد تختلف عن الطباعة التقليدية. بدل وضع الحبر على الورق، تبني الطابعة الجسم طبقة فوق طبقة اعتمادًا على نموذج رقمي. ولهذا يمكن استخدامها لصناعة أشكال معقدة يصعب تصنيعها بطرق أخرى.",
        "hashtags": [
            "#Shorts",
            "#طباعة_ثلاثية_الأبعاد",
            "#تقنية",
            "#هل_تعلم",
            "#Technology"
        ],
    },
    {
        "search": "satellite earth orbit",
        "fallback_searches": [
            "satellite space",
            "earth satellite",
            "satellite technology"
        ],
        "title": "كيف تبقى الأقمار الصناعية في مدارها؟",
        "text": "القمر الصناعي لا يبقى في الفضاء لأنه بعيد عن الجاذبية. الجاذبية ما زالت تؤثر فيه، لكن سرعته الجانبية تجعله في حالة سقوط مستمر حول الأرض. وهذا التوازن بين الحركة والجاذبية يسمح له بالبقاء في المدار.",
        "hashtags": [
            "#Shorts",
            "#أقمار_صناعية",
            "#فضاء",
            "#علوم",
            "#هل_تعلم"
        ],
    },
    {
        "search": "earth atmosphere clouds sky",
        "fallback_searches": [
            "atmosphere earth",
            "clouds sky",
            "earth weather"
        ],
        "title": "لماذا لا نشعر بالهواء رغم أنه يحيط بنا؟",
        "text": "الهواء موجود حولنا في كل مكان، لكننا لا نراه لأن معظم مكوناته غازات شفافة. ومع ذلك فإن للهواء كتلة وضغطًا ويمكنه التأثير في الأجسام. ولهذا نستطيع ملاحظة وجوده من خلال الرياح والضغط وحركة الأشياء.",
        "hashtags": [
            "#Shorts",
            "#علوم",
            "#هواء",
            "#طقس",
            "#هل_تعلم"
        ],
    },
]


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

    missing = [
        name for name, value in required.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing)
        )

    check_binary("ffmpeg")
    check_binary("ffprobe")

    WORK_DIR.mkdir(parents=True, exist_ok=True)


def clean_previous_files():
    print("Cleaning previous generated files...")

    for file in [
        OUTPUT_VIDEO,
        VOICE_FILE,
        SUBTITLE_FILE
    ]:
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
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )

    temporary.replace(path)


def load_used_clips():
    return set(
        str(x)
        for x in load_json_list(USED_CLIPS_FILE)
    )


def save_used_clips(used_clips):
    save_json_list(
        USED_CLIPS_FILE,
        sorted(used_clips)
    )


def load_used_content():
    return load_json_list(USED_CONTENT_FILE)


def save_used_content(used_content):
    save_json_list(
        USED_CONTENT_FILE,
        used_content
    )


# =========================================================
# CONTENT MEMORY
# =========================================================

def normalize_content(text):
    text = str(text).lower()

    text = re.sub(
        r"[\u064B-\u065F\u0670]",
        "",
        text
    )

    text = re.sub(
        r"[^\w\s\u0600-\u06FF]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def content_fingerprint(topic):
    return (
        normalize_content(
            topic.get("title", "")
        ),
        normalize_content(
            topic.get("text", "")
        ),
        normalize_content(
            topic.get("search", "")
        ),
    )


def content_already_used(topic, used_content):
    title = normalize_content(
        topic.get("title", "")
    )

    text = normalize_content(
        topic.get("text", "")
    )

    search = normalize_content(
        topic.get("search", "")
    )

    for old in used_content:

        old_title = normalize_content(
            old.get("title", "")
        )

        old_text = normalize_content(
            old.get("text", "")
        )

        old_search = normalize_content(
            old.get("search", "")
        )

        if title and title == old_title:
            return True

        if text and text == old_text:
            return True

        if search and search == old_search:
            return True

    return False


def select_new_topic(used_content):

    available = [
        topic
        for topic in TOPICS
        if not content_already_used(
            topic,
            used_content
        )
    ]

    if not available:
        raise RuntimeError(
            "ALL CONTENT TOPICS HAVE BEEN USED. "
            "Add more unique topics to TOPICS."
        )

    topic = random.choice(available)

    print("\n================================")
    print("NEW CONTENT SELECTED")
    print(topic["title"])
    print(
        f"Remaining unused topics: "
        f"{len(available) - 1}"
    )
    print("================================\n")

    return topic


def remember_content(
    topic,
    video_id,
    used_content
):
    used_content.append({
        "title": topic["title"],
        "text": topic["text"],
        "search": topic["search"],
        "fingerprint": list(
            content_fingerprint(topic)
        ),
        "video_id": video_id,
        "saved_at": int(time.time()),
    })

    save_used_content(
        used_content
    )

    print(
        f"Content memory updated. "
        f"Total: {len(used_content)}"
    )


# =========================================================
# PEXELS
# =========================================================

def search_pexels(query, page=1):

    url = "https://api.pexels.com/v1/videos/search"

    headers = {
        "Authorization": PEXELS_API_KEY
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


def choose_video_file(video):

    files = video.get(
        "video_files",
        []
    )

    vertical = []

    for item in files:

        width = item.get("width") or 0
        height = item.get("height") or 0
        link = item.get("link")

        if not link:
            continue

        if (
            height > width
            and width >= 500
            and height >= 800
        ):
            vertical.append(item)

    if vertical:

        return max(
            vertical,
            key=lambda item:
                (item.get("width") or 0)
                *
                (item.get("height") or 0)
        )

    # If Pexels returns no vertical file,
    # accept a good landscape source.

    usable = [
        item
        for item in files
        if (
            item.get("link")
            and
            (item.get("width") or 0) >= 640
        )
    ]

    if usable:

        return max(
            usable,
            key=lambda item:
                (item.get("width") or 0)
                *
                (item.get("height") or 0)
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

        for page in range(1, 4):

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
                    video.get("id", "")
                )

                if (
                    not video_id
                    or video_id in used_clips
                ):
                    continue

                video_file = choose_video_file(
                    video
                )

                if not video_file:
                    continue

                candidates[video_id] = {
                    "id": video_id,
                    "link": video_file["link"],
                }

            if len(candidates) >= 35:
                break

        if len(candidates) >= NUMBER_OF_CLIPS:
            break

    candidates_list = list(
        candidates.values()
    )

    random.shuffle(
        candidates_list
    )

    if len(candidates_list) < NUMBER_OF_CLIPS:

        raise RuntimeError(
            f"Not enough NEW Pexels clips. "
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
            " ",
            item["id"]
        )

    return selected


# =========================================================
# ROBUST PEXELS DOWNLOAD
# =========================================================

def download_video(
    url,
    destination
):

    print(
        f"Downloading: {destination}"
    )

    max_attempts = 5

    for attempt in range(
        1,
        max_attempts + 1
    ):

        temporary = destination.with_suffix(
            ".part"
        )

        try:

            if temporary.exists():
                temporary.unlink()

            print(
                f"Download attempt "
                f"{attempt}/{max_attempts}"
            )

            response = requests.get(
                url,
                stream=True,
                timeout=(30, 180),
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "*/*",
                    "Connection": "keep-alive",
                },
            )

            response.raise_for_status()

            expected_size = (
                response.headers.get(
                    "Content-Length"
                )
            )

            expected_size = (
                int(expected_size)
                if expected_size
                else None
            )

            downloaded_size = 0

            with open(
                temporary,
                "wb"
            ) as file:

                for chunk in response.iter_content(
                    chunk_size=256 * 1024
                ):

                    if chunk:

                        file.write(chunk)

                        downloaded_size += len(
                            chunk
                        )

            response.close()

            if downloaded_size < 10000:

                raise RuntimeError(
                    "Downloaded file is too small: "
                    f"{downloaded_size} bytes"
                )

            if (
                expected_size
                and downloaded_size != expected_size
            ):

                raise RuntimeError(
                    "Incomplete download: "
                    f"{downloaded_size}/"
                    f"{expected_size} bytes"
                )

            temporary.replace(
                destination
            )

            print(
                "Download successful: "
                f"{downloaded_size / (1024 * 1024):.2f} MB"
            )

            return

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
            RuntimeError,
        ) as error:

            print(
                f"Download failed on attempt "
                f"{attempt}/{max_attempts}: "
                f"{error}"
            )

            if temporary.exists():

                try:
                    temporary.unlink()
                except Exception:
                    pass

            if attempt < max_attempts:

                wait_time = min(
                    5 * attempt,
                    20
                )

                print(
                    f"Retrying in "
                    f"{wait_time} seconds..."
                )

                time.sleep(
                    wait_time
                )

            else:

                raise RuntimeError(
                    "Failed to download video "
                    f"after {max_attempts} attempts: "
                    f"{url}"
                ) from error


# =========================================================
# VOICE
# =========================================================

def create_voice(text):

    async def generate():

        communicate = edge_tts.Communicate(
            text,
            VOICE_NAME,
            rate=VOICE_RATE,
            volume=VOICE_VOLUME,
            pitch=VOICE_PITCH,
        )

        await communicate.save(
            str(VOICE_FILE)
        )

    asyncio.run(
        generate()
    )

    if (
        not VOICE_FILE.exists()
        or VOICE_FILE.stat().st_size < 1000
    ):

        raise RuntimeError(
            "Voice file was not created correctly."
        )


def get_audio_duration():

    result = command_output([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(VOICE_FILE),
    ])

    duration = float(result)

    if duration <= 0:
        raise RuntimeError(
            "Invalid audio duration."
        )

    return duration


# =========================================================
# SUBTITLES
# =========================================================

def clean_text(text):

    text = re.sub(
        r"\s+",
        " ",
        str(text)
    )

    return text.strip()


def split_text_for_subtitles(text):

    words = clean_text(text).split()

    parts = []
    current = []

    for word in words:

        candidate = " ".join(
            current + [word]
        )

        if len(candidate) <= 27:

            current.append(word)

        else:

            if current:
                parts.append(
                    " ".join(current)
                )

            current = [word]

    if current:
        parts.append(
            " ".join(current)
        )

    return parts


def ass_time(seconds):

    total_cs = max(
        0,
        int(round(seconds * 100))
    )

    hours, remainder = divmod(
        total_cs,
        360000
    )

    minutes, remainder = divmod(
        remainder,
        6000
    )

    seconds_value, centiseconds = divmod(
        remainder,
        100
    )

    return (
        f"{hours}:"
        f"{minutes:02d}:"
        f"{seconds_value:02d}."
        f"{centiseconds:02d}"
    )


def escape_ass_text(text):

    return (
        str(text)
        .replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", " ")
    )


def create_subtitle_file(
    text,
    duration
):

    parts = split_text_for_subtitles(
        text
    )

    if not parts:
        raise RuntimeError(
            "Subtitle text is empty."
        )

    total_characters = sum(
        max(1, len(part))
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
Style: Arabic,Arial,64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H99000000,-1,0,0,0,100,100,0,5,1,5,2,2,60,60,270,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    with open(
        SUBTITLE_FILE,
        "w",
        encoding="utf-8-sig"
    ) as file:

        file.write(
            ass_header
        )

        for index, part in enumerate(parts):

            part_duration = (
                max(1, len(part))
                / total_characters
            ) * duration

            start = current_time

            end = (
                duration
                if index == len(parts) - 1
                else min(
                    duration,
                    current_time
                    + part_duration
                )
            )

            file.write(
                "Dialogue: 0,"
                f"{ass_time(start)},"
                f"{ass_time(end)},"
                "Arabic,,0,0,0,,"
                f"{escape_ass_text(part)}\n"
            )

            current_time = end


# =========================================================
# VIDEO PROCESSING
# =========================================================

def probe_video_duration(path):

    try:

        return float(
            command_output([
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ])
        )

    except Exception:

        return 0.0


def prepare_clip(
    input_file,
    output_file,
    duration
):

    source_duration = probe_video_duration(
        input_file
    )

    if source_duration <= duration + 0.2:

        start_time = 0

    else:

        max_start = max(
            0.0,
            source_duration
            - duration
            - 0.1
        )

        start_time = random.uniform(
            0,
            min(max_start, 3.0)
        )

    video_filter = (
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "setsar=1,"
        "setdar=9/16,"
        "fps=30"
    )

    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start_time:.3f}",
        "-i",
        str(input_file),
        "-t",
        str(duration),
        "-vf",
        video_filter,
        "-an",
        "-r",
        str(FPS),
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


def create_concat_file(clips):

    concat_file = WORK_DIR / "concat.txt"

    with open(
        concat_file,
        "w",
        encoding="utf-8"
    ) as file:

        for clip in clips:

            path = clip.resolve()

            path_string = str(
                path
            ).replace(
                "'",
                "'\\''"
            )

            file.write(
                f"file '{path_string}'\n"
            )

    return concat_file


def create_silent_video(clips):

    concat_file = create_concat_file(
        clips
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
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(FPS),
        "-an",
        "-movflags",
        "+faststart",
        str(silent_video),
    ]

    run_command(
        command
    )

    return silent_video


def create_final_video(
    silent_video,
    text
):

    audio_duration = get_audio_duration()

    print(
        f"Audio duration: "
        f"{audio_duration:.2f}s"
    )

    # Make sure the visual track
    # is never shorter than the voice.

    silent_duration = probe_video_duration(
        silent_video
    )

    if silent_duration < audio_duration:

        extra = (
            audio_duration
            - silent_duration
            + 0.2
        )

        print(
            f"Extending visual track "
            f"by {extra:.2f}s"
        )

        extended = (
            WORK_DIR
            / "silent_extended.mp4"
        )

        command = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(silent_video),
            "-t",
            f"{audio_duration + 0.2:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            str(extended),
        ]

        run_command(
            command
        )

        silent_video = extended

    create_subtitle_file(
        text,
        audio_duration
    )

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

    subtitle_path = (
        SUBTITLE_FILE
        .resolve()
        .as_posix()
        .replace(
            ":",
            r"\:"
        )
    )

    subtitle_filter = (
        f"ass='{subtitle_path}'"
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
        subtitle_filter,
        "-af",
        audio_filter,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-ar",
        "48000",
        "-shortest",
        "-movflags",
        "+faststart",
        str(OUTPUT_VIDEO),
    ]

    run_command(
        final_command
    )

    if (
        not OUTPUT_VIDEO.exists()
        or OUTPUT_VIDEO.stat().st_size < 10000
    ):

        raise RuntimeError(
            "Final video was not created correctly."
        )

    print(
        f"Final video created: "
        f"{OUTPUT_VIDEO}"
    )


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

        credentials.refresh(
            Request()
        )

    except Exception as error:

        raise RuntimeError(
            "YouTube OAuth refresh failed. "
            "The refresh token may be expired/revoked "
            "or belong to a different OAuth client. "
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

    hashtags = " ".join(
        topic.get(
            "hashtags",
            []
        )
    )

    return (
        f"{topic['text']}\n\n"
        f"{hashtags}\n\n"
        "معلومات قصيرة وحقائق متنوعة بشكل مبسط.\n"
        "اشترك للمزيد من المقاطع."
    )


def upload_to_youtube(topic):

    if not OUTPUT_VIDEO.exists():

        raise RuntimeError(
            "Output video does not exist."
        )

    youtube = get_youtube_service()

    title = build_video_title(
        topic
    )

    description = build_video_description(
        topic
    )

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "categoryId": YOUTUBE_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": YOUTUBE_PRIVACY,
            "selfDeclaredMadeForKids":
                YOUTUBE_MADE_FOR_KIDS,
        },
    }

    media = MediaFileUpload(
        str(OUTPUT_VIDEO),
        mimetype="video/mp4",
        resumable=True,
        chunksize=8 * 1024 * 1024,
    )

    print(
        "Uploading to YouTube..."
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None

    while response is None:

        try:

            status, response = (
                request.next_chunk()
            )

            if status:

                print(
                    "Upload progress: "
                    f"{int(status.progress() * 100)}%"
                )

        except Exception as error:

            print(
                "Upload error:",
                error
            )

            raise

    video_id = response.get(
        "id"
    )

    if not video_id:

        raise RuntimeError(
            "YouTube upload returned no "
            f"video ID: {response}"
        )

    print(
        f"YouTube upload successful: "
        f"{video_id}"
    )

    print(
        f"https://www.youtube.com/shorts/"
        f"{video_id}"
    )

    return video_id


# =========================================================
# VALIDATION
# =========================================================

def validate_final_video():

    if not OUTPUT_VIDEO.exists():

        raise RuntimeError(
            "short.mp4 does not exist."
        )

    duration = probe_video_duration(
        OUTPUT_VIDEO
    )

    if duration <= 0:

        raise RuntimeError(
            "Could not read final video duration."
        )

    size_mb = (
        OUTPUT_VIDEO.stat().st_size
        / (1024 * 1024)
    )

    print(
        "\nVIDEO CHECK"
    )

    print(
        f"Duration: {duration:.2f}s"
    )

    print(
        f"Size: {size_mb:.2f} MB"
    )

    if duration < 1:

        raise RuntimeError(
            "Video is too short."
        )

    return duration


# =========================================================
# MAIN PIPELINE
# =========================================================

def main():

    print(
        "\n========================================"
    )

    print(
        "YOUTUBE SHORTS AUTOMATION"
    )

    print(
        "========================================\n"
    )

    check_environment()

    used_content = load_used_content()

    used_clips = load_used_clips()

    topic = select_new_topic(
        used_content
    )

    clean_previous_files()

    selected_videos = select_unique_videos(
        topic,
        used_clips,
    )

    downloaded = []

    print(
        "\nDownloading clips..."
    )

    for index, item in enumerate(
        selected_videos,
        start=1
    ):

        raw_file = (
            WORK_DIR
            / f"raw_{index:02d}.mp4"
        )

        prepared_file = (
            WORK_DIR
            / f"clip_{index:02d}.mp4"
        )

        download_video(
            item["link"],
            raw_file,
        )

        prepare_clip(
            raw_file,
            prepared_file,
            CLIP_DURATION,
        )

        downloaded.append(
            prepared_file
        )

    if len(downloaded) != NUMBER_OF_CLIPS:

        raise RuntimeError(
            "Clip preparation count is incorrect."
        )

    print(
        "\nCreating silent video..."
    )

    silent_video = create_silent_video(
        downloaded
    )

    print(
        "\nCreating Arabic voice..."
    )

    create_voice(
        topic["text"]
    )

    print(
        "\nCreating final Short..."
    )

    create_final_video(
        silent_video,
        topic["text"],
    )

    validate_final_video()

    print(
        "\nUploading..."
    )

    video_id = upload_to_youtube(
        topic
    )

    # Only remember the content and
    # Pexels clips AFTER a successful upload.

    for item in selected_videos:

        used_clips.add(
            str(item["id"])
        )

    save_used_clips(
        used_clips
    )

    remember_content(
        topic,
        video_id,
        used_content,
    )

    print(
        "\n========================================"
    )

    print(
        "DONE"
    )

    print(
        f"Video ID: {video_id}"
    )

    print(
        f"Used Pexels clips remembered: "
        f"{len(used_clips)}"
    )

    print(
        f"Used content items remembered: "
        f"{len(used_content)}"
    )

    print(
        "========================================"
    )


if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\nStopped by user."
        )

        raise

    except Exception as error:

        print(
            "\n========================================"
        )

        print(
            "AUTOMATION FAILED"
        )

        print(
            "========================================"
        )

        print(
            type(error).__name__
            + ":",
            error
        )

        raise
