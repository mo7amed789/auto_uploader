"""
Instagram Reels Auto-Uploader
نقطة انطلاق البرنامج (تشغيل الواجهة الرسومية GUI أو سطر الأوامر CLI)
"""

import sys
import argparse
import os

# ضبط ترميز الإخراج ليدعم اللغة العربية في ويندوز
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# إضافة المجلد الحالي للمسار
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def main():
    parser = argparse.ArgumentParser(
        description="أداة رفع فيديوهات YouTube Shorts / Reels إلى إنستغرام تلقائياً"
    )
    parser.add_argument("--cli", action="store_true", help="تشغيل البرنامج في وضع سطر الأوامر بدون واجهة رسومية")
    parser.add_argument("--sessionid", type=str, help="كود Session ID من المتصفح (موصى به لتفادي مشاكل تسجيل الدخول)")
    parser.add_argument("--username", type=str, help="اسم مستخدم إنستغرام")
    parser.add_argument("--password", type=str, help="كلمة مرور إنستغرام")
    parser.add_argument("--folder", type=str, help="مسار مجلد الفيديوهات للرفع")
    parser.add_argument("--delay", type=int, default=15, help="الفاصل الزمني بين الفيديوهات بالدقائق (الافتراضي: 15)")
    parser.add_argument("--hashtags", type=str, default="#reels #shorts #viral", help="الهاشتاجات")

    args = parser.parse_args()

    if args.cli:
        if not args.folder or (not args.sessionid and (not args.username or not args.password)):
            print("خطأ: يتطلب وضع CLI توفير --folder وأيضاً (--sessionid أو --username مع --password)")
            sys.exit(1)

        from uploader_engine import InstagramUploaderEngine
        from pathlib import Path

        engine = InstagramUploaderEngine(work_dir=current_dir)
        if args.sessionid:
            print("[*] جاري تسجيل الدخول باستخدام Session ID...")
            if not engine.login_by_sessionid(args.sessionid):
                print("[-] فشل تسجيل الدخول عبر Session ID. تأكد من صحة الكود.")
                sys.exit(1)
        else:
            print(f"[*] جاري تسجيل الدخول بحساب: {args.username}")
            if not engine.login(args.username, args.password):
                print("[-] فشل تسجيل الدخول. تأكد من البيانات أو راجع الأمان في إنستغرام.")
                sys.exit(1)

        # جمع الفيديوهات
        folder_path = Path(args.folder)
        if not folder_path.exists():
            print(f"[-] المجلد غير موجود: {args.folder}")
            sys.exit(1)

        valid_exts = {".mp4", ".mov", ".avi", ".m4v"}
        videos = []
        for f in sorted(folder_path.glob("*")):
            if f.suffix.lower() in valid_exts:
                videos.append({"path": str(f.resolve())})

        if not videos:
            print("[-] لم يتم العثور على أي ملفات فيديو صالحة في المجلد.")
            sys.exit(0)

        print(f"[+] تم العثور على {len(videos)} فيديو. بدء الرفع التلقائي...")
        engine.start_batch_upload(
            video_list=videos,
            caption_template="{filename}",
            hashtags=args.hashtags,
            delay_minutes=args.delay,
            logger_callback=lambda msg: print(f"[LOG] {msg}")
        )
    else:
        from gui import launch
        launch()

if __name__ == "__main__":
    main()
