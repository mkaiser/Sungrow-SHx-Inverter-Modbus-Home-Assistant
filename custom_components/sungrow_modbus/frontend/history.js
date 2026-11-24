// Sungrow Modbus: the inverter's own energy history, as bars.
//
// Part of the integration's dashboard module, loaded by sungrow-modbus.js.
// From github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT).
// Keep this line with any copy -- doc/attribution.md.

// The strategy hands over only the entities a house has, so a month or a year
// without one has no bar. A tap on a bar opens that sensor.

const { el, language } = await import(new URL(`shared.js${new URL(import.meta.url).search}`, import.meta.url));

const COLORS = {
  amber: "var(--amber-color, #ffc107)", blue: "var(--blue-color, #2196f3)", green: "var(--green-color, #4caf50)",
};
const HEIGHT = 180;

export class SungrowModbusHistoryCard extends HTMLElement {
  static getStubConfig() {
    return { period: "month", bars: [] };
  }

  setConfig(config) {
    if (!Array.isArray(config?.bars)) throw new Error("`bars` is required");
    this._config = config;
    this._seen = undefined;
  }

  set hass(hass) {
    this._hass = hass;
    const seen = `${language(hass)} ${this._config.bars.map((bar) => hass.states[bar.entity]?.state).join()}`;
    if (seen === this._seen) return;
    this._seen = seen;
    this._render();
  }

  getCardSize() {
    return 5;
  }

  getGridOptions() {
    return { columns: "full", rows: "auto" };
  }

  _label(label) {
    if (this._config.period !== "month") return label;
    return new Date(2000, Number(label) - 1, 1).toLocaleDateString(this._hass.locale?.language, { month: "short" });
  }

  _number(value) {
    return value.toLocaleString(this._hass.locale?.language, { maximumFractionDigits: 0 });
  }

  _render() {
    this._root ??= this.attachShadow({ mode: "open" });
    const style = el("style");
    style.textContent = `
      .content { padding: 16px; }
      .legend { display: flex; flex-wrap: wrap; gap: 4px 16px; margin-bottom: 12px; font-size: 13px; color: var(--secondary-text-color); }
      .legend span { display: inline-flex; align-items: center; gap: 6px; }
      .dot { width: 10px; height: 10px; border-radius: 2px; }
      .scroll { overflow-x: auto; }
      .chart { display: flex; gap: 10px; align-items: flex-end; min-width: min-content; }
      .group { flex: 1 0 44px; text-align: center; }
      .bars { display: flex; gap: 2px; align-items: flex-end; justify-content: center; height: ${HEIGHT}px; border-bottom: 1px solid var(--divider-color); }
      button { flex: 1 1 0; max-width: 18px; min-width: 6px; min-height: 2px; padding: 0; border: none; border-radius: 3px 3px 0 0; cursor: pointer; }
      button.none { background: var(--divider-color) !important; }
      .label { font-size: 12px; margin-top: 4px; white-space: nowrap; }
      .top { font-size: 11px; color: var(--secondary-text-color); white-space: nowrap; }
    `;
    const card = el("ha-card");
    const content = el("div", "content");
    card.append(content);
    this._root.replaceChildren(style, card);
    const bars = this._config.bars.map((bar) => ({ ...bar, value: Number.parseFloat(this._hass.states[bar.entity]?.state) }));
    const most = Math.max(...bars.map(({ value }) => (Number.isFinite(value) ? value : 0)), 1);
    const legend = el("div", "legend");
    for (const bar of new Map(bars.map((one) => [one.name, one])).values()) {
      const item = el("span");
      const dot = el("span", "dot");
      dot.style.background = COLORS[bar.color] ?? bar.color;
      item.append(dot, bar.name);
      legend.append(item);
    }
    const chart = el("div", "chart");
    for (const label of new Set(bars.map((bar) => bar.label))) {
      const group = el("div", "group");
      const mine = bars.filter((bar) => bar.label === label);
      const first = mine[0].value;
      group.append(el("div", "top", Number.isFinite(first) ? this._number(first) : "–"));
      const box = el("div", "bars");
      for (const bar of mine) {
        const known = Number.isFinite(bar.value);
        const button = el("button", known ? "" : "none");
        button.type = "button";
        button.style.cssText = `height:${known ? Math.round((HEIGHT * bar.value) / most) : 2}px;background:${COLORS[bar.color] ?? bar.color}`;
        button.title = `${bar.name}, ${this._label(label)}: ${known ? `${this._number(bar.value)} kWh` : "–"}`;
        button.setAttribute("aria-label", button.title);
        button.addEventListener("click", () => this.dispatchEvent(new CustomEvent("hass-more-info", {
          bubbles: true, composed: true, detail: { entityId: bar.entity },
        })));
        box.append(button);
      }
      group.append(box, el("div", "label", this._label(label)));
      chart.append(group);
    }
    const scroll = el("div", "scroll");
    scroll.append(chart);
    content.append(legend, scroll, el("div", "top", "kWh"));
  }
}
