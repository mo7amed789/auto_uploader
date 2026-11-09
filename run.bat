@echo off
chcp 65001 > nul
title Instagram Auto-Uploader
cd /d "%~dp0"

echo ========================================================
echo     Instagram Reels Auto-Uploader ^| اداة الرفع التلقائي
echo ========================================================
echo.
echo جاري فحص وتشغيل البرنامج...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo حدث خطأ اثناء التشغيل. اضغط اي زر للإغلاق.
    pause > nul
)
