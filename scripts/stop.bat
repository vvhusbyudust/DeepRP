@echo off
echo Stopping DeepRP...
cd /d %~dp0..
docker-compose -f docker/docker-compose.yml down
echo.
echo DeepRP stopped.
pause
