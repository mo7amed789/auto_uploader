# أداة الرفع التلقائي للريلز والشورتس (Instagram & YouTube Auto-Uploader)

أداة سطح مكتب بواجهة رسومية بسيطة وسهلة الاستخدام لرفع مقاطع الفيديو المخزنة على جهاز الكمبيوتر إلى **Instagram Reels** و **YouTube Shorts** في نفس الوقت أو لكل منصة على حدة، مع جدولة ذكية وفواصل زمنية لمنع الحظر.

---

## 🌟 المميزات الرئيسية

1. **دعم المنصات المتعددة (Multi-Platform)**:
   * **Instagram Reels**: رفع كامل الدقة مع استخراج تلقائي للغلاف وحفظ الجلسات.
   * **YouTube Shorts**: رفع رسمي عبر واجهة **YouTube Data API v3** مع إضافة وسوم `#Shorts` والتحكم بالخصوصية (`public` / `unlisted` / `private`).
   * إمكانية اختيار المنصات المستهدفة بنقرة واحدة (رفع لإنستغرام فقط، أو يوتيوب فقط، أو كلاهما معاً).
2. **واجهة رسومية تفاعلية (Desktop GUI)**: تمكنك من اختيار الفيديوهات الفردية أو استيراد مجلد كامل.
3. **حفظ جلسات تسجيل الدخول**:
   * إنستغرام: حفظ الجلسة محلياً (`session.json`) مع دعم كود `sessionid`.
   * يوتيوب: حفظ توكن المصادقة (`youtube_token.json`) وتجديده تلقائياً.
4. **فواصل زمنية ذكية (Anti-Ban Delay)**: تحديد وقت انتظار بين كل فيديو لتفادي تقييد الحسابات.
5. **استخراج تلقائي للغلاف (Thumbnail)**: عبر `ffmpeg` المدمج دون الحاجة لأي برامج خارجية.
6. **دعم سطر الأوامر (CLI Mode)**: إمكانية تشغيل الأداة عبر الـ Terminal بدون شاشة رسومية.

---

## 🚀 طريقة التشغيل السريعة

### تشغيل الواجهة الرسومية:
فقط اضغط مرتين على ملف:
```
run.bat
```
أو عبر سطر الأوامر:
```powershell
python main.py
```

---

## ⚙️ تشغيل عبر سطر الأوامر (CLI Mode)

* **الرفع لإنستغرام فقط**:
  ```powershell
  python main.py --cli --sessionid "YOUR_SESSION_ID" --folder "C:\Path\To\Videos" --delay 15
  ```
* **الرفع ليوتيوب شورتس فقط**:
  ```powershell
  python main.py --cli --youtube --no-instagram --folder "C:\Path\To\Videos" --delay 10
  ```
* **الرفع للمنصتين معاً (Instagram + YouTube)**:
  ```powershell
  python main.py --cli --sessionid "YOUR_SESSION_ID" --youtube --folder "C:\Path\To\Videos" --delay 15
  ```
