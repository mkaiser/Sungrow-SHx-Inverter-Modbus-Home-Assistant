// Sungrow Modbus: the diagnosis's options, in the Diagnosis view.
//
// Part of the integration's dashboard module, loaded by sungrow-modbus.js.
// From github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT).
// Keep this line with any copy -- doc/attribution.md.

// The same options Configure holds, with Configure's own texts: what is said
// about the installation (`answers`), and what the test may do (`tests`, which
// the layout puts behind the lock). Each field is saved when it is left.

const { language, say } = await import(new URL(`shared.js${new URL(import.meta.url).search}`, import.meta.url));

const DOMAIN = "sungrow_modbus";
const SECTION = { answers: "diagnosis", tests: "capability_test" };
const DETAIL = "diagnosis_other_inverter_detail";

const el = (tag, className, content) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined) node.textContent = content;
  return node;
};

// Configure's texts are loaded with its dialog, so asked for here. Once for all
// cards: a second question while the first is open is answered without them.
let texts;
let textsOf;
const loadTexts = (hass, lang) => {
  if (textsOf !== lang) {
    textsOf = lang;
    texts = (async () => ({
      options: await hass.loadBackendTranslation("options", DOMAIN),
      selector: await hass.loadBackendTranslation("selector", DOMAIN),
    }))();
    texts.catch(() => (textsOf = undefined));
  }
  return texts;
};

export class SungrowModbusSettingsCard extends HTMLElement {
  static getStubConfig() {
    return { device_id: "", part: "answers" };
  }

  setConfig(config) {
    if (!config?.device_id) throw new Error("`device_id` is required: the inverter's or the wallbox's");
    if (!SECTION[config.part]) throw new Error("`part` is answers or tests");
    this._config = config;
    this._seen = undefined;
  }

  set hass(hass) {
    this._hass = hass;
    // A run starting or ending fixes or frees the fields.
    const seen = `${language(hass)} ${(this._config.watch ?? []).map((id) => hass.states[id]?.state).join()}`;
    if (seen === this._seen) return;
    this._seen = seen;
    // Typing is not interrupted; leaving the field fetches.
    if (!this._root?.activeElement) this._fetch();
  }

  getCardSize() {
    return 6;
  }

  getGridOptions() {
    return { columns: "full", rows: "auto" };
  }

  async _fetch() {
    const mine = (this._request = (this._request ?? 0) + 1);
    let view;
    try {
      this._lang = language(this._hass);
      this._localize = await loadTexts(this._hass, this._lang);
      view = await this._hass.callWS({ type: `${DOMAIN}/diagnosis/settings`, device_id: this._config.device_id });
    } catch (err) {
      console.warn("sungrow-modbus: no settings", err);
    }
    if (mine === this._request) this._render(view);
  }

  _text(category, path) {
    return this._localize[category]?.(`component.${DOMAIN}.${category}.${path}`) || "";
  }

  // The detail is asked on a page of its own in Configure, whose text that is.
  _label(step, key, kind) {
    if (key === DETAIL) return this._text("options", `step.other_inverter.${kind}.${key}`);
    return this._text("options", `step.${step}.sections.${SECTION[this._config.part]}.${kind}.${key}`);
  }

  async _save(key, value) {
    this._note.textContent = "";
    try {
      this._view = await this._hass.callWS({
        type: `${DOMAIN}/diagnosis/settings/save`, device_id: this._config.device_id,
        part: this._config.part, values: { [key]: value },
      });
      this._render(this._view);
      this._note.textContent = say("settings_saved", this._lang);
    } catch (err) {
      console.warn("sungrow-modbus: not saved", err);
      // What is stored, not what was typed, is what a run goes by.
      await this._fetch();
      if (this._note) this._note.textContent = say("settings_failed", this._lang, { error: err.message ?? err });
    }
  }

  _input(row, running) {
    let input;
    if (row.kind === "select") {
      input = el("select");
      input.append(new Option("", ""));
      for (const option of row.options) {
        input.append(new Option(this._text("selector", `${row.key}.options.${option}`) || option, option));
      }
      input.value = row.value ?? "";
    } else if (row.kind === "multiline") {
      input = el("textarea");
      input.rows = 3;
      input.value = row.value ?? "";
    } else {
      input = el("input");
      input.type = { boolean: "checkbox", number: "number" }[row.kind] ?? "text";
      if (row.kind === "boolean") input.checked = Boolean(row.value);
      else input.value = row.value ?? "";
      if (row.kind === "number") Object.assign(input, { min: row.min, max: row.max, step: 1 });
    }
    input.disabled = running;
    input.id = row.key;
    input.addEventListener("change", () => {
      let value = input.value;
      if (row.kind === "boolean") value = input.checked;
      else if (row.kind === "number") value = input.value === "" ? null : Number(input.value);
      else if (row.kind === "select") value = input.value || null;
      this._save(row.key, value);
    });
    return input;
  }

  _render(view) {
    this._root ??= this.attachShadow({ mode: "open" });
    const focus = this._root.activeElement?.id;
    const style = el("style");
    style.textContent = `
      .content { padding: 12px 16px; display: grid; gap: 14px; }
      .field { display: grid; gap: 4px; }
      .check { display: flex; gap: 10px; align-items: flex-start; cursor: pointer; }
      .hint, .note { color: var(--secondary-text-color); font-size: 12px; overflow-wrap: anywhere; white-space: pre-line; }
      .note:empty { display: none; }
      details > summary { cursor: pointer; color: var(--secondary-text-color); font-size: 12px; }
      input:not([type=checkbox]), select, textarea {
        font: inherit; color: var(--primary-text-color); background: var(--secondary-background-color);
        border: 1px solid var(--divider-color); border-radius: 8px; padding: 8px; width: 100%; box-sizing: border-box;
      }
      input[type=checkbox] { width: 18px; height: 18px; flex: none; margin: 1px 0 0; accent-color: var(--primary-color); }
      :disabled { opacity: 0.6; }
    `;
    const card = el("ha-card");
    const content = el("div", "content");
    card.append(content);
    this._note = el("div", "note");
    if (!view) content.append(el("div", "hint", say("settings_unavailable", this._lang ?? "en")));
    else if (view.running) content.append(el("div", "hint", say("settings_running", this._lang)));
    const rows = view?.[this._config.part] ?? [];
    if (view && !rows.length) content.append(el("div", "hint", say("settings_none", this._lang)));
    for (const row of rows) {
      // What the other inverter is, only after a yes.
      if (row.key === DETAIL && rows.find((other) => other.key === "diagnosis_other_inverter")?.value !== "yes") continue;
      const field = el("div", "field");
      const label = el("label", row.kind === "boolean" ? "check" : "");
      label.htmlFor = row.key;
      const name = el("span", "", this._label(view.step, row.key, "data") || row.key);
      const input = this._input(row, view.running);
      label.append(...(row.kind === "boolean" ? [input, name] : [name]));
      field.append(label);
      if (row.kind !== "boolean") field.append(input);
      const hint = this._label(view.step, row.key, "data_description");
      if (hint) {
        const more = el("details");
        more.append(el("summary", "", say("settings_more", this._lang)), el("div", "hint", hint));
        field.append(more);
      }
      content.append(field);
    }
    content.append(this._note);
    this._root.replaceChildren(style, card);
    if (focus) this._root.getElementById(focus)?.focus();
  }
}
