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
    # =========================================================
    # FOOTBALL ONLY — ENGAGING PLAYER-FOCUSED CONTENT
    # Active categories: 1, 4, 5, 6, 7, 9, 10
    # =========================================================

    # ---------------------------------------------------------
    # 1) Unexpected numbers and statistics
    # ---------------------------------------------------------
    {"search":"Lionel Messi dribbling goal action","fallback_searches":["Messi close control football","Messi dribble match"],"title":"ميسي لا يحتاج إلى مساحة كبيرة ليصنع الخطورة","text":"من أكثر الأشياء اللافتة في أسلوب ميسي قدرته على تغيير اتجاهه بسرعة داخل مساحات ضيقة. هذا التحكم يجعل المدافع أمامه مضطرًا إلى اتخاذ قرار في لحظة قصيرة جدًا.","hashtags":["#Shorts","#ميسي","#كرة_القدم"]},
    {"search":"Cristiano Ronaldo powerful shot football","fallback_searches":["Ronaldo shooting football","Cristiano Ronaldo match action"],"title":"رونالدو جمع بين السرعة والقوة في التسديد","text":"من أبرز ما ميّز رونالدو طوال مسيرته قدرته على التسديد بقوة من مسافات مختلفة. ومع تطور أسلوبه أصبح يعتمد أكثر على اختيار المكان والتوقيت بدل القوة وحدها.","hashtags":["#Shorts","#رونالدو","#كرة_القدم"]},
    {"search":"Kylian Mbappe sprint football","fallback_searches":["Mbappe speed match","Mbappe running football"],"title":"سرعة مبابي تصبح أخطر عندما يبدأ من المساحة","text":"خطورة مبابي لا تأتي من سرعته القصوى فقط، بل من توقيت انطلاقته. عندما يبدأ الركض قبل أن يغلق المدافع المساحة، يتحول الفارق الصغير إلى فرصة خطيرة خلال ثوانٍ.","hashtags":["#Shorts","#مبابي","#كرة_القدم"]},
    {"search":"Erling Haaland goal celebration football","fallback_searches":["Haaland goal match","Haaland striker football"],"title":"هالاند لا يحتاج إلى لمس الكرة كثيرًا ليؤثر في المباراة","text":"أسلوب هالاند يعتمد كثيرًا على التحرك داخل منطقة الجزاء واختيار المكان المناسب. لذلك قد تكون لمساته قليلة مقارنة بغيره، لكنه يبقى حاضرًا عندما تصل الكرة إلى المنطقة الخطرة.","hashtags":["#Shorts","#هالاند","#كرة_القدم"]},
    {"search":"Mohamed Salah Liverpool goal action","fallback_searches":["Salah dribbling football","Mohamed Salah sprint"],"title":"صلاح يجعل أول خطوة بعد استلام الكرة مهمة جدًا","text":"من نقاط قوة صلاح قدرته على تحويل الاستلام إلى انطلاقة مباشرة نحو المرمى. تغيير السرعة بعد اللمسة الأولى يمنحه مساحة إضافية قبل أن يلحق به المدافع.","hashtags":["#Shorts","#صلاح","#كرة_القدم"]},
    {"search":"Neymar dribbling football match","fallback_searches":["Neymar skills football","Neymar close control"],"title":"نيمار يعتمد على الخداع قبل المهارة نفسها","text":"عند مشاهدة نيمار، قد تبدو المهارة هي العنصر الأبرز، لكن الخداع يبدأ قبل الحركة. تغيير اتجاه الجسم ونظرة اللاعب يمكن أن يدفع المدافع للتحرك قبل تنفيذ المراوغة.","hashtags":["#Shorts","#نيمار","#كرة_القدم"]},
    {"search":"Luka Modric passing football match","fallback_searches":["Modric pass football","Luka Modric midfield"],"title":"مودريتش يستطيع تغيير اتجاه الهجمة بلمسة واحدة","text":"يمتلك مودريتش قدرة لافتة على رؤية المساحة قبل وصول الكرة إليه. لذلك يمكنه أحيانًا تنفيذ تمريرة واحدة تنقل اللعب من جهة إلى أخرى قبل أن ينظم المنافس دفاعه.","hashtags":["#Shorts","#مودريتش","#كرة_القدم"]},
    {"search":"Kevin De Bruyne assist football","fallback_searches":["De Bruyne passing","Kevin De Bruyne cross"],"title":"دي بروين لا يمرر دائمًا إلى مكان اللاعب","text":"في بعض تمريراته، يرسل دي بروين الكرة إلى المساحة التي يتوقع أن يصل إليها زميله. هذه الفكرة تجعل التمريرة أسرع من انتظار وصول اللاعب إلى موقعه ثم تمرير الكرة إليه.","hashtags":["#Shorts","#دي_بروين","#كرة_القدم"]},
    {"search":"Karim Benzema football goal action","fallback_searches":["Benzema striker movement","Benzema football match"],"title":"بنزيما كان يخلق المساحة لغيره قبل أن يبحث عن الهدف","text":"لم يعتمد بنزيما على إنهاء الهجمات فقط، بل كان يتراجع أحيانًا لسحب المدافع وفتح مساحة لزميله. هذا النوع من التحرك قد لا يظهر في الإحصائيات البسيطة لكنه يؤثر في الهجمة.","hashtags":["#Shorts","#بنزيما","#كرة_القدم"]},
    {"search":"Robert Lewandowski striker goal football","fallback_searches":["Lewandowski finishing","Lewandowski movement"],"title":"ليفاندوفسكي يجعل اللمسة الأولى جزءًا من عملية التسجيل","text":"من نقاط قوة ليفاندوفسكي التحكم في الكرة داخل المنطقة ثم تجهيزها بسرعة للتسديد. تقليل عدد اللمسات يمنح المهاجم وقتًا أقل للمدافع كي يتدخل.","hashtags":["#Shorts","#ليفاندوفسكي","#كرة_القدم"]},

    # ---------------------------------------------------------
    # 4) Rare moments and unusual details
    # ---------------------------------------------------------
    {"search":"Messi free kick football close up","fallback_searches":["Messi free kick match","Messi set piece"],"title":"ميسي غيّر طريقة تنفيذ الركلات الحرة مع مرور السنوات","text":"في بداياته كان ميسي يعتمد على القوة والاتجاه في الركلات الحرة، ثم أصبح يركز أكثر على الدقة وتغيير ارتفاع الكرة ومسارها. تطور هذه التفاصيل جعل الركلة أكثر تنوعًا.","hashtags":["#Shorts","#ميسي","#كرة_القدم"]},
    {"search":"Ronaldo free kick football slow motion","fallback_searches":["Ronaldo free kick","Cristiano Ronaldo set piece"],"title":"طريقة رونالدو في الركلات الحرة أصبحت علامة مميزة","text":"كان رونالدو يضع تركيزًا كبيرًا على وقفته قبل الركلة وعلى طريقة ضرب الكرة. اختلاف نقطة الضرب والدوران يمكن أن يغير مسار الكرة بصورة واضحة.","hashtags":["#Shorts","#رونالدو","#كرة_القدم"]},
    {"search":"Mbappe celebration football match","fallback_searches":["Mbappe goal celebration","Mbappe match action"],"title":"احتفال مبابي الشهير بدأ كإشارة بسيطة ثم أصبح معروفًا للجميع","text":"احتفال مبابي بعد التسجيل أصبح من أكثر اللقطات التي يتعرف عليها الجمهور بسرعة. المميز أن الحركة نفسها بسيطة جدًا، لكنها ارتبطت به حتى أصبحت جزءًا من صورته داخل الملعب.","hashtags":["#Shorts","#مبابي","#كرة_القدم"]},
    {"search":"Haaland meditation celebration football","fallback_searches":["Haaland celebration","Haaland goal celebration"],"title":"احتفال هالاند الهادئ له قصة مختلفة عن شكل الاحتفال","text":"اختار هالاند في بعض أهدافه احتفالًا هادئًا يشبه وضعية التأمل. لذلك أصبحت اللقطة لافتة لأنها تختلف تمامًا عن الاحتفالات الصاخبة المعتادة بعد التسجيل.","hashtags":["#Shorts","#هالاند","#كرة_القدم"]},
    {"search":"Neymar football skills close up","fallback_searches":["Neymar skill move","Neymar trick football"],"title":"لماذا تبدو مراوغات نيمار وكأنها تحدث فجأة؟","text":"نيمار يستخدم تغيير السرعة وتوجيه القدم والجسم معًا لخداع المدافع. عندما يتوقف للحظة ثم ينطلق، يصبح المدافع مضطرًا إلى توقع اتجاه الحركة قبل أن تتضح بالكامل.","hashtags":["#Shorts","#نيمار","#كرة_القدم"]},
    {"search":"Vinicius Junior dribble football","fallback_searches":["Vinicius Jr speed","Vinicius football match"],"title":"فينيسيوس يجعل المدافع في مشكلة بمجرد أن يواجهه واحدًا لواحد","text":"أحد أخطر أساليب فينيسيوس هو الجمع بين المراوغة والانطلاق. المدافع لا يعرف هل سيغير اللاعب اتجاهه أم يمر بالسرعة، وهذا التردد قد يصنع المساحة المطلوبة.","hashtags":["#Shorts","#فينيسيوس","#كرة_القدم"]},
    {"search":"Jude Bellingham football celebration","fallback_searches":["Bellingham match action","Jude Bellingham goal"],"title":"بيلينغهام لا ينتظر دائمًا داخل منطقة الجزاء ليظهر في الهجمة","text":"يميل بيلينغهام إلى التحرك من الخلف نحو مناطق التسجيل بدل البقاء ثابتًا. هذا التوقيت يجعل وصوله أصعب على المدافعين الذين يركزون أولًا على المهاجمين أمامهم.","hashtags":["#Shorts","#بيلينغهام","#كرة_القدم"]},
    {"search":"Luka Modric outside foot pass","fallback_searches":["Modric outside foot pass","Modric football technique"],"title":"لمسة مودريتش بالقدم الخارجية ليست مجرد استعراض","text":"استخدام القدم الخارجية يسمح للاعب بتغيير اتجاه الكرة من دون تدوير جسمه بالكامل. هذه اللمسة تمنح مودريتش زاوية تمرير مختلفة في مواقف ضيقة.","hashtags":["#Shorts","#مودريتش","#كرة_القدم"]},
    {"search":"Salah left foot football goal","fallback_searches":["Salah cutting inside","Mohamed Salah goal"],"title":"الحركة التي يكررها صلاح ويعرفها المدافعون مسبقًا","text":"يميل صلاح إلى استلام الكرة على الجهة ثم التحرك إلى الداخل قبل البحث عن التسديد أو التمرير. ورغم أن الفكرة معروفة، فإن سرعة التنفيذ تجعل إيقافها صعبًا.","hashtags":["#Shorts","#صلاح","#كرة_القدم"]},
    {"search":"Ronaldo header football goal","fallback_searches":["Cristiano Ronaldo header","Ronaldo aerial goal"],"title":"قفزات رونالدو لم تكن مجرد قوة بدنية","text":"في الكرات الهوائية، لا تكفي القدرة على القفز وحدها. التوقيت ومكان الانطلاق ووضعية الجسم لحظة الارتقاء كلها تحدد مدى نجاح اللاعب في الوصول إلى الكرة وتوجيهها.","hashtags":["#Shorts","#رونالدو","#كرة_القدم"]},

    # ---------------------------------------------------------
    # 5) Career details and behind-the-scenes football stories
    # ---------------------------------------------------------
    {"search":"Messi Barcelona youth football","fallback_searches":["Messi early football","Messi young player"],"title":"ميسي لم يبدأ مسيرته بالطريقة التي يتخيلها كثيرون","text":"بدأ ميسي طريقه في كرة القدم منذ سن صغيرة، وكان تطوره مرتبطًا بالتدريب المستمر واللعب في بيئات تنافسية. قصته توضح أن المهارة وحدها ليست الجزء الوحيد من بناء لاعب استثنائي.","hashtags":["#Shorts","#ميسي","#كرة_القدم"]},
    {"search":"Ronaldo Manchester United young football","fallback_searches":["Ronaldo young player","Cristiano Ronaldo early career"],"title":"رونالدو تغيّر كثيرًا بين بدايته ومرحلة النضج","text":"في بداياته كان رونالدو يعتمد كثيرًا على المراوغة والسرعة، ثم تطور تدريجيًا ليصبح أكثر تركيزًا على التحرك والتسجيل وإنهاء الهجمات. هذا التغير كان واضحًا في أسلوب لعبه.","hashtags":["#Shorts","#رونالدو","#كرة_القدم"]},
    {"search":"Mbappe Monaco young football","fallback_searches":["Mbappe early career","Mbappe young player"],"title":"مبابي ظهر مبكرًا بأسلوب يعتمد على الانطلاق خلف الدفاع","text":"منذ بداياته الاحترافية كان مبابي يعتمد على السرعة والتحرك في المساحة خلف المدافعين. ومع تطوره أضاف إلى ذلك القدرة على التسجيل وصناعة الفرص من أكثر من منطقة.","hashtags":["#Shorts","#مبابي","#كرة_القدم"]},
    {"search":"Haaland Salzburg young football","fallback_searches":["Haaland early career","Haaland young striker"],"title":"هالاند لفت الأنظار قبل وصوله إلى أكبر الملاعب","text":"ظهر هالاند كمهاجم شاب يمتلك مزيجًا من القوة والسرعة والحس التهديفي. انتقاله بين مراحل مختلفة من مسيرته كشف أن تطوره لم يعتمد على عامل واحد فقط.","hashtags":["#Shorts","#هالاند","#كرة_القدم"]},
    {"search":"Salah early career football","fallback_searches":["Mohamed Salah early career","Salah young football"],"title":"صلاح احتاج إلى أكثر من محطة حتى يصل إلى مستواه المعروف","text":"مر صلاح بعدة مراحل في مسيرته قبل أن يثبت نفسه كأحد أبرز المهاجمين. في كل مرحلة تطورت جوانب مختلفة من سرعته وتحركاته وإنهائه للهجمات.","hashtags":["#Shorts","#صلاح","#كرة_القدم"]},
    {"search":"Benzema Lyon young football","fallback_searches":["Benzema early career","Karim Benzema young"],"title":"بنزيما بدأ كمهاجم ثم أصبح دوره أكثر شمولًا","text":"مع تطور مسيرته لم يعد بنزيما يعتمد فقط على الوقوف أمام المرمى. أصبح يشارك في بناء الهجمة والربط بين الخطوط وفتح المساحات، ثم يعود لإنهاء الهجمة.","hashtags":["#Shorts","#بنزيما","#كرة_القدم"]},
    {"search":"Lewandowski young football striker","fallback_searches":["Lewandowski early career","Lewandowski training"],"title":"ليفاندوفسكي بنى قوته التهديفية من تفاصيل صغيرة","text":"تطور ليفاندوفسكي كمهاجم من خلال تحسين الحركة داخل المنطقة والتمركز واللمسة الأخيرة. هذه التفاصيل جعلته قادرًا على التسجيل بطرق متعددة بدل الاعتماد على نوع واحد من الفرص.","hashtags":["#Shorts","#ليفاندوفسكي","#كرة_القدم"]},
    {"search":"Modric early career football","fallback_searches":["Luka Modric young","Modric early football"],"title":"مودريتش لم يكن مجرد لاعب تمرير منذ بدايته","text":"تطور مودريتش تدريجيًا ليجمع بين التحكم بالكرة والرؤية والقدرة على تغيير اتجاه اللعب. ومع الخبرة أصبح تأثيره في إيقاع المباراة أكبر من مجرد صناعة تمريرة.","hashtags":["#Shorts","#مودريتش","#كرة_القدم"]},
    {"search":"Neymar Santos young football","fallback_searches":["Neymar young player","Neymar early career"],"title":"نيمار لفت الأنظار منذ أن كان لاعبًا شابًا","text":"منذ بداياته ظهر أسلوب نيمار القائم على المراوغة واللمسات السريعة. ومع انتقاله إلى مستويات أعلى أصبح مطالبًا بإضافة صناعة الفرص والتسجيل والعمل ضمن منظومات مختلفة.","hashtags":["#Shorts","#نيمار","#كرة_القدم"]},
    {"search":"Vinicius Junior young football","fallback_searches":["Vinicius early career","Vinicius young player"],"title":"تطور فينيسيوس لم يكن في السرعة فقط","text":"مع مرور الوقت أصبح فينيسيوس أكثر هدوءًا في القرار الأخير، وأفضل في اختيار توقيت التمرير والتسديد. هذا التطور جعل سرعته أداة داخل منظومة لعب متكاملة.","hashtags":["#Shorts","#فينيسيوس","#كرة_القدم"]},

    # ---------------------------------------------------------
    # 6) Records and achievements
    # ---------------------------------------------------------
    {"search":"Messi Ballon d'Or football","fallback_searches":["Messi awards football","Messi trophy football"],"title":"ميسي صنع رقمًا استثنائيًا في جائزة الكرة الذهبية","text":"يملك ميسي الرقم القياسي في عدد مرات الفوز بالكرة الذهبية، وهو إنجاز يعكس طول فترة بقائه ضمن أعلى مستوى فردي في كرة القدم العالمية.","hashtags":["#Shorts","#ميسي","#الكرة_الذهبية"]},
    {"search":"Ronaldo Champions League goals football","fallback_searches":["Ronaldo Champions League","Cristiano Ronaldo goals"],"title":"رونالدو يملك رقمًا تاريخيًا في أهداف دوري الأبطال","text":"يُعد رونالدو صاحب الرقم القياسي في عدد أهداف دوري أبطال أوروبا، كما سجل في مراحل مختلفة من البطولة وعلى مدار سنوات عديدة، ما جعل رقمه مرتبطًا بتاريخ المسابقة نفسها.","hashtags":["#Shorts","#رونالدو","#دوري_الأبطال"]},
    {"search":"Ronaldo international goals football","fallback_searches":["Cristiano Ronaldo national team goals","Ronaldo Portugal goals"],"title":"رونالدو وصل إلى رقم استثنائي مع منتخب بلاده","text":"يملك رونالدو الرقم القياسي العالمي في الأهداف الدولية للرجال، وهو رقم جمعه عبر سنوات طويلة من المشاركة والتسجيل مع المنتخب.","hashtags":["#Shorts","#رونالدو","#كرة_القدم"]},
    {"search":"Messi World Cup football trophy","fallback_searches":["Messi World Cup final","Messi Argentina football"],"title":"ميسي جمع بين أكبر إنجازات الأندية والمنتخب","text":"حقق ميسي خلال مسيرته إنجازات كبرى مع الأندية والمنتخب، ومن أبرزها الفوز بكأس العالم عام 2022. لذلك أصبحت مسيرته مرتبطة بعدة مراحل مختلفة من النجاح.","hashtags":["#Shorts","#ميسي","#كأس_العالم"]},
    {"search":"Mbappe World Cup goal final football","fallback_searches":["Mbappe World Cup","Mbappe final goals"],"title":"مبابي دخل سجلًا مميزًا في كأس العالم وهو في عمر صغير","text":"سجل مبابي في كأس العالم وهو في سن صغيرة، ثم واصل التألق في البطولة التالية. وصول لاعب شاب إلى هذه المرحلة التهديفية في أكبر مسابقة للمنتخبات جعله من أبرز الأسماء في جيله.","hashtags":["#Shorts","#مبابي","#كأس_العالم"]},
    {"search":"Haaland goal record football","fallback_searches":["Haaland scoring record","Haaland Premier League goals"],"title":"هالاند حطم أرقامًا تهديفية بسرعة لافتة","text":"منذ انتقاله إلى مستوى المنافسة الأعلى، سجل هالاند أهدافًا بمعدل مرتفع وحقق أرقامًا قياسية في فترات زمنية قصيرة. قوته في الإنهاء والتحرك جعلته من أكثر المهاجمين إنتاجًا.","hashtags":["#Shorts","#هالاند","#كرة_القدم"]},
    {"search":"Salah Premier League goals record football","fallback_searches":["Mohamed Salah scoring record","Salah Liverpool records"],"title":"صلاح ترك أرقامًا مهمة في موسم واحد","text":"حقق صلاح أرقامًا تهديفية وصناعية بارزة خلال مواسمه، وكان أحد مواسمه الأولى مع فريقه نقطة تحول كبيرة في أرقامه الفردية وفي نظرة الجمهور إلى مستواه.","hashtags":["#Shorts","#صلاح","#كرة_القدم"]},
    {"search":"Lewandowski goals record football","fallback_searches":["Lewandowski scoring record","Lewandowski Bundesliga goals"],"title":"ليفاندوفسكي وصل إلى أرقام تهديفية نادرة في موسم واحد","text":"سجل ليفاندوفسكي عددًا ضخمًا من الأهداف في موسم واحد، وحقق رقمًا قياسيًا تهديفيًا في الدوري الألماني عندما سجل أربعين هدفًا في موسم واحد.","hashtags":["#Shorts","#ليفاندوفسكي","#كرة_القدم"]},
    {"search":"Benzema Ballon d'Or football","fallback_searches":["Karim Benzema Ballon d'Or","Benzema award"],"title":"بنزيما أنهى مرحلة طويلة من الانتظار بجائزة فردية كبرى","text":"فاز بنزيما بالكرة الذهبية بعد موسم قدم فيه مستوى تهديفيًا وصناعة فرص لافتًا، ليحصل على واحدة من أهم الجوائز الفردية في مسيرته.","hashtags":["#Shorts","#بنزيما","#الكرة_الذهبية"]},
    {"search":"Modric Ballon d'Or football","fallback_searches":["Luka Modric Ballon d'Or","Modric award"],"title":"مودريتش كسر هيمنة المهاجمين على الكرة الذهبية في عام استثنائي","text":"فاز مودريتش بالكرة الذهبية بعد موسم برز فيه كلاعب وسط وقائد وصانع لعب، ليصبح أحد الأسماء القليلة من لاعبي الوسط الذين حصلوا على الجائزة في العصر الحديث.","hashtags":["#Shorts","#مودريتش","#الكرة_الذهبية"]},

    # ---------------------------------------------------------
    # 7) Smart comparisons between stars
    # ---------------------------------------------------------
    {"search":"Messi Ronaldo comparison football","fallback_searches":["Messi Ronaldo skills","Messi Ronaldo goals"],"title":"ميسي ورونالدو: لماذا يصعب اختزال الفرق بينهما في الأهداف؟","text":"ميسي اشتهر أكثر بصناعة اللعب والمراوغة والتمرير إلى جانب التسجيل، بينما اشتهر رونالدو بالتسجيل والتحرك واللعب الهوائي والتسديد. لذلك المقارنة بينهما تتغير بحسب الجانب الذي تنظر إليه.","hashtags":["#Shorts","#ميسي","#رونالدو","#كرة_القدم"]},
    {"search":"Mbappe Haaland comparison football","fallback_searches":["Mbappe Haaland skills","Haaland Mbappe goals"],"title":"مبابي وهالاند: السرعة ضد القوة التهديفية","text":"يميل مبابي إلى استغلال المساحات والسرعة والانطلاق، بينما يعتمد هالاند أكثر على التمركز والقوة والحسم داخل المنطقة. كلا الأسلوبين يمكن أن يصنع الفارق لكن بطريقة مختلفة.","hashtags":["#Shorts","#مبابي","#هالاند","#كرة_القدم"]},
    {"search":"Messi Neymar comparison football","fallback_searches":["Messi Neymar dribbling","Messi Neymar skills"],"title":"ميسي ونيمار: مهارتان متشابهتان لكن طريقة الخروج من الضغط مختلفة","text":"كلاهما يمتلك تحكمًا استثنائيًا بالكرة، لكن ميسي يميل إلى تغيير الاتجاه بسرعة مع دفع الكرة للأمام، بينما يعتمد نيمار كثيرًا على الخداع والمهارات وتغيير الإيقاع.","hashtags":["#Shorts","#ميسي","#نيمار","#كرة_القدم"]},
    {"search":"Salah Mbappe comparison football","fallback_searches":["Salah Mbappe speed","Salah Mbappe goals"],"title":"صلاح ومبابي يشتركان في ميزة خطيرة: الانطلاق بعد استلام الكرة","text":"كلا اللاعبين يستطيع تحويل اللمسة الأولى إلى هجمة سريعة، لكن صلاح يعتمد كثيرًا على التحرك من الجهة إلى الداخل، بينما يستخدم مبابي المساحات الواسعة والانطلاق المباشر خلف الدفاع.","hashtags":["#Shorts","#صلاح","#مبابي","#كرة_القدم"]},
    {"search":"Ronaldo Haaland comparison football","fallback_searches":["Ronaldo Haaland finishing","Ronaldo Haaland striker"],"title":"رونالدو وهالاند: مهاجمان لكن طريقة الوصول للهدف مختلفة","text":"رونالدو جمع خلال مسيرته بين التسديد والتحرك والكرات الهوائية، بينما يعتمد هالاند بصورة أكبر على التمركز والسرعة في الوصول إلى الكرة داخل المنطقة. النتيجة واحدة: البحث عن أفضل لحظة للتسجيل.","hashtags":["#Shorts","#رونالدو","#هالاند","#كرة_القدم"]},
    {"search":"De Bruyne Modric comparison football","fallback_searches":["De Bruyne Modric passing","Modric De Bruyne midfield"],"title":"دي بروين ومودريتش: صانع لعب بطريقتين مختلفتين","text":"يميل دي بروين إلى التمريرات المباشرة وصناعة الفرص بسرعة، بينما يبرع مودريتش أكثر في التحكم بإيقاع اللعب وتغيير اتجاه الهجمة. كلاهما يملك رؤية عالية لكن استخدامهما لها مختلف.","hashtags":["#Shorts","#دي_بروين","#مودريتش","#كرة_القدم"]},
    {"search":"Vinicius Neymar comparison football","fallback_searches":["Vinicius Neymar dribbling","Brazil football skills"],"title":"فينيسيوس ونيمار: لماذا تبدو مراوغاتهما مختلفة؟","text":"يعتمد فينيسيوس كثيرًا على تغيير السرعة والانطلاق بعد المراوغة، بينما يستخدم نيمار الخداع واللمسات القصيرة وتغيير الإيقاع. كلاهما يهدف إلى جعل المدافع يتحرك قبل الوقت المناسب.","hashtags":["#Shorts","#فينيسيوس","#نيمار","#كرة_القدم"]},
    {"search":"Benzema Lewandowski comparison football","fallback_searches":["Benzema Lewandowski striker","Lewandowski Benzema goals"],"title":"بنزيما وليفاندوفسكي: مهاجمان بأسلوبين مختلفين","text":"ليفاندوفسكي معروف بالتمركز والحسم داخل المنطقة، بينما اشتهر بنزيما أيضًا بالربط وصناعة المساحات والمشاركة في بناء الهجمة. لذلك قد يؤدي المهاجمان الدور نفسه بطرق مختلفة.","hashtags":["#Shorts","#بنزيما","#ليفاندوفسكي","#كرة_القدم"]},

    # ---------------------------------------------------------
    # 9) Short match stories and turning points
    # ---------------------------------------------------------
    {"search":"Messi dramatic goal football match","fallback_searches":["Messi late goal","Messi decisive match"],"title":"هناك مباريات لا تحتاج فيها إلى عشر فرص حتى تصبح البطل","text":"في بعض مباريات ميسي، كانت لحظة واحدة كافية لتغيير النتيجة: تمريرة أو مراوغة أو تسديدة في الوقت المناسب. قيمة اللاعب تظهر أحيانًا في تأثيره عندما تكون الفرصة الوحيدة هي الأهم.","hashtags":["#Shorts","#ميسي","#كرة_القدم"]},
    {"search":"Ronaldo Champions League comeback goal","fallback_searches":["Ronaldo comeback match","Ronaldo decisive goal"],"title":"رونالدو اشتهر بالظهور عندما تصبح المباراة في لحظتها الأصعب","text":"خلال مسيرته، سجل رونالدو أهدافًا حاسمة في مراحل كبيرة من البطولات. ما يجعل هذه اللقطات مميزة هو توقيتها، لأن الهدف في مباراة متقاربة قد يغير كل شيء.","hashtags":["#Shorts","#رونالدو","#دوري_الأبطال"]},
    {"search":"Mbappe World Cup final goal action","fallback_searches":["Mbappe final match","Mbappe decisive goal"],"title":"مبابي أثبت أن مباراة واحدة قد تغير كل شيء في دقائق","text":"في المباريات الكبيرة يمكن أن تتغير النتيجة خلال دقائق قليلة، ومبابي قدم أمثلة واضحة على ذلك عندما استغل السرعة والمساحة والحسم في اللحظات الحاسمة.","hashtags":["#Shorts","#مبابي","#كرة_القدم"]},
    {"search":"Haaland hat trick football match","fallback_searches":["Haaland three goals","Haaland match goals"],"title":"هاتريك هالاند يبدأ غالبًا من قراءة المكان قبل وصول الكرة","text":"عندما يسجل هالاند عدة أهداف في مباراة واحدة، لا تكون كل الأهداف بالطريقة نفسها. جزء كبير من خطورته يأتي من وصوله إلى المكان الصحيح قبل المدافع ثم إنهاء الهجمة بسرعة.","hashtags":["#Shorts","#هالاند","#كرة_القدم"]},
    {"search":"Salah comeback football goal","fallback_searches":["Salah decisive match","Salah late goal"],"title":"صلاح يستطيع تحويل هجمة واحدة إلى فرصة خلال ثوانٍ","text":"عندما يستلم صلاح الكرة في المساحة المناسبة، يمكن أن ينتقل من الاستلام إلى المراوغة ثم التسديد بسرعة كبيرة. لهذا تكون بعض هجماته قصيرة جدًا لكنها خطيرة.","hashtags":["#Shorts","#صلاح","#كرة_القدم"]},
    {"search":"Neymar comeback football match","fallback_searches":["Neymar decisive goal","Neymar match moment"],"title":"نيمار كان يستطيع تغيير شكل الهجمة بلمسة واحدة","text":"في بعض المباريات كانت لمسة نيمار الأولى كافية لتغيير اتجاه الهجمة. قدرته على استقبال الكرة تحت الضغط ثم مواجهة المدافع مباشرة جعلت لحظاته الفردية مؤثرة.","hashtags":["#Shorts","#نيمار","#كرة_القدم"]},
    {"search":"Bellingham late goal football match","fallback_searches":["Jude Bellingham late goal","Bellingham decisive match"],"title":"بيلينغهام جعل الوصول المتأخر إلى منطقة الجزاء سلاحًا","text":"عندما يتقدم بيلينغهام من الخلف في الوقت المناسب، قد يصل إلى منطقة الجزاء دون مراقبة مباشرة. هذه الحركة تمنحه فرصة للتسديد أو استغلال ارتداد الكرة.","hashtags":["#Shorts","#بيلينغهام","#كرة_القدم"]},
    {"search":"Modric Champions League match pass","fallback_searches":["Modric decisive pass","Modric big match"],"title":"تمريرة واحدة من مودريتش قد تغيّر اتجاه المباراة","text":"في المباريات المتقاربة، تمريرة واحدة تكسر خط الضغط يمكن أن تنقل الفريق من الدفاع إلى الهجوم فورًا. هذا النوع من التمرير من أبرز نقاط قوة مودريتش.","hashtags":["#Shorts","#مودريتش","#كرة_القدم"]},
    {"search":"Vinicius Champions League goal football","fallback_searches":["Vinicius decisive goal","Vinicius big match"],"title":"فينيسيوس خطير عندما يحصل على متر واحد فقط","text":"لا يحتاج فينيسيوس إلى مساحة كبيرة لبدء الانطلاقة. إذا حصل على متر إضافي أمام المدافع، يستطيع تغيير الاتجاه ثم استخدام سرعته للوصول إلى منطقة خطرة بسرعة.","hashtags":["#Shorts","#فينيسيوس","#كرة_القدم"]},
    {"search":"De Bruyne assist big match football","fallback_searches":["De Bruyne decisive assist","Kevin De Bruyne big match"],"title":"دي بروين يستطيع صناعة فرصة قبل أن يتوقعها المدافع","text":"ميزة دي بروين في بعض الهجمات أنه يمرر الكرة قبل أن تصبح المساحة واضحة للجميع. سرعة القرار تجعل المدافع يتأخر في قراءة اتجاه الهجمة.","hashtags":["#Shorts","#دي_بروين","#كرة_القدم"]},

    # ---------------------------------------------------------
    # 10) Skills and playing styles
    # ---------------------------------------------------------
    {"search":"Messi close control dribbling football","fallback_searches":["Messi dribbling close up","Messi ball control"],"title":"سر مراوغة ميسي يبدأ من قرب الكرة من قدمه","text":"يحافظ ميسي أثناء المراوغة على الكرة قريبة من قدمه، وهذا يسمح له بتغيير الاتجاه بسرعة عندما يتحرك المدافع. كلما قصرت المسافة بين اللاعب والكرة أصبح التحكم أسرع.","hashtags":["#Shorts","#ميسي","#مهارات_كرة_القدم"]},
    {"search":"Ronaldo stepovers football skills","fallback_searches":["Ronaldo skills","Cristiano Ronaldo dribbling"],"title":"الخطوات السريعة حول الكرة كانت جزءًا من أسلوب رونالدو","text":"استخدم رونالدو حركات القدم حول الكرة لإجبار المدافع على توقع اتجاهه. الفكرة ليست في الحركة وحدها، بل في اللحظة التي يغير فيها اللاعب سرعته بعدها.","hashtags":["#Shorts","#رونالدو","#مهارات_كرة_القدم"]},
    {"search":"Mbappe change direction sprint football","fallback_searches":["Mbappe dribbling","Mbappe acceleration"],"title":"مبابي لا يحتاج إلى أقصى سرعة طوال المراوغة","text":"الخطير في أسلوب مبابي هو الانتقال السريع بين السرعات. قد يبدأ بسرعة متوسطة ثم يرفعها فجأة، وهذا التغير أصعب على المدافع من السرعة الثابتة.","hashtags":["#Shorts","#مبابي","#مهارات_كرة_القدم"]},
    {"search":"Haaland first touch football training","fallback_searches":["Haaland first touch","Haaland finishing technique"],"title":"لمسة هالاند الأولى تساعده على إنهاء الهجمة بسرعة","text":"داخل منطقة الجزاء، يمكن أن تكون اللمسة الأولى هي الفارق بين فرصة وتسديدة. هالاند يحاول توجيه الكرة إلى مكان يسمح له بالتسديد باللمسة التالية مباشرة.","hashtags":["#Shorts","#هالاند","#مهارات_كرة_القدم"]},
    {"search":"Salah cutting inside football","fallback_searches":["Salah dribbling left foot","Salah shooting technique"],"title":"لماذا يحب صلاح التحرك من الجهة إلى الداخل؟","text":"التحرك من الجهة إلى الداخل يفتح أمام صلاح زاوية أكبر للتمرير أو التسديد. ومع سرعته يصبح المدافع أمام خيار صعب بين إغلاق الطريق أو الاستعداد للانطلاق خلفه.","hashtags":["#Shorts","#صلاح","#مهارات_كرة_القدم"]},
    {"search":"Neymar elastico football skill","fallback_searches":["Neymar dribbling skill","Neymar football trick"],"title":"حركة نيمار السريعة تجعل المدافع يتفاعل مع اتجاه خاطئ","text":"بعض حركات نيمار تعتمد على دفع الكرة في اتجاه ثم سحبها أو تغييرها بسرعة. الهدف هو جعل المدافع ينقل وزنه إلى الجهة الخطأ قبل الانطلاق.","hashtags":["#Shorts","#نيمار","#مهارات_كرة_القدم"]},
    {"search":"Vinicius dribbling speed football","fallback_searches":["Vinicius one on one","Vinicius skill football"],"title":"فينيسيوس يحول المواجهة الفردية إلى سباق قصير","text":"عند مواجهة مدافع واحد، يستطيع فينيسيوس استخدام تغيير الاتجاه ثم الانطلاق بدل الاستمرار في المراوغة لوقت طويل. السرعة بعد تجاوز المدافع هي الجزء الأخطر من الحركة.","hashtags":["#Shorts","#فينيسيوس","#مهارات_كرة_القدم"]},
    {"search":"Bellingham ball control football","fallback_searches":["Bellingham dribbling","Jude Bellingham skills"],"title":"بيلينغهام يستخدم جسمه لحماية الكرة قبل تغيير الاتجاه","text":"عند الضغط عليه، يستطيع بيلينغهام استخدام وضعية الجسم لإبعاد المدافع عن الكرة، ثم تدوير جسمه والانطلاق إلى المساحة. القوة والتوازن هنا جزء من المهارة نفسها.","hashtags":["#Shorts","#بيلينغهام","#مهارات_كرة_القدم"]},
    {"search":"Modric outside foot football pass","fallback_searches":["Modric technique","Modric passing skill"],"title":"القدم الخارجية تمنح مودريتش زاوية تمرير غير متوقعة","text":"عندما يستخدم اللاعب القدم الخارجية، يستطيع تمرير الكرة بزاوية مختلفة مع إبقاء جسمه في اتجاه آخر. هذه الحركة مفيدة عندما تكون المساحة ضيقة والوقت محدودًا.","hashtags":["#Shorts","#مودريتش","#مهارات_كرة_القدم"]},
    {"search":"De Bruyne through ball football","fallback_searches":["De Bruyne through pass","Kevin De Bruyne technique"],"title":"التمريرة البينية عند دي بروين تعتمد على التوقيت قبل القوة","text":"التمريرة البينية الناجحة تحتاج إلى إرسال الكرة في اللحظة التي يبدأ فيها المهاجم بالتحرك. إذا سبقت الكرة اللاعب كثيرًا خرجت من الملعب، وإذا تأخرت وصل المدافع إليها.","hashtags":["#Shorts","#دي_بروين","#مهارات_كرة_القدم"]},
    {"search":"Lewandowski finishing football training","fallback_searches":["Lewandowski finishing skill","Lewandowski striker technique"],"title":"ليفاندوفسكي يختصر الوقت بين استلام الكرة والتسديد","text":"في منطقة الجزاء، يحاول ليفاندوفسكي تجهيز جسمه قبل وصول الكرة حتى لا يحتاج إلى حركة إضافية بعد الاستلام. هذا يقلل الوقت المتاح للمدافع للتدخل.","hashtags":["#Shorts","#ليفاندوفسكي","#مهارات_كرة_القدم"]},
    {"search":"Benzema first touch football","fallback_searches":["Benzema ball control","Benzema technique"],"title":"لمسة بنزيما الأولى كانت جزءًا من صناعة الفرصة","text":"لم يكن هدف اللمسة الأولى عند بنزيما دائمًا التقدم نحو المرمى. أحيانًا كانت اللمسة موجهة لحماية الكرة أو ربط الهجمة بزميل قادم من الخلف.","hashtags":["#Shorts","#بنزيما","#مهارات_كرة_القدم"]},
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

    The pool intentionally contains football-only, player-focused topics from the active categories.
    Science, engineering, technology, gaming, history, and geography are excluded.
    """
    if not TOPICS:
        raise RuntimeError("TOPICS is empty.")

    seen = set()
    for index, topic in enumerate(TOPICS, start=1):
        title = sanitize_script(topic.get("title", "")) if "sanitize_script" in globals() else str(topic.get("title", ""))
        text = sanitize_script(topic.get("text", "")) if "sanitize_script" in globals() else str(topic.get("text", ""))
        if not title or not text:
            raise RuntimeError(f"Topic {index} has an empty title or script.")

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
            # Keep the narration at natural speed. The Arabic script is already
            # cleaned before this function, so Edge TTS receives narration only.
            communicate = edge_tts.Communicate(
                text,
                VOICE_NAME,
                rate=VOICE_RATE,
                volume=VOICE_VOLUME,
                pitch=VOICE_PITCH,
            )
            await communicate.save(str(VOICE_FILE))

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

    print("\nCreating Arabic voice...")
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
