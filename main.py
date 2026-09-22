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
VOICE_RATE = "+5%"
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
    """Return hard-blocked terms found in the human-facing topic text."""
    combined = normalize_content(" ".join(str(x or "") for x in texts))
    found = []
    for term in BLOCKED_CONTENT_TERMS:
        normalized_term = normalize_content(term)
        if normalized_term and normalized_term in combined:
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
