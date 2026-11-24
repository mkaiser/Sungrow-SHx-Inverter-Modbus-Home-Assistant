// Sungrow Modbus: the power flow card.
//
// Part of the integration's dashboard module, loaded by sungrow-modbus.js.
// From github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT).
// Keep this line with any copy -- doc/attribution.md.

// It draws nothing itself. It shows power-flow-card-plus, or for the day's
// energy energy-flow-card-plus, both by flixlix (MIT), which come with the
// integration's library under names of their own, with the house's entities
// filled in; tiles where one is missing or fails to load. It chooses when it
// is shown, so a dashboard taken over follows too.

const { language, say } = await import(new URL(`shared.js${new URL(import.meta.url).search}`, import.meta.url));

// `kind` of the card: the element, and its file. Not versioned: the server
// revalidates it, and an element is defined once per page.
const KINDS = {
  power: ["sungrow-modbus-power-flow", "/sungrow_modbus_cards/power-flow.js"],
  energy: ["sungrow-modbus-energy-flow", "/sungrow_modbus_cards/energy-flow.js"],
};

const bundles = new Map();
const available = async (kind) => {
  const [tag, url] = KINDS[kind];
  if (customElements.get(tag)) return true;
  try {
    await (bundles.get(kind) ?? bundles.set(kind, import(url)).get(kind));
  } catch (err) {
    console.warn(`sungrow-modbus: no ${kind} flow card, showing tiles`, err);
    bundles.delete(kind);
  }
  return Boolean(customElements.get(tag));
};

// The day's energy: the same circles from the day's sensors, which are in kWh.
const energyConfig = (e, lang) => {
  const entities = {};
  if (e.solar) entities.solar = { entity: e.solar, name: say("solar", lang) };
  if (e.import || e.export) {
    entities.grid = { entity: { consumption: e.import, production: e.export }, name: say("grid", lang), color_circle: true };
  }
  if (e.charge || e.discharge) {
    entities.battery = {
      entity: { consumption: e.discharge, production: e.charge },
      state_of_charge: e.level,
      name: say("battery", lang),
      color_circle: true,
    };
  }
  entities.home = { entity: e.home, name: say("home", lang), color_icon: true };
  // The lifetime counter: the card takes what it rose by in the period.
  if (e.car) {
    entities.individual = [{ entity: e.car, name: say("car", lang), icon: "mdi:car-electric", color: "#9c27b0", display_zero: true }];
  }
  return { type: `custom:${KINDS.energy[0]}`, entities, clickable_entities: true };
};

const plusConfig = (e, lang) => {
  const entities = {};
  if (e.solar) entities.solar = { entity: e.solar, name: say("solar", lang) };
  if (e.import || e.export) {
    entities.grid = { entity: { consumption: e.import, production: e.export }, name: say("grid", lang), color_circle: true };
  }
  if (e.charge || e.discharge) {
    entities.battery = {
      entity: { consumption: e.discharge, production: e.charge },
      state_of_charge: e.level,
      name: say("battery", lang),
      color_circle: true,
    };
  }
  entities.home = { name: say("home", lang), color_icon: true };
  if (e.car) {
    entities.individual = [{ entity: e.car, name: say("car", lang), icon: "mdi:car-electric", color: "#9c27b0", display_zero: true }];
  }
  return {
    type: `custom:${KINDS.power[0]}`,
    entities,
    clickable_entities: true,
    use_new_flow_rate_model: true,
    display_zero_lines: { mode: "grey_out", transparency: 50, grey_color: [189, 189, 189] },
    watt_threshold: 1000,
    kw_decimals: 2,
    w_decimals: 0,
  };
};

const TILES = [
  ["solar", "mdi:solar-power", "amber"],
  ["home", "mdi:home", "blue"],
  ["import", "mdi:transmission-tower-import", "red"],
  ["export", "mdi:transmission-tower-export", "green"],
  ["charge", "mdi:battery-plus", "teal"],
  ["discharge", "mdi:battery-minus", "teal"],
  ["car", "mdi:car-electric", "purple"],
];
const tilesConfig = (e, lang) => ({
  type: "grid",
  columns: 2,
  square: false,
  cards: TILES.filter(([role]) => e[role]).map(([role, icon, color]) => ({
    type: "tile", entity: e[role], name: say(role, lang), icon, color,
  })),
});

export class SungrowModbusFlowCard extends HTMLElement {
  setConfig(config) {
    if (!config?.entities) throw new Error("`entities` is required");
    this._config = config;
    this._started = false;
    if (this._hass) this._start();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._child) this._child.hass = hass;
    if (this._config && !this._started) this._start();
  }

  getCardSize() {
    return 5;
  }

  getGridOptions() {
    return { columns: "full", rows: "auto" };
  }

  async _start() {
    this._started = true;
    this.style.display = "block";
    const lang = language(this._hass);
    const kind = this._config.kind === "energy" ? "energy" : "power";
    const plus = this._config.style !== "tiles" && (await available(kind));
    const helpers = await window.loadCardHelpers();
    const e = this._config.entities;
    const child = helpers.createCardElement(
      !plus ? tilesConfig(e, lang) : kind === "energy" ? energyConfig(e, lang) : plusConfig(e, lang),
    );
    child.hass = this._hass;
    this.replaceChildren(child);
    this._child = child;
  }
}
