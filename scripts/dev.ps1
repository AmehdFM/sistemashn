param(
    [Parameter(Position = 0)]
    [ValidateSet('test', 'build', 'run')]
    [string]$Task = 'test',
    [ValidateSet('repuestos', 'ferreteria')]
    [string]$Vertical = 'repuestos'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo 'evn\Scripts\python.exe'
$flet = Join-Path $repo 'evn\Scripts\flet.exe'
$entry = if ($Vertical -eq 'repuestos') { 'src\main.py' } else { "src\main_$Vertical.py" }
$entryPath = Join-Path $repo $entry
$verticalLabel = if ($Vertical -eq 'repuestos') { 'Repuestos' } else { 'Ferreteria' }

if ($Task -ne 'test' -and -not (Test-Path -LiteralPath $entryPath)) {
    throw "No existe el punto de entrada de $Vertical`: $entryPath"
}

if (-not (Test-Path -LiteralPath $python)) {
    throw 'Falta evn\Scripts\python.exe. Instale el entorno según README.md.'
}

function Invoke-Checked([string]$label, [scriptblock]$action) {
    Write-Host "`n== $label =="
    & $action
    if ($LASTEXITCODE -ne 0) { throw "$label falló (código $LASTEXITCODE)." }
}

function Invoke-Tests {
    Push-Location $repo
    try {
        Invoke-Checked 'pytest' { & $python -m pytest -q }
        Invoke-Checked 'ruff check' { & $python -m ruff check src tests tools scripts }
        Invoke-Checked 'ruff format' { & $python -m ruff format --check src tests tools scripts }
    }
    finally { Pop-Location }
}

if ($Task -eq 'test') { Invoke-Tests; exit 0 }
if ($Task -eq 'run') {
    Push-Location $repo
    $manualData = if ($Vertical -eq 'repuestos') { '.dev-data\manual' } else { ".dev-data\manual-$Vertical" }
    try { & $python $entry --data-dir $manualData; exit $LASTEXITCODE }
    finally { Pop-Location }
}

Invoke-Tests
if (-not (Test-Path -LiteralPath $flet)) { throw 'Falta evn\Scripts\flet.exe.' }

Push-Location $repo
try {
    $env:PYTHONIOENCODING = 'utf-8'
    $version = & $python -c 'from sistemashn import __version__; print(__version__)'
    if ($LASTEXITCODE -ne 0 -or -not $version) { throw 'No se pudo leer la versión.' }

    $work = Join-Path $env:TEMP "sistemashn-build-$Vertical-$PID"
    $project = Join-Path $work 'proyecto'
    $stage = Join-Path $work 'salida'
    New-Item -ItemType Directory -Path $project -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $repo 'pyproject.toml') -Destination $project
    & robocopy (Join-Path $repo 'src') (Join-Path $project 'src') /E /XD __pycache__ /XF *.pyc | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "No se pudo copiar src (robocopy $LASTEXITCODE)." }
    if ($Vertical -ne 'repuestos') {
        Copy-Item -LiteralPath $entryPath -Destination (Join-Path $project 'src\main.py') -Force
    }

    Invoke-Checked 'flet build windows' {
        & $flet build windows --product "SistemasHN $verticalLabel" --build-version $version -o $stage $project
    }

    # Flet deja las revisiones como .pyc; Alembic solo descubre los .py originales.
    $migrations = Join-Path $stage 'app\sistemashn\migrations'
    $versions = Join-Path $migrations 'versions'
    if (-not (Test-Path -LiteralPath $versions)) { throw "No existe $versions en el build." }
    Copy-Item -Path (Join-Path $repo 'src\sistemashn\migrations\env.py') -Destination $migrations -Force
    Copy-Item -Path (Join-Path $repo 'src\sistemashn\migrations\versions\*.py') -Destination $versions -Force
    Invoke-Checked 'migraciones y arranque del ejecutable' {
        & $python scripts\verify_windows_release.py $stage --smoke
    }

    $build = Join-Path $repo 'build'
    $releaseName = if ($Vertical -eq 'repuestos') { 'windows_release' } else { "windows_release_$Vertical" }
    $release = Join-Path $build $releaseName
    $archive = Join-Path $build "SistemasHN$verticalLabel$version.zip"
    New-Item -ItemType Directory -Path $build -Force | Out-Null
    $resolvedBuild = (Resolve-Path -LiteralPath $build).Path
    $absoluteRelease = [IO.Path]::GetFullPath($release)
    if (-not $absoluteRelease.StartsWith($resolvedBuild + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Ruta de release inesperada: $release"
    }
    if (Test-Path -LiteralPath $release) { Remove-Item -LiteralPath $release -Recurse -Force }
    New-Item -ItemType Directory -Path $release -Force | Out-Null
    Copy-Item -Path (Join-Path $stage '*') -Destination $release -Recurse -Force
    Invoke-Checked 'verificación de la copia final' { & $python scripts\verify_windows_release.py $release }
    Compress-Archive -Path (Join-Path $release '*') -DestinationPath $archive -Force

    $resolvedTemp = (Resolve-Path -LiteralPath $env:TEMP).Path
    $absoluteWork = (Resolve-Path -LiteralPath $work).Path
    if (-not $absoluteWork.StartsWith($resolvedTemp + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Ruta temporal inesperada: $work"
    }
    Remove-Item -LiteralPath $work -Recurse -Force
    Write-Host "`nBuild Windows listo: $release"
    Write-Host "ZIP: $archive"
}
finally { Pop-Location }
