#!/usr/bin/env python3
"""المنسّق اليومي للنظام الجديد.

الترتيب:
  1. اختيار موضوع لم يُنتج من قبل (من topics.json مقابل used_content.json)
  2. إنتاج الفيديو بواسطة MoneyPrinterTurbo (حتى 3 محاولات)
  3. فحص الجودة (check_video.py) - إذا فشل لا يُنشر شيء
  4. الرفع إلى YouTube حسب PRIVACY: private | unlisted | public | none
     (none = تجربة بدون رفع ولا حفظ ذاكرة)
  5. حفظ الموضوع ومعرّف الفيديو في used_content.json
     وحفظ معرّفات مقاطع Pexels في used_pexels.json

متغيرات البيئة المطلوبة:
  MPT_DIR, RUN_PY            (يضبطها الـ workflow)
  PRIVACY                    (الافتراضي private)
  FORCE_TOPIC_ID             (اختياري: لتجربة موضوع محدد)
  YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN
                             (مطلوبة فقط عند الرفع)
لا يطبع هذا السكربت أي قيمة سرية.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
