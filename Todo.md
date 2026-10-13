# Next steps

1. Release the library: fingerprint schema 20 (`export_scale` block) and the control test writing 13074 at the measured factor are not in 0.1.0a10, and the integration stamps whatever `SCHEMA` the pinned library has.
2. Optional: have the integration's own fingerprint carry `export_scale` once its entity has probed. It stores only the factor in entry data, not the write behind it.

Done 2026-10-13:

- fwitten, `--export-scale` over each inverter's own LAN port: master (.247, unit 1) and slave (.140, unit 2) both answer **stores a written word as handed** (1:1). Held words written back (24990, 11880) were accepted and left in place; limitation was already on (0xAA).
- The per-inverter wiring is committed and released: 0.1.0a10 on PyPI ships `export_scale`.
- Same answer through both WiNet-S (.241 master, .144 slave, unit 1 each). Merged as an `export_scale` block (schema 20) into all four fwitten fingerprints.

## Sweep for step 1 (PowerShell, on the desktop)

$net = "192.168.3"      # first three octets of fwitten's subnet
$port = 502             # rerun with 516: open there means a WiNet-S dongle
$timeoutMs = 3000

$probes = 1..254 | ForEach-Object {
    $c = New-Object System.Net.Sockets.TcpClient
    [pscustomobject]@{ Ip = "$net.$_"; Client = $c; Task = $c.ConnectAsync("$net.$_", $port) }
}
[void][System.Threading.Tasks.Task]::WaitAll(@($probes.Task), $timeoutMs) 2>$null
$probes | Where-Object { $_.Task.Status -eq 'RanToCompletion' -and $_.Client.Connected } |
    ForEach-Object { "{0}:{1} open" -f $_.Ip, $port }
$probes | ForEach-Object { $_.Client.Dispose() }

## Running the scripts from Windows (no `make`)

Survey, read-only, stdlib only — needs nothing but Python 3:

cd <repo>\scripts\sungrow_scan
py sungrow_survey.py                                   # asks which network to sweep, e.g. 192.168.x.0/24
py sungrow_survey.py <ip1> <ip2>                       # skip the sweep once the hosts are known
py probe.py sweep 192.168.x.0/24 --concurrency 32 --timeout 3   # 502 only
py probe.py sweep 192.168.x.0/24 --port 516     # dongles only
py probe.py units <ip>                          # which unit ids answer
py probe.py capabilities <ip>

Export-scale probe, which writes and needs the library installed:

cd <repo>
py -m pip install -e .
py scripts\sungrow_control_test.py <master-ip> --unit 1 --export-scale --dry-run
py scripts\sungrow_control_test.py <master-ip> --unit 1 --export-scale
py scripts\sungrow_control_test.py <slave-ip> --unit 2 --export-scale

