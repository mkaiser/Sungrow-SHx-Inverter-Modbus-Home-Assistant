// Sungrow Modbus: the lock card, which guards changing a card and not reading it.
//
// Part of the integration's dashboard module, loaded by sungrow-modbus.js.
// From github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT).
// Keep this line with any copy -- doc/attribution.md.

const { language, say } = await import(new URL(`shared.js${new URL(import.meta.url).search}`, import.meta.url));

// Unlocks are kept per browser tab, by group: the controls of one view open
// together, and one person's unlock never opens another screen's.
const unlockedUntil = new Map();
const LOCK_EVENT = "sungrow-modbus-lock-changed";

export class SungrowModbusLockCard extends HTMLElement {
  static getStubConfig() {
    return { card: { type: "entities", entities: [] } };
  }

  setConfig(config) {
    if (!config?.card) throw new Error("`card` is required: the card to lock");
    const changed = JSON.stringify(config.card) !== JSON.stringify(this._config?.card);
    this._config = {
      group: config.group ?? null,
      hold_seconds: Number(config.hold_seconds) > 0 ? Number(config.hold_seconds) : 3,
      unlock_seconds: Number(config.unlock_seconds) > 0 ? Number(config.unlock_seconds) : 30,
      card: config.card,
    };
    this._key = this._config.group ?? this;
    this._render();
    if (changed) this._createChild();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._child) this._child.hass = hass;
    this._label();
  }

  getCardSize() {
    return this._child?.getCardSize?.() ?? 3;
  }

  getGridOptions() {
    return { columns: "full", rows: "auto" };
  }

  connectedCallback() {
    this._onLockEvent = () => this._update();
    window.addEventListener(LOCK_EVENT, this._onLockEvent);
    this._update();
  }

  disconnectedCallback() {
    window.removeEventListener(LOCK_EVENT, this._onLockEvent);
    this._cancelHold();
    clearInterval(this._ticker);
    this._ticker = undefined;
  }

  async _createChild() {
    const helpers = await window.loadCardHelpers();
    const child = helpers.createCardElement(this._config.card);
    child.addEventListener("ll-rebuild", (event) => {
      event.stopPropagation();
      this._createChild();
    }, { once: true });
    if (this._hass) child.hass = this._hass;
    this._child?.remove();
    this._child = child;
    this._wrap.append(child);
  }

  _render() {
    if (this._root) return;
    this._root = this.attachShadow({ mode: "open" });
    this._root.innerHTML = `
      <style>
        :host { display: block; position: relative; }
        .wrap { transition: opacity 0.2s, filter 0.2s; }
        :host([locked]) .wrap { pointer-events: none; user-select: none; }
        /* Over the card and invisible: the values stay readable, a tap goes nowhere. */
        .overlay {
          position: absolute; inset: 0; z-index: 1; display: none; cursor: pointer; touch-action: pan-y;
          border-radius: var(--ha-card-border-radius, 12px); -webkit-touch-callout: none; user-select: none;
        }
        :host([locked]) .overlay { display: block; }
        .bar, .status {
          display: none; align-items: center; gap: 6px; min-height: 32px; padding: 0 12px; margin-bottom: 8px;
          border-radius: var(--ha-card-border-radius, 12px); box-sizing: border-box;
          background: color-mix(in srgb, var(--primary-text-color) 8%, transparent);
          color: var(--secondary-text-color); font-size: 13px; position: relative; overflow: hidden;
        }
        :host([locked]) .bar { display: flex; }
        .progress {
          position: absolute; left: 0; top: 0; bottom: 0; width: 0; opacity: 0.35;
          background: var(--warning-color, #ff9800);
        }
        .holding .progress { width: 100%; transition: width var(--hold) linear; }
        :host([unlocked]) .status { display: flex; background: color-mix(in srgb, var(--warning-color, #ff9800) 25%, transparent); }
        .status .left { flex: 1; }
        button {
          font: inherit; border: none; border-radius: 12px; padding: 2px 10px; cursor: pointer;
          background: var(--primary-color); color: var(--text-primary-color, #fff);
        }
        ha-icon { --mdc-icon-size: 18px; position: relative; }
        span { position: relative; }
      </style>
      <div class="bar"><div class="progress"></div><ha-icon icon="mdi:lock"></ha-icon><span class="hold"></span></div>
      <div class="status"><ha-icon icon="mdi:lock-open-variant"></ha-icon><span class="left"></span><button></button></div>
      <div class="wrap"></div>
      <div class="overlay" role="button" tabindex="0"></div>`;
    this._wrap = this._root.querySelector(".wrap");
    const overlay = this._root.querySelector(".overlay");
    const badge = this._root.querySelector(".bar");
    overlay.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      this._startHold(badge);
    });
    for (const name of ["pointerup", "pointerleave", "pointercancel"]) overlay.addEventListener(name, () => this._cancelHold());
    overlay.addEventListener("contextmenu", (event) => event.preventDefault());
    overlay.addEventListener("keydown", (event) => {
      if ((event.key === "Enter" || event.key === " ") && !event.repeat) {
        event.preventDefault();
        this._startHold(badge);
      }
    });
    overlay.addEventListener("keyup", () => this._cancelHold());
    this._root.querySelector("button").addEventListener("click", () => this._lock());
    this._update();
  }

  _startHold(badge) {
    this._cancelHold();
    this._badge = badge;
    badge.style.setProperty("--hold", `${this._config.hold_seconds}s`);
    // Next frame, so the bar starts from empty.
    requestAnimationFrame(() => badge.classList.add("holding"));
    this._holdTimer = setTimeout(() => this._unlock(), this._config.hold_seconds * 1000);
  }

  _cancelHold() {
    clearTimeout(this._holdTimer);
    this._holdTimer = undefined;
    this._badge?.classList.remove("holding");
  }

  _unlock() {
    this._cancelHold();
    unlockedUntil.set(this._key, Date.now() + this._config.unlock_seconds * 1000);
    window.dispatchEvent(new Event(LOCK_EVENT));
  }

  _lock() {
    unlockedUntil.delete(this._key);
    window.dispatchEvent(new Event(LOCK_EVENT));
  }

  _remaining() {
    const until = unlockedUntil.get(this._key) ?? 0;
    return Math.max(0, Math.ceil((until - Date.now()) / 1000));
  }

  _update() {
    if (!this._config) return;
    const open = this._remaining() > 0;
    this.toggleAttribute("locked", !open);
    this.toggleAttribute("unlocked", open);
    // Neither a tap nor the keyboard reaches a locked card's inputs.
    this._wrap.inert = !open;
    if (open && !this._ticker) {
      this._ticker = setInterval(() => {
        if (this._remaining() === 0) {
          unlockedUntil.delete(this._key);
          clearInterval(this._ticker);
          this._ticker = undefined;
          this._update();
        } else {
          this._label();
        }
      }, 1000);
    }
    if (!open && this._ticker) {
      clearInterval(this._ticker);
      this._ticker = undefined;
    }
    this._label();
  }

  _label() {
    if (!this._root || !this._config) return;
    const lang = language(this._hass);
    this._root.querySelector(".hold").textContent = say("hold", lang, { s: this._config.hold_seconds });
    this._root.querySelector(".left").textContent = say("unlocked", lang, { s: this._remaining() });
    this._root.querySelector("button").textContent = say("lock", lang);
  }
}
