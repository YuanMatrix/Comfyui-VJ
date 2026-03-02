Set objShell = CreateObject("WScript.Shell")
objShell.CurrentDirectory = "C:\Users\admin\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\"
objShell.Run "cmd /c auto-start-comfyui.bat", 0, False
