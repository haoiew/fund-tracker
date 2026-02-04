Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 1. 获取当前 vbs 脚本文件所在的 绝对路径
CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)

' 2. 拼接出 bat 文件的完整路径
TargetBat = CurrentDirectory & "\run_fund_tracker.bat"

' 3. 隐形运行 (数字 0 表示隐藏窗口)
WshShell.Run chr(34) & TargetBat & chr(34), 0

Set WshShell = Nothing