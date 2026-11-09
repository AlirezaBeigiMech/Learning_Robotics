# Removes the stray CoppeliaSim files that a first, wrong extraction left directly in %LOCALAPPDATA%\Programs
# (and 8 small CoppeliaSim scripts that landed in Programs\Python). The real install in Programs\CoppeliaSim is
# NOT touched. Every path comes from the CoppeliaSim zip's own file list (coppeliasim_leftovers.txt).
# Run:  powershell -ExecutionPolicy Bypass -File scripts\cleanup_coppeliasim_leftovers.ps1
$paths = Get-Content (Join-Path $PSScriptRoot "coppeliasim_leftovers.txt") | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
$paths | ForEach-Object { "  $_" }
if ((Read-Host "Delete these $($paths.Count) items? (y/N)") -ne "y") { "Nothing deleted."; exit }
$paths | ForEach-Object { Remove-Item -LiteralPath $_ -Recurse -Force }
"Done."
