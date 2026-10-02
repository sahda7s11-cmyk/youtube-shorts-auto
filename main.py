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

TOPICS = [{'search': 'ميسي والأرقام التي لا تظهر بمجرد عد الأهداف', 'fallback_searches': ['ميسي والأرقام football match', 'ميسي والأرقام action'], 'title': 'أرقام ميسي لا تختصر تأثيره في التسجيل فقط؛ فصناعة الفرص والمراوغات والتمريرات الحاسمة تكشف جانبًا آخر من حجم تأثيره في المباراة.', 'text': 'Lionel Messi chance creation dribbling match', 'hashtags': ['#Shorts', '#كرة_القدم', '#ميسي']}, {'search': 'رونالدو وكيف تحولت أرقامه مع تغير مركزه', 'fallback_searches': ['رونالدو وكيف football match', 'رونالدو وكيف action'], 'title': 'أرقام رونالدو التهديفية ارتبطت أيضًا بتطور مركزه داخل الملعب. انتقاله من الجناح إلى أدوار هجومية أكثر قربًا من المرمى غيّر نوع الفرص التي يحصل عليها.', 'text': 'Cristiano Ronaldo position striker match', 'hashtags': ['#Shorts', '#كرة_القدم', '#رونالدو']}, {'search': 'مبابي والسرعة التي تتحول إلى أرقام', 'fallback_searches': ['مبابي والسرعة football match', 'مبابي والسرعة action'], 'title': 'سرعة مبابي لا تصبح مؤثرة لمجرد أنه سريع؛ قيمتها تظهر عندما يستلم الكرة في المساحة ويحوّل الانطلاقة إلى فرصة أو تسديدة خلال وقت قصير.', 'text': 'Kylian Mbappe sprint attacking football', 'hashtags': ['#Shorts', '#كرة_القدم', '#مبابي']}, {'search': 'هالاند ولماذا تكشف لمساته القليلة شيئًا مهمًا', 'fallback_searches': ['هالاند ولماذا football match', 'هالاند ولماذا action'], 'title': 'عدد لمساته لا يشرح وحده أداء هالاند. المهاجم قد يلمس الكرة مرات قليلة لكنه يختار أماكنه داخل المنطقة بحيث تصبح كل لمسة أخطر.', 'text': 'Erling Haaland striker movement match', 'hashtags': ['#Shorts', '#كرة_القدم', '#هالاند']}, {'search': 'صلاح والأرقام خلف تحركاته من الجناح', 'fallback_searches': ['صلاح والأرقام football match', 'صلاح والأرقام action'], 'title': 'تأثير صلاح لا يعتمد على التسديد فقط؛ دخوله من الجهة إلى العمق يجمع بين التسجيل وصناعة الفرص وإجبار الدفاع على تغيير تمركزه.', 'text': 'Mohamed Salah cutting inside match', 'hashtags': ['#Shorts', '#كرة_القدم', '#صلاح']}, {'search': 'نيمار والأرقام التي تكشف قيمة المراوغة', 'fallback_searches': ['نيمار والأرقام football match', 'نيمار والأرقام action'], 'title': 'المراوغة ليست مجرد لقطة جميلة؛ عندما يتجاوز نيمار لاعبًا بالكرة تتغير زوايا التمرير والمساحة المتاحة لبقية الهجمة.', 'text': 'Neymar dribbling chance creation football', 'hashtags': ['#Shorts', '#كرة_القدم', '#نيمار']}, {'search': 'مودريتش وكيف يظهر تأثيره في عدد التمريرات', 'fallback_searches': ['مودريتش وكيف football match', 'مودريتش وكيف action'], 'title': 'كثرة التمريرات ليست المقياس الوحيد لمودريتش؛ الأهم هو أين يستلم الكرة وإلى أي منطقة ينقل اللعب بعد اللمسة.', 'text': 'Luka Modric passing midfield match', 'hashtags': ['#Shorts', '#كرة_القدم', '#مودريتش']}, {'search': 'دي بروين ولماذا تكون التمريرة الواحدة كافية', 'fallback_searches': ['دي بروين football match', 'دي بروين action'], 'title': 'قد تصنع تمريرة واحدة من دي بروين فرصة أخطر من سلسلة تمريرات قصيرة، لأن توقيتها قد يكسر خطًا كاملًا من الدفاع.', 'text': 'Kevin De Bruyne through pass match', 'hashtags': ['#Shorts', '#كرة_القدم', '#دي_بروين']}, {'search': 'بنزيما والأرقام التي تكشف دوره كمهاجم وصانع لعب', 'fallback_searches': ['بنزيما والأرقام football match', 'بنزيما والأرقام action'], 'title': 'بنزيما لم يكن يعتمد على التسجيل فقط؛ مساهمته في الربط وسحب المدافعين وصناعة المساحة كانت جزءًا من قيمته الهجومية.', 'text': 'Karim Benzema link up play match', 'hashtags': ['#Shorts', '#كرة_القدم', '#بنزيما']}, {'search': 'ليفاندوفسكي وكيف يختصر الطريق إلى التسديدة', 'fallback_searches': ['ليفاندوفسكي وكيف football match', 'ليفاندوفسكي وكيف action'], 'title': 'من أهم جوانب ليفاندوفسكي تقليل الوقت بين استلام الكرة والتسديد. هذا يجعل المدافع أمام فرصة قصيرة جدًا للتدخل.', 'text': 'Robert Lewandowski finishing match', 'hashtags': ['#Shorts', '#كرة_القدم', '#ليفاندوفسكي']}, {'search': 'فينيسيوس وتحول الانطلاقة إلى فرصة', 'fallback_searches': ['فينيسيوس وتحول football match', 'فينيسيوس وتحول action'], 'title': 'أرقام فينيسيوس في الهجوم ترتبط كثيرًا بما يحدث بعد أول مراوغة؛ فالمساحة التي يصنعها لنفسه تتحول بسرعة إلى تمريرة أو تسديدة.', 'text': 'Vinicius Junior dribbling attack match', 'hashtags': ['#Shorts', '#كرة_القدم', '#فينيسيوس']}, {'search': 'بيلينغهام والأرقام التي تأتي من الوسط', 'fallback_searches': ['بيلينغهام والأرقام football match', 'بيلينغهام والأرقام action'], 'title': 'وجود بيلينغهام في مناطق مختلفة يجعل تأثيره يتجاوز التسجيل؛ تحركاته من الوسط نحو الثلث الأخير تضيف خيارًا هجوميًا إضافيًا.', 'text': 'Jude Bellingham midfield attack match', 'hashtags': ['#Shorts', '#كرة_القدم', '#بيلينغهام']}, {'search': 'رونالدو والكرات الهوائية كجزء من سجله', 'fallback_searches': ['رونالدو والكرات football match', 'رونالدو والكرات action'], 'title': 'الكرات الهوائية كانت عنصرًا واضحًا في أسلوب رونالدو، خصوصًا عندما يختار توقيت الركض والارتقاء بدل الاعتماد على القوة وحدها.', 'text': 'Cristiano Ronaldo aerial header football', 'hashtags': ['#Shorts', '#كرة_القدم', '#رونالدو']}, {'search': 'ميسي وعدد اللمسات في المساحات الضيقة', 'fallback_searches': ['ميسي وعدد football match', 'ميسي وعدد action'], 'title': 'عندما تكون المساحة ضيقة، تصبح اللمسات القصيرة وتغيير الاتجاه أهم من السرعة القصوى، وهذا يفسر جانبًا من قوة ميسي في المواقف الفردية.', 'text': 'Lionel Messi close control dribbling', 'hashtags': ['#Shorts', '#كرة_القدم', '#ميسي']}, {'search': 'هالاند والتمركز الذي يسبق الإحصائية', 'fallback_searches': ['هالاند والتمركز football match', 'هالاند والتمركز action'], 'title': 'قبل أن يظهر اسم هالاند في جدول الهدافين، هناك حركة بدون كرة تساعده على الوصول إلى المكان المناسب قبل المدافع.', 'text': 'Erling Haaland off ball movement', 'hashtags': ['#Shorts', '#كرة_القدم', '#هالاند']}, {'search': 'صلاح ولماذا تبدأ بعض أهدافه من أول لمسة', 'fallback_searches': ['صلاح ولماذا football match', 'صلاح ولماذا action'], 'title': 'في كثير من هجمات صلاح، اللمسة الأولى تحدد اتجاه الهجمة. إذا جاءت للأمام أو إلى الداخل، يصبح لديه وقت ومساحة أكبر للقرار التالي.', 'text': 'Mohamed Salah first touch attack', 'hashtags': ['#Shorts', '#كرة_القدم', '#صلاح']}, {'search': 'ميسي والركلة الحرة التي تحتاج أكثر من قوة', 'fallback_searches': ['ميسي والركلة football match', 'ميسي والركلة action'], 'title': 'تنفيذ الركلة الحرة يعتمد على زاوية القدم ومسار الكرة وارتفاعها، وميسي طوّر أسلوبًا يعتمد كثيرًا على الدقة أكثر من القوة الخام.', 'text': 'Lionel Messi free kick football', 'hashtags': ['#Shorts', '#كرة_القدم', '#ميسي']}, {'search': 'رونالدو ووقفة الركلة الحرة قبل التسديد', 'fallback_searches': ['رونالدو ووقفة football match', 'رونالدو ووقفة action'], 'title': 'الوقفة الشهيرة قبل الركلات الحرة ليست الجزء المهم وحده؛ الأهم هو طريقة الاقتراب من الكرة ونقطة ضربها والتحكم في المسار.', 'text': 'Cristiano Ronaldo free kick football', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'مبابي واحتفاله الذي أصبح علامة معروفة', 'fallback_searches': ['مبابي واحتفاله football match', 'مبابي واحتفاله action'], 'title': 'حركة احتفال مبابي بسيطة، لكنها ارتبطت به بسرعة وأصبحت من اللقطات التي يتعرف عليها الجمهور مباشرة بعد أهدافه.', 'text': 'Kylian Mbappe celebration football', 'hashtags': ['#Shorts', '#كرة_القدم', '#مبابي']}, {'search': 'هالاند واحتفال التأمل الهادئ', 'fallback_searches': ['هالاند واحتفال football match', 'هالاند واحتفال action'], 'title': 'اختار هالاند في عدة مناسبات وضعية هادئة بعد التسجيل، وهو ما جعل الاحتفال مختلفًا بصريًا عن الاحتفالات المعتادة.', 'text': 'Erling Haaland meditation celebration', 'hashtags': ['#Shorts', '#كرة_القدم', '#هالاند']}, {'search': 'نيمار والحركة التي تجعل المدافع يتحرك قبل المراوغة', 'fallback_searches': ['نيمار والحركة football match', 'نيمار والحركة action'], 'title': 'الخداع عند نيمار يبدأ أحيانًا من حركة الجسم قبل لمس الكرة، فيجعل المدافع يتوقع اتجاهًا ثم يغيره بسرعة.', 'text': 'Neymar body feint dribbling', 'hashtags': ['#Shorts', '#كرة_القدم', '#نيمار']}, {'search': 'صلاح وتغيير السرعة بعد المراوغة', 'fallback_searches': ['صلاح وتغيير football match', 'صلاح وتغيير action'], 'title': 'اللقطة الخطيرة ليست دائمًا في المراوغة نفسها؛ تغيير السرعة مباشرة بعدها هو ما يصنع الفارق في كثير من مواجهات صلاح الفردية.', 'text': 'Mohamed Salah acceleration dribbling', 'hashtags': ['#Shorts', '#كرة_القدم', '#صلاح']}, {'search': 'مودريتش والتمرير بالقدم الخارجية', 'fallback_searches': ['مودريتش والتمرير football match', 'مودريتش والتمرير action'], 'title': 'استخدام القدم الخارجية يسمح بتمرير الكرة من زاوية غير معتادة، وهو أحد التفاصيل الفنية التي تجعل بعض تمريرات مودريتش لافتة.', 'text': 'Luka Modric outside foot pass', 'hashtags': ['#Shorts', '#كرة_القدم', '#مودريتش']}, {'search': 'دي بروين والتمريرة التي تصل قبل المدافع', 'fallback_searches': ['دي بروين football match', 'دي بروين action'], 'title': 'عندما يرسل دي بروين الكرة إلى المساحة قبل وصول المهاجم إليها، يعتمد نجاح الهجمة على قراءة اللحظة لا على قوة التمريرة فقط.', 'text': 'Kevin De Bruyne through ball', 'hashtags': ['#Shorts', '#كرة_القدم', '#دي_بروين']}, {'search': 'بنزيما واللمسة التي تحافظ على استمرار الهجمة', 'fallback_searches': ['بنزيما واللمسة football match', 'بنزيما واللمسة action'], 'title': 'اللمسة الأولى قد تكون للربط مع زميل بدل التوجه للمرمى، وهذه من التفاصيل التي ظهرت كثيرًا في طريقة لعب بنزيما.', 'text': 'Karim Benzema first touch football', 'hashtags': ['#Shorts', '#كرة_القدم', '#بنزيما']}, {'search': 'ليفاندوفسكي وكيف يجهز جسمه قبل وصول الكرة', 'fallback_searches': ['ليفاندوفسكي وكيف football match', 'ليفاندوفسكي وكيف action'], 'title': 'التمركز الجيد يجعل المهاجم مستعدًا للتسديد قبل وصول الكرة، وهذا يقلل عدد الحركات التي يحتاجها بعد الاستلام.', 'text': 'Robert Lewandowski positioning finishing', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'فينيسيوس والوقوف أمام المدافع قبل الانطلاق', 'fallback_searches': ['فينيسيوس والوقوف football match', 'فينيسيوس والوقوف action'], 'title': 'في المواجهة الفردية، يمكن لتوقف قصير أن يجبر المدافع على تثبيت قدمه، ثم تأتي الانطلاقة لتستغل لحظة التردد.', 'text': 'Vinicius Junior one on one dribbling', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'بيلينغهام واستخدام الجسم تحت الضغط', 'fallback_searches': ['بيلينغهام واستخدام football match', 'بيلينغهام واستخدام action'], 'title': 'التحكم بالجسم يساعد بيلينغهام على حماية الكرة ثم الدوران نحو المساحة بدل فقدانها عند أول ضغط.', 'text': 'Jude Bellingham ball control match', 'hashtags': ['#Shorts', '#كرة_القدم', '#بيلينغهام']}, {'search': 'رونالدو والقفز في اللحظة المناسبة', 'fallback_searches': ['رونالدو والقفز football match', 'رونالدو والقفز action'], 'title': 'الكرات العالية تحتاج توقيتًا دقيقًا؛ الارتقاء المبكر أو المتأخر قد يلغي أفضلية اللاعب مهما كانت قدرته البدنية.', 'text': 'Cristiano Ronaldo header timing', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'ميسي واللمسة التي تسبق تغيير الاتجاه', 'fallback_searches': ['ميسي واللمسة football match', 'ميسي واللمسة action'], 'title': 'في المساحات الضيقة، دفع الكرة مسافة صغيرة يسمح لميسي بتغيير اتجاهه دون فقدان السيطرة.', 'text': 'Lionel Messi close control football', 'hashtags': ['#Shorts', '#كرة_القدم', '#ميسي']}, {'search': 'نيمار والخداع قبل لمس الكرة', 'fallback_searches': ['نيمار والخداع football match', 'نيمار والخداع action'], 'title': 'نظرة اللاعب واتجاه جسمه قد يوحيان بقرار مختلف عن القرار الحقيقي، وهذه التفاصيل تساعد نيمار على خلق المساحة للمراوغة.', 'text': 'Neymar feint football skill', 'hashtags': ['#Shorts', '#كرة_القدم', '#نيمار']}, {'search': 'هالاند والحركة خلف المدافع قبل العرضية', 'fallback_searches': ['هالاند والحركة football match', 'هالاند والحركة action'], 'title': 'المهاجم الذي يتحرك قبل وصول العرضية يملك أفضلية زمنية، وهالاند يعتمد كثيرًا على اختيار المسار داخل المنطقة.', 'text': 'Erling Haaland movement cross', 'hashtags': ['#Shorts', '#كرة_القدم', '#هالاند']}, {'search': 'كيف تحول رونالدو من جناح مهاري إلى هداف متكامل', 'fallback_searches': ['كيف تحول football match', 'كيف تحول action'], 'title': 'بدايات رونالدو اعتمدت كثيرًا على المراوغة والسرعة، ثم أصبح أكثر تركيزًا على التحرك والتسجيل وإنهاء الهجمات.', 'text': 'Cristiano Ronaldo early career Manchester United', 'hashtags': ['#Shorts', '#كرة_القدم', '#رونالدو']}, {'search': 'المرحلة التي غيرت طريقة لعب ميسي', 'fallback_searches': ['المرحلة التي football match', 'المرحلة التي action'], 'title': 'مع تطور مسيرته تغيّر دور ميسي من لاعب يعتمد على التحرك والمراوغة إلى لاعب يشارك في صناعة اللعب والتسجيل معًا.', 'text': 'Lionel Messi career playing style', 'hashtags': ['#Shorts', '#كرة_القدم', '#ميسي']}, {'search': 'كيف تطور مبابي من موهبة شابة إلى مهاجم متعدد الأدوار', 'fallback_searches': ['كيف تطور football match', 'كيف تطور action'], 'title': 'مع مرور الوقت أضاف مبابي إلى سرعته مهارات في صناعة الفرص وإنهاء الهجمات والتحرك في أكثر من مركز هجومي.', 'text': 'Kylian Mbappe career development', 'hashtags': ['#Shorts', '#كرة_القدم', '#مبابي']}, {'search': 'لماذا كان انتقال هالاند بين الأندية مهمًا لأسلوبه', 'fallback_searches': ['لماذا كان football match', 'لماذا كان action'], 'title': 'تدرج هالاند بين مستويات مختلفة من المنافسة منحه خبرة في أنظمة هجومية متنوعة، مع بقاء قوته الأساسية في التحرك والحسم.', 'text': 'Erling Haaland career development', 'hashtags': ['#Shorts', '#كرة_القدم', '#هالاند']}, {'search': 'رحلة صلاح قبل الوصول إلى قمة مستواه', 'fallback_searches': ['رحلة صلاح football match', 'رحلة صلاح action'], 'title': 'مر صلاح بعدة مراحل احترافية ساعدته على تطوير السرعة والقرار الأخير والقدرة على التسجيل من الجهة.', 'text': 'Mohamed Salah career early football', 'hashtags': ['#Shorts', '#كرة_القدم', '#صلاح']}, {'search': 'كيف تغير دور بنزيما مع الخبرة', 'fallback_searches': ['كيف تغير football match', 'كيف تغير action'], 'title': 'مع تقدم مسيرته أصبح بنزيما يشارك أكثر في بناء الهجمة والربط وفتح المساحات إلى جانب إنهاء الفرص.', 'text': 'Karim Benzema career playing style', 'hashtags': ['#Shorts', '#كرة_القدم', '#بنزيما']}, {'search': 'لماذا أصبح ليفاندوفسكي أكثر تنوعًا كمهاجم', 'fallback_searches': ['لماذا أصبح football match', 'لماذا أصبح action'], 'title': 'تطور ليفاندوفسكي في التمركز والإنهاء واللعب بظهره للمرمى، ما جعله قادرًا على التعامل مع أنواع مختلفة من الفرص.', 'text': 'Robert Lewandowski career development', 'hashtags': ['#Shorts', '#كرة_القدم', '#ليفاندوفسكي']}, {'search': 'كيف حافظ مودريتش على أسلوبه رغم تغير أدواره', 'fallback_searches': ['كيف حافظ football match', 'كيف حافظ action'], 'title': 'خبرة مودريتش سمحت له بتعديل موقعه وطريقة تحركه مع الحفاظ على أهم عناصر لعبه: الرؤية والتحكم بإيقاع الهجمة.', 'text': 'Luka Modric career playing style', 'hashtags': ['#Shorts', '#كرة_القدم', '#مودريتش']}, {'search': 'نيمار بين المراوغة وصناعة اللعب', 'fallback_searches': ['نيمار بين football match', 'نيمار بين action'], 'title': 'مع ارتفاع مستوى المنافسة، لم يعد دور نيمار قائمًا على المراوغة فقط؛ أصبح مطالبًا بصناعة الفرص والتسجيل والربط بين الخطوط.', 'text': 'Neymar career playing style', 'hashtags': ['#Shorts', '#كرة_القدم', '#نيمار']}, {'search': 'تطور فينيسيوس من السرعة إلى القرار', 'fallback_searches': ['تطور فينيسيوس football match', 'تطور فينيسيوس action'], 'title': 'من أبرز جوانب تطور فينيسيوس تحسين قراره في اللحظة الأخيرة، سواء بالتمرير أو التسديد بدل الاعتماد على الانطلاقة وحدها.', 'text': 'Vinicius Junior career development', 'hashtags': ['#Shorts', '#كرة_القدم', '#فينيسيوس']}, {'search': 'كيف أصبح بيلينغهام أخطر من منطقة الوسط', 'fallback_searches': ['كيف أصبح football match', 'كيف أصبح action'], 'title': 'قدرة بيلينغهام على التحرك من الخلف أضافت بعدًا هجوميًا إلى دوره كلاعب وسط، خصوصًا عندما يصل إلى الثلث الأخير.', 'text': 'Jude Bellingham career playing style', 'hashtags': ['#Shorts', '#كرة_القدم', '#بيلينغهام']}, {'search': 'دي بروين وبناء أسلوبه حول صناعة الفرص', 'fallback_searches': ['دي بروين football match', 'دي بروين action'], 'title': 'أسلوب دي بروين يعتمد على الرؤية والتمرير المباشر واستغلال المساحات، وهي عناصر ظهرت بوضوح مع تطور مسيرته.', 'text': 'Kevin De Bruyne career playing style', 'hashtags': ['#Shorts', '#كرة_القدم', '#دي_بروين']}, {'search': 'لماذا تغيرت طريقة لعب رونالدو داخل منطقة الجزاء', 'fallback_searches': ['لماذا تغيرت football match', 'لماذا تغيرت action'], 'title': 'مع مرور السنوات أصبح التحرك داخل المنطقة والتمركز لإنهاء الهجمة أهم من الاعتماد على المراوغة لمسافات طويلة.', 'text': 'Cristiano Ronaldo striker evolution', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'ميسي وكيف جمع بين صانع اللعب والهداف', 'fallback_searches': ['ميسي وكيف football match', 'ميسي وكيف action'], 'title': 'أحد أكثر جوانب مسيرة ميسي تميزًا هو قدرته على الانتقال بين صناعة الهجمة وإنهائها بنفسه.', 'text': 'Lionel Messi playmaker goals', 'hashtags': ['#Shorts', '#كرة_القدم', '#ميسي']}, {'search': 'هالاند وكيف صقل أسلوبه بدون كرة', 'fallback_searches': ['هالاند وكيف football match', 'هالاند وكيف action'], 'title': 'جزء مهم من تطور هالاند هو الحركة قبل استلام الكرة، لأنها تساعده على الوصول إلى مناطق التسجيل بأفضلية زمنية.', 'text': 'Erling Haaland off ball development', 'hashtags': ['#Shorts', '#كرة_القدم', '#هالاند']}, {'search': 'صلاح وكيف أصبح أكثر هدوءًا في القرار الأخير', 'fallback_searches': ['صلاح وكيف football match', 'صلاح وكيف action'], 'title': 'مع الخبرة أصبح صلاح أكثر قدرة على اختيار اللحظة المناسبة بين التسديد والتمرير والانطلاق.', 'text': 'Mohamed Salah decision making career', 'hashtags': ['#Shorts', '#كرة_القدم', '#صلاح']}, {'search': 'رقم رونالدو التاريخي في دوري أبطال أوروبا', 'fallback_searches': ['رقم رونالدو football match', 'رقم رونالدو action'], 'title': 'رونالدو يملك الرقم القياسي في عدد أهداف دوري أبطال أوروبا، وهو رقم جمعه عبر سنوات طويلة من المشاركة في البطولة.', 'text': 'Cristiano Ronaldo Champions League goals record', 'hashtags': ['#Shorts', '#كرة_القدم', '#رونالدو']}, {'search': 'رقم ميسي في الكرة الذهبية', 'fallback_searches': ['رقم ميسي football match', 'رقم ميسي action'], 'title': 'ميسي يملك الرقم القياسي في عدد مرات الفوز بالكرة الذهبية، وهو إنجاز امتد عبر مراحل مختلفة من مسيرته.', 'text': "Lionel Messi Ballon d'Or record", 'hashtags': ['#Shorts', '#كرة_القدم', '#ميسي']}, {'search': 'رقم رونالدو مع منتخب البرتغال', 'fallback_searches': ['رقم رونالدو football match', 'رقم رونالدو action'], 'title': 'رونالدو يملك الرقم القياسي العالمي في الأهداف الدولية للرجال، وهو من أبرز أرقامه مع المنتخب.', 'text': 'Cristiano Ronaldo international goals record', 'hashtags': ['#Shorts', '#كرة_القدم', '#رونالدو']}, {'search': 'ميسي وكأس العالم الذي أكمل مسيرته الدولية', 'fallback_searches': ['ميسي وكأس football match', 'ميسي وكأس action'], 'title': 'فوز ميسي بكأس العالم مع الأرجنتين عام 2022 أضاف أهم لقب دولي إلى سجل مسيرته.', 'text': 'Lionel Messi World Cup trophy 2022', 'hashtags': ['#Shorts', '#كرة_القدم', '#ميسي']}, {'search': 'مبابي والإنجاز المبكر في كأس العالم', 'fallback_searches': ['مبابي والإنجاز football match', 'مبابي والإنجاز action'], 'title': 'فوز مبابي بكأس العالم مع فرنسا وهو في سن صغيرة جعله يدخل مبكرًا في قائمة اللاعبين الذين حققوا أكبر ألقاب المنتخبات.', 'text': 'Kylian Mbappe World Cup 2018', 'hashtags': ['#Shorts', '#كرة_القدم', '#مبابي']}, {'search': 'هالاند والأرقام التهديفية السريعة', 'fallback_searches': ['هالاند والأرقام football match', 'هالاند والأرقام action'], 'title': 'من أبرز ما يميز هالاند قدرته على الوصول إلى أرقام تهديفية كبيرة خلال عدد قليل نسبيًا من المباريات.', 'text': 'Erling Haaland scoring records', 'hashtags': ['#Shorts', '#كرة_القدم', '#هالاند']}, {'search': 'صلاح وموسم غيّر أرقامه في الدوري الإنجليزي', 'fallback_searches': ['صلاح وموسم football match', 'صلاح وموسم action'], 'title': 'موسم صلاح الأول مع ليفربول كان نقطة تحول تهديفية كبيرة، وسجل خلاله رقمًا بارزًا في الدوري الإنجليزي بنظام 38 مباراة.', 'text': 'Mohamed Salah 2017 2018 Premier League record', 'hashtags': ['#Shorts', '#كرة_القدم', '#صلاح']}, {'search': 'ليفاندوفسكي والرقم القياسي في موسم واحد بالدوري الألماني', 'fallback_searches': ['ليفاندوفسكي والرقم football match', 'ليفاندوفسكي والرقم action'], 'title': 'سجل ليفاندوفسكي 41 هدفًا في موسم واحد من الدوري الألماني، محققًا رقمًا قياسيًا في المسابقة.', 'text': 'Robert Lewandowski 41 goals Bundesliga record', 'hashtags': ['#Shorts', '#كرة_القدم', '#ليفاندوفسكي']}, {'search': 'بنزيما والكرة الذهبية بعد موسم استثنائي', 'fallback_searches': ['بنزيما والكرة football match', 'بنزيما والكرة action'], 'title': 'حصل بنزيما على الكرة الذهبية بعد موسم بارز مع ريال مدريد، ليضيف الجائزة الفردية الكبرى إلى مسيرته.', 'text': "Karim Benzema Ballon d'Or 2022", 'hashtags': ['#Shorts', '#كرة_القدم', '#بنزيما']}, {'search': 'مودريتش والكرة الذهبية كلاعب وسط', 'fallback_searches': ['مودريتش والكرة football match', 'مودريتش والكرة action'], 'title': 'فوز مودريتش بالكرة الذهبية عام 2018 كان إنجازًا لافتًا للاعب وسط في عصر هيمن فيه المهاجمون على الجائزة.', 'text': "Luka Modric Ballon d'Or 2018", 'hashtags': ['#Shorts', '#كرة_القدم', '#مودريتش']}, {'search': 'رونالدو وعدد ألقاب دوري الأبطال', 'fallback_searches': ['رونالدو وعدد football match', 'رونالدو وعدد action'], 'title': 'حقق رونالدو دوري أبطال أوروبا عدة مرات، وارتبط اسمه بالبطولة أكثر من أي لاعب آخر من حيث الأهداف والمشاركة في مراحلها الحاسمة.', 'text': 'Cristiano Ronaldo Champions League trophies', 'hashtags': ['#Shorts', '#كرة_القدم', '#رونالدو']}, {'search': 'ميسي وأرقام التسجيل مع برشلونة', 'fallback_searches': ['ميسي وأرقام football match', 'ميسي وأرقام action'], 'title': 'حقق ميسي أرقامًا تهديفية استثنائية مع برشلونة خلال سنواته الطويلة مع النادي، وأصبح الهداف التاريخي للنادي.', 'text': 'Lionel Messi Barcelona scoring record', 'hashtags': ['#Shorts', '#كرة_القدم', '#ميسي']}, {'search': 'هالاند وأسرع الوصول إلى أرقام كبيرة في إنجلترا', 'fallback_searches': ['هالاند وأسرع football match', 'هالاند وأسرع action'], 'title': 'قدرة هالاند على التسجيل بمعدل مرتفع جعلته يصل إلى أرقام تهديفية في الدوري الإنجليزي بسرعة لافتة.', 'text': 'Erling Haaland Premier League scoring record', 'hashtags': ['#Shorts', '#كرة_القدم', '#هالاند']}, {'search': 'مبابي وأرقامه التهديفية في كأس العالم', 'fallback_searches': ['مبابي وأرقامه football match', 'مبابي وأرقامه action'], 'title': 'سجل مبابي عددًا كبيرًا من الأهداف في كأس العالم رغم صغر سنه، وأصبح من أبرز الهدافين الشباب في تاريخ البطولة.', 'text': 'Kylian Mbappe World Cup goals', 'hashtags': ['#Shorts', '#كرة_القدم', '#مبابي']}, {'search': 'ميسي وعدد الأهداف الدولية', 'fallback_searches': ['ميسي وعدد football match', 'ميسي وعدد action'], 'title': 'واصل ميسي تسجيل الأهداف مع الأرجنتين عبر سنوات طويلة، وأصبح من أبرز الهدافين الدوليين في تاريخ كرة القدم للرجال.', 'text': 'Lionel Messi Argentina international goals', 'hashtags': ['#Shorts', '#كرة_القدم', '#ميسي']}, {'search': 'رونالدو والهداف التاريخي للمنتخبات', 'fallback_searches': ['رونالدو والهداف football match', 'رونالدو والهداف action'], 'title': 'استمر رونالدو في تسجيل الأهداف الدولية عبر عدة أجيال من لاعبي المنتخب البرتغالي، حتى وصل إلى الرقم القياسي العالمي.', 'text': 'Cristiano Ronaldo Portugal international record', 'hashtags': ['#Shorts', '#كرة_القدم', '#رونالدو']}, {'search': 'ميسي ورونالدو: اختلاف الطريقة قبل اختلاف الأرقام', 'fallback_searches': ['ميسي ورونالدو: football match', 'ميسي ورونالدو: action'], 'title': 'ميسي يعتمد كثيرًا على المراوغة وصناعة اللعب والتمرير، بينما برز رونالدو في التسجيل والتحرك والكرات الهوائية.', 'text': 'Messi Ronaldo comparison football', 'hashtags': ['#Shorts', '#كرة_القدم', '#ميسي', '#رونالدو']}, {'search': 'مبابي وهالاند: كيف يصل كل منهما إلى المرمى', 'fallback_searches': ['مبابي وهالاند: football match', 'مبابي وهالاند: action'], 'title': 'مبابي يستفيد من السرعة والمساحات، بينما يعتمد هالاند أكثر على التمركز والقوة والحسم داخل المنطقة.', 'text': 'Mbappe Haaland comparison football', 'hashtags': ['#Shorts', '#كرة_القدم', '#مبابي', '#هالاند']}, {'search': 'صلاح ومبابي: من الأخطر في المساحة؟', 'fallback_searches': ['صلاح ومبابي: football match', 'صلاح ومبابي: action'], 'title': 'كلاهما يستطيع استغلال المساحة خلف الدفاع، لكن طريقة الوصول إليها تختلف بين تحرك صلاح من الجهة وانطلاق مبابي المباشر.', 'text': 'Salah Mbappe comparison football', 'hashtags': ['#Shorts', '#كرة_القدم', '#مبابي', '#صلاح']}, {'search': 'نيمار وميسي: المراوغة بطريقتين مختلفتين', 'fallback_searches': ['نيمار وميسي: football match', 'نيمار وميسي: action'], 'title': 'كلاهما يمتلك تحكمًا عاليًا بالكرة، لكن ميسي يميل إلى تغيير الاتجاه بسرعة بينما يعتمد نيمار أكثر على الخداع وتغيير الإيقاع.', 'text': 'Neymar Messi dribbling comparison', 'hashtags': ['#Shorts', '#كرة_القدم', '#ميسي', '#نيمار']}, {'search': 'رونالدو وهالاند: مهاجمان بخصائص مختلفة', 'fallback_searches': ['رونالدو وهالاند: football match', 'رونالدو وهالاند: action'], 'title': 'رونالدو جمع بين التسديد واللعب الهوائي والتحرك، بينما يعتمد هالاند بصورة كبيرة على التمركز والإنهاء داخل المنطقة.', 'text': 'Ronaldo Haaland striker comparison', 'hashtags': ['#Shorts', '#كرة_القدم', '#رونالدو', '#هالاند']}, {'search': 'دي بروين ومودريتش: صناعة اللعب من زاويتين', 'fallback_searches': ['دي بروين football match', 'دي بروين action'], 'title': 'دي بروين يميل إلى التمريرات المباشرة وصناعة الفرص، بينما يركز مودريتش أكثر على التحكم بالإيقاع وتغيير اتجاه اللعب.', 'text': 'De Bruyne Modric comparison', 'hashtags': ['#Shorts', '#كرة_القدم', '#مودريتش', '#دي_بروين']}, {'search': 'بنزيما وليفاندوفسكي: كيف يخدم المهاجم فريقه؟', 'fallback_searches': ['بنزيما وليفاندوفسكي: football match', 'بنزيما وليفاندوفسكي: action'], 'title': 'ليفاندوفسكي يبرز في التمركز والإنهاء، بينما يجمع بنزيما بين التسجيل والربط وصناعة المساحات.', 'text': 'Benzema Lewandowski comparison', 'hashtags': ['#Shorts', '#كرة_القدم', '#بنزيما', '#ليفاندوفسكي']}, {'search': 'فينيسيوس ونيمار: ماذا يحدث بعد المراوغة؟', 'fallback_searches': ['فينيسيوس ونيمار: football match', 'فينيسيوس ونيمار: action'], 'title': 'فينيسيوس يعتمد كثيرًا على التسارع بعد تجاوز المدافع، بينما يستخدم نيمار الخداع وتغيير الإيقاع للحفاظ على السيطرة.', 'text': 'Vinicius Neymar comparison', 'hashtags': ['#Shorts', '#كرة_القدم', '#نيمار', '#فينيسيوس']}, {'search': 'ميسي ومبابي: التحكم مقابل الانفجار', 'fallback_searches': ['ميسي ومبابي: football match', 'ميسي ومبابي: action'], 'title': 'ميسي يعتمد على التحكم الدقيق وتغيير الاتجاه، بينما يمتلك مبابي ميزة واضحة في التسارع واستغلال المساحة.', 'text': 'Messi Mbappe comparison', 'hashtags': ['#Shorts', '#كرة_القدم', '#ميسي', '#مبابي']}, {'search': 'صلاح ورونالدو: الجناح الذي يتحول إلى هداف', 'fallback_searches': ['صلاح ورونالدو: football match', 'صلاح ورونالدو: action'], 'title': 'كلاهما استطاع تطوير دوره الهجومي، لكن طريقة الوصول إلى المرمى مختلفة بحسب الحركة والتسديد والتمركز.', 'text': 'Salah Ronaldo comparison', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'هالاند وليفاندوفسكي: قراءة منطقة الجزاء', 'fallback_searches': ['هالاند وليفاندوفسكي: football match', 'هالاند وليفاندوفسكي: action'], 'title': 'كلاهما من أبرز المهاجمين في التمركز، لكن طريقة تحرك كل لاعب قبل التسديد تختلف حسب المساحة والمدافع.', 'text': 'Haaland Lewandowski comparison', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'مودريتش ودي بروين: التمريرة الحاسمة ليست شكلًا واحدًا', 'fallback_searches': ['مودريتش ودي football match', 'مودريتش ودي action'], 'title': 'دي بروين يبرع في تمريرات المساحة المباشرة، بينما يتميز مودريتش بقدرته على تغيير اتجاه اللعب وصناعة زوايا جديدة.', 'text': 'Modric De Bruyne passing comparison', 'hashtags': ['#Shorts', '#كرة_القدم', '#مودريتش', '#دي_بروين']}, {'search': 'بيلينغهام ومودريتش: لاعب وسط من جيلين', 'fallback_searches': ['بيلينغهام ومودريتش: football match', 'بيلينغهام ومودريتش: action'], 'title': 'مودريتش يعتمد على التحكم والإيقاع والخبرة، بينما يضيف بيلينغهام الحركة والقوة والوصول المتأخر إلى منطقة الجزاء.', 'text': 'Bellingham Modric midfield comparison', 'hashtags': ['#Shorts', '#كرة_القدم', '#مودريتش', '#بيلينغهام']}, {'search': 'مبابي وفينيسيوس: السرعة مع الكرة', 'fallback_searches': ['مبابي وفينيسيوس: football match', 'مبابي وفينيسيوس: action'], 'title': 'كلاهما خطير في المواجهات الفردية، لكن توقيت تغيير الاتجاه وطريقة استغلال المساحة تختلف بينهما.', 'text': 'Mbappe Vinicius comparison', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'نيمار وصلاح: صناعة الخطورة من الجناح', 'fallback_searches': ['نيمار وصلاح: football match', 'نيمار وصلاح: action'], 'title': 'نيمار يعتمد أكثر على الخداع والمهارة، بينما يميل صلاح إلى السرعة والتحرك إلى الداخل والبحث عن التسديد.', 'text': 'Neymar Salah comparison', 'hashtags': ['#Shorts', '#كرة_القدم', '#صلاح', '#نيمار']}, {'search': 'رونالدو وبنزيما: مهاجمان في منظومة واحدة بطريقتين', 'fallback_searches': ['رونالدو وبنزيما: football match', 'رونالدو وبنزيما: action'], 'title': 'رونالدو ركز كثيرًا على إنهاء الهجمات، بينما كان بنزيما يجمع بين الربط وصناعة المساحة والتسجيل.', 'text': 'Ronaldo Benzema comparison', 'hashtags': ['#Shorts', '#كرة_القدم', '#رونالدو', '#بنزيما']}, {'search': 'هدف واحد غيّر ليلة ميسي في مباراة كبيرة', 'fallback_searches': ['هدف واحد football match', 'هدف واحد action'], 'title': 'في المباريات المتقاربة، لحظة واحدة قد تكون أهم من عدد الفرص، وميسي اشتهر بصناعة هذه اللحظات بالتمريرة أو المراوغة أو التسديد.', 'text': 'Lionel Messi decisive goal match', 'hashtags': ['#Shorts', '#كرة_القدم', '#ميسي']}, {'search': 'رونالدو واللحظة التي ينتظرها في المباريات الكبيرة', 'fallback_searches': ['رونالدو واللحظة football match', 'رونالدو واللحظة action'], 'title': 'عندما تضيق المساحات، يصبح التحرك دون كرة مهمًا، ورونالدو كثيرًا ما بحث عن اللحظة التي يستطيع فيها الانفصال عن المدافع.', 'text': 'Cristiano Ronaldo big match movement', 'hashtags': ['#Shorts', '#كرة_القدم', '#رونالدو']}, {'search': 'مبابي وكيف يمكن لهجمة واحدة أن تقلب المباراة', 'fallback_searches': ['مبابي وكيف football match', 'مبابي وكيف action'], 'title': 'السرعة تجعل الهجمة تتحول بسرعة من استلام الكرة إلى مواجهة مباشرة مع الدفاع، وهذا ما يجعل بعض لحظات مبابي قصيرة وحاسمة.', 'text': 'Kylian Mbappe decisive attack match', 'hashtags': ['#Shorts', '#كرة_القدم', '#مبابي']}, {'search': 'هالاند والهدف الذي يبدأ قبل وصول الكرة', 'fallback_searches': ['هالاند والهدف football match', 'هالاند والهدف action'], 'title': 'التحرك إلى المكان المناسب قبل وصول التمريرة قد يحسم الهجمة قبل أن تبدأ التسديدة أصلًا.', 'text': 'Erling Haaland goal movement match', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'صلاح والهجمة التي تبدأ من الجهة', 'fallback_searches': ['صلاح والهجمة football match', 'صلاح والهجمة action'], 'title': 'عندما يستلم صلاح في الجهة ثم يدخل إلى العمق بسرعة، قد تتحول الهجمة إلى فرصة قبل أن يتمكن الدفاع من إعادة تمركزه.', 'text': 'Mohamed Salah decisive attack match', 'hashtags': ['#Shorts', '#كرة_القدم', '#صلاح']}, {'search': 'نيمار واللمسة التي كسرت ضغط الدفاع', 'fallback_searches': ['نيمار واللمسة football match', 'نيمار واللمسة action'], 'title': 'استلام الكرة تحت الضغط ثم الخروج منها بالمراوغة قد يحول وضعية دفاعية إلى هجمة في ثوانٍ.', 'text': 'Neymar pressure dribble match', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'مودريتش والتمريرة التي قلبت اتجاه اللعب', 'fallback_searches': ['مودريتش والتمريرة football match', 'مودريتش والتمريرة action'], 'title': 'تغيير جهة اللعب بسرعة يمكن أن يفتح مساحة كبيرة في الطرف المقابل قبل أن يتحرك الدفاع إليها.', 'text': 'Luka Modric switch pass match', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'دي بروين والتمريرة قبل ظهور المساحة', 'fallback_searches': ['دي بروين football match', 'دي بروين action'], 'title': 'أحيانًا تكون أفضل تمريرة هي التي تأتي قبل أن يلاحظ الجميع الفراغ، وهذا جزء من سرعة قراءة دي بروين للهجمة.', 'text': 'Kevin De Bruyne decisive pass match', 'hashtags': ['#Shorts', '#كرة_القدم', '#دي_بروين']}, {'search': 'بنزيما والعودة التي تبدأ من مهاجم', 'fallback_searches': ['بنزيما والعودة football match', 'بنزيما والعودة action'], 'title': 'تراجع المهاجم لاستلام الكرة قد يسحب المدافع ويخلق طريقًا لزميل قادم من الخلف، وهي إحدى أفكار بنزيما الهجومية.', 'text': 'Karim Benzema link up match', 'hashtags': ['#Shorts', '#كرة_القدم', '#بنزيما']}, {'search': 'ليفاندوفسكي واللمسة التي تحسم داخل المنطقة', 'fallback_searches': ['ليفاندوفسكي واللمسة football match', 'ليفاندوفسكي واللمسة action'], 'title': 'في منطقة الجزاء لا يوجد وقت طويل للتفكير، لذلك تصبح زاوية اللمسة الأولى والتسديد السريع حاسمة.', 'text': 'Robert Lewandowski decisive finish', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'فينيسيوس والمرتدة التي تتحول إلى سباق', 'fallback_searches': ['فينيسيوس والمرتدة football match', 'فينيسيوس والمرتدة action'], 'title': 'عندما يحصل فينيسيوس على المساحة، يمكن أن تصبح المرتدة مواجهة سرعة مباشرة بينه وبين خط الدفاع.', 'text': 'Vinicius Junior counter attack match', 'hashtags': ['#Shorts', '#كرة_القدم', '#فينيسيوس']}, {'search': 'بيلينغهام والوصول المتأخر الذي يفاجئ الدفاع', 'fallback_searches': ['بيلينغهام والوصول football match', 'بيلينغهام والوصول action'], 'title': 'التحرك من الخلف يجعل مراقبة اللاعب أصعب، خصوصًا عندما ينشغل المدافع بالمهاجم الموجود أمامه.', 'text': 'Jude Bellingham late run match', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'رونالدو والعودة في مباراة دوري الأبطال', 'fallback_searches': ['رونالدو والعودة football match', 'رونالدو والعودة action'], 'title': 'بعض مباريات دوري الأبطال ارتبطت بأهداف رونالدو الحاسمة في لحظات ضغط عالية، وهو ما جعل حضوره في الأدوار الإقصائية لافتًا.', 'text': 'Cristiano Ronaldo Champions League comeback match', 'hashtags': ['#Shorts', '#كرة_القدم', '#رونالدو']}, {'search': 'ميسي والتمريرة التي سبقت الهدف', 'fallback_searches': ['ميسي والتمريرة football match', 'ميسي والتمريرة action'], 'title': 'في بعض الهجمات تكون التمريرة قبل الأخيرة هي التي تفتح كل شيء، وليس اللمسة الأخيرة فقط.', 'text': 'Lionel Messi key pass match', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'هالاند والهجمة التي تحتاج ثانيتين فقط', 'fallback_searches': ['هالاند والهجمة football match', 'هالاند والهجمة action'], 'title': 'عندما يتحرك هالاند خلف المدافع في اللحظة المناسبة، قد تختصر الهجمة إلى تمريرة واحدة وتسديدة مباشرة.', 'text': 'Erling Haaland quick attack match', 'hashtags': ['#Shorts', '#كرة_القدم', '#هالاند']}, {'search': 'صلاح وكيف تتحول أول لمسة إلى فرصة', 'fallback_searches': ['صلاح وكيف football match', 'صلاح وكيف action'], 'title': 'استلام صلاح باتجاه المرمى بدل الوقوف على الكرة يسمح له بتحويل المساحة الصغيرة إلى هجمة سريعة.', 'text': 'Mohamed Salah first touch attack match', 'hashtags': ['#Shorts', '#كرة_القدم', '#صلاح']}, {'search': 'ميسي وكيف يحافظ على الكرة قريبة من قدمه', 'fallback_searches': ['ميسي وكيف football match', 'ميسي وكيف action'], 'title': 'المسافة القصيرة بين الكرة والقدم تمنح ميسي فرصة لتغيير الاتجاه بسرعة عندما يقترب المدافع.', 'text': 'Lionel Messi close control dribbling', 'hashtags': ['#Shorts', '#كرة_القدم', '#ميسي']}, {'search': 'رونالدو وحركة القدم حول الكرة', 'fallback_searches': ['رونالدو وحركة football match', 'رونالدو وحركة action'], 'title': 'حركات القدم السريعة تجبر المدافع على قراءة اتجاه محتمل قبل أن يقرر رونالدو الانطلاق.', 'text': 'Cristiano Ronaldo stepovers football', 'hashtags': ['#Shorts', '#كرة_القدم', '#رونالدو']}, {'search': 'مبابي وتغيير السرعة أثناء المراوغة', 'fallback_searches': ['مبابي وتغيير football match', 'مبابي وتغيير action'], 'title': 'الانتقال من سرعة متوسطة إلى انطلاقة مفاجئة قد يكون أصعب على المدافع من الجري بأقصى سرعة طوال الوقت.', 'text': 'Kylian Mbappe acceleration dribbling', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'هالاند واللمسة الأولى داخل المنطقة', 'fallback_searches': ['هالاند واللمسة football match', 'هالاند واللمسة action'], 'title': 'اللمسة الأولى الجيدة تجعل الجسم في وضعية مناسبة للتسديد قبل أن يصل المدافع إلى اللاعب.', 'text': 'Erling Haaland first touch finishing', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'صلاح والدخول إلى الداخل بعد استلام الكرة', 'fallback_searches': ['صلاح والدخول football match', 'صلاح والدخول action'], 'title': 'التحرك من الجهة إلى العمق يفتح زاوية للتسديد ويجبر المدافع على تغيير اتجاهه.', 'text': 'Mohamed Salah cutting inside', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'نيمار والخداع قبل تغيير الاتجاه', 'fallback_searches': ['نيمار والخداع football match', 'نيمار والخداع action'], 'title': 'إشارة الجسم إلى اتجاه ثم تغيير القرار في اللحظة الأخيرة يمكن أن تفقد المدافع توازنه.', 'text': 'Neymar feint dribbling skill', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'فينيسيوس والسرعة بعد تجاوز المدافع', 'fallback_searches': ['فينيسيوس والسرعة football match', 'فينيسيوس والسرعة action'], 'title': 'بعد نجاح المراوغة، يصبح التسارع هو الجزء الذي يمنع المدافع من العودة إلى المواجهة.', 'text': 'Vinicius Junior acceleration dribbling', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'بيلينغهام وحماية الكرة بالجسم', 'fallback_searches': ['بيلينغهام وحماية football match', 'بيلينغهام وحماية action'], 'title': 'استخدام الجسم في المساحات الضيقة يسمح له بالحفاظ على الكرة ثم الدوران نحو المساحة المتاحة.', 'text': 'Jude Bellingham shielding ball', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'مودريتش والقدم الخارجية في التمرير', 'fallback_searches': ['مودريتش والقدم football match', 'مودريتش والقدم action'], 'title': 'القدم الخارجية تتيح تمرير الكرة من زاوية مختلفة مع إبقاء اتجاه الجسم أقل وضوحًا للمدافع.', 'text': 'Luka Modric outside foot pass', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'دي بروين والتمريرة البينية في توقيتها الصحيح', 'fallback_searches': ['دي بروين football match', 'دي بروين action'], 'title': 'التمريرة البينية الناجحة تحتاج أن تغادر القدم في اللحظة التي يبدأ فيها المهاجم بالتحرك.', 'text': 'Kevin De Bruyne through ball technique', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'ليفاندوفسكي وكيف يسبق المدافع بخطوة', 'fallback_searches': ['ليفاندوفسكي وكيف football match', 'ليفاندوفسكي وكيف action'], 'title': 'اختيار نقطة التحرك داخل المنطقة قبل وصول الكرة يعطي المهاجم أفضلية زمنية.', 'text': 'Robert Lewandowski positioning', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'بنزيما واللمسة التي تربط الخطوط', 'fallback_searches': ['بنزيما واللمسة football match', 'بنزيما واللمسة action'], 'title': 'التحكم بالكرة واللعب بلمسة أو لمستين يساعد المهاجم على ربط الوسط بالثلث الهجومي.', 'text': 'Karim Benzema link up play', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'ميسي وتغيير الاتجاه من دون إيقاف الكرة', 'fallback_searches': ['ميسي وتغيير football match', 'ميسي وتغيير action'], 'title': 'دفع الكرة أمام القدم أثناء الجري يسمح بتغيير المسار من دون فقدان السرعة بالكامل.', 'text': 'Lionel Messi change direction dribbling', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'رونالدو والتحرك قبل العرضية', 'fallback_searches': ['رونالدو والتحرك football match', 'رونالدو والتحرك action'], 'title': 'الركض نحو نقطة مختلفة قبل وصول العرضية يجعل المدافع مضطرًا إلى تغيير اتجاهه في وقت قصير.', 'text': 'Cristiano Ronaldo movement cross', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'مبابي وكيف يستخدم المساحة خلف الظهير', 'fallback_searches': ['مبابي وكيف football match', 'مبابي وكيف action'], 'title': 'الانطلاق خلف الظهير تحتاج توقيتًا دقيقًا حتى لا يبدأ اللاعب من وضعية تسلل أو يغلق المدافع المسار.', 'text': 'Kylian Mbappe movement behind defense', 'hashtags': ['#Shorts', '#كرة_القدم']}, {'search': 'هالاند واختيار نقطة التسديد', 'fallback_searches': ['هالاند واختيار football match', 'هالاند واختيار action'], 'title': 'داخل المنطقة، اختيار مكان استقبال الكرة قبل التسديد قد يكون أهم من قوة التسديدة نفسها.', 'text': 'Erling Haaland finishing technique', 'hashtags': ['#Shorts', '#كرة_القدم']}]

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



# ---------------------------------------------------------
# SMART VISUAL RELEVANCE
# ---------------------------------------------------------
# Pexels search can return generic football footage even when the query
# contains a famous player's name. These profiles let the pipeline build
# several precise searches around the actual player(s) and the visual
# context of the topic, then select clips from those relevant groups.
VISUAL_PLAYER_PROFILES = {
    "messi": {
        "names": ["lionel messi", "messi"],
        "arabic": ["ميسي", "ليونيل ميسي"],
    },
    "ronaldo": {
        "names": ["cristiano ronaldo", "ronaldo"],
        "arabic": ["رونالدو", "كريستيانو رونالدو"],
    },
    "mbappe": {
        "names": ["kylian mbappe", "mbappe"],
        "arabic": ["مبابي", "كيليان مبابي"],
    },
    "haaland": {
        "names": ["erling haaland", "haaland"],
        "arabic": ["هالاند", "إيرلينغ هالاند"],
    },
    "salah": {
        "names": ["mohamed salah", "salah"],
        "arabic": ["صلاح", "محمد صلاح"],
    },
    "neymar": {
        "names": ["neymar", "neymar jr"],
        "arabic": ["نيمار"],
    },
    "modric": {
        "names": ["luka modric", "modric"],
        "arabic": ["مودريتش", "لوكا مودريتش"],
    },
    "de_bruyne": {
        "names": ["kevin de bruyne", "de bruyne"],
        "arabic": ["دي بروين", "كيفين دي بروين"],
    },
    "benzema": {
        "names": ["karim benzema", "benzema"],
        "arabic": ["بنزيما", "كريم بنزيما"],
    },
    "lewandowski": {
        "names": ["robert lewandowski", "lewandowski"],
        "arabic": ["ليفاندوفسكي", "روبرت ليفاندوفسكي"],
    },
    "vinicius": {
        "names": ["vinicius junior", "vinicius jr", "vinicius"],
        "arabic": ["فينيسيوس", "فينيسيوس جونيور"],
    },
    "bellingham": {
        "names": ["jude bellingham", "bellingham"],
        "arabic": ["بيلينغهام", "جود بيلينغهام"],
    },
}

VISUAL_CONTEXT_TERMS = [
    ("dribble", ["dribbling", "football match action"]),
    ("dribbling", ["dribbling", "football match action"]),
    ("goal", ["goal celebration", "football match action"]),
    ("celebration", ["goal celebration", "football match"]),
    ("shoot", ["shooting", "football match action"]),
    ("shot", ["shooting", "football match action"]),
    ("free kick", ["free kick", "football match"]),
    ("header", ["header", "football match"]),
    ("pass", ["passing", "football match action"]),
    ("assist", ["assist", "football match action"]),
    ("cross", ["crossing", "football match"]),
    ("sprint", ["sprinting", "football match action"]),
    ("speed", ["sprinting", "football match action"]),
    ("skills", ["football skills", "dribbling"]),
    ("skill", ["football skill", "dribbling"]),
    ("ball control", ["ball control", "football match"]),
    ("first touch", ["first touch", "football match"]),
    ("finishing", ["finishing", "football match action"]),
    ("striker", ["striker", "football match action"]),
    ("midfield", ["midfielder", "football match action"]),
    ("passing", ["passing", "football match action"]),
    ("through ball", ["through ball", "football match"]),
    ("trophy", ["football trophy", "player celebration"]),
    ("ballon d'or", ["football awards", "football player ceremony"]),
    ("world cup", ["world cup football", "football match"]),
    ("champions league", ["champions league football", "football match"]),
    ("premier league", ["premier league football", "football match"]),
]

def _topic_search_text(topic):
    return " ".join(
        clean_text(str(topic.get(key, "")))
        for key in ("search", "title", "text")
    ).lower()


def detect_visual_players(topic):
    """Return the famous-player profiles explicitly present in this topic."""
    combined = _topic_search_text(topic)
    found = []

    for key, profile in VISUAL_PLAYER_PROFILES.items():
        if any(name.lower() in combined for name in profile["names"]):
            found.append(key)
            continue

        if any(name in combined for name in profile["arabic"]):
            found.append(key)

    return found


def detect_visual_context(topic):
    """Extract the concrete football action/event from the topic."""
    combined = _topic_search_text(topic)
    found = []

    for trigger, variants in VISUAL_CONTEXT_TERMS:
        if trigger in combined:
            found.extend(variants)

    unique = []
    seen = set()
    for item in found:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique[:4]


def build_visual_query_groups(topic):
    """
    Build relevance-first query groups.

    A group belongs to one explicit player. Comparison topics therefore
    produce separate player groups instead of one vague comparison query.
    """
    players = detect_visual_players(topic)
    context = detect_visual_context(topic)

    primary = clean_text(topic.get("search", ""))
    groups = []

    if not players:
        fallback = [primary] if primary else []
        for query in topic.get("fallback_searches", []):
            query = clean_text(query)
            if query and query not in fallback:
                fallback.append(query)
        return [fallback[:5]] if fallback else []

    for player_key in players:
        profile = VISUAL_PLAYER_PROFILES[player_key]
        full_name = profile["names"][0]

        queries = [
            f"{full_name} football match action",
            f"{full_name} professional football match",
        ]

        for action in context:
            queries.append(f"{full_name} {action}")

        if primary and any(
            name.lower() in primary.lower() for name in profile["names"]
        ):
            queries.insert(0, primary)

        unique = []
        seen = set()
        for query in queries:
            query = clean_text(query)
            key = query.lower()
            if query and key not in seen:
                seen.add(key)
                unique.append(query)

        groups.append(unique[:6])

    return groups


def build_visual_queries(topic):
    """Compatibility wrapper: return all relevance-first searches."""
    groups = build_visual_query_groups(topic)
    queries = []

    for group in groups:
        for query in group:
            if query.lower() not in {q.lower() for q in queries}:
                queries.append(query)

    return queries[:18]


def _candidate_score(video, query_rank, group_rank, portrait, resolution_score):
    """Score relevance before resolution."""
    relevance = max(0, 1000 - (query_rank * 90) - (group_rank * 25))
    format_bonus = 180 if portrait else 0
    quality = min(160, resolution_score / 25000)
    return relevance + format_bonus + quality


def select_unique_videos(topic, used_clips):
    groups = build_visual_query_groups(topic)

    if not groups:
        raise RuntimeError("Could not build relevant visual searches for the topic.")

    players = detect_visual_players(topic)
    print("Visual subjects:", ", ".join(players) if players else "fallback")

    candidates_by_group = []
    global_candidates = {}

    for group_index, queries in enumerate(groups):
        group_candidates = {}

        for query_rank, query in enumerate(queries):
            print(
                f"Searching Pexels [subject {group_index + 1}, "
                f"query {query_rank + 1}]: {query}"
            )

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
                    portrait = height > width
                    resolution_score = min(width, 1080) * min(height, 1920)

                    score = _candidate_score(
                        video,
                        query_rank,
                        group_index,
                        portrait,
                        resolution_score,
                    )

                    item = {
                        "id": video_id,
                        "link": video_file["link"],
                        "width": width,
                        "height": height,
                        "portrait": portrait,
                        "score": score,
                        "subject_group": group_index,
                        "query_rank": query_rank,
                        "query": query,
                    }

                    old = group_candidates.get(video_id)
                    if old is None or item["score"] > old["score"]:
                        group_candidates[video_id] = item

                    old_global = global_candidates.get(video_id)
                    if old_global is None or item["score"] > old_global["score"]:
                        global_candidates[video_id] = item

                if len(group_candidates) >= 30:
                    break

            if len(group_candidates) >= 30:
                break

        candidates_by_group.append(
            sorted(
                group_candidates.values(),
                key=lambda item: item["score"],
                reverse=True,
            )
        )

    # Guarantee subject coverage first. For comparison topics this prevents
    # nine clips of one player when the topic explicitly names two players.
    selected = []
    selected_ids = set()

    while len(selected) < NUMBER_OF_CLIPS:
        added_this_round = False

        for group in candidates_by_group:
            if len(selected) >= NUMBER_OF_CLIPS:
                break

            while group and group[0]["id"] in selected_ids:
                group.pop(0)

            if not group:
                continue

            item = group.pop(0)
            selected.append(item)
            selected_ids.add(item["id"])
            added_this_round = True

        if not added_this_round:
            break

    # Fill remaining slots only from other high-relevance candidates for
    # this exact topic, never from an unrelated generic pool.
    if len(selected) < NUMBER_OF_CLIPS:
        remaining = [
            item for item in global_candidates.values()
            if item["id"] not in selected_ids
        ]
        remaining.sort(key=lambda item: item["score"], reverse=True)

        for item in remaining:
            if len(selected) >= NUMBER_OF_CLIPS:
                break
            selected.append(item)
            selected_ids.add(item["id"])

    if len(selected) < NUMBER_OF_CLIPS:
        raise RuntimeError(
            f"Not enough NEW relevant Pexels clips. Found {len(selected)}, "
            f"need {NUMBER_OF_CLIPS}."
        )

    print("\nSELECTED RELEVANT PEXELS CLIPS:")
    for index, item in enumerate(selected, start=1):
        print(
            f"  {index:02d}. ID={item['id']} | "
            f"subject_group={item['subject_group'] + 1} | "
            f"score={item['score']:.1f} | query={item['query']}"
        )

    return selected[:NUMBER_OF_CLIPS]

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
