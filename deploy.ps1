### time in format of YYYYMMDD-HHMMSS
$time = "$(Get-Date -format 's')" -replace "-" -replace ":" -replace "T", "-"
$filepath = "./deploy-logs/deploy-$time.log"

### run script without stdout buffer and redirect stderr to stdout
### pipe result ToString to avoid errors propagating to the terminal
### pipe to tee to write log file while still logging results
py -u trydeploy.py 2>&1 | % ToString | tee $filepath