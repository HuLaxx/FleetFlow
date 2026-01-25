param(
    [int]$Seed = 42,
    [int]$Epochs = 1,
    [string]$StartDate = "2023-01-01",
    [string]$EndDate = "2023-01-15"
)

$ErrorActionPreference = 'Stop'
python "${PSScriptRoot}\..\ml\training\train_forecaster.py" --seed $Seed --epochs $Epochs --start-date $StartDate --end-date $EndDate