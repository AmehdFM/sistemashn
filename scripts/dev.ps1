param(
    [Parameter(Position = 0)]
    [ValidateSet('test', 'build', 'run')]
    [string]$Task = 'test'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo 'evn\Scripts\python.exe'
$flet = Join-Path $repo 'evn\Scripts\flet.exe'

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
    try { & $python src\main.py --data-dir .dev-data\manual; exit $LASTEXITCODE }
    finally { Pop-Location }
}

Invoke-Tests
if (-not (Test-Path -LiteralPath $flet)) { throw 'Falta evn\Scripts\flet.exe.' }

Push-Location $repo
try {
    $env:PYTHONIOENCODING = 'utf-8'
    $version = & $python -c 'from sistemashn import __version__; print(__version__)'
    if ($LASTEXITCODE -ne 0 -or -not $version) { throw 'No se pudo leer la versión.' }

    $work = Join-Path $env:TEMP "sistemashn-build-repuestos-$PID"
    $project = Join-Path $work 'proyecto'
    $stage = Join-Path $work 'salida'
    New-Item -ItemType Directory -Path $project -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $repo 'pyproject.toml') -Destination $project
    & robocopy (Join-Path $repo 'src') (Join-Path $project 'src') /E /XD __pycache__ /XF *.pyc | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "No se pudo copiar src (robocopy $LASTEXITCODE)." }

    Invoke-Checked 'flet build windows' {
        & $flet build windows --product 'SistemasHN Repuestos' --build-version $version -o $stage $project
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
    $release = Join-Path $build 'windows_release'
    $archive = Join-Path $build "SistemasHNRepuestos$version.zip"
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
