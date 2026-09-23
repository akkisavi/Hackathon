@echo off
REM One-click launcher for the SIH26162 stack. Double-click this file.
REM Bypasses PowerShell's execution policy just for this run and forwards any
REM flags (e.g. run.bat -Mobile, run.bat -Seed) straight through to dev.ps1.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1" %*
if errorlevel 1 pause
