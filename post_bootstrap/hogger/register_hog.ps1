$TaskName   = "criticalservice"
$PythonExe  = "C:\Program Files\Python313\python.exe"
$ScriptPath = "C:\ProgramData\company\scripts\reshog_v2.py"

# Startup trigger (at boot)
$trigger = New-ScheduledTaskTrigger -AtStartup

# Run as SYSTEM, highest privileges
$principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# Start only after network stack is up (loopback-ready proxy); also retry if it still fails
$action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$ScriptPath`""

$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -MultipleInstances IgnoreNew `
  -RestartCount 10 `
  -RestartInterval (New-TimeSpan -Minutes 1)

# Delay a bit after boot (often enough for loopback/services); adjust as needed
$trigger.Delay = "PT30S"

Register-ScheduledTask -TaskName $TaskName -Trigger $trigger -Action $action -Principal $principal -Settings $settings

