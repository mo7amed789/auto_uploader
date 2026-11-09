@echo off
chcp 65001 > nul
title Instagram Auto-Uploader
cd /d "%~dp0"

echo ========================================================
echo     Instagram Reels Auto-Uploader ^| أداة الرفع التلقائي
echo ========================================================
echo.

:: 1. فحص وجود بايثون في النظام
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [X] خطأ: لم يتم العثور على Python في هذا الجهاز!
    echo.
    echo الحل:
    echo 1. تأكد من تثبيت بايثون من الموقع الرسمي: https://www.python.org/downloads/
    echo 2. أثناء التثبيت، تأكد من وضع علامة صح على: "Add python.exe to PATH"
    echo 3. إذا كنت قد قمت بتثبيته للتو، أعد تشغيل الجهاز أو أغلق النوافذ وافتحها من جديد.
    echo.
    echo اضغط أي زر للإغلاق...
    pause > nul
    exit /b
)

:: 2. فحص وتثبيت المكتبات إن كانت ناقصة
python -c "import instagrapi, imageio_ffmpeg" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] يبدو أن بعض المكتبات غير مثبتة، جاري تثبيتها تلقائياً الآن...
    pip install -r requirements.txt
    echo.
)

:: 3. تشغيل واجهة البرنامج
echo جاري تشغيل البرنامج...
python main.py

:: 4. إبقاء النافذة مفتوحة دائماً في حال حدوث أي خطأ
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] حدث خطأ أثناء تشغيل البرنامج (انظر للرسالة أعلاه لمعرفة السبب).
    echo.
)

echo.
echo تم إغلاق البرنامج. اضغط أي زر للخروج...
pause > nul
