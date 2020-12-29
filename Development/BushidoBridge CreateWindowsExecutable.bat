cd ..\pythoncode
del dist\BushidoBridge.exe
pyinstaller --clean BushidoBridge.spec
move dist\BushidoBridge.exe ..\WindowsExecutable
pause