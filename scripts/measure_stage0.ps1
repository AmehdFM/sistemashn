<#
.SYNOPSIS
    Sonda de medición de arranque/consumo para Fase 0 (T0.5b).

.DESCRIPTION
    Lanza un ejecutable N veces, mide el tiempo hasta que su ventana principal
    aparece, espera a que se estabilice y registra memoria (working set y
    private bytes) del proceso y sus hijos. No define umbrales de aprobación:
    solo recopila datos para que el jefe los revise.

.PARAMETER ExePath
    Ruta al ejecutable a medir. Obligatorio.

.PARAMETER OutDir
    Carpeta donde se escribe stage0-measurements.json. Obligatorio.

.PARAMETER Runs
    Número de corridas. Por defecto 5.

.PARAMETER SettleSeconds
    Segundos de espera tras detectar la ventana principal, antes de medir
    memoria. Por defecto 8.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ExePath,

    [Parameter(Mandatory = $true)]
    [string]$OutDir,

    [int]$Runs = 5,

    [int]$SettleSeconds = 8
)

if (-not (Test-Path -LiteralPath $ExePath)) {
    Write-Error "ExePath no existe: $ExePath" -ErrorAction Continue
    exit 2
}

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $OutDir)) {
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
}

function Get-ProcessTree {
    param([int]$ParentId)

    $all = @()
    $direct = Get-CimInstance Win32_Process -Filter "ParentProcessId=$ParentId" -ErrorAction SilentlyContinue
    foreach ($child in $direct) {
        $all += $child
        $all += Get-ProcessTree -ParentId $child.ProcessId
    }
    return $all
}

function Stop-ProcessTree {
    param([int]$ProcessId)

    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        Stop-ProcessTree -ProcessId $child.ProcessId
    }
    try {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue -Confirm:$false
    }
    catch {}
}

function Measure-TreeMemoryMb {
    param([int]$RootProcessId)

    $pids = @($RootProcessId)
    $childInfos = Get-ProcessTree -ParentId $RootProcessId
    foreach ($c in $childInfos) { $pids += $c.ProcessId }

    $workingSetBytes = 0
    $privateBytes = 0
    foreach ($processId in $pids) {
        try {
            $proc = Get-Process -Id $processId -ErrorAction Stop
            $workingSetBytes += $proc.WorkingSet64
            $privateBytes += $proc.PrivateMemorySize64
        }
        catch {
            # el proceso ya pudo haber terminado; se ignora en la suma
        }
    }

    [PSCustomObject]@{
        working_set_mb = [math]::Round($workingSetBytes / 1MB, 2)
        private_mb     = [math]::Round($privateBytes / 1MB, 2)
    }
}

function Get-DiskMediaType {
    try {
        $disks = Get-PhysicalDisk -ErrorAction Stop
        $types = $disks | Select-Object -ExpandProperty MediaType -Unique
        if ($types) {
            return ($types -join ", ")
        }
        return "desconocido"
    }
    catch {
        return "desconocido"
    }
}

$computerSystem = Get-CimInstance Win32_ComputerSystem
$processorInfo = Get-CimInstance Win32_Processor | Select-Object -First 1
$osInfo = Get-CimInstance Win32_OperatingSystem

$equipo = [PSCustomObject]@{
    modelo    = "$($computerSystem.Manufacturer) $($computerSystem.Model)"
    ram_gb    = [math]::Round($computerSystem.TotalPhysicalMemory / 1GB, 2)
}

$cpu = $processorInfo.Name
$so = [PSCustomObject]@{
    caption = $osInfo.Caption
    version = $osInfo.Version
}
$tipoDisco = Get-DiskMediaType

$corridas = @()

for ($i = 1; $i -le $Runs; $i++) {
    Write-Host "Corrida $i de $Runs..."

    $proceso = Start-Process -FilePath $ExePath -PassThru

    $timeoutSeconds = 60
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $windowFound = $false

    while ($sw.Elapsed.TotalSeconds -lt $timeoutSeconds) {
        try {
            $proceso.Refresh()
            if ($proceso.MainWindowHandle -ne 0) {
                $windowFound = $true
                break
            }
        }
        catch {}
        Start-Sleep -Milliseconds 200
    }
    $sw.Stop()
    $startupSeconds = [math]::Round($sw.Elapsed.TotalSeconds, 2)

    if (-not $windowFound) {
        Write-Warning "Corrida $i : no se detectó MainWindowHandle en $timeoutSeconds s."
    }

    Start-Sleep -Seconds $SettleSeconds

    $memoria = Measure-TreeMemoryMb -RootProcessId $proceso.Id

    $corridas += [PSCustomObject]@{
        run              = $i
        window_detected  = $windowFound
        startup_seconds  = $startupSeconds
        working_set_mb   = $memoria.working_set_mb
        private_mb       = $memoria.private_mb
    }

    Stop-ProcessTree -ProcessId $proceso.Id
    Start-Sleep -Seconds 1
}

$promedios = [PSCustomObject]@{
    startup_seconds_avg = [math]::Round((($corridas | Measure-Object -Property startup_seconds -Average).Average), 2)
    working_set_mb_avg  = [math]::Round((($corridas | Measure-Object -Property working_set_mb -Average).Average), 2)
    private_mb_avg      = [math]::Round((($corridas | Measure-Object -Property private_mb -Average).Average), 2)
}

$resultado = [PSCustomObject]@{
    fecha     = (Get-Date).ToString("o")
    exe_path  = $ExePath
    equipo    = $equipo
    cpu       = $cpu
    so        = $so
    tipo_disco = $tipoDisco
    runs      = $corridas
    promedios = $promedios
}

$outFile = Join-Path -Path $OutDir -ChildPath "stage0-measurements.json"
$resultado | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outFile -Encoding utf8

Write-Host "Medición guardada en $outFile"
