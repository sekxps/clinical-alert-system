@echo off
echo ===================================================
echo Setting up Clinical Alert Client to run at startup...
echo ===================================================
echo.

:: Get the current directory (where the bat file is located)
set "DIR=%~dp0"
:: Remove trailing backslash
if "%DIR:~-1%"=="\" set "DIR=%DIR:~0,-1%"

:: Define paths
set "VENV_PYTHON=%DIR%\venv\Scripts\pythonw.exe"
set "MAIN_PY=%DIR%\main.py"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_NAME=Clinical Alert Client.lnk"

:: Check if virtual environment pythonw.exe exists
if not exist "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found at:
    echo %VENV_PYTHON%
    echo Please make sure you have created the venv and installed requirements first!
    echo.
    pause
    exit /b 1
)

:: Create a temporary VBScript to generate the Windows Shortcut (.lnk)
set "VBS_SCRIPT=%TEMP%\create_shortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_SCRIPT%"
echo sLinkFile = "%STARTUP_FOLDER%\%SHORTCUT_NAME%" >> "%VBS_SCRIPT%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS_SCRIPT%"
echo oLink.TargetPath = "%VENV_PYTHON%" >> "%VBS_SCRIPT%"
echo oLink.Arguments = """%MAIN_PY%""" >> "%VBS_SCRIPT%"
echo oLink.WorkingDirectory = "%DIR%" >> "%VBS_SCRIPT%"
echo oLink.Description = "Clinical Alert System Tray Client" >> "%VBS_SCRIPT%"
echo oLink.Save >> "%VBS_SCRIPT%"

:: Execute the VBScript and then delete it
cscript //nologo "%VBS_SCRIPT%"
del "%VBS_SCRIPT%"

echo [SUCCESS] Shortcut created in your Startup folder!
echo Location: %STARTUP_FOLDER%\%SHORTCUT_NAME%
echo The application will now start automatically next time you log in.
echo.
pause
