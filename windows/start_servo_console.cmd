@echo off
setlocal
set "LAB_PYTHON=C:\Users\hetia\CMU\18649\zephyrproject\.venv\Scripts\python.exe"
if exist "%LAB_PYTHON%" (
  "%LAB_PYTHON%" "%~dp0servo_console.py" %*
) else (
  py -3 "%~dp0servo_console.py" %*
)
pause
