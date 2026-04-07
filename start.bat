@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo Installing and preparing dependencies...
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Failed to create the virtual environment.
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    exit /b 1
)

python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    exit /b 1
)

echo Starting the Flask backend...
start "Akhgam Herbals Backend" ".venv\Scripts\python.exe" app.py

timeout /t 3 /nobreak >nul
echo Opening the site in your browser...
start "" http://127.0.0.1:5000

endlocal
