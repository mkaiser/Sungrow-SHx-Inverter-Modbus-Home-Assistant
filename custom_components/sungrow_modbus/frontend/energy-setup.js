// Sungrow Modbus: which sensors Home Assistant's Energy dashboard takes.
//
// Part of the integration's dashboard module, loaded by sungrow-modbus.js.
// From github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT).
// Keep this line with any copy -- doc/attribution.md.

// The house's own entities, field by field, and, for an administrator while
// nothing is set up, a press that adds them. It never changes a set-up one.

const { DOCS, el, errorText, language, say } = await import(
  new URL(`shared.js${new URL(import.meta.url).search}`, import.meta.url)
);

// In the order of the Energy dashboard's own settings page.
const FIELDS = ["import", "export", "grid_power", "solar", "solar_power", "charge", "discharge", "battery_power", "soc", "car"];
// Expected of a new sensor: its statistics begin with the first full hour.
const EARLY = new Set(["statistics_not_defined"]);

const optional = (key, value) => (value ? { [key]: value } : {});

// What `energy/save_prefs` takes; `doc/energy_dashboard.md` says why these.
export const energyPrefs = (e) => {
  const sources = [];
  if (e.import || e.export) {
    sources.push({
      type: "grid", stat_energy_from: e.import ?? null, stat_energy_to: e.export ?? null, cost_adjustment_day: 0,
      ...optional("stat_rate", e.grid_power),
    });
  }
  if (e.solar) sources.push({ type: "solar", stat_energy_from: e.solar, config_entry_solar_forecast: null, ...optional("stat_rate", e.solar_power) });
  if (e.charge && e.discharge) {
    sources.push({
      type: "battery", stat_energy_from: e.discharge, stat_energy_to: e.charge,
      ...optional("stat_rate", e.battery_power), ...optional("stat_soc", e.soc),
    });
  }
  return { sources, devices: e.car ? [{ stat_consumption: e.car }] : [] };
};

export class SungrowModbusEnergySetupCard extends HTMLElement {
  static getStubConfig() {
    return { entities: {} };
  }

  setConfig(config) {
    if (!config?.entities) throw new Error("`entities` is required");
    this._config = config;
    this._lang = undefined;
  }

  set hass(hass) {
    this._hass = hass;
    const lang = language(hass);
    if (lang !== this._lang) this._render(lang);
    for (const [cell, id] of this._values) cell.textContent = this._value(id);
  }

  getCardSize() {
    return this._config.done ? 1 : 6;
  }

  getGridOptions() {
    return { columns: "full", rows: "auto" };
  }

  _value(id) {
    const state = this._hass.states[id];
    return state ? (this._hass.formatEntityState?.(state) ?? state.state) : "";
  }

  _render(lang) {
    this._lang = lang;
    this._root ??= this.attachShadow({ mode: "open" });
    const style = el("style");
    style.textContent = `
      .content { padding: 12px 16px; display: grid; gap: 10px; }
      [hidden] { display: none !important; }
      .note { color: var(--secondary-text-color); font-size: 13px; overflow-wrap: anywhere; }
      .said:empty { display: none; }
      .said { font-weight: 500; }
      .error { color: var(--error-color); }
      .buttons { display: flex; flex-wrap: wrap; gap: 8px; }
      button {
        font: inherit; border: 1px solid var(--primary-color); border-radius: 12px; padding: 6px 14px; cursor: pointer;
        background: none; color: var(--primary-color);
      }
      button:disabled { opacity: 0.5; cursor: default; }
      button.main { background: var(--primary-color); color: var(--text-primary-color, #fff); }
      button.danger { border-color: var(--error-color); color: var(--error-color); }
      ul { margin: 0; padding-inline-start: 20px; font-size: 13px; }
      .scroll { overflow-x: auto; }
      table { border-collapse: collapse; width: 100%; font-size: 14px; }
      th, td { text-align: start; padding: 6px 12px 6px 0; border-bottom: 1px solid var(--divider-color); vertical-align: top; }
      th { color: var(--secondary-text-color); font-weight: 500; }
      td:last-child { white-space: nowrap; }
      code { display: block; color: var(--secondary-text-color); font-size: 12px; overflow-wrap: anywhere; user-select: all; }
      summary { cursor: pointer; }
      a { color: var(--primary-color); }
      .links { display: flex; flex-wrap: wrap; gap: 4px 20px; }
    `;
    const card = el("ha-card");
    const content = el("div", "content");
    card.append(content);
    this._root.replaceChildren(style, card);
    this._values = [];
    const { entities, done, several } = this._config;
    let body = content;
    if (done) {
      const fold = el("details");
      body = el("div", "content");
      fold.append(el("summary", "", say("energy_fold", lang)), body);
      content.append(fold);
    } else content.append(el("div", "", say("energy_hint", lang)));
    body.append(this._table(entities, lang));
    if (several) body.append(el("div", "note", say("energy_several", lang)));
    const links = el("div", "links");
    for (const [key, href, target] of [["energy_setup", "/config/energy"], ["energy_guide", `${DOCS}/energy_dashboard.md`, "_blank"]]) {
      const link = el("a", "", say(key, lang));
      link.href = href;
      if (target) Object.assign(link, { target, rel: "noreferrer" });
      links.append(link);
    }
    body.append(links);
    // Which inverter the grid and the battery hang on, with several, is the owner's to say.
    if (!done && !several && this._hass.user?.is_admin && energyPrefs(entities).sources.length) this._offer(content, lang);
  }

  _table(entities, lang) {
    const table = el("table");
    const head = el("tr");
    for (const key of ["energy_field", "energy_entity", "energy_now"]) head.append(el("th", "", say(key, lang)));
    table.append(head);
    for (const role of FIELDS) {
      const id = entities[role];
      if (!id) continue;
      const row = el("tr");
      const entity = el("td", "", this._hass.states[id]?.attributes.friendly_name ?? id);
      entity.append(el("code", "", id));
      const value = el("td");
      this._values.push([value, id]);
      row.append(el("td", "", say(`energy_${role}`, lang)), entity, value);
      table.append(row);
    }
    const scroll = el("div", "scroll");
    scroll.append(table);
    return scroll;
  }

  _offer(content, lang) {
    const buttons = el("div", "buttons");
    const said = el("div", "said");
    said.setAttribute("role", "status");
    const note = el("div", "note", say("energy_ask", lang));
    const button = (key, className, action) => {
      const node = el("button", className, say(key, lang));
      node.type = "button";
      node.addEventListener("click", action);
      return node;
    };
    const add = button("energy_add", "main", () => ask(true));
    const yes = button("energy_confirm", "main", async () => {
      ask(false);
      add.disabled = true;
      add.disabled = await this._add(said, lang);
    });
    const no = button("energy_cancel", "", () => ask(false));
    const ask = (asking) => {
      add.hidden = asking;
      yes.hidden = no.hidden = note.hidden = !asking;
    };
    ask(false);
    buttons.append(add, yes, no);
    content.append(note, buttons, said);
  }

  // Returns whether there is nothing left to add.
  async _add(said, lang) {
    said.classList.remove("error");
    said.textContent = "";
    try {
      let now = {};
      try {
        now = await this._hass.callWS({ type: "energy/get_prefs" });
      } catch (err) {
        // The only answer that says nothing is set up; any other is no answer.
        if (err?.code !== "not_found") throw err;
      }
      if (now.energy_sources?.length) {
        said.textContent = say("energy_already", lang);
        return true;
      }
      const { sources, devices } = energyPrefs(this._config.entities);
      const addDevices = devices.length && !now.device_consumption?.length;
      await this._hass.callWS({
        type: "energy/save_prefs", energy_sources: sources, ...(addDevices ? { device_consumption: devices } : {}),
      });
    } catch (err) {
      console.warn("sungrow-modbus: energy dashboard not set up", err);
      said.classList.add("error");
      said.textContent = say("energy_failed", lang, { error: await errorText(this._hass, err) });
      return false;
    }
    said.textContent = say("energy_added", lang);
    try {
      const report = await this._hass.callWS({ type: "energy/validate" });
      const issues = [...(report.energy_sources ?? []), ...(report.device_consumption ?? [])].flat().filter((issue) => !EARLY.has(issue.type));
      if (issues.length) said.textContent = say("energy_check", lang, { issues: [...new Set(issues.map((issue) => issue.type))].join(", ") });
    } catch (err) {
      console.warn("sungrow-modbus: could not check the energy dashboard", err);
    }
    return true;
  }
}
