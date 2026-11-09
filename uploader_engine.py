"""
Instagram Auto-Uploader Engine
محرك رفع الفيديوهات إلى إنستغرام ريلز تلقائياً
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from typing import Callable, Optional, List, Dict

# ضبط ترميز الإخراج ليدعم اللغة العربية في ويندوز
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# التأكد من إتاحة ffmpeg في مسار النظام
try:
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    target_ffmpeg = os.path.join(ffmpeg_dir, "ffmpeg.exe")
    if not os.path.exists(target_ffmpeg):
        import shutil
        shutil.copyfile(ffmpeg_exe, target_ffmpeg)
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except Exception as e:
    print(f"Warning: ffmpeg setup warning: {e}")

from instagrapi import Client
from instagrapi.exceptions import (
    BadPassword,
    TwoFactorRequired,
    ChallengeRequired,
    LoginRequired,
    RateLimitError,
    ClientError
)


class InstagramUploaderEngine:
    def __init__(self, work_dir: str = "."):
        self.work_dir = Path(work_dir)
        self.session_file = self.work_dir / "session.json"
        self.history_file = self.work_dir / "uploaded_history.json"
        self.client: Optional[Client] = None
        self.is_running = False
        self.is_paused = False
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
            print(f"Error saving history: {e}")

    def login_by_sessionid(
        self,
        sessionid: str,
        proxy: Optional[str] = None,
        logger_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        تسجيل الدخول عبر Session ID (كوكيز المتصفح)
        هذه الطريقة تتجاوز بالكامل خطأ 'Your version of Instagram is out of date'
        """
        def log(msg: str):
            if logger_callback:
                logger_callback(msg)
            print(msg)

        sessionid = sessionid.strip().strip('"').strip("'")
        if not sessionid:
            log("خطأ: لم يتم إدخال Session ID.")
            return False

        log("جاري التحقق من كود الجلسة (Session ID)...")
        self.client = Client()

        if proxy and proxy.strip():
            log(f"استخدام البروكسي: {proxy.strip()}")
            self.client.set_proxy(proxy.strip())

        try:
            self.client.login_by_sessionid(sessionid)
            self.client.dump_settings(self.session_file)
            username = getattr(self.client, "username", "Unknown")
            log(f"تم تسجيل الدخول بنجاح للحساب: @{username} وتم حفظ الجلسة!")
            return True
        except Exception as e:
            log(f"فشل تسجيل الدخول عبر Session ID: {str(e)}")
            log("تأكد من نسخ قيمة sessionid كاملة من المتصفح بشكل صحيح.")
            return False

    def login(
        self,
        username: str,
        password: str,
        proxy: Optional[str] = None,
        two_factor_callback: Optional[Callable[[], str]] = None,
        logger_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        تسجيل الدخول إلى إنستغرام مع دعم الجلسة المحفوظة و 2FA
        """
        def log(msg: str):
            if logger_callback:
                logger_callback(msg)
            print(msg)

        log(f"جاري تسجيل الدخول للحساب: {username} ...")
        self.client = Client()

        if proxy and proxy.strip():
            log(f"استخدام البروكسي: {proxy.strip()}")
            self.client.set_proxy(proxy.strip())

        # محاولة تحميل الجلسة السابقة
        if self.session_file.exists():
            try:
                log("محاولة استعادة الجلسة السابقة (Saved Session)...")
                self.client.load_settings(self.session_file)
                self.client.login(username, password)
                # فحص صلاحية الجلسة
                self.client.get_timeline_feed()
                log("تم تسجيل الدخول بنجاح عبر الجلسة المحفوظة!")
                return True
            except Exception as e:
                log(f"انتهت الجلسة السابقة أو غير صالحة ({e})، سيتم تسجيل الدخول من جديد...")

        # تسجيل دخول جديد
        try:
            self.client.login(username, password)
            self.client.dump_settings(self.session_file)
            log("تم تسجيل الدخول بنجاح وحفظ الجلسة للاستخدام المستقبلي.")
            return True

        except TwoFactorRequired:
            log("الحساب يتطلب كود المصادقة الثنائية (2FA)!")
            if two_factor_callback:
                code = two_factor_callback()
                if code:
                    log("جاري التحقق من كود 2FA...")
                    self.client.two_factor_login(code)
                    self.client.dump_settings(self.session_file)
                    log("تم تسجيل الدخول بنجاح عبر كود 2FA!")
                    return True
                else:
                    log("تم إلغاء إدخال كود 2FA.")
                    return False
            else:
                log("خطأ: يتطلب الحساب 2FA ولكن لا توجد نافذة لإدخال الكود.")
                return False

        except ChallengeRequired:
            log("تنبيه: إنستغرام يطلب تأكيد الهوية (Challenge). يرجى فتح التطبيق على هاتفك والموافقة على تسجيل الدخول ثم إعادة المحاولة.")
            return False

        except BadPassword:
            log("خطأ: كلمة المرور أو اسم المستخدم غير صحيح.")
            return False

        except Exception as e:
            log(f"خطأ أثناء تسجيل الدخول: {str(e)}")
            return False

    def is_logged_in(self) -> bool:
        if not self.client:
            return False
        try:
            return bool(self.client.user_id)
        except Exception:
            return False

    def upload_single_reel(
        self,
        video_path: str,
        caption: str = "",
        logger_callback: Optional[Callable[[str], None]] = None,
    ) -> Optional[dict]:
        """
        رفع فيديو واحد كـ Reel
        """
        def log(msg: str):
            if logger_callback:
                logger_callback(msg)
            print(msg)

        path = Path(video_path)
        if not path.exists():
            log(f"الملف غير موجود: {video_path}")
            return None

        if not self.client or not self.client.user_id:
            log("لم يتم تسجيل الدخول بعد!")
            return None

        log(f"جاري تحضير ورفع الريل: {path.name} ...")
        try:
            media = self.client.clip_upload(
                path=path,
                caption=caption,
            )
            media_dict = media.dict() if hasattr(media, "dict") else {"pk": getattr(media, "pk", str(time.time()))}
            log(f"تم رفع الريل بنجاح! ID: {media_dict.get('pk', 'N/A')}")
            
            # حفظ في السجل
            self.uploaded_history[str(path.resolve())] = {
                "name": path.name,
                "upload_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "pk": media_dict.get("pk"),
                "caption": caption
            }
            self._save_history()
            return media_dict

        except RateLimitError:
            log("تنبيه: إنستغرام فرض حد مؤقت (Rate Limit)! يجب إيقاف الرفع لعدة ساعات لتجنب تقييد الحساب.")
            raise
        except Exception as e:
            log(f"فشل رفع الفيديو {path.name}: {str(e)}")
            return None

    def start_batch_upload(
        self,
        video_list: List[Dict[str, str]],
        caption_template: str,
        hashtags: str,
        delay_minutes: int,
        progress_callback: Optional[Callable[[int, int, str, str], None]] = None,
        logger_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        تشغيل قائمة الانتظار لرفع الفيديوهات واحداً تلو الآخر مع فاصل زمني آمن
        """
        def log(msg: str):
            if logger_callback:
                logger_callback(msg)
            print(msg)

        self.is_running = True
        self.is_paused = False
        total = len(video_list)

        log(f"بدء عملية الرفع التلقائي لعدد {total} فيديو...")
        log(f"الفاصل الزمني المختار بين كل فيديو: {delay_minutes} دقيقة (لحماية الحساب من الحظر).")

        for index, item in enumerate(video_list):
            if not self.is_running:
                log("تم إيقاف عملية الرفع من قبل المستخدم.")
                break

            video_path = item["path"]
            filename = Path(video_path).stem

            # تجهيز الكابشن
            clean_caption = caption_template.replace("{filename}", filename).replace("{title}", filename)
            if hashtags.strip():
                clean_caption = f"{clean_caption}\n\n{hashtags.strip()}".strip()

            if progress_callback:
                progress_callback(index + 1, total, video_path, "uploading")

            log(f"\n[{index + 1}/{total}] جاري معالجة: {Path(video_path).name}")

            success = False
            try:
                result = self.upload_single_reel(
                    video_path=video_path,
                    caption=clean_caption,
                    logger_callback=logger_callback
                )
                if result:
                    success = True
            except RateLimitError:
                if progress_callback:
                    progress_callback(index + 1, total, video_path, "rate_limited")
                log("توقف فوري بسبب فرض قيود من إنستغرام.")
                break
            except Exception as e:
                log(f"خطأ غير متوقع: {e}")

            status = "completed" if success else "failed"
            if progress_callback:
                progress_callback(index + 1, total, video_path, status)

            # إذا لم يكن هذا آخر فيديو وكانت العملية مستمرة، ننتظر الفاصل الزمني
            if index < total - 1 and self.is_running:
                wait_seconds = max(delay_minutes * 60, 10)
                log(f"سيبدأ العد التنازلي لمدة {delay_minutes} دقيقة قبل رفع الفيديو التالي...")
                
                start_wait = time.time()
                while time.time() - start_wait < wait_seconds:
                    if not self.is_running:
                        log("تم إلغاء الانتظار وإيقاف العملية.")
                        break
                    remaining = int(wait_seconds - (time.time() - start_wait))
                    mins, secs = divmod(remaining, 60)
                    if remaining % 30 == 0 or remaining <= 5:
                        log(f"الوقت المتبقي لرفع الفيديو التالي: {mins:02d}:{secs:02d}")
                    time.sleep(1)

        self.is_running = False
        log("\nانتهت معالجة جميع الفيديوهات في القائمة.")

    def stop(self):
        self.is_running = False
