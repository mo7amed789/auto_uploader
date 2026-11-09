@echo off
chcp 65001 > nul
title Instagram Auto-Uploader
cd /d "%~dp0"

echo ========================================================
echo     Instagram Reels Auto-Uploader ^| اداة الرفع التلقائي
echo ========================================================
echo.

:: فحص ما إذا كانت المكتبات مثبتة، وتثبيتها تلقائياً إن لزم الأمر
python -c "import instagrapi, moviepy, imageio_ffmpeg" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] يبدو أن بعض المكتبات غير مثبتة، جاري تثبيتها تلقائياً لأول مرة...
    pip install -r requirements.txt
    echo.
)

echo جاري تشغيل واجهة البرنامج...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo حدث خطأ اثناء التشغيل. اضغط اي زر للإغلاق.
    pause > nul
)
