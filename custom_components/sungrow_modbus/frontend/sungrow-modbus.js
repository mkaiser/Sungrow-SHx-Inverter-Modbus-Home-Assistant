// Sungrow Modbus: the integration's dashboard strategy and its controls lock card.
//
// Served by the integration itself (dashboard.py), so nothing comes from HACS.
// plans/T055-generated-dashboard.md is the design; layout.json is the layout,
// and tests/test_dashboard_layout.py holds its keys to the integration's.
//
// The strategy finds entities by what the integration owns -- platform,
// translation key and device -- never by entity id, so a room prefix, a
// legacy id or a `_2` changes nothing. A card whose entities a house lacks is
// left out, and so is a section or view left empty.
//
// From github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT).
// Keep this line with any copy -- doc/attribution.md.

const DOMAIN = "sungrow_modbus";
const STRATEGY = "sungrow-modbus";
const LOCK_CARD = "sungrow-modbus-lock-card";
const HERE = new URL(import.meta.url);
const VIEW_ORDER = ["overview", "battery", "inverter", "wallbox", "controls"];

const TEXT = {
  en: {
    empty: "No Sungrow Modbus device found. Add the integration under Settings → Devices & services.",
    device_page: "Device page",
    hold: "Hold {s} s to unlock",
    unlocked: "Unlocked · locks in {s} s",
    lock: "Lock",
    strategy_description: "Inverter, battery and wallbox, built from what your house has.",
    card_description: "Locks any card until it is held for a few seconds.",
  },
  de: {
    empty: "Kein Sungrow-Modbus-Gerät gefunden. Die Integration wird unter Einstellungen → Geräte & Dienste hinzugefügt.",
    device_page: "Geräteseite",
    hold: "{s} s halten zum Entsperren",
    unlocked: "Entsperrt · sperrt in {s} s",
    lock: "Sperren",
    strategy_description: "Wechselrichter, Batterie und Wallbox, gebaut aus dem, was das Haus hat.",
    card_description: "Sperrt eine Karte, bis sie einige Sekunden gehalten wird.",
  },
};

const language = (hass) => {
  const lang = (hass?.locale?.language || hass?.language || navigator.language || "en").split("-")[0];
  return lang in TEXT ? lang : "en";
};
const text = (value, lang) => (typeof value === "string" ? value : value?.[lang] ?? value?.en ?? "");
const say = (key, lang, values = {}) =>
  TEXT[lang][key].replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ""));

// ---------------------------------------------------------------- layout

let layoutPromise;
const loadLayout = () => {
  layoutPromise ??= fetch(new URL(`layout.json${HERE.search}`, HERE)).then((response) => {
    if (!response.ok) throw new Error(`layout.json: HTTP ${response.status}`);
    return response.json();
  });
  // A failed fetch is not remembered: the next generate asks again.
  layoutPromise.catch(() => (layoutPromise = undefined));
  return layoutPromise;
};

// ---------------------------------------------------------------- the house

// Group the integration's entities by device family: an inverter and the
// devices that hang off it (battery, wallbox, WiFi module). A wallbox entry of
// its own is a family of its own.
const indexHouse = (hass) => {
  const own = Object.values(hass.entities ?? {}).filter(
    (entity) => entity.platform === DOMAIN && entity.device_id && entity.translation_key && !entity.hidden,
  );
  const devices = new Set(own.map((entity) => entity.device_id));
  const rootOf = (deviceId) => {
    let current = deviceId;
    for (let hops = 0; hops < 8; hops += 1) {
      const via = hass.devices?.[current]?.via_device_id;
      if (!via || !devices.has(via)) return current;
      current = via;
    }
    return current;
  };
  const families = new Map();
  const everywhere = new Map();
  for (const entity of own) {
    const ref = `${entity.entity_id.split(".")[0]}.${entity.translation_key}`;
    const root = rootOf(entity.device_id);
    if (!families.has(root)) families.set(root, new Map());
    const family = families.get(root);
    if (!family.has(ref)) family.set(ref, []);
    family.get(ref).push(entity.entity_id);
    if (!everywhere.has(ref)) everywhere.set(ref, []);
    everywhere.get(ref).push(entity.entity_id);
  }
  const deviceName = (id) => hass.devices?.[id]?.name_by_user || hass.devices?.[id]?.name || id;
  const roots = [...families.keys()].sort((a, b) => deviceName(a).localeCompare(deviceName(b)));
  return { families, everywhere, roots, rootOf, deviceName };
};

// `a|b` takes the first that exists; `~a` may come from anywhere in the
// integration if it is unique there, and does not on its own keep a card.
const resolve = (ref, family, everywhere) => {
  for (const alternative of ref.split("|")) {
    const context = alternative.startsWith("~");
    const key = context ? alternative.slice(1) : alternative;
    const ids = family.get(key) ?? (context && everywhere.get(key)?.length === 1 ? everywhere.get(key) : null);
    if (ids?.length) return { entity: ids[0], anchor: !context };
  }
  return null;
};

// ---------------------------------------------------------------- cards

const expand = (card) => {
  if (!card.repeat) return [card];
  const [low, high] = card.repeat;
  const numbers = Array.from({ length: high - low + 1 }, (_, i) => low + i);
  if (card.split) {
    // One card per number, its title numbered too.
    return numbers.map((n) => JSON.parse(JSON.stringify({ ...card, repeat: undefined }).replaceAll("{n}", String(n))));
  }
  const entities = numbers.flatMap((n) => card.entities.map((ref) => ref.replaceAll("{n}", String(n))));
  return [{ ...card, repeat: undefined, entities }];
};

const named = (entity) => ({ entity, name: { type: "entity" } });

// One layout card to zero or more Lovelace cards, each with `anchor`: whether
// it shows something of this family, which is what keeps a section.
const buildCard = (card, ctx) => {
  const { family, everywhere, lang, root } = ctx;
  if (card.type === "markdown") return [{ anchor: false, config: { type: "markdown", content: text(card.content, lang) } }];
  if (card.type === "device-link") {
    return [{
      anchor: false,
      config: {
        type: "button",
        name: say("device_page", lang),
        icon: "mdi:chip",
        show_state: false,
        tap_action: { action: "navigate", navigation_path: `/config/devices/device/${root}` },
        grid_options: { columns: 6, rows: 1 },
      },
    }];
  }
  if (card.entity) {
    const found = resolve(card.entity, family, everywhere);
    if (!found) return [];
    const config = { type: card.type, ...named(found.entity) };
    for (const key of ["color", "min", "max", "needle", "severity"]) if (key in card) config[key] = card[key];
    if (card.type === "tile") config.vertical = false;
    return [{ anchor: found.anchor, config }];
  }
  const found = card.entities.map((ref) => resolve(ref, family, everywhere)).filter(Boolean);
  const seen = new Set();
  const unique = found.filter((f) => !seen.has(f.entity) && seen.add(f.entity));
  if (!unique.some((f) => f.anchor)) return [];
  const config = { type: card.type, entities: unique.map((f) => named(f.entity)) };
  if (card.title) config.title = text(card.title, lang);
  for (const key of ["hours_to_show", "days_to_show", "period", "chart_type", "stat_types"]) {
    if (key in card) config[key] = card[key];
  }
  if (card.type === "entities") config.show_header_toggle = false;
  return [{ anchor: true, config }];
};

const lockCard = (cards, options) => ({
  type: `custom:${LOCK_CARD}`,
  group: "controls",
  hold_seconds: options.hold_seconds,
  unlock_seconds: options.unlock_seconds,
  grid_options: { columns: "full" },
  card: cards.length === 1 ? cards[0] : { type: "vertical-stack", cards },
});

const buildSection = (section, ctx, locked) => {
  const built = section.cards.flatMap(expand).flatMap((card) => buildCard(card, ctx));
  const anchor = built.some((card) => card.anchor);
  // A section that names entities and found none is left out; one of text
  // alone (the controls' warning) stays, but does not on its own make a view.
  if (!anchor && section.cards.some((card) => card.entity || card.entities)) return null;
  let cards = built.map((card) => card.config);
  if (locked && ctx.options.controls === "hold") {
    const writable = cards.filter((card) => card.type !== "markdown");
    if (writable.length) cards = [...cards.filter((card) => card.type === "markdown"), lockCard(writable, ctx.options)];
  }
  const grid = {
    type: "grid",
    cards: [{ type: "heading", heading: text(section.heading, ctx.lang), heading_style: "title", icon: section.icon }, ...cards],
  };
  if (section.column_span) grid.column_span = section.column_span;
  return { grid, anchor };
};

const buildView = (view, ctx) => {
  const locked = Boolean(view.locked);
  const sections = view.sections.map((section) => buildSection(section, ctx, locked)).filter(Boolean);
  if (!sections.some((section) => section.anchor)) return null;
  return {
    title: text(view.title, ctx.lang),
    path: view.id,
    icon: view.icon,
    type: "sections",
    max_columns: 3,
    sections: sections.map((section) => section.grid),
    ...(locked && ctx.admins ? { visible: ctx.admins } : {}),
  };
};

// Who may see the controls. The strategy runs in the viewer's browser, so a
// plain user simply does not get the view; the user list is for a dashboard
// an administrator takes over, which everyone then loads as it was saved.
const adminVisibility = async (hass) => {
  try {
    const users = await hass.callWS({ type: "config/auth/list" });
    const admins = users.filter(
      (user) => user.is_active && !user.system_generated && user.group_ids?.includes("system-admin"),
    );
    return admins.length ? admins.map((user) => ({ user: user.id })) : null;
  } catch (err) {
    console.warn("sungrow-modbus: could not list the administrators", err);
    return null;
  }
};

class SungrowModbusDashboardStrategy extends HTMLElement {
  static registryDependencies = ["entities", "devices"];

  static async generate(config, hass) {
    const lang = language(hass);
    const options = {
      controls: ["hold", "admin", "hidden"].includes(config.controls) ? config.controls : "hold",
      hold_seconds: Number(config.hold_seconds) > 0 ? Number(config.hold_seconds) : 3,
      unlock_seconds: Number(config.unlock_seconds) > 0 ? Number(config.unlock_seconds) : 30,
    };
    const wanted = (Array.isArray(config.views) ? config.views : VIEW_ORDER).filter(
      (id) => VIEW_ORDER.includes(id) && !(id === "controls" && (options.controls === "hidden" || !hass.user?.is_admin)),
    );
    const layout = await loadLayout();
    const house = indexHouse(hass);
    // `device_id` pins one family: the inverter's, or the one a named battery
    // or wallbox belongs to.
    const roots = config.device_id
      ? house.roots.filter((root) => root === house.rootOf(config.device_id))
      : house.roots;
    const admins = wanted.includes("controls") ? await adminVisibility(hass) : null;

    const built = [];
    for (const id of wanted) {
      const view = layout.views.find((v) => v.id === id);
      if (!view) continue;
      const perRoot = roots
        .map((root) => ({
          root,
          config: buildView(view, {
            family: house.families.get(root),
            everywhere: house.everywhere,
            lang,
            root,
            options,
            admins,
          }),
        }))
        .filter((entry) => entry.config);
      for (const [index, entry] of perRoot.entries()) {
        if (perRoot.length > 1) {
          entry.config.title = `${entry.config.title} · ${house.deviceName(entry.root)}`;
          entry.config.path = `${entry.config.path}-${index + 1}`;
        }
        built.push(entry.config);
      }
    }
    if (!built.length) {
      return {
        views: [{ title: "Sungrow", path: "sungrow", type: "sections",
          sections: [{ type: "grid", cards: [{ type: "markdown", content: say("empty", lang) }] }] }],
      };
    }
    return { views: built };
  }
}

// ---------------------------------------------------------------- lock card

// Unlocks are kept per browser tab, by group: the controls of one view open
// together, and one person's unlock never opens another screen's.
const unlockedUntil = new Map();
const LOCK_EVENT = "sungrow-modbus-lock-changed";

class SungrowModbusLockCard extends HTMLElement {
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
        :host([locked]) .wrap { opacity: 0.55; filter: grayscale(0.5); pointer-events: none; user-select: none; }
        .overlay {
          position: absolute; inset: 0; z-index: 1; display: none; cursor: pointer;
          align-items: center; justify-content: center; touch-action: pan-y;
          border-radius: var(--ha-card-border-radius, 12px); -webkit-touch-callout: none; user-select: none;
        }
        :host([locked]) .overlay { display: flex; }
        .badge, .status {
          display: flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 18px;
          background: var(--card-background-color, #fff); color: var(--primary-text-color);
          box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0, 0, 0, 0.3)); font-size: 14px;
          position: relative; overflow: hidden;
        }
        .progress {
          position: absolute; left: 0; top: 0; bottom: 0; width: 0; opacity: 0.35;
          background: var(--warning-color, #ff9800);
        }
        .holding .progress { width: 100%; transition: width var(--hold) linear; }
        /* Below the card, not over it: an unlocked card's last row stays reachable. */
        .status { display: none; width: fit-content; margin: 6px 0 0 auto; font-size: 12px; }
        :host([unlocked]) .status { display: flex; }
        button {
          font: inherit; border: none; border-radius: 12px; padding: 2px 10px; cursor: pointer;
          background: var(--primary-color); color: var(--text-primary-color, #fff);
        }
        ha-icon { --mdc-icon-size: 18px; position: relative; }
        span { position: relative; }
      </style>
      <div class="wrap"></div>
      <div class="overlay" role="button" tabindex="0">
        <div class="badge"><div class="progress"></div><ha-icon icon="mdi:lock"></ha-icon><span class="hold"></span></div>
      </div>
      <div class="status"><ha-icon icon="mdi:lock-open-variant"></ha-icon><span class="left"></span><button></button></div>`;
    this._wrap = this._root.querySelector(".wrap");
    const overlay = this._root.querySelector(".overlay");
    const badge = this._root.querySelector(".badge");
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

// ---------------------------------------------------------------- register

if (!customElements.get(`ll-strategy-dashboard-${STRATEGY}`)) {
  customElements.define(`ll-strategy-dashboard-${STRATEGY}`, SungrowModbusDashboardStrategy);
}
if (!customElements.get(LOCK_CARD)) {
  customElements.define(LOCK_CARD, SungrowModbusLockCard);
}

const lang = language(document.querySelector("home-assistant")?.hass);
window.customStrategies ??= [];
if (!window.customStrategies.some((s) => s.type === STRATEGY && s.strategyType === "dashboard")) {
  window.customStrategies.push({
    type: STRATEGY,
    strategyType: "dashboard",
    name: "Sungrow Modbus",
    description: say("strategy_description", lang),
    // On the development branch until the merge into main, which moves it.
    documentationURL:
      "https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/blob/proper-ha-integration/doc/dashboard.md",
  });
}
window.customCards ??= [];
if (!window.customCards.some((c) => c.type === LOCK_CARD)) {
  window.customCards.push({
    type: LOCK_CARD,
    name: "Sungrow Modbus lock",
    description: say("card_description", lang),
  });
}
