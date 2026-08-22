$ErrorActionPreference = "Stop"
$commit = "78e2ef1d10320aab293631f97ec636cf64d4cbea"
$dir = Join-Path $PWD "OneUIX-compat-build"
if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
git clone https://github.com/SoClear/OneUIX.git $dir
Set-Location $dir
git checkout $commit
Copy-Item (Join-Path $PSScriptRoot "..\patch\apply_oneuix_vector_sr_compat.py") .\apply_oneuix_vector_sr_compat.py
python .\apply_oneuix_vector_sr_compat.py
.\gradlew.bat :app:assembleRelease --stacktrace
Write-Host "APK output: $dir\app\build\outputs\apk\release"
