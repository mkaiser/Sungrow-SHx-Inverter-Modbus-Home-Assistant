# The maintainer's SH10RT: a forced-charging window, sampled every 2 s, 2026-11-01

The control test's own engine, with only the charge window check, on the
maintainer's SH10RT (`anon-37323352958`, SAPPHIRE-H_B001.V000.P020) over its
own LAN port, Home Assistant stopped. A wrapper around the engine logged every
sample and every write with its time; the snapshot was flushed before the
first write and the ordinary restore put every word back, read back after.
Battery power is the inverter's sign: negative while charging.

## Run 1, 13:48-13:53 local, recovery 180 s

| t (s) | Event or sample | Battery W | PV W | Load W |
| --- | --- | --- | --- | --- |
| 16.3 | sample | 0 | 979 | 923 |
| 26.5 | sample | 0 | 986 | 1276 |
| 30.6 | sample | 436 | 978 | 1421 |
| 32.6 | sample | 0 | 981 | 880 |
| 34.7 | sample | 0 | 989 | 922 |
| 36.8 | **write forced_charging_raw = 170** (0xAA, on) | | | |
| 38.8 | sample | -261 | 988 | 923 |
| 40.9 | sample | -4499 | 1001 | 903 |
| 42.9 | sample | -4500 | 1002 | 903 |
| 49.0 | sample | -4499 | 1005 | 927 |
| 59.2 | sample | -4499 | 984 | 1421 |
| 69.4 | sample | -4499 | 986 | 926 |
| 79.6 | sample | -4499 | 983 | 924 |
| 89.8 | sample | -4499 | 990 | 935 |
| 98.8 | sample | -4499 | 988 | 939 |
| 109.0 | sample | -4499 | 981 | 935 |
| 111.1 | sample | -4499 | 979 | 928 |
| 113.1 | sample | -4499 | 978 | 932 |
| 115.1 | sample | -4499 | 967 | 934 |
| 117.1 | **write forced_charging_raw = 85** (0x55, back to the snapshot) | | | |
| 119.2 | sample | 0 | 955 | 940 |
| 121.2 | sample | 0 | 958 | 940 |
| 123.2 | sample | 0 | 944 | 934 |
| 131.4 | sample | 0 | 943 | 933 |
| 141.6 | sample | 0 | 936 | 931 |
| 151.8 | sample | 0 | 932 | 954 |
| 161.9 | sample | 174 | 919 | 984 |
| 172.1 | sample | 180 | 897 | 944 |
| 182.3 | sample | 180 | 886 | 940 |
| 192.5 | sample | 194 | 879 | 942 |
| 202.7 | sample | 217 | 864 | 946 |
| 212.9 | sample | 233 | 858 | 949 |
| 223.0 | sample | 248 | 837 | 955 |
| 233.2 | sample | 256 | 824 | 974 |
| 243.4 | sample | 303 | 808 | 982 |
| 253.6 | sample | 325 | 796 | 989 |
| 263.8 | sample | 346 | 776 | 992 |
| 273.9 | sample | 322 | 764 | 967 |
| 284.2 | sample | 339 | 758 | 974 |
| 294.4 | sample | 336 | 741 | 961 |
| 303.3 | sample | 357 | 727 | 966 |
| 313.5 | sample | 366 | 722 | 965 |

Every fifth sample kept away from the writes; all kept within 6 s of them.
The engine's verdict, under the rule of the time: before 0 W,
during 4499 W, after -359.5 W (charge power), drift
359.5 W, "could not tell". SoC read 7.7 % throughout; the window's
target was 17 %.

## Run 2, 13:56-13:59 local, recovery 20 s, the start judged by its bracket

Before -439 W ±54.5, during 4499 W ±0, after
-229 W ±34 (charge power), verdict "the inverter did as it was told". Every word
restored and read back: True.
