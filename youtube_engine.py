"""
YouTube Shorts & Video Uploader Engine
محرك رفع الفيديوهات إلى يوتيوب شورتس تلقائياً عبر واجهة YouTube Data API v3
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Callable, Optional, List, Dict

# ضبط ترميز الإخراج ليدعم اللغة العربية في ويندوز
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    YOUTUBE_DEPS_AVAILABLE = True
except ImportError:
    YOUTUBE_DEPS_AVAILABLE = False
    build = None
    MediaFileUpload = None
    InstalledAppFlow = None
    Request = None
    Credentials = None

# صلاحيات الرفع على يوتيوب
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]


class YouTubeUploaderEngine:
    def __init__(self, work_dir: str = "."):
        self.work_dir = Path(work_dir)
        self.token_file = self.work_dir / "youtube_token.json"
        self.client_secrets_file = self.work_dir / "client_secrets.json"
        self.history_file = self.work_dir / "youtube_history.json"
        self.service = None
        self.channel_title = None
        self.uploaded_history = self._load_history()

    def _load_history(self) -> Dict[str, dict]:
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_history(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.uploaded_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving YouTube history: {e}")

    def is_logged_in(self) -> bool:
        return self.service is not None

    def authenticate(
        self,
        client_secrets_path: Optional[str] = None,
        logger_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        تسجيل الدخول وربط قناة يوتيوب عبر OAuth 2.0
        """
        def log(msg: str):
            if logger_callback:
                logger_callback(msg)
            print(msg)

        if not YOUTUBE_DEPS_AVAILABLE:
            log("تنبيه: مكتبات Google API غير مثبتة في هذه البيئة (Python Environment).")
            log("لتثبيتها، قم بتشغيل الأمر: pip install -r requirements.txt")
            return False

        creds = None

        # 1. محاولة استعادة التوكن المحفوظ
        if self.token_file.exists():
            try:
                log("جاري استعادة جلسة يوتيوب المحفوظة (youtube_token.json)...")
                creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
            except Exception as e:
                log(f"تعذر قراءة التوكن المحفوظ: {e}")

        # 2. تجديد التوكن إذا كان منتهي الصلاحية
        if creds and creds.expired and creds.refresh_token:
            try:
                log("جاري تجديد صلاحية التوكن تلقائياً...")
                creds.refresh(Request())
                with open(self.token_file, "w", encoding="utf-8") as token:
                    token.write(creds.to_json())
                log("تم تجديد التوكن بنجاح!")
            except Exception as e:
                log(f"فشل تجديد التوكن: {e}")
                creds = None

        # 3. إذا لم يوجد توكن صالح، تسجيل دخول جديد عبر المتصفح
        if not creds or not creds.valid:
            secrets_file = Path(client_secrets_path) if client_secrets_path else self.client_secrets_file
            if not secrets_file.exists():
                log(f"خطأ: ملف client_secrets.json غير موجود في: {secrets_file}")
                log("يرجى تحديد مسار ملف client_secrets.json الذي قمت بتحميله من Google Cloud Console.")
                return False

            try:
                log("جاري فتح المتصفح لتسجيل الدخول واختيار قناة يوتيوب...")
                flow = InstalledAppFlow.from_client_secrets_file(str(secrets_file), SCOPES)
                creds = flow.run_local_server(port=0, prompt="consent")
                
                # حفظ التوكن
                with open(self.token_file, "w", encoding="utf-8") as token:
                    token.write(creds.to_json())
                log("تم حفظ بيانات الدخول بنجاح في youtube_token.json!")
            except Exception as e:
                log(f"فشل تسجيل الدخول عبر Google OAuth: {e}")
                return False

        try:
            self.service = build("youtube", "v3", credentials=creds)
            # جلب اسم القناة للتأكيد
            channels_response = self.service.channels().list(mine=True, part="snippet").execute()
            items = channels_response.get("items", [])
            if items:
                self.channel_title = items[0]["snippet"]["title"]
                log(f"تم ربط قناة يوتيوب بنجاح: {self.channel_title} ✅")
            else:
                self.channel_title = "قناة يوتيوب متصلة"
                log("تم الاتصال بيوتيوب بنجاح! ✅")
            return True
        except Exception as e:
            log(f"فشل الاتصال بخدمة YouTube Data API: {e}")
            self.service = None
            return False

    def upload_short_or_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        privacy_status: str = "public",
        is_short: bool = True,
        logger_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[dict]:
        """
        رفع فيديو أو شورت إلى يوتيوب
        """
        def log(msg: str):
            if logger_callback:
                logger_callback(msg)
            print(msg)

        if not self.service:
            log("لم يتم ربط قناة يوتيوب بعد!")
            return None

        path = Path(video_path)
        if not path.exists():
            log(f"الملف غير موجود: {video_path}")
            return None

        # إضافة وسم #Shorts للعنوان والوصف إذا كان شورت
        final_title = title.strip()
        if is_short and "#Shorts" not in final_title and "#shorts" not in final_title:
            final_title = f"{final_title} #Shorts"
        final_title = final_title[:100]  # حد أقصى للعنوان 100 حرف

        final_desc = description.strip()
        if is_short and "#Shorts" not in final_desc:
            final_desc = f"{final_desc}\n\n#Shorts #shorts".strip()

        final_tags = tags or ["Shorts", "YouTubeShorts", "Viral"]

        body = {
            "snippet": {
                "title": final_title,
                "description": final_desc,
                "tags": final_tags,
                "categoryId": "22",  # People & Blogs
                "defaultLanguage": "ar",
                "defaultAudioLanguage": "ar"
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False
            }
        }

        log(f"جاري رفع الفيديو إلى يوتيوب ({privacy_status}): {final_title} ...")
        try:
            media = MediaFileUpload(
                str(path),
                chunksize=1024 * 1024 * 5,  # 5MB chunks
                resumable=True
            )

            request = self.service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    percent = int(status.progress() * 100)
                    log(f"نسبة رفع يوتيوب: {percent}%")

            video_id = response.get("id")
            video_url = f"https://youtu.be/{video_id}"
            log(f"تم رفع الفيديو على يوتيوب بنجاح! الرابط: {video_url} ✅")

            # حفظ في السجل
            self.uploaded_history[str(path.resolve())] = {
                "name": path.name,
                "upload_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "video_id": video_id,
                "url": video_url,
                "title": final_title
            }
            self._save_history()

            return response

        except Exception as e:
            log(f"فشل الرفع إلى يوتيوب ({path.name}): {str(e)}")
            return None
