@echo off
cd /d "%~dp0"
where python >nul 2>nul || (echo Python is not installed. Get it from https://www.python.org/downloads/ and tick "Add Python to PATH". & pause & exit /b)
if not exist venv (python -m venv venv)
call venv\Scripts\activate
pip install -q -r requirements.txt
echo.
echo FinTrack is starting. Your browser will open. Demo login: demo@fintrack.app / Demo@1234
python app.py
pause
