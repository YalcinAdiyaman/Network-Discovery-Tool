@echo off
echo Building Discovery Tool...
pyinstaller --noconfirm --onefile --windowed --name "DiscoveryTool" --add-data "assets;assets" --add-data "locales;locales" --hidden-import "PIL._tkinter_finder" main.py
echo Build complete! Check the 'dist' folder.
pause
