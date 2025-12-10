@echo off
echo ========================================
echo Starting DeepRP Development Servers
echo ========================================
echo.

cd /d %~dp0..

:: Start backend in a new window
echo Starting backend server...
start "DeepRP Backend" cmd /k "cd server && .\venv\Scripts\python main.py"

:: Wait a moment for backend to initialize
timeout /t 3 /nobreak > nul

:: Start frontend in a new window  
echo Starting frontend server...
start "DeepRP Frontend" cmd /k "cd client && npm run dev"

echo.
echo ========================================
echo DeepRP is starting!
echo ========================================
echo.
echo Backend:  http://localhost:7412
echo Frontend: http://localhost:5173
echo.
echo Close this window when done, or press any key to continue...
pause > nul
