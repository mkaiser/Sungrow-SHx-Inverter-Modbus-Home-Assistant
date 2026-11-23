// Sungrow Modbus: the notice that the dashboard has a newer layout.
//
// Part of the integration's dashboard module, loaded by sungrow-modbus.js.
// From github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT).
// Keep this line with any copy -- doc/attribution.md.

// On a generated dashboard it is always current and shows nothing, unless the
// tab still runs the module of before an update. On a dashboard taken over,
// the revision it carries is the one it was taken over with.

const { getChoices, language, onHold, say, setChoice, text } = await import(
  new URL(`shared.js${new URL(import.meta.url).search}`, import.meta.url)
);

const STRATEGY = "custom:sungrow-modbus";
const HOLD_SECONDS = 3;

export class SungrowModbusUpdateCard extends HTMLElement {
  connectedWhileHidden = true;

  setConfig(config) {
    if (!Number.isInteger(config?.revision)) throw new Error("`revision` is required");
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    if (this._started) return;
    this._started = true;
    this._show(false);
    this._check().catch((err) => console.warn("sungrow-modbus: could not look for a newer dashboard", err));
  }

  getCardSize() {
    return this.hidden ? 0 : 3;
  }

  getGridOptions() {
    return { columns: "full", rows: "auto" };
  }

  _show(visible) {
    this.hidden = !visible;
    this.style.display = visible ? "block" : "none";
    this.dispatchEvent(new Event("card-visibility-changed", { bubbles: true, composed: true }));
  }

  // The dashboard's path as the websocket names it: the default one has none.
  get _urlPath() {
    const path = location.pathname.split("/")[1];
    return path === "lovelace" ? null : path;
  }

  async _check() {
    if (!this._hass.user?.is_admin) return;
    const response = await fetch(new URL(`layout.json?t=${Date.now()}`, import.meta.url), { cache: "no-store" });
    if (!response.ok) throw new Error(`layout.json: HTTP ${response.status}`);
    const layout = await response.json();
    if (layout.revision <= this._config.revision) return;
    const saved = await this._hass.callWS({ type: "lovelace/config", url_path: this._urlPath });
    const lang = language(this._hass);
    if (saved.strategy) {
      this._render([[say("update_reload", lang)]], [this._button(say("reload", lang), () => location.reload())]);
      return;
    }
    if ((await getChoices(this._hass)).dismissed_revision >= layout.revision) return;
    const changes = layout.changes.filter((change) => change.revision > this._config.revision);
    const dashboards = await this._hass.callWS({ type: "lovelace/dashboards/list" });
    const own = dashboards.find((dashboard) => dashboard.url_path === this._urlPath);
    const buttons = [this._button(say("add_beside", lang), () => this._add(dashboards))];
    // A dashboard kept in YAML is a file, which nothing here can write.
    const replaceable = own?.mode === "storage";
    if (replaceable) buttons.push(this._holdButton(say("replace", lang, { s: HOLD_SECONDS }), () => this._replace()));
    buttons.push(this._button(say("dismiss", lang), async () => {
      await setChoice(this._hass, { dismissed_revision: layout.revision });
      this._show(false);
    }));
    this._render(
      [[say("update_text", lang)], changes.map((change) => text(change.text, lang)), replaceable ? [say("replace_note", lang)] : []],
      buttons,
    );
  }

  get _strategyConfig() {
    return { strategy: { ...(this._config.options ?? {}), type: STRATEGY } };
  }

  async _add(dashboards) {
    const taken = new Set(dashboards.map((dashboard) => dashboard.url_path));
    let path = "sungrow-modbus";
    for (let n = 2; taken.has(path); n += 1) path = `sungrow-modbus-${n}`;
    await this._hass.callWS({
      type: "lovelace/dashboards/create", url_path: path, title: "Sungrow", icon: "mdi:solar-power",
      mode: "storage", show_in_sidebar: true, require_admin: false,
    });
    await this._hass.callWS({ type: "lovelace/config/save", url_path: path, config: this._strategyConfig });
    location.assign(`/${path}`);
  }

  // The copy as it is now, not as it was when the notice appeared, goes into
  // the file first; any failure before the save leaves the dashboard alone.
  async _replace() {
    const saved = await this._hass.callWS({ type: "lovelace/config", url_path: this._urlPath, force: true });
    if (!saved.views?.length) throw new Error("nothing to back up");
    const url = URL.createObjectURL(new Blob([JSON.stringify(saved, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `${this._urlPath ?? "lovelace"}-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.append(link);
    link.click();
    link.remove();
    // Long enough for the browser to have taken the file.
    await new Promise((resolve) => setTimeout(resolve, 1500));
    URL.revokeObjectURL(url);
    await this._hass.callWS({ type: "lovelace/config/save", url_path: this._urlPath, config: this._strategyConfig });
    location.reload();
  }

  _guarded(action) {
    return async () => {
      try {
        await action();
      } catch (err) {
        console.error("sungrow-modbus:", err);
        this._error.textContent = say("update_failed", language(this._hass), { error: err.message ?? err });
      }
    };
  }

  _button(label, action) {
    const button = document.createElement("button");
    button.textContent = label;
    button.addEventListener("click", this._guarded(action));
    return button;
  }

  _holdButton(label, action) {
    const button = document.createElement("button");
    const bar = document.createElement("div");
    bar.className = "progress";
    const caption = document.createElement("span");
    caption.textContent = label;
    button.className = "hold";
    button.append(bar, caption);
    onHold(button, button, () => HOLD_SECONDS, this._guarded(action));
    return button;
  }

  _render(paragraphs, buttons) {
    this._root ??= this.attachShadow({ mode: "open" });
    this._root.innerHTML = `
      <style>
        .content { padding: 16px; border-inline-start: 4px solid var(--info-color, #039be5); }
        .title { font-weight: 500; }
        p, ul { margin: 6px 0; color: var(--secondary-text-color); }
        .buttons { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
        button {
          font: inherit; border: 1px solid var(--primary-color); border-radius: 12px; padding: 6px 14px; cursor: pointer;
          background: none; color: var(--primary-color); position: relative; overflow: hidden; touch-action: none; user-select: none;
        }
        button span { position: relative; }
        .progress { position: absolute; left: 0; top: 0; bottom: 0; width: 0; opacity: 0.35; background: var(--error-color); }
        .hold { border-color: var(--error-color); color: var(--error-color); }
        .holding .progress { width: 100%; transition: width var(--hold) linear; }
        .error { color: var(--error-color); }
      </style>
      <ha-card><div class="content"><div class="title"></div><div class="text"></div><div class="buttons"></div><p class="error"></p></div></ha-card>`;
    this._root.querySelector(".title").textContent = say("update_title", language(this._hass));
    this._error = this._root.querySelector(".error");
    const body = this._root.querySelector(".text");
    for (const [index, lines] of paragraphs.entries()) {
      if (!lines.length) continue;
      const list = index === 1;
      const block = document.createElement(list ? "ul" : "p");
      for (const line of lines) {
        const node = list ? document.createElement("li") : document.createElement("span");
        node.textContent = line;
        block.append(node);
      }
      body.append(block);
    }
    this._root.querySelector(".buttons").append(...buttons);
    this._show(true);
  }
}
