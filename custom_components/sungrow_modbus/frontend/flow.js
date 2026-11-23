// Sungrow Modbus: the power flow card.
//
// Part of the integration's dashboard module, loaded by sungrow-modbus.js.
// From github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT).
// Keep this line with any copy -- doc/attribution.md.

// It draws nothing itself. Where the user has power-flow-card-plus (from HACS)
// it shows that, with the house's entities filled in; everywhere else tiles,
// and for administrators one line on how to get it. It chooses when it is
// shown, so a dashboard taken over changes too once the card is installed.

const { DOCS, getChoices, language, say, setChoice } = await import(new URL(`shared.js${new URL(import.meta.url).search}`, import.meta.url));

const PLUS = "power-flow-card-plus";
const HACS_LINK =
  "https://my.home-assistant.io/redirect/hacs_repository/?owner=flixlix&repository=power-flow-card-plus&category=plugin";

// How long a listed resource may take to define its card.
const DEFINE_MS = 10_000;

const plusAvailable = async (hass) => {
  if (customElements.get(PLUS)) return true;
  try {
    const resources = await hass.callWS({ type: "lovelace/resources" });
    if (!resources.some((resource) => resource.url?.includes(PLUS))) return false;
  } catch (err) {
    console.warn("sungrow-modbus: could not list the dashboard resources", err);
    return false;
  }
  return Promise.race([
    customElements.whenDefined(PLUS).then(() => true),
    new Promise((resolve) => setTimeout(() => resolve(false), DEFINE_MS)),
  ]);
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
    type: `custom:${PLUS}`,
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
    const plus = this._config.style !== "tiles" && (await plusAvailable(this._hass));
    const helpers = await window.loadCardHelpers();
    const child = helpers.createCardElement(
      plus ? plusConfig(this._config.entities, lang) : tilesConfig(this._config.entities, lang),
    );
    child.hass = this._hass;
    this.replaceChildren(child);
    this._child = child;
    if (!plus && this._config.style !== "tiles" && this._hass.user?.is_admin) await this._hint(lang);
  }

  async _hint(lang) {
    if ((await getChoices(this._hass)).no_flow_hint) return;
    const hacs = this._hass.config.components.includes("hacs");
    const row = document.createElement("div");
    row.style.cssText =
      "display:flex;flex-wrap:wrap;gap:4px 16px;margin-top:8px;padding:0 4px;font-size:12px;color:var(--secondary-text-color)";
    const label = document.createElement("span");
    label.style.flex = "1 1 auto";
    label.textContent = say("flow_hint", lang);
    const link = document.createElement("a");
    link.href = hacs ? HACS_LINK : `${DOCS}/dashboard.md#the-power-flow`;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.style.color = "var(--primary-color)";
    link.textContent = say(hacs ? "flow_install" : "flow_how", lang);
    const dismiss = document.createElement("a");
    dismiss.href = "#";
    dismiss.style.color = "var(--secondary-text-color)";
    dismiss.textContent = say("flow_dismiss", lang);
    dismiss.addEventListener("click", async (event) => {
      event.preventDefault();
      await setChoice(this._hass, { no_flow_hint: true });
      row.remove();
    });
    row.append(label, link, dismiss);
    this.append(row);
  }
}
