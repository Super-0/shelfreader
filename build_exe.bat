@echo off
cd /d %~dp0
py -m pip install -r requirements.txt
py -m PyInstaller --noconfirm --onefile --windowed --name ShelfReader main.py
