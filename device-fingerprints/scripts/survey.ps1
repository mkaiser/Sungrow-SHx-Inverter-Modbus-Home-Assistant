# Run the Sungrow survey on Windows. survey.cmd starts this; so can
#   powershell -ExecutionPolicy Bypass -File survey.ps1 [the survey's own arguments]
#
# The survey runs on the published `sungrow-modbus` library, pinned in the
# PEP 723 header of sungrow_survey.py. This finds a way to give it that:
#
#   1. uv, if it is installed -- it fetches a suitable Python and the pinned
#      library by itself, into a cache, and touches nothing else;
#   2. otherwise a Python 3.13+ that already has exactly that library;
#   3. otherwise it offers to install uv, and asks first.
#
# The survey reads, and writes only if its last question is answered yes:
# then it runs the control test after the reading. `control` as the first
# argument hands the rest to the control test itself (--dry-run, --restore
# <snapshot>, --start-only).
#
# Every argument is handed to the survey, and so is its exit code: 0 to 5
# each mean something -- 5 that the house was left changed -- and this
# script's own failures are 1.

$ErrorActionPreference = 'Stop'
# Relative paths in the environment and the arguments are the caller's, not
# this folder's; the script resolves its path arguments against this.
$Origin = (Get-Location).Path
$env:SUNGROW_CALLER_DIR = $Origin
Set-Location -LiteralPath $PSScriptRoot

$Script = 'python/sungrow_survey.py'

# The pin and the dependency list, read from the header so the version lives
# in one place.
# One quoted entry per line between `# dependencies = [` and `# ]`.
$Text = Get-Content -LiteralPath $Script -Raw
$Block = if ($Text -match '(?ms)^# dependencies = \[(.*?)^# \]') { $Matches[1] } else { '' }
if ($Block -notmatch '"sungrow-modbus==([^"]*)"') {
    Write-Host "$Script names no sungrow-modbus version in its header; this copy is damaged."
    exit 1
}
$Pin = $Matches[1]
$Dependencies = ([regex]::Matches($Block, '"[^"]+"') | ForEach-Object { $_.Value }) -join ' '

function Find-Uv {
    $onPath = Get-Command uv -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    # Where the installer puts it, which a window opened before the install
    # does not have on its PATH yet.
    $installed = Join-Path $env:USERPROFILE '.local\bin\uv.exe'
    if (Test-Path -LiteralPath $installed) { return $installed }
    return $null
}

# Whether this interpreter can run the survey as it is: 3.13 or newer, the
# pinned library exactly, and the Modbus backend the survey talks through.
# Handed over on stdin, and in single quotes: Windows PowerShell mangles a
# double quote inside an argument to a native program.
$Check = @'
import sys
from importlib.metadata import version

if sys.version_info < (3, 13):
    raise SystemExit(1)
if version('sungrow-modbus') != sys.argv[1]:
    raise SystemExit(1)
import modbus_connection.tmodbus  # noqa: F401
'@

function Test-Ready([string[]]$Interpreter) {
    $exe = $Interpreter[0]
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { return $false }
    $rest = @($Interpreter | Select-Object -Skip 1)
    try {
        $Check | & $exe @rest - $Pin *> $null
    } catch {
        return $false
    }
    return $LASTEXITCODE -eq 0
}

function Show-Manual {
    Write-Host ''
    Write-Host 'To run the survey, install uv and run this again:'
    Write-Host ''
    Write-Host '    https://docs.astral.sh/uv/getting-started/installation/'
    Write-Host ''
    Write-Host 'Or, with Python 3.13 or newer, install the library and run it directly:'
    Write-Host ''
    Write-Host "    py -m pip install $Dependencies"
    Write-Host "    py $Script"
}

# A library other than the published one, for trying a version that is not
# released yet: a wheel (`make wheel`), or a source folder with its
# pyproject.toml. uv installs the pin as usual and lays this over it. Unset --
# which is how a contributor runs this -- nothing here happens.
if ($env:SUNGROW_MODBUS_LIBRARY) {
    $Library = $env:SUNGROW_MODBUS_LIBRARY
    if (-not [IO.Path]::IsPathRooted($Library)) { $Library = Join-Path $Origin $Library }
    if ($Library -like '*.whl' -and (Test-Path -LiteralPath $Library -PathType Leaf)) {
        $With = '--with'
    } elseif (Test-Path -LiteralPath (Join-Path $Library 'pyproject.toml') -PathType Leaf) {
        $With = '--with-editable'
    } else {
        Write-Host "SUNGROW_MODBUS_LIBRARY=$env:SUNGROW_MODBUS_LIBRARY is neither a .whl file nor a folder with a pyproject.toml."
        exit 1
    }
    $uv = Find-Uv
    if (-not $uv) {
        Write-Host 'SUNGROW_MODBUS_LIBRARY needs uv, and uv is not here.'
        exit 1
    }
    Write-Host "Running on $Library, NOT the published sungrow-modbus $Pin."
    & $uv run $With $Library --script $Script @args
    exit $LASTEXITCODE
}

$Candidates = @(@('py', '-3.14'), @('py', '-3.13'), @('python'))

while ($true) {
    $uv = Find-Uv
    if ($uv) {
        & $uv run --script $Script @args
        exit $LASTEXITCODE
    }

    foreach ($candidate in $Candidates) {
        if (Test-Ready $candidate) {
            $exe = $candidate[0]
            $rest = @($candidate | Select-Object -Skip 1)
            & $exe @rest $Script @args
            exit $LASTEXITCODE
        }
    }

    Write-Host "The survey needs uv, or a Python 3.13+ with sungrow-modbus $Pin, and"
    Write-Host 'neither is here.'
    if (-not [Environment]::UserInteractive -or [Console]::IsInputRedirected) {
        # Nobody to ask. Installing software unasked is not an option.
        Show-Manual
        exit 1
    }
    $answer = Read-Host 'Install uv (from astral.sh)? [y/N]'
    if ($answer -notmatch '^[yY]') {
        Show-Manual
        exit 1
    }

    try {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    } catch {
        Write-Host "The uv installer failed: $_"
        Show-Manual
        exit 1
    }
    if (-not (Find-Uv)) {
        Write-Host 'uv was installed, but not where this looks for it.'
        Show-Manual
        exit 1
    }
}
