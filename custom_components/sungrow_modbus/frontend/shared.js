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
    history_note: "On some inverters the yearly PV and PV export read too high; the lifetime totals are not affected.",
    strategy_description: "Inverter, battery and wallbox, built from what your house has.",
    lock_description: "Guards any card against changes until it is held for a few seconds.",
    flow_description: "Power between PV, house, grid and battery, live.",
    solar: "PV", home: "House", grid: "Grid", battery: "Battery", car: "Car",
    import: "From the grid", export: "To the grid", charge: "Charging", discharge: "Discharging", level: "Battery",
    energy_hint: "Home Assistant's Energy dashboard is not set up yet. It asks you to pick a sensor for each field; these are yours.",
    energy_fold: "Which sensors the Energy dashboard takes",
    energy_field: "In the Energy dashboard", energy_entity: "Your sensor", energy_now: "Now",
    energy_import: "Grid → Grid consumption", energy_export: "Grid → Return to grid", energy_grid_power: "Grid → Grid power",
    energy_solar: "Solar panels → Solar production energy", energy_solar_power: "Solar panels → Solar production power",
    energy_charge: "Home battery storage → Energy charged", energy_discharge: "Home battery storage → Energy discharged",
    energy_battery_power: "Home battery storage → Battery power", energy_soc: "Home battery storage → State of charge",
    energy_car: "Individual devices",
    energy_several: "Several inverters: add the solar panels of each, but the grid and the battery only from the inverter they are wired to. See the guide.",
    energy_add: "Add these for me", energy_confirm: "Yes, add them", energy_cancel: "Cancel",
    energy_ask: "This writes the sensors above into Home Assistant's Energy dashboard, which is empty now. Prices are not set. You can change everything there afterwards.",
    energy_added: "Added. The Energy dashboard fills with the first full hour.",
    energy_already: "The Energy dashboard is already set up, so nothing was changed.",
    energy_failed: "Not added: {error}", energy_check: "Added, but Home Assistant reports: {issues}",
    energy_setup: "Set it up",
    energy_guide: "Which sensors to pick",
    tests_done: "{n} of {total} checks completed",
    tests_none: "No test has run yet.",
    tests_unavailable: "The results could not be read.",
    bucket_failed: "Failed", bucket_inconclusive: "Not clear yet", bucket_not_run: "Waiting", bucket_passed: "Passed",
    bucket_not_supported: "Not enforced or not available",
    kind_effect: "Control response", kind_readback: "Settings write & read", kind_plausibility: "Plausibility", kind_wallbox: "Wallbox",
    running: "Being measured now",
    disputed: "Two runs disagree",
    ev_commanded: "Asked for", ev_before: "Before", ev_during: "During", ev_after: "After", ev_observable: "Watched",
    ev_original: "Original", ev_written: "Written", ev_library_read: "Read back", ev_detail: "Detail", ev_verdict: "Verdict",
    ev_name: "Check", ev_run: "Run",
    waits_for: "Waits for",
    log: "Log, last 24 hours", log_empty: "Nothing recorded yet.", log_unavailable: "The log could not be read.",
    runs: "Runs ({n})", run: "Run {n}", put_back: "all {n} settings as before", not_put_back: "Not put back: {fields}",
    download: "Download the last diagnosis",
    download_failed: "The document is no longer there: it is kept until Home Assistant restarts. Download diagnostics on the device page has the results.",
    test_docs: "What the tests do",
    measuring: "Measuring now: {what}", auto_waits: "Auto repeat is on, and no run is in progress.", starting: "Starting",
    run_overall: "Overall", run_overall_value: "{n} of {total} checks", run_none: "no test kept yet", run_this: "This run",
    run_next: "Next attempt", next_running: "after this run", next_house: "as soon as conditions fit, checked every minute", next_off: "auto repeat is off",
    start: "Start", start_anyway: "Start anyway", started: "Started.", action_failed: "That did not work: {error}",
    missing_extended: "Not started. The extended test needs these answers first (about {title}):",
    missing_read_only: "These answers about {title} are missing. The results are worth more with them:",
    missing_go: "Go to the questions", missing_elsewhere: "Answer them in the settings of {title}: Settings → Devices & services → Sungrow Modbus → Configure.",
    clear_history: "Clear test results", clear_history_note: "Forgets the kept test runs and what they measured. Running the tests again brings them back, in about a day and a night. Nothing on the device changes.",
    clear_readings: "Clear collected readings", clear_readings_note: "Forgets what the plausibility checks collected minute by minute. Collecting it again takes days. The test runs stay, and nothing on the device changes.",
    clear_confirm: "Yes, clear", clear_cancel: "Cancel", cleared: "Cleared.",
    answers_intro: "These answers help the maintainers judge the test results correctly: no register reports them.", answers_required: "* needed before an extended test",
    settings_saved: "Saved.", settings_failed: "Not saved: {error}", settings_more: "What this means",
    settings_running: "Fixed while a test runs.", settings_none: "Nothing to set for this device.",
    settings_unavailable: "The settings could not be read.",
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
    history_note: "Bei manchen Wechselrichtern sind die Jahreswerte für PV und PV-Einspeisung zu hoch; die Gesamtzähler sind davon nicht betroffen.",
    strategy_description: "Wechselrichter, Batterie und Wallbox, gebaut aus dem, was das Haus hat.",
    lock_description: "Schützt eine Karte vor Änderungen, bis sie einige Sekunden gehalten wird.",
    flow_description: "Leistung zwischen PV, Haus, Netz und Batterie, live.",
    solar: "PV", home: "Haus", grid: "Netz", battery: "Batterie", car: "Auto",
    import: "Vom Netz", export: "Ins Netz", charge: "Lädt", discharge: "Entlädt", level: "Batterie",
    energy_hint: "Das Energie-Dashboard von Home Assistant ist noch nicht eingerichtet. Es fragt für jedes Feld nach einem Sensor; das sind deine.",
    energy_fold: "Welche Sensoren das Energie-Dashboard braucht",
    energy_field: "Im Energie-Dashboard", energy_entity: "Dein Sensor", energy_now: "Jetzt",
    energy_import: "Stromnetz → Netzverbrauch", energy_export: "Stromnetz → Netzeinspeisung", energy_grid_power: "Stromnetz → Netzleistung",
    energy_solar: "Solarmodule → Solarproduktion (Energie)", energy_solar_power: "Solarmodule → Solarproduktion (Leistung)",
    energy_charge: "Batteriespeicher → In die Batterie geladen", energy_discharge: "Batteriespeicher → Aus der Batterie entladen",
    energy_battery_power: "Batteriespeicher → Batterieleistung", energy_soc: "Batteriespeicher → Ladestand",
    energy_car: "Einzelne Geräte",
    energy_several: "Mehrere Wechselrichter: die Solarmodule von jedem hinzufügen, Netz und Batterie aber nur von dem Wechselrichter, an dem sie hängen. Siehe Anleitung.",
    energy_add: "Für mich eintragen", energy_confirm: "Ja, eintragen", energy_cancel: "Abbrechen",
    energy_ask: "Das schreibt die Sensoren oben in das Energie-Dashboard von Home Assistant, das jetzt leer ist. Preise werden nicht gesetzt. Alles lässt sich dort danach ändern.",
    energy_added: "Eingetragen. Das Energie-Dashboard füllt sich mit der ersten vollen Stunde.",
    energy_already: "Das Energie-Dashboard ist schon eingerichtet, es wurde nichts geändert.",
    energy_failed: "Nicht eingetragen: {error}", energy_check: "Eingetragen, aber Home Assistant meldet: {issues}",
    energy_setup: "Einrichten",
    energy_guide: "Welche Sensoren",
    tests_done: "{n} von {total} Prüfungen abgeschlossen",
    tests_none: "Noch kein Test gelaufen.",
    tests_unavailable: "Die Ergebnisse konnten nicht gelesen werden.",
    bucket_failed: "Fehlgeschlagen", bucket_inconclusive: "Noch nicht eindeutig", bucket_not_run: "Wartet", bucket_passed: "Bestanden",
    bucket_not_supported: "Nicht erzwungen oder nicht vorhanden",
    kind_effect: "Reaktion auf Befehle", kind_readback: "Einstellungen schreiben & lesen", kind_plausibility: "Plausibilität der Messwerte", kind_wallbox: "Wallbox",
    running: "Wird gerade gemessen",
    disputed: "Zwei Läufe widersprechen sich",
    ev_commanded: "Verlangt", ev_before: "Vorher", ev_during: "Währenddessen", ev_after: "Nachher", ev_observable: "Beobachtet",
    ev_original: "Ursprünglich", ev_written: "Geschrieben", ev_library_read: "Zurückgelesen", ev_detail: "Einzelheit", ev_verdict: "Ergebnis",
    ev_name: "Prüfung", ev_run: "Lauf",
    waits_for: "Wartet auf",
    log: "Protokoll, letzte 24 Stunden", log_empty: "Noch nichts aufgezeichnet.", log_unavailable: "Das Protokoll konnte nicht gelesen werden.",
    runs: "Läufe ({n})", run: "Lauf {n}", put_back: "alle {n} Einstellungen wie vorher", not_put_back: "Nicht zurückgesetzt: {fields}",
    download: "Letzte Diagnose herunterladen",
    download_failed: "Das Dokument ist nicht mehr da: es bleibt bis zum Neustart von Home Assistant. Diagnosedaten herunterladen auf der Geräteseite enthält die Ergebnisse.",
    test_docs: "Was die Tests tun",
    measuring: "Wird gerade gemessen: {what}", auto_waits: "Die automatische Wiederholung ist an, gerade läuft kein Test.", starting: "Startet",
    run_overall: "Insgesamt", run_overall_value: "{n} von {total} Prüfungen", run_none: "noch kein Test aufbewahrt", run_this: "Dieser Lauf",
    run_next: "Nächster Versuch", next_running: "nach diesem Lauf", next_house: "sobald die Bedingungen passen, jede Minute geprüft", next_off: "automatische Wiederholung ist aus",
    start: "Starten", start_anyway: "Trotzdem starten", started: "Gestartet.", action_failed: "Das hat nicht geklappt: {error}",
    missing_extended: "Nicht gestartet. Der erweiterte Test braucht zuerst diese Angaben (zu {title}):",
    missing_read_only: "Diese Angaben zu {title} fehlen. Mit ihnen sind die Ergebnisse mehr wert:",
    missing_go: "Zu den Fragen", missing_elsewhere: "Beantworte sie in den Einstellungen von {title}: Einstellungen → Geräte & Dienste → Sungrow Modbus → Konfigurieren.",
    clear_history: "Testergebnisse löschen", clear_history_note: "Vergisst die aufbewahrten Testläufe und ihre Messungen. Neue Läufe bringen sie zurück, in etwa einem Tag und einer Nacht. Am Gerät ändert sich nichts.",
    clear_readings: "Gesammelte Messwerte löschen", clear_readings_note: "Vergisst, was die Plausibilitätsprüfungen Minute für Minute gesammelt haben. Das neu zu sammeln dauert Tage. Die Testläufe bleiben, und am Gerät ändert sich nichts.",
    clear_confirm: "Ja, löschen", clear_cancel: "Abbrechen", cleared: "Gelöscht.",
    answers_intro: "Diese Angaben helfen den Maintainern, die Testergebnisse richtig zu beurteilen: kein Register verrät sie.", answers_required: "* vor einem erweiterten Test nötig",
    settings_saved: "Gespeichert.", settings_failed: "Nicht gespeichert: {error}", settings_more: "Was das bedeutet",
    settings_running: "Während ein Test läuft nicht änderbar.", settings_none: "Für dieses Gerät gibt es nichts einzustellen.",
    settings_unavailable: "Die Einstellungen konnten nicht gelesen werden.",
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

// The profile's number format, which need not be its language's. An array is
// tried in order, as Home Assistant's own formatter does.
const NUMBER_LOCALES = {
  comma_decimal: ["en-US", "en"],
  decimal_comma: ["de", "es", "it"],
  space_comma: ["fr", "sv", "cs"],
  quote_decimal: ["de-CH"],
  system: undefined,
};
export const numberLocale = (hass) => {
  const format = hass.locale?.number_format;
  return {
    locale: format in NUMBER_LOCALES ? NUMBER_LOCALES[format] : hass.locale?.language,
    options: format === "none" ? { useGrouping: false } : {},
  };
};

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

export const el = (tag, className, content) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined) node.textContent = content;
  return node;
};

const DOMAIN = "sungrow_modbus";

// Configure's texts are loaded with its dialog, so asked for here. Once for all
// cards: a second question while the first is open is answered without them.
let texts;
let textsOf;
export const loadTexts = (hass, lang) => {
  if (textsOf !== lang) {
    textsOf = lang;
    texts = (async () => ({
      options: await hass.loadBackendTranslation("options", DOMAIN),
      selector: await hass.loadBackendTranslation("selector", DOMAIN),
      exceptions: await hass.loadBackendTranslation("exceptions", DOMAIN),
    }))();
    texts.catch(() => (textsOf = undefined));
  }
  return texts;
};

// What the server refused with, in the reader's language where it has one.
export const errorText = async (hass, err) => {
  if (err?.translation_domain === DOMAIN) {
    const { exceptions } = await loadTexts(hass, language(hass));
    const path = `component.${DOMAIN}.exceptions.${err.translation_key}.message`;
    const said = exceptions(path, err.translation_placeholders);
    if (said) return said;
  }
  return String(err?.message ?? err);
};

// What `sensor.diagnosis_step` starts with while auto repeat waits.
export const WAITING = "auto repeat";
// Its earlier start, still in the recorded history the log is drawn from.
const WAITING_BEFORE = "waiting for changed test conditions";
export const isWaiting = (state) => state.startsWith(`${WAITING}: `) || state.startsWith(WAITING_BEFORE);
// The same sensor's state, read: whether a run is in flight, and at what.
export const readStep = (state) => {
  if (!state || ["unknown", "unavailable", "never run", "stopped", "finished"].includes(state)) return { running: false, waiting: false, what: "" };
  if (isWaiting(state)) return { running: false, waiting: true, what: "" };
  if (state.startsWith("failed:")) return { running: false, waiting: false, what: state };
  return { running: true, waiting: false, what: state.startsWith("starting the ") ? "" : state.replace(/^(wallbox )?capability test: /, "").replaceAll("_", " ") };
};

// The check a step belongs to, by its ledger name. The table before the names:
// "discharging 4712 W to make the house export" is not the check "discharging
// start threshold", which is its own step. Names longest first: one may start another.
export const checkOf = (state, names, steps) => {
  const step = state?.match(/test: (.*)$/)?.[1];
  const own = step && names.find((name) => step.startsWith(name));
  return own ?? (step && steps.find(([start]) => step.startsWith(start))?.[1]);
};

// Asks the settings card of an entry to show its questions.
export const SHOW_ANSWERS = "sungrow-modbus-show-answers";
