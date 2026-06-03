@echo off
setlocal
pushd "%~dp0" || goto :path_error

where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -m pip install -r requirements.txt || goto :error
  py -3 -m PyInstaller --noconfirm --onefile --windowed --name ShelfReader main.py || goto :error
  goto :cleanup
)

where python >nul 2>&1
if %errorlevel%==0 (
  python -m pip install -r requirements.txt || goto :error
  python -m PyInstaller --noconfirm --onefile --windowed --name ShelfReader main.py || goto :error
  goto :cleanup
)

echo Python was not found. Install Python 3 and try again.
goto :error

:path_error
echo Could not open this folder from a UNC/WSL path.
echo Copy the project to a normal Windows path like C:\Users\Ben\Projects and try again.
goto :error

:error
echo.
echo ShelfReader build failed.
pause
exit /b 1

:cleanup
popd
endlocal
