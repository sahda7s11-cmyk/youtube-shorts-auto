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
    # =========================
    # كرة القدم والرياضة
    # =========================
    {"search":"football match player action","fallback_searches":["soccer match action","football player running"],"title":"اللاعب يقطع عدة كيلومترات أثناء المباراة","text":"يقطع لاعب كرة القدم المحترف عدة كيلومترات خلال المباراة، لكن المسافة ليست العامل الوحيد. اللاعب ينتقل باستمرار بين المشي والركض والجري السريع، ويغيّر سرعته بحسب مكان الكرة وحركة زملائه والمنافسين.","hashtags":["#Shorts","#كرة_القدم","#رياضة","#معلومات"]},
    {"search":"football goalkeeper save","fallback_searches":["soccer goalkeeper","goalkeeper training"],"title":"حارس المرمى يبدأ الحركة قبل وصول الكرة","text":"يستطيع حارس المرمى أحيانًا توقع اتجاه التسديدة قبل أن تصل الكرة إليه. فهو يراقب وضعية جسم المهاجم واتجاه قدمه ومكان الكرة، ثم يبدأ الاستجابة خلال جزء قصير جدًا من الثانية.","hashtags":["#Shorts","#كرة_القدم","#حراس_المرمى"]},
    {"search":"football penalty kick goalkeeper","fallback_searches":["soccer penalty","football goalkeeper penalty"],"title":"ركلة الجزاء أسرع من قدرة العين على التتبع","text":"تتحرك الكرة في ركلة الجزاء بسرعة كبيرة، لذلك لا يعتمد الحارس على رؤية الكرة وحدها. قراءة حركة اللاعب واتجاه جسده قبل التسديد تساعده على اختيار اتجاه القفز خلال وقت قصير جدًا.","hashtags":["#Shorts","#كرة_القدم","#رياضة"]},
    {"search":"football passing training","fallback_searches":["soccer passing","football training"],"title":"التمرير الدقيق يحتاج إلى أكثر من قوة القدم","text":"يعتمد التمرير الدقيق في كرة القدم على زاوية القدم وسرعة الكرة وتوقيت التمريرة. ولهذا يتدرب اللاعب على التمرير في ظروف مختلفة حتى يستطيع تنفيذ الحركة بسرعة أثناء المباراة.","hashtags":["#Shorts","#كرة_القدم","#تدريب"]},
    {"search":"football stadium modern","fallback_searches":["soccer stadium","modern football stadium"],"title":"تصميم الملعب يؤثر في تجربة المشجع","text":"تصميم ملعب كرة القدم لا يتعلق بشكل المدرجات فقط. توزيع المقاعد ومواقع الشاشات وممرات الحركة وأنظمة الإضاءة والصوت كلها تُخطط لتجعل متابعة المباراة أكثر وضوحًا وتنظيمًا.","hashtags":["#Shorts","#كرة_القدم","#ملاعب"]},
    {"search":"football VAR referee technology","fallback_searches":["soccer referee technology","football video review"],"title":"الكاميرات تساعد الحكم في مراجعة اللقطات","text":"تستخدم أنظمة التحكيم الحديثة عدة كاميرات لمراجعة بعض الحالات المهمة في المباراة. تُجمع الصور من زوايا مختلفة، ثم تُعرض اللقطة للحكم لمساعدته على اتخاذ القرار وفق قوانين اللعبة.","hashtags":["#Shorts","#كرة_القدم","#تقنية"]},
    {"search":"football ball spin close up","fallback_searches":["soccer ball spinning","football free kick"],"title":"دوران الكرة يغيّر مسارها في الهواء","text":"عندما تدور كرة القدم أثناء تحركها في الهواء، تتغير طريقة تفاعل الهواء معها. هذا التأثير يمكن أن يجعل الكرة تنحرف عن مسارها المتوقع، ولذلك يستطيع اللاعبون استغلال دوران الكرة في الركلات والتمريرات.","hashtags":["#Shorts","#كرة_القدم","#علوم"]},
    {"search":"football sprint player","fallback_searches":["soccer sprint","football speed"],"title":"الانطلاق السريع في كرة القدم يحتاج إلى طاقة كبيرة","text":"الجري السريع يستهلك طاقة أكبر من الركض الهادئ، ولذلك لا يستطيع اللاعب الحفاظ على أقصى سرعة طوال المباراة. يعتمد الأداء على تكرار انطلاقات قصيرة مع فترات من الحركة الأقل سرعة.","hashtags":["#Shorts","#كرة_القدم","#رياضة"]},
    {"search":"football tactics team training","fallback_searches":["soccer tactics","football team training"],"title":"تحرك لاعب واحد قد يفتح مساحة لزميله","text":"في كرة القدم، لا يتحرك اللاعب دائمًا للحصول على الكرة. أحيانًا يجذب تحركه أحد المدافعين إلى منطقة معينة، فينشأ فراغ يستطيع زميل آخر استغلاله. هذه الفكرة جزء أساسي من العمل الجماعي في الهجوم.","hashtags":["#Shorts","#كرة_القدم","#تكتيك"]},
    {"search":"football boot close up","fallback_searches":["soccer boots","football player feet"],"title":"شكل حذاء كرة القدم يؤثر في طريقة الحركة","text":"يؤثر تصميم حذاء كرة القدم في الاحتكاك بين القدم والأرض. المسامير الموجودة أسفل الحذاء تساعد اللاعب على الثبات أثناء التسارع وتغيير الاتجاه، ويختلف تصميمها بحسب نوع الملعب.","hashtags":["#Shorts","#كرة_القدم","#رياضة"]},

    # =========================
    # العلوم
    # =========================
    {"search":"lightning storm","fallback_searches":["lightning science","thunderstorm"],"title":"البرق يسخن الهواء المحيط به بسرعة هائلة","text":"ترتفع درجة حرارة قناة البرق إلى مستويات شديدة الارتفاع خلال زمن قصير جدًا. يؤدي التسخين السريع إلى تمدد الهواء المحيط فجأة، وينتج عن ذلك موجة ضغط نسمعها على شكل صوت الرعد.","hashtags":["#Shorts","#علوم","#برق"]},
    {"search":"volcano eruption close up","fallback_searches":["volcano science","volcano crater"],"title":"الضغط داخل البركان يمكن أن يدفع الصهارة إلى الأعلى","text":"توجد الصهارة تحت سطح الأرض في درجات حرارة مرتفعة، وقد تحتوي على غازات مذابة. عندما يتغير الضغط وتتحرك الصهارة نحو الأعلى، تتمدد الغازات، ويمكن أن تساهم في دفع المواد البركانية إلى السطح.","hashtags":["#Shorts","#علوم","#براكين"]},
    {"search":"human eye close up","fallback_searches":["eye science","human vision"],"title":"العين تحول الضوء إلى إشارات يفسرها الدماغ","text":"تدخل أشعة الضوء إلى العين وتصل إلى الشبكية، حيث توجد خلايا حساسة للضوء. هذه الخلايا تحول المعلومات الضوئية إلى إشارات عصبية تنتقل عبر العصب البصري إلى الدماغ لتكوين الصورة التي نراها.","hashtags":["#Shorts","#علوم","#جسم_الإنسان"]},
    {"search":"human brain neurons","fallback_searches":["brain science","neurons"],"title":"الدماغ يعالج معلومات كثيرة في الوقت نفسه","text":"يستقبل الدماغ إشارات من الحواس المختلفة ويعالجها باستمرار. فهو ينسق الحركة والانتباه والذاكرة واتخاذ القرار من خلال شبكة ضخمة من الخلايا العصبية التي تتواصل فيما بينها.","hashtags":["#Shorts","#علوم","#دماغ"]},
    {"search":"plant photosynthesis leaves","fallback_searches":["photosynthesis","green leaves science"],"title":"النبات يصنع غذاءه باستخدام الضوء","text":"تستخدم النباتات ضوء الشمس وثاني أكسيد الكربون والماء لإنتاج الطاقة الكيميائية التي تحتاج إليها. تحدث هذه العملية في خلايا تحتوي على الكلوروفيل، وتُعرف باسم البناء الضوئي.","hashtags":["#Shorts","#علوم","#نباتات"]},
    {"search":"water droplet surface tension","fallback_searches":["water science","surface tension"],"title":"قطرة الماء تميل إلى اتخاذ شكل قريب من الكرة","text":"تؤثر قوى التماسك بين جزيئات الماء في شكل القطرة. عند سقوط قطرة صغيرة بعيدًا عن الأسطح، تميل هذه القوى إلى تقليل مساحة سطحها، ولذلك يصبح شكلها قريبًا من الكرة.","hashtags":["#Shorts","#علوم","#فيزياء"]},
    {"search":"ice melting close up","fallback_searches":["ice science","water freezing"],"title":"الجليد يطفو لأن كثافته أقل من الماء","text":"عندما يتجمد الماء، تنتظم جزيئاته في بنية تحتوي على فراغات أكثر من الماء السائل. لذلك تصبح كثافة الجليد أقل، فيطفو على سطح الماء بدلًا من الغوص إلى القاع.","hashtags":["#Shorts","#علوم","#ماء"]},
    {"search":"magnet iron filings","fallback_searches":["magnet science","magnetic field"],"title":"المغناطيس يستطيع التأثير في بعض المعادن من دون لمسها","text":"ينتج المغناطيس مجالًا مغناطيسيًا يمكنه التأثير في مواد معينة مثل الحديد. لهذا يمكن للمغناطيس جذب جسم معدني من مسافة قصيرة حتى من دون تلامس مباشر.","hashtags":["#Shorts","#علوم","#مغناطيس"]},
    {"search":"sound wave speaker","fallback_searches":["sound science","speaker vibration"],"title":"الصوت يحتاج إلى وسط لينتقل عبره","text":"ينتقل الصوت على شكل اهتزازات خلال مادة مثل الهواء أو الماء أو الأجسام الصلبة. في الفراغ لا توجد جزيئات كافية لنقل هذه الاهتزازات، ولذلك لا ينتقل الصوت بالطريقة المعتادة.","hashtags":["#Shorts","#علوم","#فيزياء"]},
    {"search":"rain water droplets cloud","fallback_searches":["cloud science","rain formation"],"title":"قطرات المطر تبدأ من قطرات ماء صغيرة داخل السحب","text":"تحتوي السحب على قطرات ماء دقيقة وبلورات جليد. عندما تتجمع هذه الجسيمات وتنمو وتصبح أثقل من قدرة الهواء على إبقائها معلقة، تبدأ بالسقوط نحو الأرض على شكل هطول.","hashtags":["#Shorts","#علوم","#طقس"]},
    {"search":"shark underwater","fallback_searches":["shark swimming","marine science"],"title":"أسماك القرش تعتمد على حواس متعددة للعثور على فرائسها","text":"تمتلك أسماك القرش حواسًا تساعدها على اكتشاف الحركة والروائح والتغيرات في البيئة المحيطة. وبعض أنواعها تستطيع أيضًا استشعار إشارات كهربائية ضعيفة تنتجها الكائنات الحية.","hashtags":["#Shorts","#علوم","#حيوانات"]},
    {"search":"cheetah running","fallback_searches":["cheetah speed","wildlife running"],"title":"الفهد يعتمد على تسارع قصير للوصول إلى سرعة عالية","text":"يمتلك الفهد جسمًا مهيأ للجري السريع، مع أطراف طويلة وعمود فقري مرن وذيل يساعده على التوازن. لكنه يعتمد على انطلاقات قصيرة لأن الجري بأقصى سرعة يستهلك طاقة كبيرة.","hashtags":["#Shorts","#علوم","#حيوانات"]},
    {"search":"octopus underwater","fallback_searches":["octopus science","marine animal"],"title":"الأخطبوط يستطيع تغيير لون جلده بسرعة","text":"يحتوي جلد الأخطبوط على خلايا متخصصة تحتوي على أصباغ، ويمكنه تغيير مظهره بسرعة للمساعدة في التمويه والتواصل. وتعمل هذه الخلايا مع أنظمة عصبية وعضلية دقيقة.","hashtags":["#Shorts","#علوم","#بحار"]},
    {"search":"butterfly wings close up","fallback_searches":["butterfly science","insect wings"],"title":"ألوان أجنحة بعض الفراشات لا تأتي من الصبغة فقط","text":"تحتوي أجنحة بعض الفراشات على تراكيب مجهرية تغير طريقة انعكاس الضوء. لذلك قد تظهر ألوان لامعة أو متغيرة بحسب زاوية النظر، حتى عندما تكون كمية الصبغة قليلة.","hashtags":["#Shorts","#علوم","#حشرات"]},
    {"search":"space stars night sky","fallback_searches":["astronomy stars","space science"],"title":"ضوء النجوم يصل إلينا بعد رحلة طويلة عبر الفضاء","text":"الضوء ينتقل بسرعة كبيرة، لكنه يحتاج إلى وقت حتى يصل من النجوم البعيدة إلى الأرض. لذلك عندما ننظر إلى بعض النجوم، فنحن نرى ضوءًا غادر تلك النجوم قبل سنوات أو أكثر بحسب المسافة.","hashtags":["#Shorts","#علوم","#فضاء"]},

    # =========================
    # الهندسة والتقنية
    # =========================
    {"search":"bridge engineering structure","fallback_searches":["bridge construction","engineering bridge"],"title":"شكل الجسر يوزع الأحمال بطريقة محسوبة","text":"يصمم المهندسون الجسور بحيث تنتقل الأحمال من سطح الجسر إلى العناصر الحاملة ثم إلى الدعامات والأساسات. اختيار الشكل والمواد يحدد مقدار القوى التي يستطيع الجسر تحملها بأمان.","hashtags":["#Shorts","#هندسة","#جسور"]},
    {"search":"construction crane building","fallback_searches":["engineering construction","tower crane"],"title":"الرافعة البرجية تستطيع رفع أوزان ضخمة إلى ارتفاعات كبيرة","text":"تستخدم الرافعات البرجية ذراعًا طويلًا ونظامًا من الموازنة والكوابل لتوزيع الأحمال. ويحدد المهندسون وزن الحمولة وموقعها بدقة حتى لا تتجاوز الرافعة حدود التشغيل الآمنة.","hashtags":["#Shorts","#هندسة","#بناء"]},
    {"search":"train high speed engineering","fallback_searches":["high speed train","railway engineering"],"title":"القطارات السريعة تحتاج إلى مسار مصمم بدقة","text":"كلما زادت سرعة القطار أصبحت جودة المسار والهندسة المحيطة به أكثر أهمية. تُستخدم منحنيات محسوبة وأنظمة تحكم وإشارات دقيقة للمساعدة في الحفاظ على حركة مستقرة وآمنة.","hashtags":["#Shorts","#هندسة","#قطارات"]},
    {"search":"airplane cockpit flight instruments","fallback_searches":["aircraft navigation","pilot cockpit"],"title":"أنظمة الطائرة تجمع بيانات كثيرة أثناء الرحلة","text":"تعتمد الطائرة على أجهزة وأنظمة تقيس الارتفاع والسرعة والاتجاه ومعلومات أخرى. تُجمع هذه البيانات وتُعرض للطيار وأنظمة التحكم لمساعدتهم على متابعة حالة الرحلة.","hashtags":["#Shorts","#هندسة","#طيران"]},
    {"search":"rocket launch engineering","fallback_searches":["rocket engine","spacecraft launch"],"title":"الصاروخ يحتاج إلى دفع يتغلب على الجاذبية أثناء الإطلاق","text":"ينتج محرك الصاروخ قوة دفع من خلال دفع الغازات بسرعة كبيرة في الاتجاه المعاكس. عند الإطلاق يجب أن تكون قوة الدفع كافية لتسريع الصاروخ ورفع كتلته بعيدًا عن سطح الأرض.","hashtags":["#Shorts","#هندسة","#فضاء"]},
    {"search":"solar panels electricity","fallback_searches":["solar energy panels","photovoltaic cells"],"title":"الألواح الشمسية تحول الضوء إلى طاقة كهربائية","text":"تحتوي الألواح الشمسية على خلايا كهروضوئية تمتص الفوتونات القادمة من ضوء الشمس. تؤدي هذه العملية إلى توليد تيار كهربائي يمكن استخدامه مباشرة أو تخزينه في البطاريات.","hashtags":["#Shorts","#هندسة","#طاقة_شمسية"]},
    {"search":"3d printer engineering","fallback_searches":["three dimensional printer","3d printing"],"title":"الطابعة ثلاثية الأبعاد تبني الجسم طبقة فوق طبقة","text":"تعمل الطابعة ثلاثية الأبعاد بإضافة المادة تدريجيًا وفق نموذج رقمي. تُنشئ طبقة رقيقة ثم تضيف طبقات أخرى فوقها حتى يتكون الجسم بالشكل المطلوب.","hashtags":["#Shorts","#هندسة","#تقنية"]},
    {"search":"robot arm factory","fallback_searches":["robotics engineering","industrial robot"],"title":"الروبوت الصناعي يستطيع تكرار حركة دقيقة آلاف المرات","text":"تستخدم الروبوتات الصناعية محركات وحساسات وأنظمة تحكم لتنفيذ حركات محددة بدقة. ويمكن برمجتها لتكرار المهمة نفسها مرات كثيرة مع الحفاظ على المسار والسرعة المطلوبين.","hashtags":["#Shorts","#هندسة","#روبوتات"]},
    {"search":"computer processor close up","fallback_searches":["computer chip","processor technology"],"title":"المعالج ينفذ التعليمات بسرعة كبيرة داخل الحاسوب","text":"يستقبل المعالج تعليمات من البرامج ثم ينفذ عمليات حسابية ومنطقية وينقل البيانات بين أجزاء النظام. وتعمل داخله أعداد هائلة من الترانزستورات لتنفيذ هذه العمليات خلال أزمنة قصيرة جدًا.","hashtags":["#Shorts","#تقنية","#حاسوب"]},
    {"search":"smartphone sensors close up","fallback_searches":["phone sensors","smartphone technology"],"title":"الهاتف يعرف اتجاهه باستخدام حساسات صغيرة","text":"يحتوي الهاتف على حساسات تقيس الحركة والدوران وأحيانًا المجال المغناطيسي. تجمع البرامج هذه القراءات لتحديد اتجاه الجهاز وحركته، ولذلك تتغير الشاشة تلقائيًا عند تدوير الهاتف.","hashtags":["#Shorts","#تقنية","#هواتف"]},
    {"search":"electric car motor engineering","fallback_searches":["electric vehicle motor","electric car technology"],"title":"المحرك الكهربائي يحول الطاقة الكهربائية إلى حركة","text":"يستخدم المحرك الكهربائي تفاعل المجالات المغناطيسية لإنتاج دوران. تنتقل الطاقة من البطارية إلى النظام الكهربائي ثم إلى المحرك، الذي يحولها إلى حركة تدير عجلات المركبة.","hashtags":["#Shorts","#هندسة","#سيارات"]},
    {"search":"wind turbine engineering","fallback_searches":["wind turbine","renewable energy engineering"],"title":"توربينات الرياح تحول حركة الهواء إلى كهرباء","text":"عندما يدفع الهواء شفرات التوربين تبدأ بالدوران. ينقل العمود هذه الحركة إلى مولد كهربائي، فيحوّل الطاقة الحركية الناتجة عن الرياح إلى طاقة كهربائية.","hashtags":["#Shorts","#هندسة","#طاقة"]},
    {"search":"dam engineering water","fallback_searches":["hydroelectric dam","dam construction"],"title":"السدود تستخدم فرق الارتفاع لتوليد الطاقة","text":"عندما تتحرك المياه من مستوى مرتفع إلى مستوى منخفض يمكن استغلال طاقتها الحركية. في محطات الطاقة الكهرومائية تمر المياه عبر توربينات تدور بدورها مولدات كهربائية.","hashtags":["#Shorts","#هندسة","#طاقة"]},
    {"search":"fiber optic cable close up","fallback_searches":["fiber optics","internet cable"],"title":"الألياف الضوئية تنقل البيانات باستخدام الضوء","text":"تنتقل البيانات داخل الألياف الضوئية على هيئة نبضات ضوئية عبر ألياف دقيقة جدًا. وتساعد خصائص المادة وتصميم الليف على إبقاء الضوء داخل مساره لمسافات طويلة.","hashtags":["#Shorts","#تقنية","#إنترنت"]},
    {"search":"satellite orbit earth","fallback_searches":["satellite engineering","space satellite"],"title":"القمر الصناعي يبقى في المدار بسبب توازن السرعة والجاذبية","text":"يدور القمر الصناعي بسرعة أفقية كبيرة بينما تجذبه جاذبية الأرض نحوها. يؤدي الجمع بين الحركة الأمامية والجاذبية إلى مسار مداري بدلًا من سقوطه مباشرة نحو سطح الأرض.","hashtags":["#Shorts","#هندسة","#فضاء"]},

    # =========================
    # الألعاب الإلكترونية
    # =========================
    {"search":"esports gaming competition","fallback_searches":["competitive gaming","esports players"],"title":"الألعاب التنافسية تعتمد على سرعة القرار وليس سرعة اليد فقط","text":"في الألعاب التنافسية يحتاج اللاعب إلى قراءة الموقف بسرعة ثم اختيار القرار المناسب. التوقيت ومعرفة الخريطة وتوقع حركة الخصم قد تكون عوامل مهمة إلى جانب سرعة الاستجابة.","hashtags":["#Shorts","#ألعاب","#رياضات_إلكترونية"]},
    {"search":"video game controller close up","fallback_searches":["gaming controller","gamepad"],"title":"يد التحكم ترسل أوامر اللاعب إلى اللعبة خلال أجزاء من الثانية","text":"عند الضغط على زر في يد التحكم تتحول الحركة إلى إشارة يقرأها الجهاز. ثم يعالج النظام الأمر ويرسل النتيجة إلى اللعبة، وتظهر الاستجابة على الشاشة خلال زمن قصير جدًا.","hashtags":["#Shorts","#ألعاب","#تقنية"]},
    {"search":"gaming computer graphics card","fallback_searches":["gaming pc","graphics card"],"title":"بطاقة الرسومات تعالج جزءًا كبيرًا من الصورة التي تراها في اللعبة","text":"تعالج بطاقة الرسومات العمليات المتعلقة بالرسم وإظهار المشاهد ثلاثية الأبعاد. كلما زادت تفاصيل المشهد احتاجت عملية الرسم إلى قدرة حسابية أكبر للحفاظ على سلاسة العرض.","hashtags":["#Shorts","#ألعاب","#حاسوب"]},
    {"search":"video game loading screen","fallback_searches":["game loading","gaming technology"],"title":"تظهر شاشة التحميل عندما يحتاج الجهاز إلى تجهيز بيانات جديدة","text":"أثناء تحميل مرحلة جديدة تنقل اللعبة بيانات من وحدة التخزين إلى الذاكرة وتجهز النماذج والأصوات والخرائط المطلوبة. تعتمد مدة التحميل على حجم البيانات وسرعة مكونات الجهاز.","hashtags":["#Shorts","#ألعاب","#تقنية"]},
    {"search":"video game physics simulation","fallback_searches":["game physics","gaming simulation"],"title":"محركات الألعاب تحاكي الحركة والاصطدامات باستخدام الرياضيات","text":"تعتمد الألعاب الحديثة على محركات فيزيائية لحساب الحركة والجاذبية والاصطدامات. تُجرى هذه الحسابات باستمرار حتى تبدو الأجسام داخل اللعبة وكأنها تتفاعل مع البيئة بطريقة واقعية.","hashtags":["#Shorts","#ألعاب","#علوم"]},
    {"search":"game development coding","fallback_searches":["video game programming","game developer"],"title":"كل حركة داخل اللعبة تبدأ بتعليمات برمجية","text":"تحدد البرمجيات ما يحدث عندما يتحرك اللاعب أو يضغط زرًا أو يصطدم جسمان داخل اللعبة. يترجم محرك اللعبة هذه التعليمات إلى أحداث وصور وأصوات تظهر للمستخدم.","hashtags":["#Shorts","#ألعاب","#برمجة"]},
    {"search":"gaming network multiplayer","fallback_searches":["online multiplayer gaming","game server"],"title":"اللعب الجماعي عبر الإنترنت يحتاج إلى تبادل البيانات بسرعة","text":"عندما تلعب عبر الإنترنت تُرسل معلومات عن حركتك وأوامرك إلى الخادم، ثم تعود إليك بيانات اللاعبين الآخرين. كلما زاد زمن انتقال البيانات أصبحت الاستجابة بين حركة اللاعب وما يظهر على الشاشة أبطأ.","hashtags":["#Shorts","#ألعاب","#إنترنت"]},
    {"search":"gaming monitor high refresh rate","fallback_searches":["gaming display","high refresh monitor"],"title":"معدل التحديث يحدد عدد مرات تحديث الصورة في الثانية","text":"يعبر معدل تحديث الشاشة عن عدد المرات التي يمكن فيها تحديث الصورة خلال ثانية واحدة. المعدل الأعلى يمكن أن يجعل الحركة تبدو أكثر سلاسة عندما يستطيع الجهاز إنتاج عدد مناسب من الإطارات.","hashtags":["#Shorts","#ألعاب","#شاشات"]},
    {"search":"game console hardware","fallback_searches":["gaming console","console technology"],"title":"أجهزة الألعاب تجمع المعالج والرسومات والذاكرة في نظام واحد","text":"يحتوي جهاز الألعاب على معالج وذاكرة ووحدة لمعالجة الرسومات ووحدات أخرى تعمل معًا. صممت هذه المكونات لتشغيل الألعاب ومعالجة الرسومات والصوت وإدارة البيانات في الوقت نفسه.","hashtags":["#Shorts","#ألعاب","#تقنية"]},
    {"search":"video game artificial intelligence enemies","fallback_searches":["game enemy ai","game artificial intelligence"],"title":"الشخصيات غير القابلة للتحكم تعتمد على خوارزميات لاتخاذ قراراتها","text":"تستخدم الألعاب خوارزميات مختلفة لتحديد كيفية تحرك الشخصيات التي لا يتحكم بها اللاعب. يمكن للنظام اختيار مسار أو البحث عن اللاعب أو تغيير السلوك وفق الأحداث التي تحدث داخل اللعبة.","hashtags":["#Shorts","#ألعاب","#ذكاء_اصطناعي"]},
    {"search":"racing video game steering","fallback_searches":["racing game","driving simulator"],"title":"ألعاب السباق تحاكي تأثير السرعة والاحتكاك على السيارة","text":"تحسب ألعاب السباق عوامل مثل السرعة والتسارع والاحتكاك وتغير الاتجاه. هذه الحسابات تجعل استجابة السيارة مختلفة عند الكبح أو التسارع أو دخول المنعطفات.","hashtags":["#Shorts","#ألعاب","#سيارات"]},
    {"search":"virtual reality gaming headset","fallback_searches":["vr gaming","virtual reality headset"],"title":"نظارة الواقع الافتراضي تتتبع حركة الرأس لتغيير المشهد","text":"تحتوي نظارات الواقع الافتراضي على حساسات تتابع دوران الرأس وحركته. يستخدم النظام هذه البيانات لتحديث زاوية المشهد بسرعة، فيبدو للمستخدم أن البيئة الافتراضية تتحرك مع اتجاه نظره.","hashtags":["#Shorts","#ألعاب","#واقع_افتراضي"]},
    {"search":"gaming mouse close up","fallback_searches":["computer gaming mouse","gaming peripherals"],"title":"حساس الفأرة يحول حركة اليد إلى بيانات رقمية","text":"يستخدم فأرة الحاسوب حساسًا بصريًا لالتقاط التغير في موضعها على السطح. يحول الجهاز هذه الحركة إلى بيانات يفسرها الحاسوب لتحريك المؤشر أو تنفيذ الأوامر داخل اللعبة.","hashtags":["#Shorts","#ألعاب","#تقنية"]},
    {"search":"video game sound design headphones","fallback_searches":["game audio design","gaming headphones"],"title":"الصوت في الألعاب يساعد اللاعب على فهم ما يحدث حوله","text":"تستخدم الألعاب المؤثرات الصوتية لتحديد اتجاه الأحداث والتنبيه إلى أشياء قد لا تظهر مباشرة أمام اللاعب. لذلك يمكن للصوت أن يضيف معلومات مهمة إلى المشهد البصري.","hashtags":["#Shorts","#ألعاب","#صوت"]},
    {"search":"game animation character","fallback_searches":["video game animation","game character animation"],"title":"الحركة داخل اللعبة تتكون من سلسلة من الإطارات","text":"تظهر حركة الشخصية داخل اللعبة نتيجة عرض سلسلة من الصور أو الحالات المتغيرة بسرعة. كلما كانت الانتقالات بين الإطارات أكثر سلاسة بدت الحركة طبيعية للمشاهد.","hashtags":["#Shorts","#ألعاب","#رسوم"]},
    {"search":"gaming cooling pc fans","fallback_searches":["gaming pc cooling","computer cooling fans"],"title":"تبريد الحاسوب مهم أثناء تشغيل الألعاب الثقيلة","text":"تنتج المعالجات وبطاقات الرسومات حرارة أثناء العمل، وتزداد الحرارة عند ارتفاع الحمل. تستخدم أجهزة الحاسوب المراوح والمشتتات الحرارية وأنظمة أخرى لنقل الحرارة بعيدًا عن المكونات.","hashtags":["#Shorts","#ألعاب","#حاسوب"]},
    {"search":"game map level design","fallback_searches":["video game level design","game environment design"],"title":"تصميم مراحل الألعاب يوجه اللاعب من دون إعطائه التعليمات دائمًا","text":"يمكن للمصمم استخدام الإضاءة والألوان وشكل البيئة ومواقع العناصر لتوجيه انتباه اللاعب. بهذه الطريقة يفهم اللاعب المسار أو الهدف من خلال تصميم المرحلة نفسه.","hashtags":["#Shorts","#ألعاب","#تصميم"]},
    {"search":"esports reaction gaming","fallback_searches":["esports reaction time","competitive gaming"],"title":"زمن الاستجابة جزء مهم من الأداء في الألعاب السريعة","text":"زمن الاستجابة هو الوقت بين ظهور المعلومة واتخاذ الإجراء المناسب. في الألعاب السريعة قد تحدث عدة أحداث خلال فترة قصيرة، لذلك يحتاج اللاعب إلى الانتباه ومعالجة المعلومات بسرعة.","hashtags":["#Shorts","#ألعاب","#رياضات_إلكترونية"]},
    {"search":"game save data storage","fallback_searches":["game save system","gaming storage"],"title":"ملف الحفظ يخزن معلومات تقدم اللاعب","text":"تخزن الألعاب في ملف الحفظ بيانات مثل المرحلة التي وصل إليها اللاعب والعناصر التي حصل عليها وبعض إعدادات اللعبة. عند العودة إلى اللعبة تُقرأ هذه البيانات لاستعادة حالة التقدم.","hashtags":["#Shorts","#ألعاب","#تقنية"]},

    # =========================
    # علوم وتقنية إضافية
    # =========================
    {"search":"battery charging lithium ion","fallback_searches":["battery technology","lithium ion battery"],"title":"البطارية تخزن الطاقة في صورة طاقة كيميائية","text":"تخزن البطاريات الطاقة من خلال تفاعلات كيميائية قابلة للعكس في كثير من الأنواع الحديثة. عند توصيل الجهاز تتحول هذه الطاقة إلى تيار كهربائي يغذي الدائرة الإلكترونية.","hashtags":["#Shorts","#علوم","#تقنية"]},
    {"search":"microscope cells science","fallback_searches":["microscope biology","cells under microscope"],"title":"الخلايا هي وحدات البناء الأساسية في الكائنات الحية","text":"تتكون الكائنات الحية من خلايا تؤدي وظائف مختلفة. بعض الخلايا تنقل الإشارات، وبعضها ينتج الطاقة أو يبني الأنسجة، وتعمل هذه الخلايا معًا للحفاظ على وظائف الجسم.","hashtags":["#Shorts","#علوم","#أحياء"]},
    {"search":"DNA molecular model","fallback_searches":["DNA science","genetics molecule"],"title":"الحمض النووي يحمل تعليمات وراثية داخل الخلايا","text":"يحتوي الحمض النووي على معلومات وراثية تستخدمها الخلايا لإنتاج بروتينات وتنظيم وظائفها. وتُخزن هذه المعلومات في ترتيب وحدات كيميائية متتابعة داخل الجزيء.","hashtags":["#Shorts","#علوم","#أحياء"]},
    {"search":"telescope astronomy night","fallback_searches":["astronomy telescope","space telescope"],"title":"التلسكوب يجمع ضوءًا أكثر من العين المجردة","text":"يستخدم التلسكوب عدسات أو مرايا لجمع الضوء وتركيزه، ولذلك يستطيع إظهار أجسام فلكية خافتة لا يمكن رؤيتها بسهولة بالعين المجردة. بعض التلسكوبات تعمل خارج الغلاف الجوي للحصول على صور أوضح.","hashtags":["#Shorts","#فضاء","#علوم"]},
    {"search":"laser light beam","fallback_searches":["laser technology","laser physics"],"title":"ضوء الليزر يختلف عن الضوء العادي في خصائصه","text":"ينتج الليزر ضوءًا منظمًا يمكن أن يكون شديد التركيز وله خصائص تختلف عن مصادر الضوء المعتادة. لذلك يستخدم في الاتصالات والطب والصناعة والقياس العلمي.","hashtags":["#Shorts","#علوم","#تقنية"]},
    {"search":"computer cooling fan","fallback_searches":["cpu cooling","computer heat"],"title":"المشتت الحراري يساعد المعالج على التخلص من الحرارة","text":"عند تنفيذ العمليات تنتج الدوائر الإلكترونية حرارة. ينقل المشتت الحراري هذه الحرارة من المعالج إلى مساحة أكبر، ثم تساعد المروحة أو نظام التبريد على إخراجها إلى الهواء.","hashtags":["#Shorts","#تقنية","#حاسوب"]},
    {"search":"drone flying engineering","fallback_searches":["drone technology","quadcopter"],"title":"الطائرة المسيرة تغير اتجاهها بتعديل سرعة المراوح","text":"تستخدم الطائرات المسيرة عدة مراوح لإنتاج قوة رفع والتحكم في الحركة. عند تغيير سرعة بعض المراوح مقارنة بغيرها يتغير اتجاه القوة، فتستطيع الطائرة الصعود أو الدوران أو التحرك.","hashtags":["#Shorts","#هندسة","#تقنية"]},
    {"search":"3d animation rendering computer","fallback_searches":["computer rendering","3d graphics"],"title":"الرسم ثلاثي الأبعاد يحتاج إلى حساب شكل الضوء والسطوح","text":"عند إنشاء مشهد ثلاثي الأبعاد يحسب الحاسوب شكل الأجسام ومواقعها واتجاه الضوء والمواد المستخدمة على الأسطح. ثم يحول هذه المعلومات إلى صورة ثنائية الأبعاد تظهر على الشاشة.","hashtags":["#Shorts","#تقنية","#رسوم"]},
]


# =========================================================
# EXTENDED CONTENT POOL
# =========================================================
# Additional evergreen topics. These are intentionally different from the
# original pool and stay inside the channel categories: football, science,
# engineering/technology, and electronic gaming.
TOPICS.extend([
    # -----------------------------------------------------
    # كرة القدم والرياضة
    # -----------------------------------------------------
    {"search":"football goalkeeper gloves close up","fallback_searches":["soccer goalkeeper gloves","goalkeeper equipment"],"title":"قفازات حارس المرمى تزيد الاحتكاك بين اليد والكرة","text":"تحتوي قفازات حراس المرمى على طبقات مصممة لزيادة الاحتكاك والمساعدة على الإمساك بالكرة. ويختلف تأثيرها بحسب نوع السطح والطقس وطريقة ملامسة الكرة.","hashtags":["#Shorts","#كرة_القدم","#رياضة"]},
    {"search":"football corner kick stadium","fallback_searches":["soccer corner kick","football set piece"],"title":"الركلة الركنية تمنح الفريق فرصة لصنع مساحة داخل منطقة الجزاء","text":"عند تنفيذ الركلة الركنية تتحرك مجموعة من اللاعبين في مسارات محددة لمحاولة الوصول إلى الكرة أو فتح مساحة لزميل. التوقيت والمسافة بين اللاعبين يؤثران في نجاح التحرك.","hashtags":["#Shorts","#كرة_القدم","#تكتيك"]},
    {"search":"football ball pressure gauge","fallback_searches":["soccer ball inflation","football ball close up"],"title":"ضغط الهواء داخل الكرة يغيّر طريقة ارتدادها","text":"يؤثر ضغط الهواء داخل كرة القدم في مقدار ارتدادها واستجابتها عند الركل. لذلك تحتاج الكرة إلى نطاق ضغط محدد حتى تحافظ على سلوك متوقع أثناء اللعب.","hashtags":["#Shorts","#كرة_القدم","#علوم"]},
    {"search":"football referee whistle match","fallback_searches":["soccer referee","football match official"],"title":"صافرة الحكم تحول قرارًا سريعًا إلى إشارة واضحة للجميع","text":"تساعد الصافرة الحكم على إرسال إشارة مسموعة للاعبين والمشاهدين داخل الملعب. ويختلف توقيت استخدامها بحسب الحالة والقانون الذي ينظم اللعب.","hashtags":["#Shorts","#كرة_القدم","#رياضة"]},
    {"search":"football stadium grass close up","fallback_searches":["soccer pitch grass","football field turf"],"title":"عشب الملعب يؤثر في سرعة حركة الكرة","text":"تؤثر حالة سطح الملعب في الاحتكاك بين الكرة والعشب، كما تؤثر الرطوبة وطول العشب في سرعة الكرة وتغير اتجاهها. لهذا تتم صيانة أرضية الملعب باستمرار.","hashtags":["#Shorts","#كرة_القدم","#ملاعب"]},
    {"search":"football midfielder scanning pitch","fallback_searches":["soccer player scanning","football midfielder"],"title":"بعض اللاعبين يرفعون رؤوسهم قبل استلام الكرة","text":"ينظر اللاعب حوله قبل استلام الكرة ليعرف أماكن زملائه والمساحات المتاحة. هذه العادة تساعده على اتخاذ قرار أسرع بعد وصول الكرة إلى قدمه.","hashtags":["#Shorts","#كرة_القدم","#تكتيك"]},
    {"search":"football header training","fallback_searches":["soccer heading","football aerial duel"],"title":"توجيه الكرة بالرأس يعتمد على توقيت الحركة","text":"عند لعب الكرة بالرأس ينسق اللاعب حركة الجسم والرقبة مع لحظة ملامسة الكرة. ويؤثر اتجاه الجبهة وزاوية الجسم في مسار الكرة بعد اللمس.","hashtags":["#Shorts","#كرة_القدم","#رياضة"]},
    {"search":"football ball trajectory slow motion","fallback_searches":["soccer ball flight","football physics"],"title":"مسار الكرة يتغير بسبب السرعة والدوران والهواء","text":"لا تتحرك كرة القدم في الهواء بسبب الركل وحده. تؤثر سرعتها ودورانها ومقاومة الهواء والجاذبية في المسار الذي تسلكه حتى تصل إلى الأرض أو إلى لاعب آخر.","hashtags":["#Shorts","#كرة_القدم","#فيزياء"]},
    {"search":"football warm up training cones","fallback_searches":["soccer warm up","football training cones"],"title":"الإحماء يرفع جاهزية العضلات قبل النشاط الرياضي","text":"تساعد تمارين الإحماء على رفع درجة حرارة العضلات وتجهيز الجسم للحركة. ويستخدم اللاعبون حركات تدريجية قبل الدخول في الجهد الأعلى خلال التدريب أو المباراة.","hashtags":["#Shorts","#رياضة","#كرة_القدم"]},
    {"search":"football stadium floodlights night","fallback_searches":["soccer stadium lights","stadium lighting engineering"],"title":"إضاءة الملعب تحتاج إلى توزيع متوازن للضوء","text":"توزع أنظمة إضاءة الملاعب الضوء من زوايا متعددة حتى تقل المناطق المظلمة وتظهر الكرة واللاعبون بوضوح. كما تراعي التصميمات متطلبات البث التلفزيوني.","hashtags":["#Shorts","#كرة_القدم","#هندسة"]},
    {"search":"football training reaction lights","fallback_searches":["soccer reaction training","sports reaction lights"],"title":"تمارين الإضاءة السريعة تختبر سرعة اتخاذ القرار","text":"تستخدم بعض تدريبات كرة القدم إشارات ضوئية متغيرة لطلب حركة أو تمرير سريع. الفكرة هي تدريب اللاعب على ملاحظة الإشارة ثم اختيار الاستجابة المناسبة خلال وقت قصير.","hashtags":["#Shorts","#كرة_القدم","#تدريب"]},
    {"search":"football jersey fabric close up","fallback_searches":["soccer shirt fabric","sports clothing technology"],"title":"أقمشة الملابس الرياضية مصممة لتسهيل تبخر العرق","text":"تستخدم بعض الملابس الرياضية أقمشة خفيفة تسمح بمرور الهواء ونقل الرطوبة بعيدًا عن سطح الجلد. الهدف هو تحسين الراحة أثناء النشاط والحركة المستمرة.","hashtags":["#Shorts","#رياضة","#تقنية"]},
    {"search":"football substitution board referee","fallback_searches":["soccer substitution board","football match substitution"],"title":"لوحة التبديل الإلكترونية تعرض رقم اللاعب بسرعة","text":"تعرض لوحة التبديل رقم اللاعب الذي سيغادر ورقم اللاعب الذي سيدخل. وتسمح الإشارة الرقمية للحكم واللاعبين بمعرفة التبديل بوضوح من مسافة بعيدة.","hashtags":["#Shorts","#كرة_القدم","#تقنية"]},
    {"search":"football ball goalkeeper training machine","fallback_searches":["soccer ball launcher","goalkeeper training equipment"],"title":"آلات التدريب تستطيع تكرار التسديدات بسرعة ثابتة","text":"تستخدم بعض معدات التدريب آليات تقذف الكرة بسرعات واتجاهات مختلفة. هذا يسمح بتكرار تمرين معين عدة مرات مع تغيير المسافة أو زاوية وصول الكرة.","hashtags":["#Shorts","#كرة_القدم","#هندسة"]},
    {"search":"football player GPS training vest","fallback_searches":["soccer tracking device","sports GPS tracker"],"title":"أجهزة التتبع تقيس حركة اللاعب أثناء التدريب","text":"تستخدم بعض الفرق أجهزة صغيرة لتسجيل المسافة والسرعة وتغيرات الحركة أثناء التدريب. تساعد البيانات المدربين على فهم حجم الجهد المبذول خلال الحصة الرياضية.","hashtags":["#Shorts","#كرة_القدم","#تقنية"]},

    # -----------------------------------------------------
    # العلوم
    # -----------------------------------------------------
    {"search":"soap bubbles close up","fallback_searches":["bubble surface tension","soap bubble science"],"title":"فقاعة الصابون تحافظ على شكلها بسبب توتر السطح","text":"يتكون غشاء فقاعة الصابون من طبقة رقيقة من السائل، وتعمل قوى التوتر السطحي على تقليل مساحة الغشاء. لهذا تميل الفقاعة إلى الشكل الكروي.","hashtags":["#Shorts","#علوم","#فيزياء"]},
    {"search":"shadow sunlight science","fallback_searches":["shadow physics","light and shadow"],"title":"طول الظل يتغير مع زاوية سقوط الضوء","text":"يتغير طول الظل عندما يتغير اتجاه مصدر الضوء بالنسبة إلى الجسم. عندما يكون الضوء أكثر ارتفاعًا يصبح الظل أقصر، وعندما ينخفض مصدر الضوء يمتد الظل لمسافة أكبر.","hashtags":["#Shorts","#علوم","#فيزياء"]},
    {"search":"prism rainbow light","fallback_searches":["light dispersion prism","rainbow science"],"title":"المنشور الزجاجي يستطيع فصل الضوء إلى ألوان مختلفة","text":"عندما يمر الضوء عبر منشور زجاجي تتغير سرعته واتجاهه بطريقة تعتمد على طول الموجة. لذلك تنفصل مكونات الضوء وتظهر ألوان الطيف بوضوح.","hashtags":["#Shorts","#علوم","#ضوء"]},
    {"search":"static electricity balloon hair","fallback_searches":["static electricity science","electric charge"],"title":"الكهرباء الساكنة تنتج من تراكم شحنات على سطح الجسم","text":"يمكن للاحتكاك بين مادتين أن ينقل إلكترونات من سطح إلى آخر. يؤدي ذلك إلى اختلاف في الشحنة الكهربائية، وقد يظهر على شكل جذب أجسام خفيفة أو شرارة صغيرة.","hashtags":["#Shorts","#علوم","#كهرباء"]},
    {"search":"boiling water steam close up","fallback_searches":["water boiling science","steam physics"],"title":"غليان الماء يحدث عندما تتكون فقاعات البخار داخل السائل","text":"عند وصول الماء إلى درجة الغليان المناسبة للضغط المحيط تتكون فقاعات من بخار الماء داخل السائل. تصعد الفقاعات إلى السطح وتطلق البخار في الهواء.","hashtags":["#Shorts","#علوم","#ماء"]},
    {"search":"metal thermal expansion experiment","fallback_searches":["thermal expansion metal","heat expansion science"],"title":"المعادن تتمدد عندما ترتفع درجة حرارتها","text":"عند تسخين معظم المعادن تزداد حركة ذراتها قليلًا، فيزداد متوسط المسافة بينها. لذلك يتمدد المعدن، ويؤخذ هذا التأثير في الاعتبار عند تصميم الجسور والأنابيب والآلات.","hashtags":["#Shorts","#علوم","#هندسة"]},
    {"search":"pendulum physics experiment","fallback_searches":["pendulum motion","physics pendulum"],"title":"زمن حركة البندول يتأثر بطول خيطه","text":"في البندول البسيط يرتبط زمن الدورة بطول الخيط وتسارع الجاذبية. عند زيادة طول الخيط تستغرق الدورة وقتًا أطول، مع ثبات العوامل الأخرى تقريبًا.","hashtags":["#Shorts","#علوم","#فيزياء"]},
    {"search":"water pressure deep ocean","fallback_searches":["ocean pressure science","deep water pressure"],"title":"ضغط الماء يزداد كلما زاد العمق","text":"يزداد وزن عمود الماء الموجود فوق نقطة معينة كلما نزلنا إلى عمق أكبر. لذلك يرتفع الضغط في المياه العميقة، وتحتاج المعدات المستخدمة هناك إلى تصميم يتحمل هذه القوة.","hashtags":["#Shorts","#علوم","#بحار"]},
    {"search":"sound waves oscilloscope","fallback_searches":["sound waveform","audio physics"],"title":"يمكن تحويل الصوت إلى موجة تظهر على شاشة القياس","text":"عند التقاط الصوت بميكروفون تتحول الاهتزازات إلى إشارة كهربائية. يمكن لجهاز القياس عرض هذه الإشارة على شكل موجة توضح تغيرها مع الزمن.","hashtags":["#Shorts","#علوم","#صوت"]},
    {"search":"ultraviolet light science","fallback_searches":["uv light experiment","ultraviolet spectrum"],"title":"الأشعة فوق البنفسجية جزء من الطيف الكهرومغناطيسي","text":"الأشعة فوق البنفسجية موجات كهرومغناطيسية ذات أطوال موجية أقصر من الضوء البنفسجي المرئي. تصل بعض هذه الأشعة من الشمس إلى سطح الأرض، ولذلك تُستخدم وسائل حماية مناسبة عند التعرض القوي.","hashtags":["#Shorts","#علوم","#ضوء"]},
    {"search":"infrared thermal camera","fallback_searches":["thermal imaging","infrared camera science"],"title":"الكاميرا الحرارية تعرض فروق الإشعاع الحراري","text":"تلتقط الكاميرات الحرارية الأشعة تحت الحمراء المنبعثة من الأجسام، ثم تحول البيانات إلى صورة توضح اختلاف درجات الحرارة. تستخدم هذه التقنية في الفحص والهندسة والمراقبة العلمية.","hashtags":["#Shorts","#علوم","#تقنية"]},
    {"search":"solar eclipse safe viewing science","fallback_searches":["eclipse science","solar observation"],"title":"الكسوف يحدث عندما يحجب القمر جزءًا من ضوء الشمس عن منطقة من الأرض","text":"يحدث كسوف الشمس عندما يمر القمر بين الشمس والأرض ويقع ظله على جزء من سطح الأرض. يختلف مقدار الحجب بحسب موقع الراصد بالنسبة إلى مسار الظل.","hashtags":["#Shorts","#علوم","#فضاء"]},
    {"search":"moon phases night sky","fallback_searches":["moon phase science","lunar phases"],"title":"أطوار القمر تنتج من تغير الجزء المضيء المرئي من الأرض","text":"القمر لا يصنع ضوءه بنفسه بل يعكس ضوء الشمس. ومع دوران القمر حول الأرض يتغير الجزء المضيء الذي نراه، فتظهر الأطوار المختلفة خلال الشهر القمري.","hashtags":["#Shorts","#علوم","#فضاء"]},
    {"search":"satellite orbit earth animation","fallback_searches":["satellite orbit science","space satellite"],"title":"القمر الصناعي يبقى في المدار بسبب توازن السرعة والجاذبية","text":"يتحرك القمر الصناعي بسرعة أفقية بينما تجذبه الجاذبية نحو الأرض. هذا التفاعل يجعل مساره منحنيًا حول الأرض بدلًا من سقوطه مباشرة نحو سطحها.","hashtags":["#Shorts","#فضاء","#فيزياء"]},
    {"search":"solar panel sunlight close up","fallback_searches":["solar cell technology","photovoltaic panel"],"title":"الخلايا الشمسية تحول جزءًا من ضوء الشمس إلى كهرباء","text":"تستخدم الخلايا الشمسية مواد شبه موصلة لتحويل طاقة الضوء إلى طاقة كهربائية. عند وصول الفوتونات إلى الخلية يمكن أن تساهم في توليد تيار كهربائي داخل الدائرة.","hashtags":["#Shorts","#علوم","#تقنية"]},
    {"search":"earth atmosphere blue sky","fallback_searches":["atmosphere science","blue sky physics"],"title":"السماء تبدو زرقاء بسبب تشتت الضوء في الغلاف الجوي","text":"تتفاعل أشعة الشمس مع جزيئات الغازات في الغلاف الجوي، وتتشتت الأطوال الموجية القصيرة من الضوء المرئي بقوة أكبر من الأطوال الأطول. لهذا يغلب اللون الأزرق على السماء في النهار الصافي.","hashtags":["#Shorts","#علوم","#فضاء"]},
    {"search":"plant seed germination time lapse","fallback_searches":["seed germination","plant growth science"],"title":"البذرة تبدأ الإنبات عندما تتوافر لها ظروف مناسبة","text":"تمتص البذرة الماء وتبدأ عمليات داخلية تسمح للجنين بالنمو. ومع توافر الحرارة والأكسجين والظروف المناسبة تظهر الجذور ثم يبدأ الجزء العلوي من النبات في النمو.","hashtags":["#Shorts","#علوم","#نباتات"]},
    {"search":"tree rings close up","fallback_searches":["tree growth rings","plant biology"],"title":"حلقات جذع الشجرة تسجل مراحل من نموها","text":"ينتج الخشب الجديد في كثير من الأشجار أنماطًا يمكن رؤيتها على شكل حلقات في مقطع الجذع. تختلف هذه الحلقات في السماكة بحسب ظروف النمو خلال الفترات المختلفة.","hashtags":["#Shorts","#علوم","#نباتات"]},
    {"search":"gecko feet macro","fallback_searches":["gecko feet science","animal adhesion"],"title":"أقدام الوزغ تستطيع الالتصاق بالأسطح بآلية دقيقة","text":"تحتوي أقدام الوزغ على تراكيب مجهرية كثيرة تزيد مساحة التلامس مع السطح. تنشأ قوى جذب ضعيفة بين هذه التراكيب والسطح، وتتجمع لتساعد الحيوان على التسلق.","hashtags":["#Shorts","#علوم","#حيوانات"]},
    {"search":"bird feather macro","fallback_searches":["feather structure science","bird feather close up"],"title":"ريشة الطائر تحتوي على فروع دقيقة مترابطة","text":"تتكون الريشة من ساق رئيسية تخرج منها فروع أصغر تحمل تراكيب دقيقة مترابطة. يساعد هذا التنظيم على تكوين سطح خفيف ومتماسك يخدم الطائر أثناء الحركة في الهواء.","hashtags":["#Shorts","#علوم","#حيوانات"]},
    {"search":"fish underwater gills close up","fallback_searches":["fish gills science","aquatic respiration"],"title":"الخياشيم تستخلص الأكسجين المذاب في الماء","text":"يمر الماء عبر الخياشيم فتنتقل جزيئات الأكسجين من الماء إلى الدم عبر أسطح رقيقة جدًا. يسمح هذا الترتيب للأسماك باستخلاص الأكسجين من البيئة المائية.","hashtags":["#Shorts","#علوم","#بحار"]},

    # -----------------------------------------------------
    # الهندسة والتقنية
    # -----------------------------------------------------
    {"search":"robotic arm factory engineering","fallback_searches":["industrial robot arm","robotics manufacturing"],"title":"الذراع الآلية تتحرك عبر مفاصل يتحكم بها الحاسوب","text":"تحتوي الأذرع الآلية على مفاصل ومحركات وحساسات تسمح لها بتغيير موضعها بدقة. يرسل نظام التحكم أوامر لكل محرك للوصول إلى الوضع المطلوب.","hashtags":["#Shorts","#هندسة","#روبوتات"]},
    {"search":"3d printer printing close up","fallback_searches":["3d printing technology","additive manufacturing"],"title":"الطابعة ثلاثية الأبعاد تبني الجسم طبقة فوق طبقة","text":"تحول الطابعة ثلاثية الأبعاد نموذجًا رقميًا إلى جسم حقيقي عبر إضافة مادة على طبقات متتابعة. يختلف نوع المادة وطريقة الإضافة بحسب تقنية الطباعة المستخدمة.","hashtags":["#Shorts","#تقنية","#هندسة"]},
    {"search":"fiber optic cable light","fallback_searches":["fiber optic technology","optical fiber close up"],"title":"الألياف الضوئية تنقل البيانات باستخدام نبضات ضوئية","text":"تمر الإشارات الضوئية داخل ألياف دقيقة مصممة لحبس الضوء داخلها. يمكن استخدام هذه النبضات لتمثيل البيانات ونقلها لمسافات طويلة بسرعة عالية.","hashtags":["#Shorts","#تقنية","#اتصالات"]},
    {"search":"computer motherboard circuit close up","fallback_searches":["motherboard technology","computer circuit board"],"title":"اللوحة الأم تربط مكونات الحاسوب ببعضها","text":"تحتوي اللوحة الأم على مسارات ودوائر وموصلات تسمح بتبادل البيانات والطاقة بين المعالج والذاكرة ووحدات التخزين وغيرها من المكونات.","hashtags":["#Shorts","#تقنية","#حاسوب"]},
    {"search":"computer processor chip macro","fallback_searches":["cpu chip close up","processor technology"],"title":"المعالج ينفذ التعليمات من خلال مليارات العمليات الإلكترونية","text":"يحتوي المعالج الحديث على عدد هائل من الترانزستورات التي تتحكم في الإشارات الكهربائية. تعمل هذه الترانزستورات معًا لتنفيذ العمليات التي تحتاج إليها البرامج.","hashtags":["#Shorts","#تقنية","#حاسوب"]},
    {"search":"computer RAM memory module","fallback_searches":["ram memory technology","computer memory"],"title":"الذاكرة العشوائية تحفظ بيانات يحتاج إليها المعالج بسرعة","text":"تستخدم الذاكرة العشوائية مساحة سريعة لتخزين البيانات والتعليمات التي يحتاج إليها المعالج أثناء تشغيل البرامج. وتفقد هذه البيانات عند انقطاع الطاقة عنها.","hashtags":["#Shorts","#تقنية","#حاسوب"]},
    {"search":"SSD storage drive close up","fallback_searches":["solid state drive","SSD technology"],"title":"وحدة التخزين الصلبة تحفظ البيانات من دون أجزاء ميكانيكية متحركة","text":"تستخدم وحدات التخزين الصلبة شرائح ذاكرة لتخزين البيانات بدل الأقراص الدوارة الموجودة في بعض الأنواع الأقدم. هذا التصميم يسمح باستجابة سريعة ويقلل الأجزاء المتحركة.","hashtags":["#Shorts","#تقنية","#حاسوب"]},
    {"search":"wireless charging phone coil","fallback_searches":["wireless charging technology","charging coil"],"title":"الشحن اللاسلكي ينقل الطاقة عبر مجال مغناطيسي متغير","text":"يستخدم الشحن اللاسلكي ملفًا داخل قاعدة الشحن وملفًا آخر داخل الجهاز. يؤدي تغير المجال المغناطيسي إلى توليد تيار كهربائي في الملف الموجود داخل الجهاز.","hashtags":["#Shorts","#تقنية","#هندسة"]},
    {"search":"smartphone camera lens macro","fallback_searches":["phone camera technology","camera lens close up"],"title":"عدسات الهاتف توجه الضوء نحو حساس الصورة","text":"تجمع عدسة الكاميرا الضوء وتوجهه نحو حساس إلكتروني يحول الضوء إلى بيانات رقمية. وتستخدم الهواتف عدة عدسات في بعض الموديلات للحصول على خصائص تصوير مختلفة.","hashtags":["#Shorts","#تقنية","#هواتف"]},
    {"search":"camera image sensor macro","fallback_searches":["camera sensor technology","CMOS sensor"],"title":"حساس الكاميرا يحول الضوء إلى إشارات كهربائية","text":"يتكون حساس الصورة من عدد كبير من العناصر الحساسة للضوء. تستقبل هذه العناصر الفوتونات وتحول المعلومات إلى إشارات تستخدم لبناء الصورة الرقمية.","hashtags":["#Shorts","#تقنية","#تصوير"]},
    {"search":"computer network router lights","fallback_searches":["router technology","network equipment"],"title":"الموجه ينظم مرور البيانات بين الشبكات","text":"يستقبل الموجه حزم البيانات ويحدد المسار المناسب لإرسالها نحو الشبكة أو الجهاز المطلوب. تعتمد عملية الاختيار على معلومات موجودة في جداول التوجيه وإعدادات الشبكة.","hashtags":["#Shorts","#تقنية","#شبكات"]},
    {"search":"wifi router signal illustration","fallback_searches":["wifi technology","wireless network"],"title":"شبكة الواي فاي تنقل البيانات عبر موجات راديوية","text":"يحول جهاز الشبكة البيانات الرقمية إلى إشارات راديوية ثم يستقبلها الجهاز الآخر ويعيد تحويلها إلى بيانات. تتأثر جودة الاتصال بالمسافة والعوائق والتداخل بين الإشارات.","hashtags":["#Shorts","#تقنية","#شبكات"]},
    {"search":"server data center racks","fallback_searches":["data center technology","server room"],"title":"مراكز البيانات تحتاج إلى تبريد مستمر للحفاظ على الأجهزة","text":"تعمل الخوادم لفترات طويلة وتنتج حرارة أثناء معالجة البيانات. لذلك تستخدم مراكز البيانات أنظمة تبريد ومراقبة للحرارة للحفاظ على ظروف تشغيل مناسبة للمعدات.","hashtags":["#Shorts","#تقنية","#حاسوب"]},
    {"search":"computer keyboard switches macro","fallback_searches":["mechanical keyboard switch","keyboard technology"],"title":"المفاتيح الميكانيكية تستخدم آلية منفصلة لكل زر","text":"يحتوي المفتاح الميكانيكي عادة على آلية مستقلة تحت كل زر. عند الضغط يتحرك المفتاح ويغلق الدائرة أو يرسل إشارة إلى الحاسوب لتسجيل الإدخال.","hashtags":["#Shorts","#تقنية","#حاسوب"]},
    {"search":"bluetooth wireless headphones technology","fallback_searches":["bluetooth connection","wireless audio technology"],"title":"البلوتوث يرسل البيانات لاسلكيًا عبر موجات راديوية قصيرة المدى","text":"يستخدم البلوتوث موجات راديوية لنقل البيانات بين الأجهزة القريبة. ويقسم الاتصال البيانات إلى حزم ويستخدم آليات تنظيم تساعد الأجهزة على تبادل المعلومات.","hashtags":["#Shorts","#تقنية","#اتصالات"]},
    {"search":"electric motor rotor close up","fallback_searches":["electric motor engineering","motor rotor"],"title":"المحرك الكهربائي يحول الطاقة الكهربائية إلى حركة دورانية","text":"تتفاعل المجالات المغناطيسية داخل المحرك الكهربائي لإنتاج قوة على الجزء الدوار. تتحول هذه القوة إلى حركة دورانية يمكن استخدامها لتشغيل المراوح والعجلات والآلات.","hashtags":["#Shorts","#هندسة","#كهرباء"]},
    {"search":"wind turbine blades engineering","fallback_searches":["wind turbine technology","wind energy engineering"],"title":"شكل شفرات التوربين يساعد على تحويل حركة الهواء إلى دوران","text":"تصمم شفرات توربينات الرياح بشكل يشبه الأجنحة لتوليد قوة من مرور الهواء حولها. هذه القوة تدير الدوار، ثم يحول المولد الحركة إلى طاقة كهربائية.","hashtags":["#Shorts","#هندسة","#طاقة"]},
    {"search":"hydroelectric dam turbine","fallback_searches":["hydropower engineering","water turbine"],"title":"محطة الطاقة المائية تستخدم حركة الماء لتدوير التوربين","text":"عندما يمر الماء بسرعة عبر التوربين يدفع شفراته ويجعلها تدور. تنتقل الحركة إلى مولد كهربائي يحول الطاقة الميكانيكية إلى طاقة كهربائية.","hashtags":["#Shorts","#هندسة","#طاقة"]},
    {"search":"solar tracker panels engineering","fallback_searches":["solar tracking system","solar panel tracker"],"title":"نظام تتبع الشمس يغير زاوية الألواح خلال اليوم","text":"تستخدم بعض الأنظمة محركات وحساسات لتغيير زاوية الألواح الشمسية مع تغير موقع الشمس في السماء. الهدف هو توجيه السطح نحو الضوء بصورة أفضل خلال ساعات التشغيل.","hashtags":["#Shorts","#هندسة","#طاقة"]},
    {"search":"electric car motor close up","fallback_searches":["electric vehicle motor","EV powertrain"],"title":"السيارة الكهربائية تستخدم محركًا لتحويل الطاقة المخزنة إلى حركة","text":"تنتقل الطاقة من البطارية إلى نظام التحكم ثم إلى المحرك الكهربائي. ينتج المحرك عزمًا يدير العجلات، وتختلف طريقة التحكم في العزم بحسب سرعة السيارة وحالة القيادة.","hashtags":["#Shorts","#تقنية","#هندسة"]},
    {"search":"car regenerative braking animation","fallback_searches":["regenerative braking technology","electric car braking"],"title":"الكبح المتجدد يستطيع استعادة جزء من الطاقة أثناء التباطؤ","text":"عند تباطؤ السيارة الكهربائية يمكن للمحرك أن يعمل بطريقة مختلفة ويحول جزءًا من الحركة إلى طاقة كهربائية. تعود هذه الطاقة إلى البطارية ضمن حدود النظام.","hashtags":["#Shorts","#تقنية","#هندسة"]},
    {"search":"airplane wing wind tunnel model","fallback_searches":["airfoil engineering","aircraft wing science"],"title":"شكل الجناح يغير حركة الهواء حول الطائرة","text":"يصمم جناح الطائرة بحيث يوجه الهواء حول سطحه بطريقة تولد قوى هوائية. يعتمد أداء الجناح على الشكل والسرعة وزاوية الهجوم وكثافة الهواء.","hashtags":["#Shorts","#هندسة","#طيران"]},
    {"search":"airplane turbine engine close up","fallback_searches":["jet engine engineering","aircraft engine"],"title":"المحرك النفاث يضغط الهواء ثم يضيف إليه طاقة قبل دفع الغازات للخلف","text":"يدخل الهواء إلى المحرك ثم يمر بمراحل ضغط واحتراق وتمدد داخل نظام مصمم بعناية. تخرج الغازات بسرعة عالية من الخلف فتتولد قوة دفع تدفع الطائرة إلى الأمام.","hashtags":["#Shorts","#هندسة","#طيران"]},
    {"search":"rocket engine engineering test","fallback_searches":["space engine technology","rocket propulsion"],"title":"محرك المركبة الفضائية يحول طاقة الوقود إلى قوة دفع","text":"يخلط المحرك الوقود والمؤكسد بطريقة تنتج غازات عالية الطاقة. تندفع الغازات عبر فوهة مصممة لتسريعها، فتتولد قوة دفع تحرك المركبة في الاتجاه المعاكس.","hashtags":["#Shorts","#هندسة","#فضاء"]},
    {"search":"satellite solar panels engineering","fallback_searches":["satellite power system","spacecraft solar panels"],"title":"الألواح الشمسية تزود القمر الصناعي بالطاقة أثناء وجوده في الضوء","text":"تحول الألواح الشمسية الضوء إلى كهرباء لتشغيل الأنظمة الموجودة على القمر الصناعي. ويمكن تخزين جزء من الطاقة في البطاريات لاستخدامه عندما لا تصل أشعة الشمس إلى الألواح.","hashtags":["#Shorts","#فضاء","#هندسة"]},
    {"search":"robot vacuum sensors technology","fallback_searches":["robot vacuum navigation","home robot sensors"],"title":"المكنسة الروبوتية تستخدم حساسات لمعرفة ما حولها","text":"تجمع المكنسة الروبوتية بيانات من حساسات تساعدها على اكتشاف العوائق وتقدير موقعها. تستخدم الخوارزميات هذه البيانات لتحديد مسار الحركة داخل المكان.","hashtags":["#Shorts","#روبوتات","#تقنية"]},
    {"search":"smartwatch sensors close up","fallback_searches":["wearable technology sensors","smart watch technology"],"title":"الساعة الذكية تجمع بيانات الحركة باستخدام حساسات صغيرة","text":"تحتوي الساعات الذكية على حساسات تقيس الحركة والدوران وبعض المؤشرات الفيزيائية الأخرى. تستخدم البرامج هذه البيانات لتحديد النشاط وعرض معلومات للمستخدم.","hashtags":["#Shorts","#تقنية","#أجهزة"]},
    {"search":"microchip fabrication cleanroom","fallback_searches":["semiconductor manufacturing","chip fabrication"],"title":"تصنيع الشرائح الإلكترونية يحتاج إلى بيئة شديدة النظافة","text":"تحتوي الشرائح الإلكترونية على تفاصيل صغيرة جدًا، لذلك يمكن لجسيمات الغبار أن تؤثر في عملية التصنيع. تستخدم المصانع غرفًا نظيفة وأنظمة ترشيح دقيقة لتقليل الملوثات.","hashtags":["#Shorts","#تقنية","#هندسة"]},
    {"search":"led light bulb close up","fallback_searches":["LED technology","LED circuit"],"title":"مصباح ليد يحول الطاقة الكهربائية إلى ضوء داخل مادة شبه موصلة","text":"يصدر مصباح ليد الضوء عندما تمر الشحنات داخل مادة شبه موصلة مصممة لهذا الغرض. تختلف خصائص الضوء بحسب المادة وتركيب المصباح والدائرة المستخدمة.","hashtags":["#Shorts","#تقنية","#كهرباء"]},
    {"search":"touchscreen smartphone finger close up","fallback_searches":["capacitive touchscreen","touch screen technology"],"title":"شاشة اللمس السعوية تكتشف تغيرًا كهربائيًا عند لمسها","text":"تحتوي الشاشة السعوية على طبقة تستطيع رصد تغيرات في المجال الكهربائي عند اقتراب الإصبع. يعالج الجهاز موقع التغير ليحدد النقطة التي تم لمسها.","hashtags":["#Shorts","#تقنية","#هواتف"]},
    {"search":"qr code scanner phone","fallback_searches":["QR code technology","barcode scanner"],"title":"رمز الاستجابة السريعة يخزن المعلومات في نمط من المربعات","text":"يتكون رمز الاستجابة السريعة من وحدات مربعة مرتبة بطريقة تمثل بيانات رقمية. عند تصوير الرمز تستطيع البرامج قراءة النمط وتحويله إلى المعلومات المخزنة فيه.","hashtags":["#Shorts","#تقنية","#برمجة"]},
    {"search":"machine learning neural network visualization","fallback_searches":["neural network technology","machine learning model"],"title":"الشبكة العصبية الاصطناعية تتعلم الأنماط من البيانات","text":"تتكون الشبكات العصبية الاصطناعية من طبقات من وحدات حسابية مترابطة. أثناء التدريب تتغير أوزان هذه الروابط لتقليل الخطأ في النتائج على أمثلة التدريب.","hashtags":["#Shorts","#تقنية","#ذكاء_اصطناعي"]},
    {"search":"computer graphics GPU rendering","fallback_searches":["graphics processor","GPU rendering"],"title":"معالج الرسومات ينفذ عمليات كثيرة بالتوازي لإظهار الصور","text":"صمم معالج الرسومات لتنفيذ عدد كبير من العمليات المتشابهة في الوقت نفسه. لهذا يستخدم في رسم المشاهد ثلاثية الأبعاد ومعالجة الصور وبعض العمليات الحسابية المتوازية.","hashtags":["#Shorts","#تقنية","#ألعاب"]},
    {"search":"game console controller close up","fallback_searches":["gaming controller technology","gamepad buttons"],"title":"يد التحكم تحول ضغط الأزرار إلى إشارات يفهمها الجهاز","text":"تحتوي يد التحكم على مفاتيح وحساسات تلتقط ضغط الأزرار وحركة العصي. ترسل الدائرة الإلكترونية هذه المدخلات إلى الجهاز لتتحول إلى أوامر داخل اللعبة.","hashtags":["#Shorts","#ألعاب","#تقنية"]},
    {"search":"game physics engine simulation","fallback_searches":["video game physics","game physics simulation"],"title":"محرك الفيزياء يحسب حركة الأجسام داخل اللعبة","text":"يستخدم محرك الفيزياء معادلات لحساب الحركة والتصادم والجاذبية وغيرها من التأثيرات. ثم تُستخدم النتائج لتحديث مواقع الأجسام مع مرور الوقت داخل اللعبة.","hashtags":["#Shorts","#ألعاب","#برمجة"]},
    {"search":"game texture rendering close up","fallback_searches":["video game textures","game graphics rendering"],"title":"الخامات الرقمية تضيف تفاصيل إلى أسطح الأجسام داخل اللعبة","text":"تستخدم الألعاب صورًا أو بيانات رقمية لتحديد لون وملمس أسطح الأجسام. يطبق محرك الرسومات هذه الخامات على النماذج ثلاثية الأبعاد أثناء رسم المشهد.","hashtags":["#Shorts","#ألعاب","#رسوم"]},
    {"search":"game frame rate monitor","fallback_searches":["gaming fps counter","frame rate gaming"],"title":"معدل الإطارات يحدد عدد الصور التي تظهر خلال الثانية","text":"معدل الإطارات هو عدد الإطارات التي يرسمها الجهاز في الثانية. عندما يكون المعدل مستقرًا تبدو الحركة أكثر سلاسة، بينما قد تظهر تقطعات عند انخفاضه أو عدم استقراره.","hashtags":["#Shorts","#ألعاب","#تقنية"]},
    {"search":"gaming monitor refresh rate","fallback_searches":["monitor refresh rate gaming","gaming display"],"title":"معدل تحديث الشاشة يحدد عدد مرات تحديث الصورة في الثانية","text":"يقيس معدل التحديث عدد مرات تحديث الشاشة للصورة خلال الثانية. يمكن لمعدل أعلى أن يجعل الحركة السريعة أكثر سلاسة عندما يستطيع الجهاز توفير عدد إطارات مناسب.","hashtags":["#Shorts","#ألعاب","#تقنية"]},
    {"search":"game loading screen SSD","fallback_searches":["game loading technology","SSD gaming"],"title":"سرعة التخزين تؤثر في وقت تحميل بعض الألعاب","text":"عند تشغيل مرحلة جديدة تحتاج اللعبة إلى قراءة ملفات من وحدة التخزين ونقلها إلى الذاكرة. كلما تحسنت سرعة القراءة يمكن تقليل الوقت المطلوب لهذه العملية في بعض الحالات.","hashtags":["#Shorts","#ألعاب","#حاسوب"]},
    {"search":"game procedural generation terrain","fallback_searches":["procedural generation games","game world generation"],"title":"التوليد الإجرائي يستطيع إنشاء أجزاء من عالم اللعبة باستخدام قواعد حسابية","text":"بدل تخزين كل تفصيل يدويًا، يمكن للعبة استخدام خوارزميات تولد تضاريس أو عناصر وفق قواعد محددة. يسمح ذلك بإنشاء مساحات كبيرة ومتنوعة من عدد صغير نسبيًا من القواعد والبيانات.","hashtags":["#Shorts","#ألعاب","#برمجة"]},
    {"search":"game server multiplayer network","fallback_searches":["multiplayer game server","online gaming network"],"title":"الخادم ينسق حالة المباراة في الألعاب الجماعية عبر الإنترنت","text":"ترسل أجهزة اللاعبين بيانات عن أفعالهم إلى الخادم، ثم يعالج الخادم الحالة المشتركة ويرسل تحديثات إلى الأجهزة الأخرى. تساعد هذه العملية على إبقاء اللاعبين داخل المباراة على حالة متقاربة.","hashtags":["#Shorts","#ألعاب","#شبكات"]},
    {"search":"game animation motion capture suit","fallback_searches":["motion capture animation","game character mocap"],"title":"التقاط الحركة يحول حركات الجسم إلى بيانات تستخدم في الرسوم","text":"تستخدم أنظمة التقاط الحركة حساسات أو كاميرات لتسجيل مواقع أجزاء الجسم أثناء الحركة. يمكن تحويل هذه البيانات إلى حركات لشخصية رقمية داخل لعبة أو مشهد ثلاثي الأبعاد.","hashtags":["#Shorts","#ألعاب","#رسوم"]},
    {"search":"game audio spatial sound headphones","fallback_searches":["spatial audio gaming","3d game sound"],"title":"الصوت المكاني يحاكي اتجاه وصول الصوت داخل اللعبة","text":"تعالج بعض الألعاب الصوت بحيث يبدو للمستمع أن المؤثر يأتي من اتجاه معين. تعتمد الطريقة على اختلافات التوقيت والشدة بين الأذنين لإنتاج إحساس بالموقع.","hashtags":["#Shorts","#ألعاب","#صوت"]},
    {"search":"gaming pc liquid cooling loop","fallback_searches":["liquid cooling computer","PC cooling system"],"title":"التبريد السائل ينقل الحرارة من المعالج إلى المشعاع","text":"في أنظمة التبريد السائل تنتقل الحرارة من المعالج إلى سائل داخل كتلة تبريد، ثم يتحرك السائل إلى مشعاع يبدد الحرارة إلى الهواء. بعدها يعود السائل لإعادة الدورة.","hashtags":["#Shorts","#تقنية","#حاسوب"]},
    {"search":"game ray tracing graphics","fallback_searches":["ray tracing gaming","real time graphics"],"title":"تتبع الأشعة يحاكي مسارات الضوء لإظهار انعكاسات وإضاءة أكثر تفصيلًا","text":"تتبع الأشعة خوارزمية تحاكي مسار أشعة الضوء من المشهد إلى الكاميرا أو العكس. يمكن استخدامها لحساب الانعكاسات والظلال وبعض تأثيرات الإضاءة بصورة أكثر تفصيلًا.","hashtags":["#Shorts","#ألعاب","#تقنية"]},
    {"search":"game artificial intelligence pathfinding","fallback_searches":["game pathfinding ai","NPC navigation"],"title":"خوارزمية البحث عن المسار تساعد الشخصية الرقمية على الوصول إلى هدفها","text":"تستخدم الألعاب خوارزميات للبحث عن طريق مناسب بين نقطة البداية والهدف. تعتمد الخوارزمية على شكل البيئة والعوائق والقواعد التي يحددها مطور اللعبة.","hashtags":["#Shorts","#ألعاب","#برمجة"]},
    {"search":"game level lighting design","fallback_searches":["video game lighting","game environment lighting"],"title":"الإضاءة داخل اللعبة تساعد على توضيح العمق واتجاه المشهد","text":"تستخدم الإضاءة الرقمية لإظهار شكل الأجسام ومواقعها وإضافة إحساس بالعمق. ويمكن تغيير شدة الضوء ولونه واتجاهه بحسب تصميم المرحلة.","hashtags":["#Shorts","#ألعاب","#رسوم"]},
    {"search":"game inventory system interface","fallback_searches":["game inventory UI","video game interface"],"title":"واجهة اللعبة تحول البيانات المعقدة إلى عناصر يمكن للاعب فهمها بسرعة","text":"تعرض واجهة المستخدم معلومات مثل الأدوات والمهام والموارد بطريقة منظمة. يختار المصمم مواقع الأيقونات والنصوص والألوان بحيث يستطيع اللاعب الوصول إلى المعلومة أثناء اللعب.","hashtags":["#Shorts","#ألعاب","#تصميم"]},
    {"search":"game controller haptic vibration","fallback_searches":["haptic feedback gaming","controller vibration"],"title":"الاهتزاز في يد التحكم يحول بعض أحداث اللعبة إلى إحساس ملموس","text":"تحتوي بعض أيدي التحكم على محركات صغيرة تولد اهتزازات بدرجات مختلفة. يرسل الجهاز أوامر لهذه المحركات عندما تحدث أحداث معينة داخل اللعبة.","hashtags":["#Shorts","#ألعاب","#تقنية"]},
])


# =========================================================
# EXPANDED CONTENT BANK
# =========================================================
# Added because the original 152-topic pool has already been consumed.
# These topics are intentionally distinct from the original pool and remain
# inside the channel's approved football / science / engineering / gaming scope.
EXTRA_TOPIC_DATA = [
    # -------------------------
    # Football
    # -------------------------
    ("football offside line technology", "تقنية خط التسلل تعتمد على تحديد مواقع اللاعبين لحظة تمرير الكرة", "تحديد التسلل يحتاج إلى معرفة موقع اللاعب وموقع الكرة في اللحظة التي يمرر فيها زميله الكرة. تستخدم أنظمة التحليل الحديثة بيانات الكاميرات لتحديد هذه اللحظة بدقة أكبر.", "#كرة_القدم"),
    ("football corner kick tactics", "الركلة الركنية يمكن أن تتحول إلى فرصة مصممة مسبقًا", "لا تُنفذ الركلات الركنية دائمًا بطريقة عشوائية. يتدرب الفريق على تحركات محددة للاعبين وطرق مختلفة لإرسال الكرة إلى مناطق يمكن استغلالها.", "#كرة_القدم"),
    ("football first touch control", "اللمسة الأولى تحدد سرعة الهجمة", "عندما يستقبل اللاعب الكرة، يمكن أن تدفعها لمسته الأولى نحو المساحة التي يريد التحرك إليها. اللمسة الجيدة تقلل الوقت المطلوب للسيطرة على الكرة والاستعداد للحركة التالية.", "#كرة_القدم"),
    ("football weak foot training", "تدريب القدم غير المفضلة يوسع خيارات اللاعب", "اللاعب الذي يستطيع استخدام القدمين في التمرير والتسديد يملك خيارات أكثر أثناء اللعب. لذلك تتضمن التدريبات تكرار الحركات بالقدم غير المفضلة لتحسين التحكم والتنسيق.", "#كرة_القدم"),
    ("football pressing trigger", "الضغط الجماعي يبدأ أحيانًا من إشارة واحدة", "قد يبدأ الضغط عندما يستلم المدافع الكرة بزاوية صعبة أو عندما يمرر لاعب الخصم تمريرة بطيئة. يتحرك اللاعبون بعدها بسرعة لإغلاق الخيارات القريبة.", "#كرة_القدم"),
    ("football defensive body position", "وضعية جسم المدافع تساعده على توجيه المهاجم", "لا يواجه المدافع المهاجم دائمًا بشكل مباشر. تغيير زاوية الوقوف يمكن أن يغلق مسارًا ويجبر المهاجم على التحرك نحو منطقة يفضلها الفريق الدفاعي.", "#كرة_القدم"),
    ("football through ball timing", "التمريرة البينية تعتمد على التوقيت أكثر من القوة", "تنجح التمريرة البينية عندما تصل الكرة إلى المساحة في اللحظة التي يبدأ فيها المهاجم انطلاقته. إذا وصلت مبكرًا أو متأخرة فقد تضيع المساحة حتى لو كانت التمريرة قوية.", "#كرة_القدم"),
    ("football goalkeeper positioning", "مكان وقوف الحارس يغيّر زاوية التسديد", "تحرك الحارس خطوة أو خطوتين يمكن أن يقلل المساحة المتاحة أمام المهاجم. لذلك يدرس الحراس موقع الكرة والمدافعين والمرمى قبل اتخاذ موضعهم.", "#كرة_القدم"),
    ("football ball pressure effect", "ضغط الهواء داخل الكرة يؤثر في ارتدادها", "تغيير ضغط الهواء داخل الكرة يغير طريقة ارتدادها واستجابتها للقدم والأرض. لذلك يجب أن تكون الكرة ضمن مواصفات محددة قبل المباريات الرسمية.", "#كرة_القدم"),
    ("football grass cutting pattern", "طريقة قص عشب الملعب قد تغير شكل الخطوط الظاهرة", "تظهر بعض ملاعب كرة القدم بخطوط فاتحة وداكنة متبادلة بسبب اتجاه قص العشب. الاختلاف البصري لا يعني بالضرورة اختلافًا في لون العشب نفسه.", "#كرة_القدم"),
    ("football substitute warmup", "البديل يحتاج إلى الاستعداد قبل دخوله الملعب", "اللاعب البديل لا ينتظر دائمًا حتى لحظة التبديل. يبدأ الإحماء قبل الدخول حتى يكون مستعدًا للانتقال مباشرة إلى إيقاع المباراة.", "#كرة_القدم"),
    ("football acceleration mechanics", "أول خطوات الانطلاق تختلف عن الجري بأقصى سرعة", "في بداية الانطلاق يميل اللاعب إلى وضعية تساعده على دفع الجسم إلى الأمام. ومع زيادة السرعة تتغير وضعية الجسم وطول الخطوة تدريجيًا.", "#كرة_القدم"),
    ("football passing lane", "إغلاق ممر التمرير قد يكون أهم من مطاردة حامل الكرة", "يحاول المدافع أحيانًا قطع المسار المتوقع للتمريرة بدل الاندفاع نحو اللاعب مباشرة. هذا يقلل الخيارات المتاحة ويجعل بناء الهجمة أصعب.", "#كرة_القدم"),
    ("football wall free kick", "الجدار الدفاعي يهدف إلى تقليل جزء من زاوية التسديد", "يقف اللاعبون في الجدار لحجب جزء من المرمى عن منفذ الركلة الحرة. ويختار الحارس موقعه بحيث يغطي الجزء الآخر من الزاوية.", "#كرة_القدم"),
    ("football chip pass", "التمريرة العالية القصيرة تتجاوز المدافع بطريقة مختلفة", "عندما يرفع اللاعب الكرة فوق مدافع قريب بدل تمريرها أرضية، يستطيع تجاوز خط الضغط. يعتمد نجاح الحركة على ارتفاع الكرة وسرعتها وموقع الزميل.", "#كرة_القدم"),
    ("football dummy run", "الركضة الوهمية قد تفتح مساحة من دون لمس الكرة", "يمكن للاعب أن يتحرك باتجاه معين ليجذب مدافعًا ثم يترك المساحة لزميله. هذه الحركة لا تحتاج إلى لمس الكرة لكنها قد تغير شكل الدفاع.", "#كرة_القدم"),
    ("football goalkeeper distribution", "تمريرة الحارس قد تبدأ هجمة كاملة", "بعد الاستحواذ على الكرة يستطيع الحارس اختيار تمريرة قصيرة أو طويلة بحسب شكل الفريق. القرار يحدد أين تبدأ المرحلة التالية من الهجمة.", "#كرة_القدم"),
    ("football match ball panel design", "ألواح الكرة تؤثر في طريقة تفاعلها مع الهواء", "تصميم سطح الكرة وعدد الألواح وشكلها يغير خصائصها الهوائية. لهذا تخضع الكرات الحديثة لاختبارات دقيقة قبل اعتمادها للمنافسات.", "#كرة_القدم"),
    ("football stadium drainage", "نظام تصريف الملعب يعمل تحت العشب", "تحت بعض الملاعب توجد طبقات وأنابيب تساعد على تصريف المياه بعيدًا عن سطح اللعب. الهدف هو تقليل تجمع المياه والحفاظ على قابلية الملعب للاستخدام.", "#كرة_القدم"),
    ("football player scanning", "النظر حول اللاعب قبل استلام الكرة يقلل المفاجآت", "يفحص اللاعب محيطه قبل وصول الكرة ليعرف مواقع الزملاء والمنافسين. هذه المعلومة تساعده على اتخاذ القرار بسرعة بعد الاستلام.", "#كرة_القدم"),
    ("football one touch passing", "التمرير بلمسة واحدة يقلل زمن احتفاظ الفريق بالكرة", "عندما يمرر اللاعب الكرة مباشرة بعد استلامها، تقل فرصة الخصم في الاقتراب منه. نجاح هذا الأسلوب يحتاج إلى معرفة مسبقة بمواقع الزملاء.", "#كرة_القدم"),
    ("football crossing trajectory", "ارتفاع العرضية يحدد نوع الفرصة داخل المنطقة", "يمكن للعرضية أن تصل منخفضة أو مرتفعة أو في منطقة متوسطة. يختار اللاعب مسارها بحسب تحركات المهاجمين وموقع المدافعين.", "#كرة_القدم"),
    ("football recovery run", "العودة السريعة بعد فقدان الكرة جزء من العمل الدفاعي", "بعد فقدان الاستحواذ يبدأ بعض اللاعبين بالعودة نحو مواقعهم بدل متابعة الهجمة. سرعة هذه العودة تساعد الفريق على استعادة شكله الدفاعي.", "#كرة_القدم"),
    ("football touchline coach communication", "موقع الجهاز الفني قرب الخط يساعد على التواصل أثناء اللعب", "يقف الجهاز الفني في منطقة محددة تسمح له بمتابعة المباراة والتواصل مع اللاعبين في حدود قوانين المنافسة. هذه المنطقة جزء من تنظيم الملعب.", "#كرة_القدم"),
    ("football referee positioning", "الحكم يختار مساره لتجنب الاصطدام باللعب", "يتحرك الحكم باستمرار مع تغير موقع الكرة. اختيار مسار مناسب يساعده على رؤية الأحداث ويقلل احتمالية وجوده في طريق اللاعبين.", "#كرة_القدم"),
    ("football goal net tension", "شد شبكة المرمى يغير شكلها عند دخول الكرة", "تثبت شبكة المرمى بطريقة تسمح لها بامتصاص جزء من حركة الكرة بعد دخولها. مقدار الشد وطريقة التثبيت يؤثران في شكل الشبكة عند الاصطدام.", "#كرة_القدم"),
    ("football shin guard protection", "واقي الساق يوزع جزءًا من قوة الاصطدام", "يضع اللاعب واقيًا أمام عظمة الساق لتقليل أثر بعض الاصطدامات. تصميمه يجمع بين الخفة والقدرة على امتصاص جزء من الطاقة.", "#كرة_القدم"),
    ("football training cones spacing", "المسافة بين أقماع التدريب تغير صعوبة التمرين", "عندما تقل المسافة بين الأقماع يصبح على اللاعب تغيير اتجاهه بسرعة أكبر. لذلك يضبط المدرب المسافات بحسب المهارة التي يريد تدريبها.", "#كرة_القدم"),
    ("football tactical width", "توسيع الملعب أفقيًا يمكن أن يفتح ممرات في الوسط", "عندما ينتشر اللاعبون على عرض أكبر، يضطر الدفاع إلى تغطية مساحة أوسع. قد ينتج عن ذلك فراغات يمكن استغلالها في مناطق أخرى.", "#كرة_القدم"),
    ("football counter attack transition", "التحول السريع من الدفاع إلى الهجوم يستغل لحظة عدم التنظيم", "بعد استعادة الكرة يكون بعض لاعبي الخصم خارج مراكزهم الهجومية. سرعة التمرير والتحرك في هذه اللحظة قد تخلق فرصة قبل اكتمال العودة الدفاعية.", "#كرة_القدم"),

    # -------------------------
    # Science
    # -------------------------
    ("double rainbow optics", "قوس قزح مزدوج ينتج من مسار مختلف للضوء داخل قطرات الماء", "عندما يمر ضوء الشمس داخل قطرات الماء يمكن أن ينعكس وينكسر بطرق محددة. في بعض الظروف ينتج مساران مختلفان للضوء فيظهر قوس ثانوي أضعف.", "#علوم"),
    ("soap bubble colors optics", "ألوان فقاعات الصابون ناتجة عن تداخل الضوء", "الغشاء الرقيق لفقاعة الصابون يعكس الضوء من سطحين قريبين جدًا. تداخل الموجات المنعكسة يجعل بعض الألوان أقوى من غيرها بحسب سماكة الغشاء.", "#علوم"),
    ("sound echo reflection", "الصدى يحدث عندما تنعكس الموجات الصوتية وتعود إلى المستمع", "عندما تصل الموجة الصوتية إلى سطح مناسب قد تنعكس وتعود. إذا كان الفاصل الزمني كافيًا بين الصوت الأصلي والانعكاس، يسمع الإنسان صوتًا منفصلًا يسمى الصدى.", "#علوم"),
    ("doppler effect ambulance sound", "تغير نغمة الصوت أثناء اقتراب المصدر وابتعاده مثال على تأثير دوبلر", "عندما يتحرك مصدر الصوت بالنسبة إلى المستمع تتغير المسافة بين جبهات الموجة. لذلك تبدو النغمة مختلفة أثناء الاقتراب مقارنة بالابتعاد.", "#علوم"),
    ("static electricity balloon hair", "الكهرباء الساكنة يمكن أن تجعل الشعر ينجذب إلى جسم مشحون", "عند احتكاك مادتين يمكن أن تنتقل بعض الإلكترونات بينهما. ينتج عن ذلك شحنة كهربائية ساكنة قد تسبب تجاذبًا أو تنافرًا بين الأجسام.", "#علوم"),
    ("surface area ice melting", "زيادة مساحة سطح الجليد تغير سرعة انتقال الحرارة إليه", "الجسم الذي يملك مساحة سطح أكبر بالنسبة إلى كتلته يستطيع تبادل الحرارة مع محيطه بصورة أسرع. لذلك تؤثر هيئة قطعة الجليد في معدل ذوبانها.", "#علوم"),
    ("metal thermal expansion", "المعادن تتمدد قليلًا عندما ترتفع درجة حرارتها", "مع ارتفاع درجة الحرارة تزداد حركة الذرات داخل المادة، ويؤدي ذلك إلى زيادة صغيرة في الأبعاد. يأخذ المهندسون هذا التمدد في الاعتبار عند تصميم بعض المنشآت.", "#علوم"),
    ("boiling water pressure", "درجة غليان الماء تتغير عندما يتغير الضغط", "يبدأ السائل بالغليان عندما يصبح ضغط بخاره مناسبًا للضغط المحيط. لذلك يمكن أن تختلف درجة الغليان مع اختلاف الضغط الجوي أو داخل وعاء مضغوط.", "#علوم"),
    ("capillary action paper towel", "الماء يستطيع التحرك داخل الألياف الضيقة بفعل الخاصية الشعرية", "تجذب الأسطح الداخلية للألياف جزيئات الماء، وتساعد قوى التماسك بين الجزيئات على استمرار الحركة. لذلك ينتشر الماء داخل الورق حتى دون دفع مباشر.", "#علوم"),
    ("leaf stomata gas exchange", "النباتات تستخدم فتحات صغيرة في الأوراق لتبادل الغازات", "تحتوي الأوراق على فتحات تسمى الثغور تسمح بدخول ثاني أكسيد الكربون وخروج بخار الماء والغازات الأخرى. ويمكن للنبات التحكم في درجة انفتاحها.", "#علوم"),
    ("venus flytrap movement", "نبات صائد الذباب يغلق أوراقه استجابة لمنبه ميكانيكي", "تستجيب أوراق نبات صائد الذباب للمس المتكرر لشعيرات حسية محددة. يؤدي ذلك إلى تغير سريع في ضغط الخلايا وشكل الورقة، فتغلق على الحشرة.", "#علوم"),
    ("gecko feet adhesion", "أقدام الوزغ تعتمد على تراكيب مجهرية تساعدها على الالتصاق بالأسطح", "تحتوي أقدام الوزغ على شعيرات دقيقة جدًا تزيد مساحة التلامس مع السطح. هذه البنية تسمح بقوى تجاذب ضعيفة كثيرة تتجمع لتنتج التصاقًا ملحوظًا.", "#علوم"),
    ("owl silent flight feathers", "بنية ريش البومة تساعد على تقليل ضوضاء الطيران", "تتميز بعض ريشات البومة بحواف وبنية سطحية تساعد على تقليل الاضطرابات الهوائية. لهذا تستطيع بعض الأنواع الطيران بهدوء نسبي أثناء الصيد.", "#علوم"),
    ("whale communication low frequency", "بعض الحيتان تستخدم أصواتًا منخفضة التردد للتواصل لمسافات بعيدة", "يمكن للموجات الصوتية منخفضة التردد أن تنتقل عبر الماء لمسافات طويلة. تستفيد بعض الحيتان من هذه الخصائص في التواصل بين أفراد النوع.", "#علوم"),
    ("dolphin echolocation", "الدلافين تستخدم الصدى لتقدير موقع الأجسام تحت الماء", "تطلق الدلافين أصواتًا وتستقبل صداها بعد انعكاسها عن الأجسام. تساعد الفروق في زمن وصول الصدى وشدته على تكوين معلومات عن البيئة.", "#علوم"),
    ("bee compound eyes", "عين الحشرة المركبة تتكون من وحدات بصرية كثيرة", "العين المركبة تحتوي على عدد كبير من الوحدات الصغيرة التي تستقبل الضوء. هذا التصميم يمنح الحشرة مجال رؤية واسعًا وطريقة مختلفة لمعالجة الحركة.", "#علوم"),
    ("polarized light sunglasses", "الضوء المستقطب يمكن تقليل بعض انعكاساته باستخدام فلتر مناسب", "تحتوي بعض المرشحات البصرية على اتجاهات محددة تسمح بمرور جزء من الضوء وتقلل جزءًا آخر. يستخدم هذا المبدأ في بعض النظارات والأدوات البصرية.", "#علوم"),
    ("prism light spectrum", "المنشور الزجاجي يستطيع فصل الضوء الأبيض إلى ألوانه", "ينكسر كل لون من ألوان الضوء بزاوية مختلفة قليلًا عند مروره داخل مادة شفافة. لذلك يمكن للمنشور فصل الضوء الأبيض إلى نطاق من الألوان المرئية.", "#علوم"),
    ("infrared remote control", "جهاز التحكم عن بعد يرسل أوامر باستخدام ضوء تحت أحمر غير مرئي للعين", "تستخدم بعض أجهزة التحكم صمامًا يرسل نبضات من الأشعة تحت الحمراء. يلتقطها مستقبل الجهاز الآخر ويفسر نمط النبضات كأمر محدد.", "#علوم"),
    ("ultraviolet sunscreen absorption", "بعض المواد الواقية تمتص أو تعكس جزءًا من الأشعة فوق البنفسجية", "الأشعة فوق البنفسجية تحمل طاقة أعلى من الضوء المرئي. تحتوي بعض المواد الواقية على مركبات تقلل وصول جزء من هذه الأشعة إلى السطح.", "#علوم"),
    ("ferrofluid magnetic field", "السائل المغناطيسي يغير شكله عند وجود مجال مغناطيسي", "تحتوي السوائل المغناطيسية على جسيمات دقيقة تستجيب للمجال المغناطيسي. عند تقريب مغناطيس يمكن أن تظهر على سطح السائل أشكال مدببة مميزة.", "#علوم"),
    ("liquid surface tension needle", "التوتر السطحي يمكن أن يدعم أجسامًا صغيرة على سطح الماء", "تجعل قوى التجاذب بين جزيئات الماء سطح السائل يتصرف كغشاء مرن نسبيًا. لهذا يمكن لجسم صغير جدًا أن يبقى على السطح إذا وُضع بعناية.", "#علوم"),
    ("density oil water separation", "الزيت والماء ينفصلان لأن خصائصهما مختلفة", "لا يمتزج الزيت بالماء بسهولة بسبب اختلاف البنية الجزيئية، كما أن كثافة الزيت في العادة أقل من كثافة الماء. لذلك يتجمع الزيت في طبقة منفصلة أعلى الماء.", "#علوم"),
    ("crystal growth salt", "البلورات تتشكل عندما تنتظم الجسيمات في بنية متكررة", "عندما يتبخر الماء من محلول ملحي يمكن أن تزداد كمية الملح مقارنة بالمذيب. عند الوصول إلى ظروف مناسبة تبدأ الجسيمات بالانتظام وتكوين بلورات.", "#علوم"),
    ("magnetic levitation superconductivity", "بعض المواد فائقة التوصيل تستطيع إظهار تأثيرات مغناطيسية غير عادية", "عند تبريد بعض المواد إلى درجات منخفضة جدًا تتغير خصائصها الكهربائية والمغناطيسية. يمكن في تجارب محددة أن تظهر حالة تساعد على تثبيت جسم مغناطيسي فوقها.", "#علوم"),
    ("coral fluorescence underwater", "بعض الشعاب المرجانية تظهر ألوانًا مضيئة تحت ضوء مناسب", "تحتوي بعض الكائنات البحرية على بروتينات وأصباغ تتفاعل مع الضوء بطرق مختلفة. يمكن أن يؤدي ذلك إلى ظاهرة التألق التي تظهر بوضوح تحت أطوال موجية معينة.", "#علوم"),
    ("penguin feathers waterproof", "ترتيب الريش والزيوت يساعد بعض الطيور البحرية على مقاومة الماء", "الريش المتداخل مع وجود مواد دهنية على سطحه يقلل وصول الماء إلى الجلد. هذه البنية تساعد الطيور البحرية على الحفاظ على العزل أثناء السباحة.", "#علوم"),
    ("camel nose water conservation", "أنف الجمل يساعد في استعادة جزء من بخار الماء أثناء التنفس", "يمر الهواء داخل ممرات أنفية تساعد على تبادل الحرارة والرطوبة. عند الزفير يمكن أن يحدث تكثف جزئي لبخار الماء، ما يقلل فقده مقارنة بظروف أخرى.", "#علوم"),
    ("spider silk strength", "حرير العنكبوت يجمع بين الخفة والقدرة على تحمل الشد", "تتكون ألياف حرير العنكبوت من بروتينات مرتبة في بنية تمنحها خصائص ميكانيكية مميزة. تختلف خصائص الخيط بحسب نوع العنكبوت ووظيفة الحرير.", "#علوم"),
    ("fire color temperature", "لون اللهب يتأثر بالمواد ودرجة الحرارة وظروف الاحتراق", "لا يرتبط لون اللهب بالحرارة وحدها. نوع المادة الموجودة في اللهب ووجود ذرات أو جزيئات معينة يمكن أن يغير الضوء المنبعث منه.", "#علوم"),

    # -------------------------
    # Engineering / technology
    # -------------------------
    ("robotic arm joint motors", "المحركات في الذراع الروبوتية تتحكم في زوايا المفاصل", "تستخدم الأذرع الروبوتية محركات ومخفضات حركة لتحريك المفاصل إلى زوايا محددة. يتحكم الحاسوب في الحركة بناءً على المهمة المطلوبة وموقع الذراع.", "#هندسة"),
    ("3d printer layer by layer", "الطابعة ثلاثية الأبعاد تبني الجسم طبقة فوق طبقة", "تبدأ الطباعة ثلاثية الأبعاد بنموذج رقمي، ثم يحوله البرنامج إلى طبقات متتابعة. تضيف الطابعة المادة طبقة بعد أخرى حتى يتكون الشكل النهائي.", "#هندسة"),
    ("fiber optic internet light pulses", "الألياف الضوئية تنقل البيانات على شكل نبضات ضوئية", "تنتقل البيانات في كابل الألياف الضوئية عبر نبضات من الضوء داخل ألياف دقيقة. يمكن نقل كميات كبيرة من البيانات لمسافات طويلة مع فقد منخفض نسبيًا.", "#هندسة"),
    ("computer SSD flash memory", "وحدات التخزين الصلبة تحفظ البيانات داخل خلايا ذاكرة إلكترونية", "تستخدم وحدات التخزين الصلبة ذاكرة فلاش لتخزين البيانات دون أجزاء ميكانيكية متحركة. هذا يساعد على سرعة الوصول إلى البيانات ويقلل بعض أنواع الاهتزاز الميكانيكي.", "#تقنية"),
    ("computer CPU transistor", "المعالج الحديث يحتوي على عدد هائل من الترانزستورات", "الترانزستور عنصر إلكتروني يمكن استخدامه للتحكم في مرور الإشارات الكهربائية. تجمع المعالجات أعدادًا ضخمة من هذه العناصر لتنفيذ العمليات الحسابية والمنطقية.", "#تقنية"),
    ("GPU parallel processing", "وحدة معالجة الرسوميات تنفذ عمليات كثيرة بالتوازي", "صممت وحدات معالجة الرسوميات للتعامل بكفاءة مع عدد كبير من العمليات المتشابهة في الوقت نفسه. لهذا تستخدم في الرسوميات وبعض تطبيقات الحوسبة العلمية والذكاء الاصطناعي.", "#تقنية"),
    ("smartphone image stabilization", "تثبيت الصورة يقلل اهتزاز اللقطات أثناء التصوير", "تستخدم بعض الهواتف أنظمة ميكانيكية أو إلكترونية لتعويض حركة اليد أثناء التصوير. الهدف هو إبقاء الصورة أكثر ثباتًا خصوصًا عند استخدام تكبير مرتفع أو تصوير فيديو.", "#تقنية"),
    ("camera rolling shutter", "بعض حساسات الكاميرا تقرأ الصورة على صفوف متتابعة", "عند قراءة صفوف الحساس بالتتابع قد يتحرك الجسم أثناء عملية القراءة. لذلك يمكن أن تظهر الأجسام السريعة مشوهة قليلًا في بعض اللقطات.", "#تقنية"),
    ("battery lithium ion charging", "بطارية الليثيوم أيون تخزن الطاقة عبر حركة الأيونات بين أقطابها", "أثناء الشحن والتفريغ تتحرك أيونات الليثيوم بين مواد الأقطاب عبر الإلكتروليت. تصميم البطارية وإدارتها الحرارية يؤثران في الأداء والعمر.", "#هندسة"),
    ("electric motor electromagnetic force", "المحرك الكهربائي يحول الطاقة الكهربائية إلى حركة دورانية", "ينشأ عزم الدوران في المحرك نتيجة التفاعل بين المجالات المغناطيسية والتيارات الكهربائية. تستخدم هذه الفكرة في محركات الأجهزة والمركبات والآلات.", "#هندسة"),
    ("regenerative braking electric car", "الكبح المتجدد يحول جزءًا من حركة المركبة إلى طاقة كهربائية", "عند التباطؤ يمكن للمحرك الكهربائي أن يعمل بطريقة مختلفة ليولد تيارًا كهربائيًا. تُعاد هذه الطاقة إلى البطارية بدل فقد كل الطاقة الحركية على شكل حرارة.", "#هندسة"),
    ("wind turbine blade aerodynamics", "شكل شفرة توربين الرياح يساعد على تحويل حركة الهواء إلى دوران", "تصمم شفرات توربينات الرياح بحيث تتولد عليها قوى هوائية تدفعها للدوران. تنتقل هذه الحركة عبر منظومة ميكانيكية إلى مولد كهربائي.", "#هندسة"),
    ("solar inverter DC AC", "العاكس يحول كهرباء الألواح الشمسية إلى صيغة مناسبة للشبكة", "تنتج الألواح الشمسية كهرباء على شكل تيار مستمر. يستخدم العاكس إلكترونيات قدرة لتحويلها إلى تيار متناوب وفق خصائص النظام الكهربائي.", "#هندسة"),
    ("hydraulic excavator arm", "الحفارة تستخدم ضغط السائل لتحريك الذراع الثقيلة", "تدفع المضخة سائلًا هيدروليكيًا تحت ضغط إلى أسطوانات تعمل على تحريك الذراع والدلو. يسمح النظام بتوليد قوى كبيرة مع تحكم دقيق نسبيًا.", "#هندسة"),
    ("shock absorber car suspension", "ممتص الصدمات يقلل اهتزاز هيكل السيارة", "يعمل ممتص الصدمات على التحكم في حركة نظام التعليق بعد المطبات والحركات المفاجئة. يقلل ذلك من استمرار الاهتزاز ويحسن استقرار العجلة مع الطريق.", "#هندسة"),
    ("airplane wing lift pressure", "شكل الجناح يساهم في توليد قوة الرفع أثناء الطيران", "عند تحرك الجناح خلال الهواء تتغير الضغوط واتجاهات تدفق الهواء حوله. ينتج عن ذلك قوى هوائية يمكن أن ترفع الطائرة عندما تتوافر الشروط المناسبة.", "#هندسة"),
    ("jet engine compressor turbine", "المحرك النفاث يضغط الهواء ثم يستخدم الطاقة الناتجة لدفع الغازات", "يمر الهواء داخل مراحل من الضاغط قبل وصوله إلى منطقة الاحتراق. بعد الاحتراق تتمدد الغازات وتمر عبر التوربين ثم تخرج بسرعة عالية لتوليد الدفع.", "#هندسة"),
    ("drone flight controller sensors", "الطائرة المسيرة تستخدم حساسات للحفاظ على استقرارها", "تقرأ وحدة التحكم بيانات من حساسات مثل الجيروسكوب ومقياس التسارع. تستخدم هذه البيانات لتعديل سرعة المحركات والمحافظة على اتجاه الطائرة وارتفاعها.", "#تقنية"),
    ("robot vacuum lidar mapping", "بعض المكانس الروبوتية تبني تصورًا للمكان أثناء الحركة", "يمكن لبعض المكانس استخدام مستشعرات ضوئية لقياس المسافات وإنشاء تصور تقريبي للغرف. تستخدم هذه المعلومات لتخطيط المسار وتقليل تكرار المرور في المناطق نفسها.", "#تقنية"),
    ("3d scanner depth camera", "كاميرا العمق تقيس المسافة بدل تسجيل اللون فقط", "تستخدم بعض أنظمة الرؤية تقنيات تقيس زمن الضوء أو نمطًا ضوئيًا لتقدير المسافة إلى الأجسام. يمكن تحويل هذه القياسات إلى معلومات ثلاثية الأبعاد.", "#تقنية"),
    ("noise cancelling headphones microphones", "سماعات إلغاء الضوضاء تستخدم ميكروفونات لمراقبة الصوت المحيط", "تلتقط الميكروفونات الصوت المحيط ثم تولد الدوائر الإلكترونية إشارة مضادة تساعد على تقليل بعض الضوضاء. تكون الفعالية أفضل مع الأصوات المستمرة نسبيًا.", "#تقنية"),
    ("computer heat pipe cooling", "أنبوب الحرارة ينقل الحرارة داخل بعض أنظمة التبريد الإلكترونية", "يحتوي أنبوب الحرارة على سائل يعمل داخل بنية محكمة. يتبخر السائل قرب المصدر الساخن ثم يتكثف في منطقة أبرد، فتنتقل الحرارة بكفاءة إلى المشعاع.", "#هندسة"),
    ("semiconductor photolithography", "تصنيع الشرائح الإلكترونية يعتمد على أنماط دقيقة جدًا على سطح السيليكون", "تستخدم عمليات التصنيع الضوئي قناعًا ومصدر ضوء ومواد حساسة للضوء لتشكيل أنماط دقيقة. تتكرر العملية لبناء طبقات الدارات الإلكترونية.", "#تقنية"),
    ("ethernet packet data", "البيانات في الشبكات تقسم إلى حزم صغيرة أثناء النقل", "تُقسم البيانات إلى وحدات يمكن للشبكة نقلها والتعامل معها. تحتوي الحزم على معلومات تساعد الأجهزة على معرفة المصدر والوجهة وترتيب البيانات.", "#تقنية"),
    ("wifi radio channel", "شبكات الواي فاي تنقل البيانات عبر موجات راديوية", "يرسل جهاز الواي فاي البيانات على ترددات راديوية محددة. تؤثر المسافة والعوائق والتداخل بين الشبكات في جودة الإشارة وسرعة الاتصال.", "#تقنية"),
    ("bluetooth low energy packets", "بلوتوث منخفض الطاقة صمم لإرسال كميات صغيرة من البيانات باستهلاك محدود", "تستخدم أجهزة كثيرة بلوتوث منخفض الطاقة لإرسال معلومات قصيرة على فترات متباعدة. يساعد تقليل وقت الإرسال على خفض استهلاك البطارية في الأجهزة الصغيرة.", "#تقنية"),
    ("mechanical gear ratio", "نسبة التروس تغير العلاقة بين السرعة والعزم", "عند توصيل تروس بأحجام مختلفة يمكن تغيير سرعة الدوران أو العزم المنقول. تستخدم هذه الفكرة في الآلات والمركبات وأنظمة الحركة المختلفة.", "#هندسة"),
    ("bearing friction machine", "المحامل تقلل الاحتكاك بين الأجزاء الدوارة", "تسمح المحامل للأجزاء بالدوران مع تقليل الاحتكاك مقارنة بالتلامس المباشر. توجد منها أنواع تعتمد على كرات أو أسطوانات أو طبقات مخصصة للحركة.", "#هندسة"),
    ("carbon fiber composite", "ألياف الكربون تستخدم لتقوية مواد مركبة مع الحفاظ على وزن منخفض", "تجمع المواد المركبة بين ألياف قوية ومادة رابطة. تمنح ألياف الكربون نسبة عالية من القوة إلى الوزن في تطبيقات هندسية متعددة.", "#هندسة"),

    # -------------------------
    # Electronic games / gaming
    # -------------------------
    ("game texture compression", "ضغط الخامات يقلل حجم ملفات الألعاب", "الخامات هي الصور المستخدمة على أسطح الأجسام داخل اللعبة. يمكن ضغطها بطرق مختلفة لتقليل مساحة التخزين والذاكرة المطلوبة مع الحفاظ على جودة بصرية مناسبة.", "#ألعاب"),
    ("game level streaming", "بعض الألعاب تحمل أجزاء العالم تدريجيًا أثناء الحركة", "بدل تحميل العالم الكامل دفعة واحدة، يمكن للمحرك تحميل المناطق القريبة من اللاعب وتفريغ المناطق البعيدة. يساعد ذلك على التعامل مع عوالم كبيرة ضمن ذاكرة محدودة.", "#ألعاب"),
    ("game save checkpoint", "نقاط الحفظ التلقائي تقلل الحاجة إلى إعادة مراحل طويلة", "تسجل بعض الألعاب تقدم اللاعب عند نقاط محددة أو بعد أحداث مهمة. إذا توقف اللعب يمكن العودة إلى آخر نقطة محفوظة بدل إعادة كل ما سبق.", "#ألعاب"),
    ("game physics collision detection", "محرك اللعبة يحدد متى تتلامس الأجسام الرقمية", "تستخدم محركات الألعاب أنظمة حسابية لاكتشاف تقاطع الأجسام وحدودها. بعدها يمكن تطبيق قواعد الحركة والارتداد أو التفاعل المناسب.", "#ألعاب"),
    ("game frame rate input latency", "ارتفاع معدل الإطارات قد يجعل الاستجابة البصرية أكثر سلاسة", "معدل الإطارات يحدد عدد الصور التي يعرضها النظام في الثانية. تؤثر سرعة المعالجة والشاشة وتأخر الإدخال أيضًا في الإحساس بسرعة الاستجابة أثناء اللعب.", "#ألعاب"),
    ("game shader materials", "التظليل يحدد كيف يتفاعل سطح الجسم الرقمي مع الضوء", "تستخدم برامج التظليل معلومات عن السطح والضوء والكاميرا لحساب المظهر النهائي للبكسلات. يمكن أن تنتج عنها أسطح لامعة أو خشنة أو شفافة بحسب الإعدادات.", "#ألعاب"),
    ("game ambient occlusion", "الإضاءة المحيطة تساعد على إظهار مناطق التقاء الأجسام", "تحاول بعض تقنيات الإضاءة تقدير المناطق التي يصل إليها الضوء بشكل أقل بسبب قرب الأجسام من بعضها. يساعد ذلك على زيادة الإحساس بالعمق في المشهد.", "#ألعاب"),
    ("game level of detail", "تقنية مستوى التفاصيل تستخدم نماذج أبسط للأجسام البعيدة", "لا تحتاج الأجسام البعيدة إلى العدد نفسه من التفاصيل المستخدمة للأجسام القريبة. يمكن للمحرك تبديل النموذج أو مستوى التفاصيل بحسب المسافة لتقليل الحمل الحسابي.", "#ألعاب"),
    ("game texture mipmaps", "الخرائط المتدرجة تساعد على عرض الخامات البعيدة بكفاءة", "تخزن بعض الألعاب نسخًا أصغر من الخامة نفسها لاستخدامها عندما يظهر الجسم بعيدًا. يقلل ذلك من التشويش وبعض عمليات القراءة غير الضرورية من الذاكرة.", "#ألعاب"),
    ("game particle system", "نظام الجسيمات يصنع تأثيرات مثل الدخان والشرر", "بدل بناء كل ذرة دخان كجسم مستقل معقد، تستخدم الألعاب أعدادًا كبيرة من الجسيمات البسيطة التي تتحرك وفق قواعد محددة. يمكن أن تنتج عنها مؤثرات بصرية كثيرة.", "#ألعاب"),
    ("game ragdoll physics", "نظام الحركة الفيزيائية يجعل الشخصية تتفاعل مع القوى بطريقة ديناميكية", "يمكن لمحرك اللعبة استخدام مفاصل وأجسام فيزيائية لمحاكاة حركة شخصية بعد فقدان التحكم فيها. تختلف النتيجة بحسب الكتل والقيود والقوى المطبقة.", "#ألعاب"),
    ("game animation blending", "مزج الحركات يجعل انتقال الشخصية بين الحركات أكثر سلاسة", "قد يحتاج اللاعب إلى الانتقال بسرعة من المشي إلى الركض أو التوقف. يمزج محرك اللعبة بين حالات الحركة بدل الانتقال الحاد من حركة إلى أخرى.", "#ألعاب"),
    ("game inverse kinematics", "الحركية العكسية تساعد القدم على الوصول إلى سطح مناسب أثناء الحركة", "في بعض الألعاب تحسب الخوارزمية وضع المفاصل اللازمة لوضع اليد أو القدم في نقطة محددة. يساعد ذلك على جعل الحركة أكثر توافقًا مع البيئة.", "#ألعاب"),
    ("game camera field of view", "مجال رؤية الكاميرا يغير مقدار المشهد الظاهر على الشاشة", "عندما يتغير مجال الرؤية يظهر جزء أوسع أو أضيق من البيئة. يستخدم المصممون هذه القيمة للتأثير في الإحساس بالمسافة وحجم المشهد.", "#ألعاب"),
    ("game resolution scaling", "تغيير دقة العرض ديناميكيًا يمكن أن يساعد على تثبيت الأداء", "يمكن لبعض المحركات خفض دقة الصورة الداخلية عند ارتفاع الحمل الحسابي ثم رفعها عندما تتوفر قدرة معالجة أكبر. الهدف هو الموازنة بين جودة الصورة وسلاسة العرض.", "#ألعاب"),
    ("game shader compilation stutter", "تجهيز بعض برامج التظليل مسبقًا قد يقلل التقطعات أثناء اللعب", "عند استخدام مؤثرات رسومية جديدة قد يحتاج الجهاز إلى تجهيز برامج صغيرة لمعالجة الصورة. إذا حدث ذلك أثناء اللعب مباشرة فقد يظهر تقطع مؤقت، لذلك تستخدم بعض الأنظمة طرقًا للتجهيز المسبق.", "#ألعاب"),
    ("game audio occlusion", "اللعبة تستطيع محاكاة تغير الصوت عندما يوجد حاجز بين المصدر واللاعب", "يمكن لمحرك الصوت خفض بعض الترددات أو مستوى الصوت عندما يكون مصدره خلف جدار أو جسم. يعطي ذلك إحساسًا بأن البيئة تؤثر في انتقال الصوت.", "#ألعاب"),
    ("game dynamic weather system", "أنظمة الطقس الرقمية تغير الإضاءة والمؤثرات أثناء اللعب", "يمكن لمحرك اللعبة تغيير السحب والضباب والمطر والإضاءة وفق نظام زمني أو أحداث محددة. هذه العناصر تجعل البيئة تبدو متغيرة بدل أن تبقى ثابتة.", "#ألعاب"),
    ("game procedural generation", "التوليد الإجرائي ينشئ أجزاء من العالم باستخدام قواعد حسابية", "بدل تصميم كل عنصر يدويًا، يمكن للمطور وضع قواعد تنتج تضاريس أو غرفًا أو عناصر بطريقة حسابية. يساعد ذلك على إنشاء محتوى متنوع مع تقليل العمل اليدوي لبعض الأجزاء.", "#ألعاب"),
    ("game navigation mesh", "شبكة التنقل تحدد المناطق التي تستطيع الشخصيات الرقمية التحرك فيها", "ينشئ محرك اللعبة تمثيلًا مبسطًا للأسطح القابلة للمشي. تستخدم الشخصيات هذه الشبكة للبحث عن مسارات تتجنب العوائق.", "#ألعاب"),
    ("game input polling", "الألعاب تقرأ حالة أزرار التحكم باستمرار أثناء اللعب", "يحتاج محرك اللعبة إلى معرفة التغيرات في أزرار التحكم وحركة العصا والماوس. طريقة قراءة هذه المدخلات تؤثر في توقيت استجابة اللعبة للأوامر.", "#ألعاب"),
    ("game server tick rate", "الخادم يحدث حالة اللعبة على فترات زمنية متكررة", "في الألعاب المتصلة يكرر الخادم تحديث حالة اللاعبين والأحداث وفق معدل محدد. زيادة عدد التحديثات قد تعطي معلومات أكثر دقة، لكنها تحتاج إلى موارد شبكة ومعالجة أكبر.", "#ألعاب"),
    ("game interpolation network movement", "الاستيفاء يجعل حركة اللاعبين على الشبكة تبدو أكثر سلاسة", "قد تصل بيانات حركة اللاعب على شكل تحديثات منفصلة. يعرض العميل انتقالًا بين هذه النقاط بدل القفز مباشرة من موقع إلى آخر.", "#ألعاب"),
    ("game asset streaming storage", "بث ملفات اللعبة من وحدة التخزين يقلل الحاجة إلى تحميل كل شيء في الذاكرة", "تقرأ اللعبة الأصول المطلوبة مثل الأصوات والخامات والنماذج عند الحاجة. يساعد ذلك على تشغيل عوالم كبيرة دون الاحتفاظ بكل البيانات في الذاكرة في الوقت نفسه.", "#ألعاب"),
    ("game photo mode depth of field", "وضع التصوير يستخدم مؤثرات تشبه عدسات الكاميرات الحقيقية", "يمكن لوضع التصوير تغيير التركيز وعمق المجال والتعرض وبعض عناصر المشهد. الهدف هو منح اللاعب تحكمًا أكبر في شكل اللقطة النهائية.", "#ألعاب"),
    ("game accessibility remapping controls", "إعادة تعيين الأزرار تسمح بتخصيص طريقة التحكم", "توفر بعض الألعاب خيارات لتغيير وظيفة الأزرار أو حجم النص أو بعض المؤثرات. هذه الإعدادات تجعل التحكم قابلًا للتخصيص بحسب احتياجات اللاعب.", "#ألعاب"),
    ("game minimap rendering", "الخريطة المصغرة تعرض معلومات الموقع في مساحة صغيرة من الشاشة", "تستخدم الخريطة المصغرة رموزًا واتجاهات ومناطق مبسطة لمساعدة اللاعب على فهم موقعه. يجب تصميمها بحيث تنقل المعلومات دون حجب المشهد الأساسي.", "#ألعاب"),
    ("game inventory weight system", "بعض الألعاب تحسب وزن العناصر لتحديد ما يستطيع اللاعب حمله", "يربط نظام الوزن كل عنصر بقيمة معينة، ثم يجمع أوزان العناصر التي يحملها اللاعب. يمكن أن يغير ذلك سرعة الحركة أو عدد العناصر الممكن حملها بحسب قواعد اللعبة.", "#ألعاب"),
    ("game quest state machine", "المهام يمكن إدارتها كحالات تنتقل بينها اللعبة وفق الأحداث", "يمكن للمطور تعريف حالات للمهمة مثل متاحة ونشطة ومكتملة. عند حدوث شرط معين تنتقل المهمة إلى الحالة التالية وتظهر الأحداث أو المكافآت المناسبة.", "#ألعاب"),
]

for search, title, text, tag in EXTRA_TOPIC_DATA:
    TOPICS.append({
        "search": search,
        "fallback_searches": [search + " close up", search + " video"],
        "title": title,
        "text": text,
        "hashtags": ["#Shorts", tag],
    })



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

    The pool intentionally contains only football, science, engineering/technology,
    and electronic-gaming topics. Historical and geographic topics are excluded.
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
