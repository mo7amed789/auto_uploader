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
    os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_exe
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
        self.skip_wait_event = False
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

    def _generate_thumbnail(self, video_path: Path) -> Optional[Path]:
        """
        استخراج صورة مصغرة (Thumbnail) للفيديو باستخدام ffmpeg لتفادي مشكلة MoviePy
        """
        thumb_path = video_path.parent / f"{video_path.stem}_thumb.jpg"
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_exe

            # استخراج أول إطار (فريم) من بداية الفيديو
            cmd = [
                ffmpeg_exe,
                "-y",
                "-ss", "0",
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", "2",
                str(thumb_path)
            ]
            import subprocess
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if thumb_path.exists() and thumb_path.stat().st_size > 0:
                return thumb_path
        except Exception as e:
            print(f"Warning: ffmpeg thumbnail generation failed: {e}")

        # صورة احتياطية في حال فشل الاستخراج
        try:
            from PIL import Image
            img = Image.new("RGB", (1080, 1920), color=(18, 18, 18))
            img.save(thumb_path, "JPEG")
            return thumb_path
        except Exception:
            return None

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
        thumb_path = self._generate_thumbnail(path)

        try:
            kwargs = {
                "path": path,
                "caption": caption,
            }
            if thumb_path and thumb_path.exists():
                kwargs["thumbnail"] = thumb_path

            media = self.client.clip_upload(**kwargs)
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
        finally:
            # تنظيف ملف الصورة المصغرة المؤقت
            if thumb_path and thumb_path.exists():
                try:
                    thumb_path.unlink()
                except Exception:
                    pass

    def start_batch_upload(
        self,
        video_list: List[Dict[str, str]],
        caption_template: str,
        hashtags: str,
        delay_minutes: int,
        upload_to_instagram: bool = True,
        upload_to_youtube: bool = False,
        youtube_engine = None,
        youtube_privacy: str = "public",
        progress_callback: Optional[Callable[[int, int, str, str], None]] = None,
        countdown_callback: Optional[Callable[[str], None]] = None,
        logger_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        تشغيل قائمة الانتظار لرفع الفيديوهات إلى إنستغرام و/أو يوتيوب
        """
        def log(msg: str):
            if logger_callback:
                logger_callback(msg)
            print(msg)

        self.is_running = True
        self.is_paused = False
        self.skip_wait_event = False
        total = len(video_list)

        destinations = []
        if upload_to_instagram:
            destinations.append("Instagram Reels")
        if upload_to_youtube:
            destinations.append("YouTube Shorts")

        log(f"بدء عملية الرفع التلقائي لعدد {total} فيديو...")
        log(f"المنصات المستهدفة: {' + '.join(destinations)}")
        if delay_minutes <= 0:
            log("الفاصل الزمني: 0 (رفع فوري متتالي لجميع الفيديوهات بدون انتظار).")
        else:
            log(f"الفاصل الزمني المختار بين كل فيديو: {delay_minutes} دقيقة.")

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

            ig_success = False
            yt_success = False

            # 1. الرفع إلى إنستغرام
            if upload_to_instagram:
                log(f"-> [إنستغرام] جاري رفع الريل...")
                try:
                    res_ig = self.upload_single_reel(
                        video_path=video_path,
                        caption=clean_caption,
                        logger_callback=logger_callback
                    )
                    if res_ig:
                        ig_success = True
                except RateLimitError:
                    log("تنبيه: تم فرض قيود مؤقتة من إنستغرام على النشر السريع.")
                except Exception as e:
                    log(f"خطأ إنستغرام: {e}")

            # 2. الرفع إلى يوتيوب
            if upload_to_youtube and youtube_engine and youtube_engine.is_logged_in():
                log(f"-> [يوتيوب] جاري رفع الشورت...")
                try:
                    raw_tags = [t.strip("#").strip() for t in hashtags.split() if t.strip()]
                    res_yt = youtube_engine.upload_short_or_video(
                        video_path=video_path,
                        title=filename,
                        description=clean_caption,
                        tags=raw_tags,
                        privacy_status=youtube_privacy,
                        is_short=True,
                        logger_callback=logger_callback
                    )
                    if res_yt:
                        yt_success = True
                except Exception as e:
                    log(f"خطأ يوتيوب: {e}")

            # تحديد حالة الفيديو النهائية
            if upload_to_instagram and upload_to_youtube:
                if ig_success and yt_success:
                    status = "completed_both"
                elif ig_success:
                    status = "completed_ig_only"
                elif yt_success:
                    status = "completed_yt_only"
                else:
                    status = "failed"
            elif upload_to_youtube:
                status = "completed" if yt_success else "failed"
            else:
                status = "completed" if ig_success else "failed"

            if progress_callback:
                progress_callback(index + 1, total, video_path, status)

            # إذا لم يكن هذا آخر فيديو وكانت العملية مستمرة، ننتقل للفاصل أو التالي فوراً
            if index < total - 1 and self.is_running:
                if delay_minutes <= 0:
                    log("فاصل زمني 0: الانتقال مباشرة لرفع الفيديو التالي...")
                    time.sleep(2)
                else:
                    wait_seconds = delay_minutes * 60
                    log(f"سيبدأ العد التنازلي لمدة {delay_minutes} دقيقة قبل رفع الفيديو التالي (يمكنك الضغط على 'تخطي الانتظار' للرفع فوراً)...")
                    self.skip_wait_event = False
                    start_wait = time.time()
                    while time.time() - start_wait < wait_seconds:
                        if not self.is_running:
                            log("تم إلغاء الانتظار وإيقاف العملية.")
                            break
                        if self.skip_wait_event:
                            log("تم تخطي فترة الانتظار بطلب منك، بدء معالجة الفيديو التالي فوراً 🚀")
                            self.skip_wait_event = False
                            break

                        remaining = int(wait_seconds - (time.time() - start_wait))
                        mins, secs = divmod(remaining, 60)
                        if countdown_callback:
                            countdown_callback(f"⏳ الانتظار: باقي {mins:02d}:{secs:02d} قبل الفيديو التالي")
                        if remaining % 30 == 0 or remaining <= 5:
                            log(f"الوقت المتبقي لرفع الفيديو التالي: {mins:02d}:{secs:02d}")
                        time.sleep(1)

                    if countdown_callback:
                        countdown_callback("")

        self.is_running = False
        if countdown_callback:
            countdown_callback("")
        log("\nانتهت معالجة جميع الفيديوهات في القائمة.")

    def skip_wait(self):
        """تخطي الانتظار والبدء بالفيديو التالي فوراً"""
        self.skip_wait_event = True

    def stop(self):
        self.is_running = False
        self.skip_wait_event = True
