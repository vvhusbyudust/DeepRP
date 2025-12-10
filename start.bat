@echo off
chcp 65001 >nul
title DeepRP - Development Server
color 0A

echo ===================================================================
echo                     DeepRP Development Server
echo ===================================================================
echo   Backend:  http://localhost:7412
echo   Frontend: http://localhost:5173
echo ===================================================================
echo.

:: Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

:: Check if Node.js is available
where npm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js/npm is not installed or not in PATH
    pause
    exit /b 1
)

:: ===== First-run detection: Python venv =====
if not exist "%~dp0server\venv" (
    echo [INFO] First run detected - Creating Python virtual environment...
    cd /d "%~dp0server"
    python -m venv venv
    echo [INFO] Installing Python dependencies...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    echo [OK] Python environment ready
    echo.
)

:: ===== First-run detection: Node modules =====
if not exist "%~dp0client\node_modules" (
    echo [INFO] First run detected - Installing npm dependencies...
    cd /d "%~dp0client"
    call npm install
    echo [OK] npm dependencies installed
    echo.
)

:: Kill any existing processes on ports 7412 and 5173
echo [INFO] Cleaning up existing processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":7412"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173"') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Start backend server (use venv python)
echo [INFO] Starting backend server on port 7412...
cd /d "%~dp0server"
start /B venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 7412 > backend.log 2>&1

:: Wait for backend to start
timeout /t 3 /nobreak >nul

:: Start frontend dev server
echo [INFO] Starting frontend dev server on port 5173...
cd /d "%~dp0client"
start /B npm run dev > frontend.log 2>&1

:: Wait for frontend to start
timeout /t 3 /nobreak >nul

echo.
echo ===================================================================
echo   [OK] Both servers started successfully!
echo.
echo   Commands:
echo     1 - View backend logs
echo     2 - View frontend logs  
echo     3 - Open browser (localhost:5173)
echo     4 - Restart backend
echo     5 - Restart frontend
echo     6 - Rebuild frontend
echo     Q - Quit (stop all servers)
echo ===================================================================
echo.

:menu
set /p choice="Enter command: "

if /i "%choice%"=="1" (
    echo.
    echo === Backend Logs (last 50 lines) ===
    cd /d "%~dp0server"
    powershell -Command "Get-Content backend.log -Tail 50"
    echo.
    goto menu
)

if /i "%choice%"=="2" (
    echo.
    echo === Frontend Logs (last 50 lines) ===
    cd /d "%~dp0client"
    powershell -Command "Get-Content frontend.log -Tail 50"
    echo.
    goto menu
)

if /i "%choice%"=="3" (
    start http://localhost:5173
    echo [INFO] Opening browser...
    goto menu
)

if /i "%choice%"=="4" (
    echo [INFO] Restarting backend...
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":7412"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    cd /d "%~dp0server"
    start /B venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 7412 > backend.log 2>&1
    timeout /t 2 /nobreak >nul
    echo [OK] Backend restarted
    goto menu
)

if /i "%choice%"=="5" (
    echo [INFO] Restarting frontend...
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    cd /d "%~dp0client"
    start /B npm run dev > frontend.log 2>&1
    timeout /t 2 /nobreak >nul
    echo [OK] Frontend restarted
    goto menu
)

if /i "%choice%"=="6" (
    echo [INFO] Rebuilding frontend...
    cd /d "%~dp0client"
    call npm run build
    echo [OK] Frontend rebuilt
    goto menu
)

if /i "%choice%"=="q" goto quit
if /i "%choice%"=="Q" goto quit

echo [WARN] Invalid command. Please try again.
goto menu

:quit
echo.
echo [INFO] Stopping all servers...

:: Kill backend
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":7412"') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Kill frontend
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo [OK] All servers stopped. Goodbye!
timeout /t 2 /nobreak >nul
exit /b 0
