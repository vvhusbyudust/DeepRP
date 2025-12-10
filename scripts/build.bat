@echo off
echo Building DeepRP...
cd /d %~dp0..
docker-compose -f docker/docker-compose.yml build --no-cache
echo.
echo Build complete!
pause
