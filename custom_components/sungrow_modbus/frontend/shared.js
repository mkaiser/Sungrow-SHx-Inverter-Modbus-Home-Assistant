// Sungrow Modbus: what its modules share -- the texts and the language.
//
// Part of the integration's dashboard module, loaded by sungrow-modbus.js.
// From github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT).
// Keep this line with any copy -- doc/attribution.md.

const TEXT = {
  en: {
    empty: "No Sungrow Modbus device found. Add the integration under Settings → Devices & services.",
    device_page: "Device page",
    integration_page: "Integration",
    hold: "Hold {s} s to change",
    unlocked: "Unlocked, locks in {s} s",
    lock: "Lock",
    strategy_description: "Inverter, battery and wallbox, built from what your house has.",
    lock_description: "Guards any card against changes until it is held for a few seconds.",
    flow_description: "Power between PV, house, grid and battery, live.",
    flow_hint: "An animated power flow can be shown here.",
    flow_install: "Install Power Flow Card Plus",
    flow_how: "How",
    flow_dismiss: "Not interested",
    solar: "PV", home: "House", grid: "Grid", battery: "Battery", car: "Car",
    import: "From the grid", export: "To the grid", charge: "Charging", discharge: "Discharging", level: "Battery",
    energy_hint: "Set up Home Assistant's Energy dashboard to see your energy flow here.",
    energy_setup: "Set it up",
    energy_guide: "Which sensors to pick",
  },
  de: {
    empty: "Kein Sungrow-Modbus-Gerät gefunden. Die Integration wird unter Einstellungen → Geräte & Dienste hinzugefügt.",
    device_page: "Geräteseite",
    integration_page: "Integration",
    hold: "{s} s halten zum Ändern",
    unlocked: "Entsperrt, sperrt in {s} s",
    lock: "Sperren",
    strategy_description: "Wechselrichter, Batterie und Wallbox, gebaut aus dem, was das Haus hat.",
    lock_description: "Schützt eine Karte vor Änderungen, bis sie einige Sekunden gehalten wird.",
    flow_description: "Leistung zwischen PV, Haus, Netz und Batterie, live.",
    flow_hint: "Hier kann ein animierter Leistungsfluss stehen.",
    flow_install: "Power Flow Card Plus installieren",
    flow_how: "So geht's",
    flow_dismiss: "Kein Interesse",
    solar: "PV", home: "Haus", grid: "Netz", battery: "Batterie", car: "Auto",
    import: "Vom Netz", export: "Ins Netz", charge: "Lädt", discharge: "Entlädt", level: "Batterie",
    energy_hint: "Mit eingerichtetem Energie-Dashboard von Home Assistant steht hier der Energiefluss.",
    energy_setup: "Einrichten",
    energy_guide: "Welche Sensoren",
  },
};

// On the development branch until the merge into main, which moves it.
export const DOCS = "https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/blob/proper-ha-integration/doc";

export const language = (hass) => {
  const lang = (hass?.locale?.language || hass?.language || navigator.language || "en").split("-")[0];
  return lang in TEXT ? lang : "en";
};
export const text = (value, lang) => (typeof value === "string" ? value : value?.[lang] ?? value?.en ?? "");
export const say = (key, lang, values = {}) =>
  TEXT[lang][key].replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ""));
