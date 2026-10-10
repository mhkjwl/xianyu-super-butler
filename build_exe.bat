@echo off
REM ============================================================
REM  Xianyu Super Butler - EXE build script (Nuitka standalone)
REM
REM  Pipeline: compile main -> compile GUI shell -> assemble -> zip -> installer
REM  Output  : release\xianyu-super-butler\                (portable folder)
REM              - 闲鱼超级管家.exe (GUI shell with tray, user entry)
REM              - xianyu-butler.exe (backend service, hidden)
REM            release\xianyu-super-butler-portable-3.2.0.zip
REM            release\XianyuSuperButler-Setup-3.2.0.exe     (installer)
REM
REM  Requires build venv with:
REM    pip install -r requirements.txt -r requirements-build.txt
REM    python -m playwright install chromium
REM  IMPORTANT: run OUTSIDE any sandbox/restricted environment,
REM  otherwise the C compiler (zig) fails with AccessDenied.
REM ============================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if "%PY%"=="" set "PY=C:\Users\AO\.workbuddy\binaries\python\envs\xianyu-butler\Scripts\python.exe"

echo [1/6] Check build environment ...
"%PY%" -c "import nuitka, playwright, patchright, DrissionPage, webview, pystray" 1>nul 2>nul
if errorlevel 1 (
    echo   [ERROR] Build dependencies missing.
    echo   Install: "%PY%" -m pip install -r requirements.txt -r requirements-build.txt pywebview pystray
    goto :fail
)

echo [2/6] Nuitka compile main program ^(this may take 1-3 hours^) ...
"%PY%" -m nuitka --standalone --assume-yes-for-downloads ^
 --windows-console-mode=force ^
 --windows-company-name=XianyuButler ^
 --windows-product-name=XianyuSuperButler ^
 --windows-file-version=3.2.0.0 ^
 --windows-product-version=3.2.0.0 ^
 --output-filename=xianyu-butler.exe ^
 --output-dir=dist_build ^
 --include-package=app ^
 --include-package=utils ^
 --include-package=playwright ^
 --include-package-data=playwright ^
 --include-package=patchright ^
 --include-package-data=patchright ^
 --include-package=DrissionPage ^
 --include-package-data=DrissionPage ^
 --include-package=DrissionRecord ^
 --include-package=DrissionGet ^
 --include-package=execjs ^
 --include-package=blackboxprotobuf ^
 --include-package=google.protobuf ^
 --include-package=openai ^
 --include-package=jiter ^
 --include-package=fastapi ^
 --include-package=starlette ^
 --include-package=pydantic ^
 --include-package=pydantic_core ^
 --include-package=anyio ^
 --include-package=sniffio ^
 --include-package=h11 ^
 --include-package=click ^
 --include-package=colorama ^
 --include-package=uvicorn ^
 --include-package=watchfiles ^
 --include-package=httptools ^
 --include-package=email_validator ^
 --include-package=dns ^
 --include-package=multipart ^
 --include-package=dotenv ^
 --include-package=yaml ^
 --include-package=websockets ^
 --include-package=aiohttp ^
 --include-package=aiosignal ^
 --include-package=aiohappyeyeballs ^
 --include-package=multidict ^
 --include-package=yarl ^
 --include-package=frozenlist ^
 --include-package=propcache ^
 --include-package=attrs ^
 --include-package=httpx ^
 --include-package=httpcore ^
 --include-package=httpx2 ^
 --include-package=httpcore2 ^
 --include-package=requests ^
 --include-package=urllib3 ^
 --include-package=charset_normalizer ^
 --include-package=certifi ^
 --include-package=idna ^
 --include-package=tldextract ^
 --include-package-data=tldextract ^
 --include-package=requests_file ^
 --include-package=filelock ^
 --include-package=pandas ^
 --include-package=numpy ^
 --include-package=openpyxl ^
 --include-package=et_xmlfile ^
 --include-package=xlsxwriter ^
 --include-package=passlib ^
 --include-package=bcrypt ^
 --include-package=jwt ^
 --include-package=cryptography ^
 --include-package=cffi ^
 --include-package=pycparser ^
 --include-package=loguru ^
 --include-package=win32_setctime ^
 --include-package=psutil ^
 --include-package=PIL ^
 --include-package=qrcode ^
 --include-package=dateutil ^
 --include-package=six ^
 --include-package=typing_extensions ^
 --include-package=typing_inspection ^
 --include-package=annotated_doc ^
 --include-package=annotated_types ^
 --include-package=lxml ^
 --include-package=cssselect ^
 --include-package=websocket ^
 --include-package=greenlet ^
 --include-package=pyee ^
 --nofollow-import-to=test ^
 --nofollow-import-to=tests ^
 --nofollow-import-to=setuptools ^
 --nofollow-import-to=pip ^
 --nofollow-import-to=nuitka ^
 --nofollow-import-to=unittest ^
 --nofollow-import-to=pandas.tests ^
 --nofollow-import-to=passlib.tests ^
 --nofollow-import-to=qrcode.tests ^
 --nofollow-import-to=pygments ^
 --nofollow-import-to=pydoc ^
 --nofollow-import-to=doctest ^
 Start.py
if errorlevel 1 (
    echo   [ERROR] Nuitka compile failed.
    goto :fail
)

echo [3/6] Nuitka compile GUI shell ^(onefile, a few minutes^) ...
"%PY%" -m nuitka --onefile --assume-yes-for-downloads ^
 --windows-console-mode=disable ^
 --windows-icon-from-ico=packaging\app.ico ^
 --output-filename=XianyuSuperButler.exe ^
 --output-dir=gui_build ^
 --include-package=pythonnet ^
 --include-package-data=pythonnet ^
 --include-package=clr_loader ^
 --include-package-data=clr_loader ^
 --include-package=pystray ^
 --include-package=psutil ^
 --include-data-file=packaging\app.ico=app.ico ^
 gui_launcher.py
if errorlevel 1 (
    echo   [ERROR] GUI shell compile failed.
    goto :fail
)

echo [4/6] Assemble portable folder ...
"%PY%" "packaging\assemble.py"
if errorlevel 1 (
    echo   [ERROR] Assembly failed.
    goto :fail
)

echo [5/6] Zip package ...
"%PY%" "packaging\make_zip.py"
if errorlevel 1 (
    echo   [ERROR] Zip failed.
    goto :fail
)

echo [6/6] Build installer ^(Inno Setup, may take 20-40 minutes^) ...
if exist ".workbuddy\innosetup\app\ISCC.exe" (
    ".workbuddy\innosetup\app\ISCC.exe" "packaging\installer.iss"
    if errorlevel 1 (
        echo   [ERROR] Installer build failed.
        goto :fail
    )
) else (
    echo   [WARN] ISCC.exe not found, skipping installer step.
    echo          Install Inno Setup to .workbuddy\innosetup\app\ first.
)

echo.
echo Done.
echo   Folder: release\xianyu-super-butler
echo   Zip   : release\xianyu-super-butler-portable-3.2.0.zip
goto :ok

:fail
echo.
echo BUILD FAILED - check the messages above.
:ok
pause
