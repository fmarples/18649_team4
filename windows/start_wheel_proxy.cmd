@echo off
setlocal
if not defined LOGITECH_WHEEL_REPO (
  for %%D in ("%~dp0..\..\logitech-wheel-dev-updated-f26") do set "LOGITECH_WHEEL_REPO=%%~fD"
)
if not exist "%LOGITECH_WHEEL_REPO%\proxy_gui.py" (
  set /p "LOGITECH_WHEEL_REPO=Enter the course Logitech proxy repository folder: "
)
if not exist "%LOGITECH_WHEEL_REPO%\proxy_gui.py" (
  echo Course proxy_gui.py was not found.
  exit /b 1
)
if exist "%LOGITECH_WHEEL_REPO%\.venv\Scripts\python.exe" (
  "%LOGITECH_WHEEL_REPO%\.venv\Scripts\python.exe" "%~dp0start_wheel_proxy.py" %*
) else (
  python "%~dp0start_wheel_proxy.py" %*
)
exit /b %ERRORLEVEL%
