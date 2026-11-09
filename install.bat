@echo off
chcp 65001 > nul
title Install Requirements | تثبيت متطلبات الأداة
cd /d "%~dp0"

echo ========================================================
echo       جاري تثبيت المكتبات المطلوبة لأداة الرفع
echo ========================================================
echo.

python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ========================================================
if %ERRORLEVEL% EQU 0 (
    echo [OK] تم تثبيت جميع المكتبات بنجاح!
    echo يمكنك الآن تشغيل الأداة مباشرة عبر الملف: run.bat
) else (
    echo [ERROR] حدث خطأ أثناء التثبيت. تأكد من اتصال الإنترنت وتثبيت Python.
)
echo ========================================================
echo.
pause
