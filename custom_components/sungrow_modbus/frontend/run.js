// Sungrow Modbus: how a test stands, and starting and clearing it.
//
// Part of the integration's dashboard module, loaded by sungrow-modbus.js.
// From github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT).
// Keep this line with any copy -- doc/attribution.md.

// The server guards all of it (`testimony.py`, the permissions); this says
// beforehand what it would refuse, and afterwards what came of a press.

const { checkOf, el, errorText, language, loadTexts, readStep, say, SHOW_ANSWERS } = await import(
  new URL(`shared.js${new URL(import.meta.url).search}`, import.meta.url)
);

const DOMAIN = "sungrow_modbus";
const READ_ONLY = "read_only";
const PARTS = ["now", "start", "clear"];
const GONE = ["unknown", "unavailable"];

export class SungrowModbusRunCard extends HTMLElement {
  static getStubConfig() {
    return { part: "now", device_id: "", entities: {} };
  }

  setConfig(config) {
    if (!PARTS.includes(config?.part)) throw new Error(`\`part\` is one of ${PARTS.join(", ")}`);
    if (!config.entities) throw new Error("`entities` is required");
    this._config = config;
    this._seen = undefined;
  }

  set hass(hass) {
    this._hass = hass;
    const states = Object.values(this._config.entities).map((id) => hass.states[id]);
    const seen = `${language(hass)} ${states.map((state) => state?.last_updated).join()}`;
    if (seen === this._seen) return;
    this._seen = seen;
    this._update();
  }

  getCardSize() {
    return 2;
  }

  getGridOptions() {
    return { columns: "full", rows: "auto" };
  }

  _state(role) {
    return this._hass.states[this._config.entities[role]];
  }

  _update() {
    const lang = language(this._hass);
    if (!this._root) {
      this._root = this.attachShadow({ mode: "open" });
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
        .row { display: flex; justify-content: space-between; gap: 12px; }
        .row span:last-child { text-align: end; overflow-wrap: anywhere; min-width: 0; }
        .bar { height: 10px; border-radius: 5px; overflow: hidden; background: var(--divider-color); }
        .bar div { height: 100%; background: var(--primary-color); }
        .done div { background: var(--success-color, #43a047); }
      `;
      const card = el("ha-card");
      this._content = el("div", "content");
      card.append(this._content);
      this._root.append(style, card);
    }
    // What was asked or answered stays, only whether a press is possible moves.
    if (this._config.part === "now" || this._lang !== lang || !this._buttons) {
      this._lang = lang;
      this._buttons = [];
      this._content.replaceChildren();
      this[`_${this._config.part}`](lang);
    }
    for (const [button, role] of this._buttons) button.disabled = this._busy || (this._state(role)?.state ?? "unavailable") === "unavailable";
  }

  _button(label, action, className = "") {
    const button = el("button", className, label);
    button.type = "button";
    button.addEventListener("click", action);
    return button;
  }

  // ---------------------------------------------------------------- now

  _line(name, value, percent, className = "") {
    const row = el("div", "row");
    row.append(el("span", "note", name), el("span", "", value));
    this._content.append(row);
    if (percent === undefined) return;
    const bar = el("div", `bar ${className}`);
    const part = el("div");
    part.style.width = `${Math.max(0, Math.min(100, percent))}%`;
    bar.append(part);
    this._content.append(bar);
  }

  _now(lang) {
    const status = this._state("status");
    const { running, what } = readStep(this._state("step")?.state);
    const { established, total } = status?.attributes ?? {};
    if (total) this._line(say("run_overall", lang), say("run_overall_value", lang, { n: established, total }), (100 * established) / total, "done");
    else if (status) this._line(say("run_overall", lang), say("run_none", lang));
    const progress = this._state("progress")?.state;
    if (running && progress && !GONE.includes(progress)) this._line(say("run_this", lang), `${Math.round(Number(progress))} %`, Number(progress));
    if (running) this._content.append(el("div", "note", say("measuring", lang, { what: this._checkLabel(this._state("step")?.state, lang) ?? (what || say("starting", lang)) })));
    if (!status) return;
    const next = this._state("next")?.state;
    let when;
    if (!status.attributes.continuous) when = say("next_off", lang);
    else if (running) when = say("next_running", lang);
    else if (next && !GONE.includes(next)) when = this._time(next);
    else when = say("next_house", lang);
    this._line(say("run_next", lang), when);
  }

  // A check's name for a person, once the names were fetched.
  _checkLabel(state, lang) {
    if (!this._names) {
      this._names = { names: [], steps: [], labels: new Map() };
      this._fetchNames();
    }
    const label = this._names.labels.get(checkOf(state, this._names.names, this._names.steps));
    return label?.[lang] ?? label?.en;
  }

  async _fetchNames() {
    try {
      const { rows, steps } = await this._hass.callWS({ type: "sungrow_modbus/diagnosis/results", device_id: this._config.device_id });
      // A first run has no rows yet, so the next run asks again.
      if (!rows.length) {
        this._names = undefined;
        return;
      }
      this._names = {
        names: rows.map((row) => row.name).sort((a, b) => b.length - a.length),
        steps,
        labels: new Map(rows.map((row) => [row.name, row.label])),
      };
      this._update();
    } catch (err) {
      console.warn("sungrow-modbus: no names of the checks", err);
    }
  }

  _time(iso) {
    const at = new Date(iso);
    return at.toLocaleTimeString(this._hass.locale?.language, {
      timeStyle: "short",
      ...(this._hass.locale?.time_zone === "server" ? { timeZone: this._hass.config.time_zone } : {}),
    });
  }

  // ---------------------------------------------------------------- pressing

  _say(said, message, error = false) {
    said.textContent = message;
    said.classList.toggle("error", error);
  }

  // Returns whether the press went through; a refusal is said in the card.
  async _press(role, said, done) {
    const lang = language(this._hass);
    this._busy = true;
    this._update();
    try {
      await this._hass.callService("button", "press", { entity_id: this._config.entities[role] }, undefined, false);
      this._say(said, say(done, lang));
    } catch (err) {
      console.warn("sungrow-modbus: refused", err);
      this._say(said, say("action_failed", lang, { error: await errorText(this._hass, err) }), true);
    } finally {
      this._busy = false;
      this._update();
    }
  }

  // ---------------------------------------------------------------- start

  _start(lang) {
    const button = this._button(say("start", lang), () => this._tryStart(), "main");
    this._buttons.push([button, "start"]);
    const buttons = el("div", "buttons");
    buttons.append(button);
    this._said = el("div", "said");
    this._said.setAttribute("role", "status");
    this._asked = el("div", "content");
    this._asked.style.padding = "0";
    this._asked.hidden = true;
    this._content.append(buttons, this._said, this._asked);
  }

  _hideAsked() {
    this._asked.hidden = true;
    this._asked.replaceChildren();
  }

  async _tryStart() {
    if (this._busy) return;
    this._hideAsked();
    this._say(this._said, "");
    let missing;
    let localize;
    this._busy = true;
    this._update();
    try {
      localize = (await loadTexts(this._hass, language(this._hass))).options;
      ({ missing } = await this._hass.callWS({ type: `${DOMAIN}/diagnosis/settings`, device_id: this._config.device_id }));
    } catch (err) {
      // The server refuses what it must; this only asks first.
      console.warn("sungrow-modbus: could not check the answers", err);
    } finally {
      this._busy = false;
      this._update();
    }
    if (missing?.keys.length) this._ask(missing, localize);
    else await this._press("start", this._said, "started");
  }

  _ask({ entry_id, title, keys }, localize) {
    const lang = language(this._hass);
    const readOnly = this._state("mode")?.state === READ_ONLY;
    const list = el("ul");
    for (const key of keys) {
      list.append(el("li", "", localize(`component.${DOMAIN}.options.step.init.sections.diagnosis.data.${key}`) || key));
    }
    const buttons = el("div", "buttons");
    const go = this._button(say("missing_go", lang), () => {
      const event = new CustomEvent(SHOW_ANSWERS, { cancelable: true, detail: { entry_id, keys } });
      // Another inverter's entry may not be on this page.
      if (window.dispatchEvent(event)) this._asked.append(el("div", "note", say("missing_elsewhere", lang, { title })));
    }, "main");
    buttons.append(go);
    if (readOnly) {
      buttons.append(this._button(say("start_anyway", lang), () => {
        this._hideAsked();
        this._press("start", this._said, "started");
      }));
    }
    this._asked.replaceChildren(
      el("div", readOnly ? "" : "error", say(readOnly ? "missing_read_only" : "missing_extended", lang, { title })), list, buttons,
    );
    this._asked.hidden = false;
  }

  // ---------------------------------------------------------------- clear

  _clear(lang) {
    for (const role of ["history", "readings"]) {
      if (!this._config.entities[role]) continue;
      const buttons = el("div", "buttons");
      const said = el("div", "said");
      said.setAttribute("role", "status");
      const clear = this._button(say(`clear_${role}`, lang), () => ask(true));
      const yes = this._button(say("clear_confirm", lang), () => {
        ask(false);
        this._press(role, said, "cleared");
      }, "danger");
      const no = this._button(say("clear_cancel", lang), () => ask(false));
      const ask = (asking) => {
        this._say(said, "");
        clear.hidden = asking;
        yes.hidden = no.hidden = !asking;
      };
      ask(false);
      this._buttons.push([clear, role], [yes, role]);
      buttons.append(clear, yes, no);
      this._content.append(buttons, el("div", "note", say(`clear_${role}_note`, lang)), said);
    }
  }
}
