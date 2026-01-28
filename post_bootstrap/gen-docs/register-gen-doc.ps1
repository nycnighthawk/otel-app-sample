# C:\ProgramData\Company\Scripts\register-doc-gen.ps1
# Run this once in an elevated PowerShell. It:
# 1) writes the generator script to C:\ProgramData\Company\Scripts\New-SimulatedBusinessDoc.ps1
# 2) registers/updates a Scheduled Task running as SYSTEM every 20 minutes

$TaskName = 'SimulatedBusinessDocGenerator'
$ScriptDir = 'C:\ProgramData\Company\Scripts'
$GenScript = Join-Path $ScriptDir 'New-SimulatedBusinessDoc.ps1'
$OutDir    = 'C:\shares\documents'

New-Item -ItemType Directory -Path $ScriptDir -Force | Out-Null

# Write/update the generator script
$gen = @"
`$OutDir = '$OutDir'
New-Item -ItemType Directory -Path `$OutDir -Force | Out-Null

`$i = 1
do {
  `$fileName = 'simulated_business_doc_{0:D3}.txt' -f `$i
  `$filePath = Join-Path `$OutDir `$fileName
  `$i++
} while (Test-Path `$filePath)

@(
  (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
  'simulated business document'
) | Set-Content -Path `$filePath -Encoding UTF8
"@
Set-Content -Path $GenScript -Value $gen -Encoding UTF8

# Register/update the scheduled task (XML-based, runs as SYSTEM)
$start = (Get-Date).AddMinutes(1).ToString('yyyy-MM-ddTHH:mm:ss')

$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Author>Company</Author>
    <Description>Generate simulated business documents every 20 minutes.</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>$start</StartBoundary>
      <Enabled>true</Enabled>
      <Repetition>
        <Interval>PT20M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-NoProfile -ExecutionPolicy Bypass -File "$GenScript"</Arguments>
    </Exec>
  </Actions>
</Task>
"@

Register-ScheduledTask -TaskName $TaskName -Xml $xml -Force

