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
    tests_done: "{n} of {total} checks completed",
    tests_none: "No test has run yet.",
    tests_unavailable: "The results could not be read.",
    bucket_failed: "Failed", bucket_inconclusive: "Not clear yet", bucket_not_run: "Waiting", bucket_passed: "Passed",
    bucket_not_supported: "Not enforced or not available",
    kind_effect: "Does what it is told", kind_readback: "Takes a setting", kind_plausibility: "Readings add up", kind_wallbox: "Wallbox",
    running: "Being measured now",
    disputed: "Two runs disagree",
    ev_commanded: "Asked for", ev_before: "Before", ev_during: "During", ev_after: "After", ev_observable: "Watched",
    ev_original: "Original", ev_written: "Written", ev_library_read: "Read back", ev_detail: "Detail", ev_verdict: "Verdict",
    ev_name: "Check", ev_run: "Run",
    waits_for: "Waits for",
    log: "Log, last 24 hours", log_empty: "Nothing recorded yet.", log_unavailable: "The log could not be read.",
    runs: "Runs ({n})", run: "Run {n}", put_back: "all {n} settings as before", not_put_back: "Not put back: {fields}",
    download: "Download the last diagnosis",
    test_docs: "What the tests do",
    update_title: "A newer Sungrow dashboard is available",
    update_reload: "The integration was updated. Reload to see the new dashboard.",
    update_text: "This dashboard was taken over and stays as it is. New since then:",
    reload: "Reload", add_beside: "Add it beside this one", replace: "Hold {s} s to replace this one",
    replace_note: "Replacing first downloads this dashboard as a file. Your own changes are then gone from it.",
    dismiss: "Dismiss", update_failed: "That did not work: {error}",
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
    tests_done: "{n} von {total} Prüfungen abgeschlossen",
    tests_none: "Noch kein Test gelaufen.",
    tests_unavailable: "Die Ergebnisse konnten nicht gelesen werden.",
    bucket_failed: "Fehlgeschlagen", bucket_inconclusive: "Noch nicht eindeutig", bucket_not_run: "Wartet", bucket_passed: "Bestanden",
    bucket_not_supported: "Nicht erzwungen oder nicht vorhanden",
    kind_effect: "Tut, was verlangt wird", kind_readback: "Übernimmt Einstellungen", kind_plausibility: "Messwerte passen zusammen", kind_wallbox: "Wallbox",
    running: "Wird gerade gemessen",
    disputed: "Zwei Läufe widersprechen sich",
    ev_commanded: "Verlangt", ev_before: "Vorher", ev_during: "Währenddessen", ev_after: "Nachher", ev_observable: "Beobachtet",
    ev_original: "Ursprünglich", ev_written: "Geschrieben", ev_library_read: "Zurückgelesen", ev_detail: "Einzelheit", ev_verdict: "Ergebnis",
    ev_name: "Prüfung", ev_run: "Lauf",
    waits_for: "Wartet auf",
    log: "Protokoll, letzte 24 Stunden", log_empty: "Noch nichts aufgezeichnet.", log_unavailable: "Das Protokoll konnte nicht gelesen werden.",
    runs: "Läufe ({n})", run: "Lauf {n}", put_back: "alle {n} Einstellungen wie vorher", not_put_back: "Nicht zurückgesetzt: {fields}",
    download: "Letzte Diagnose herunterladen",
    test_docs: "Was die Tests tun",
    update_title: "Es gibt ein neueres Sungrow-Dashboard",
    update_reload: "Die Integration wurde aktualisiert. Neu laden zeigt das neue Dashboard.",
    update_text: "Dieses Dashboard wurde übernommen und bleibt, wie es ist. Seitdem neu:",
    reload: "Neu laden", add_beside: "Daneben hinzufügen", replace: "{s} s halten zum Ersetzen",
    replace_note: "Vor dem Ersetzen wird dieses Dashboard als Datei heruntergeladen. Eigene Änderungen sind danach darin nicht mehr enthalten.",
    dismiss: "Ausblenden", update_failed: "Das hat nicht geklappt: {error}",
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

// Call `done` once `target` was held for `seconds()`; `bar` fills meanwhile.
// Returns what cancels a hold in progress.
export const onHold = (target, bar, seconds, done) => {
  let timer;
  const cancel = () => {
    clearTimeout(timer);
    timer = undefined;
    bar.classList.remove("holding");
  };
  const start = () => {
    cancel();
    bar.style.setProperty("--hold", `${seconds()}s`);
    // Next frame, so the bar starts from empty.
    requestAnimationFrame(() => timer && bar.classList.add("holding"));
    timer = setTimeout(() => {
      cancel();
      done();
    }, seconds() * 1000);
  };
  target.addEventListener("pointerdown", (event) => event.button === 0 && start());
  for (const name of ["pointerup", "pointerleave", "pointercancel", "keyup"]) target.addEventListener(name, cancel);
  target.addEventListener("contextmenu", (event) => event.preventDefault());
  target.addEventListener("keydown", (event) => {
    if ((event.key === "Enter" || event.key === " ") && !event.repeat) {
      event.preventDefault();
      start();
    }
  });
  return cancel;
};

// What a user chose for themselves, kept in Home Assistant, not the browser.
const USER_DATA = "sungrow_modbus_dashboard";
export const getChoices = async (hass) => {
  try {
    return (await hass.callWS({ type: "frontend/get_user_data", key: USER_DATA })).value ?? {};
  } catch (err) {
    console.warn("sungrow-modbus: could not read the user's choices", err);
    return {};
  }
};
export const setChoice = async (hass, choice) =>
  hass.callWS({ type: "frontend/set_user_data", key: USER_DATA, value: { ...(await getChoices(hass)), ...choice } });
