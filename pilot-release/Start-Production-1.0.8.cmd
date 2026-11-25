@echo off
rem Starts the installed production 1.0.8 bundle in Ubuntu WSL.
wsl.exe -d Ubuntu --exec /usr/bin/python3 -B /home/dtran/music-sheet-transposer-releases/music-sheet-transposer-1.0.8/start.py %*
exit /b %errorlevel%
