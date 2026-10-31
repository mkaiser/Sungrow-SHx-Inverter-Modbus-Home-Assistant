Hi everyone!

I am building a proper HACS integration to replace the YAML package, with a migration that keeps your history ([code](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/tree/proper-ha-integration), [HACS preview](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant-preview)). It will also cover **Sungrow wallboxes**, the **Logger** and the **iHomeManager**.

Sungrow publishes no firmware changelogs, and some registers behave differently between firmware versions: the export power limit is written ×10 on some and 1:1 on others. So I collect surveys from real devices.

**How:** [the survey README](README.md#contributing-your-device-survey) has both ways with screenshots: the preview integration in Home Assistant, or a terminal. 5–40 minutes per device. **Run read only diagnosis** only reads. **Run complete diagnosis and tests** also writes settings and puts them back; [what it does, and how to opt out](README.md#it-reads-and-writes-only-if-you-say-yes).

**What to send:** attach the `.json` file to this issue. Your serial is replaced by a stand-in, and your address is left out unless you allow its last two octets. Keep the `.log` file to yourself.

**Which devices are missing:** below, in order of usefulness.

Thanks!
