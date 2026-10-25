# Run from PowerShell; the package may reside on Ubuntu WSL or a Windows drive.
$ErrorActionPreference = 'Stop'
$pilotRoot = $PSScriptRoot
if ($pilotRoot -match '^\\\\wsl(?:\.localhost|\$)\\Ubuntu\\(.+)$') {
    $linuxRoot = '/' + $Matches[1].Replace('\', '/')
} else {
    $linuxRoot = (& wsl.exe -d Ubuntu --exec wslpath -u $pilotRoot).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot locate package in Ubuntu WSL.' }
}
& wsl.exe -d Ubuntu --exec /usr/bin/python3 -B ($linuxRoot + '/start.py') @args
exit $LASTEXITCODE
