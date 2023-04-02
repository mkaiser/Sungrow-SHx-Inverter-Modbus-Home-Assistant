# Help / Troubleshooting

# Cannot connect to the inverter: Topmost known issue

## Error indication

No sensor values, HA log shows:
```
General exception: index out of range
Modbus IO exception Modbus Error: [Input/Output] Unable to decode request
```



## Check #1

**Using the native LAN port of the inverter is required - the WiNet Ethernet port is not fully working!**
Recent sungrow invertes come with WiNet-S, a Dongle for WLAN access / LAN interconnection. Although the dongle has an Ethernet port, modbus is not working properly with this port. Some users report, that they cannot establish a connection, some are able to, but several modbus registers are working, and some not. It seems like Sungrow is actively working on that, so maybe in the near future they will release firmware upgrades to improve the modbus via WiNet S support. 



![Inverter LAN connetion](images/Inverter_LAN_ports.drawio.svg)


## Check #2

If you are using Windows you can easily check, if the modbus connection generally works using [QModMaster](https://sourceforge.net/projects/qmodmaster/). I am pretty sure, that there are open source linux alternatives available :)

I tested it with the values shown in the screenshot. First set the TCP Settings (Options --> Modbus TCP) then adapt all highlighted parameters

![QModMaster setting ](/doc/images/QModMaster.png)


# Only a subset of the sensors is available

## Error indication

Users with single-phase inverters have reported multiple issues (sungrows nomenclature is SH3.RS - single phase, vs. SH10.RT - three phase). These inverters only support a subset of the modbus registers (although the users reported using the inverter's built-in LAN port.)

--> sorry, can't fix this. It is up to Sungrow to make a platform independent modbus implementation :/ 