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

**Using the native LAN port of the inverter is required - the WiNet Ethernet port is not fully working!**
Recent Sungrow inverters come with WiNet-S, a Dongle for WLAN access / LAN interconnection. Although the dongle has an Ethernet port, modbus is not working properly with this port. Some users report, that they cannot establish a connection, some are able to, but several modbus registers are working, and some not. It seems like Sungrow is actively working on that, so maybe in the near future they will release firmware upgrades to improve the modbus via WiNet S support. 

![Inverter LAN connetion](images/Inverter_LAN_ports.drawio.svg)

## Check #2


Some users reported, that the Inverter must be completely switched off and only is assigned an IP adress on cold-boot. So do the following: 

1. Turn off the AC to the inverter
2. Wait 10 seconds
3. Switch off battery (if available)
4. Wait 10 seconds
5. Switch off the DC power (the large switch at the side of the inverter)
6. Attach the LAN cable to the internal port
7. Wait 10 Minutes (so all capacitors inside completely discharge)
8. Perform steps 5 to 1 to properly boot the inverter, again
10. After bootup (give it 10 minutes), you should see the inverters IP adress in your LAN router.

## Check #3

If you are using Windows you can easily check, if the modbus connection generally works using [QModMaster](https://sourceforge.net/projects/qmodmaster/). I am pretty sure, that there are open source linux alternatives available :)

I tested it with the values shown in the screenshot. First set the TCP Settings (Options --> Modbus TCP) then adapt all highlighted parameters

![QModMaster setting ](/doc/images/QModMaster.png)


# 2. Only a subset of the sensors is available

## Error indication

Users with single-phase inverters have reported multiple issues (sungrows nomenclature is SH3.RS - single phase, vs. SH10.RT - three phase). These inverters only support a subset of the modbus registers (although the users reported using the inverter's built-in LAN port.)

--> sorry, can't fix this. It is up to Sungrow to make a platform independent modbus implementation :/ 


