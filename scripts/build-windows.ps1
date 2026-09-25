$ErrorActionPreference = "Stop"
$commit = "4adebea56d00369dc6cd51c2718d44b16120551d"
$dir = Join-Path $PWD "OneUIX-compat-build"
if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
git clone https://github.com/SoClear/OneUIX.git $dir
Set-Location $dir
git checkout $commit
Copy-Item (Join-Path $PSScriptRoot "..\patch\apply_oneuix_vector_sr_compat.py") .\apply_oneuix_vector_sr_compat.py
python .\apply_oneuix_vector_sr_compat.py
.\gradlew.bat :app:assembleRelease --stacktrace
Write-Host "APK output: $dir\app\build\outputs\apk\release"
