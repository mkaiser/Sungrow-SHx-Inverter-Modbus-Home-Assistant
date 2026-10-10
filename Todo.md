# Next steps

1. Find fwitten's new subnet and their inverters' own LAN ports (502 open, 516 closed), then run `scripts/hardware/sungrow_control_test.py <host> --unit <1|2> --export-scale` on master (unit 1) and slave (unit 2); expected answer: 1:1.
2. If the route doesn't reach the container, fix the VPN routing into WSL/Docker or run the two commands on the desktop.
3. Commit the uncommitted per-inverter export-scale wiring (`number.py`, `tests/test_export_limit_entity.py`; bar12 already confirmed ×10), then release the library, because 0.1.0a9 lacks `export_scale`.

## Sweep for step 1 (PowerShell, on the desktop)

```powershell
$net = "192.168.3"      # first three octets of fwitten's subnet
$port = 502             # rerun with 516: open there means a WiNet-S dongle
$timeoutMs = 3000

$probes = 1..254 | ForEach-Object {
    $c = New-Object System.Net.Sockets.TcpClient
    [pscustomobject]@{ Ip = "$net.$_"; Client = $c; Task = $c.ConnectAsync("$net.$_", $port) }
}
[void][System.Threading.Tasks.Task]::WaitAll(@($probes.Task), $timeoutMs) 2>$null
$probes | Where-Object { $_.Task.Status -eq 'RanToCompletion' -and $_.Client.Connected } |
    ForEach-Object { "{0}:{1} open" -f $_.Ip, $port }
$probes | ForEach-Object { $_.Client.Dispose() }
```

## Running the scripts from Windows (no `make`)

Survey, read-only, stdlib only — needs nothing but Python 3:

```powershell
cd <repo>\scripts\sungrow_scan
py sungrow_survey.py                                   # asks which network to sweep, e.g. 192.168.x.0/24
py sungrow_survey.py <ip1> <ip2>                       # skip the sweep once the hosts are known
py probe.py sweep 192.168.x.0/24 --concurrency 32 --timeout 3   # 502 only
py probe.py sweep 192.168.x.0/24 --port 516     # dongles only
py probe.py units <ip>                          # which unit ids answer
py probe.py capabilities <ip>
```

Export-scale probe, which writes and needs the library installed:

```powershell
cd <repo>
py -m pip install -e .
py scripts\sungrow_control_test.py <master-ip> --unit 1 --export-scale --dry-run
py scripts\sungrow_control_test.py <master-ip> --unit 1 --export-scale
py scripts\sungrow_control_test.py <slave-ip> --unit 2 --export-scale
```
