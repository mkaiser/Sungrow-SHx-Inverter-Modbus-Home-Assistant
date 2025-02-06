# Help / Troubleshooting

# Contents
- [1. Cannot connect to the inverter](#1-cannot-connect-to-the-inverter)
- [2. Only a subset of the sensors is available](#2-only-a-subset-of-the-sensors-is-available)

# 1. Cannot connect to the inverter

## Error indication

No sensor values, HA log shows:
```
General exception: index out of range
Modbus IO exception Modbus Error: [Input/Output] Unable to decode request
```

## Check #1

**Using the internal LAN port of the inverter is strongly recommended - the WiNet-S dongle is a common source of trouble**
Recent Sungrow inverters come with WiNet-S, a dongle for Wi-Fi access / LAN connection. Its primary use is facilitating the data exchange with Sungrow's iSolarCloud servers. It also offers local administration facilities. Finally, it also offers Modbus access. However, some Modbus registers are not available here that **are** available via the internal LAN port of the inverter. Its regular tasks consume much of its processing power. Providing stable Modbus access is low on its priority list. Recent firmware versions have improved the quality of Modbus access via WiNet-S and future versions might improve it more.

![Inverter LAN connection](images/Inverter_LAN_ports.drawio.svg)

## Check #2

Some users reported that the inverter must be completely switched off and only is assigned an IP adress on cold-boot. So do the following: 

1. Turn off the AC power to the inverter
2. Wait 10 seconds
3. Switch off the battery (if available)
4. Wait 10 seconds
5. Switch off the DC power to the inverter (the large switch at the side of the inverter)
6. Attach the LAN cable to the internal port
7. Wait 10 minutes (so all capacitors inside completely discharge)
8. Perform steps 5 to 1 (i.e. reverse order) to properly boot the inverter, again
9. After bootup (give it 10 minutes), you should see the inverter's IP address in your LAN router.

## Check #3

If you are using Windows you can check if the Modbus connection generally works using [QModMaster](https://sourceforge.net/projects/qmodmaster/). There are probably open source Linux alternatives available as well. :)

I tested it with the values shown in the following screenshot. First set the TCP settings (Options --> Modbus TCP) then adapt all highlighted parameters.

The following values must match values from your `secrets.yaml`:
```
Slave IP = sungrow_modbus_host_ip
TCP Port = sungrow_modbus_port
Unit ID = sungrow_modbus_slave
```

![QModMaster settings](/doc/images/QModMaster.png)


# 2. Only a subset of the sensors is available

## Error indication

Users with single-phase inverters have reported multiple issues (Sungrow's nomenclature is SH3.RS - single phase, vs. SH10.RT - three phase). These inverters only support a subset of the Modbus registers (although the users reported using the inverter's built-in LAN port.)

## Resolution
Availability of registers is determined by Sungrow's firmware. If a particular register is not available, only Sungrow can change this.