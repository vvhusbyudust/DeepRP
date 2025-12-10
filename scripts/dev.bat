@echo off
echo Starting DeepRP in development mode...
cd /d %~dp0..\server

REM Check if venv exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate venv and install dependencies
call venv\Scripts\activate.bat
pip install -r requirements.txt -q

REM Start the server
echo.
echo Starting server on http://localhost:7412
python main.py
