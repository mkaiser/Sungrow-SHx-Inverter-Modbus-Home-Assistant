Hi everyone!

I am finally building a proper HACS-based integration, with a full migration path from the current YAML package to preserve your history data. See [code development](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/tree/proper-ha-integration) and [temporary preview branch for HACS](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant-preview).

As well as the Sungrow inverters supported today, the integration will cover **Sungrow wallboxes**, the **Logger** and the **iHomeManager**.

Sungrow does not publish firmware changelogs, and we found that some registers behave differently on different firmware. For example, the export power limit is written ×10 on some firmware and 1:1 on others. So I am running a survey to collect complete register sets from real Sungrow devices. The results are kept in this repository and will help to identify firmware changes.

**How to run it:** [device-survey/README.md](README.md#contributing-your-device-survey), with screenshots. Either in Home Assistant with the HACS preview integration (choose *Perform the device survey*, then press *Run read only diagnosis*), or from a terminal. It takes 5–40 minutes per device, depending on the link. Stop anything else polling the inverter while it runs.

**It only reads**, unless you also run the *control test*, which writes settings and puts them all back. That is a separate button, and the terminal survey asks first; the default is no.

**What to send:** attach the `<label>.json` file the run names to this issue. In that file your serial is replaced by an anonymized stand-in, and your IP address is left out. Keep the `.log` file to yourself, because it contains your real serial.

**Which devices are missing:** the list below, from [devices-wanted.md](devices-wanted.md), in order of usefulness. RS, MG and T-series inverters, wallboxes, SBR batteries and Loggers are especially welcome.

Thanks!
