// Sungrow Modbus: the capability test's results.
//
// Part of the integration's dashboard module, loaded by sungrow-modbus.js.
// From github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT).
// Keep this line with any copy -- doc/attribution.md.

// The server judges; this only lays out what `sungrow_modbus/diagnosis/results`
// answers, and asks again when the status sensor changes.

const { checkOf, DOCS, el, isWaiting, language, readStep, say, WAITING } = await import(new URL(`shared.js${new URL(import.meta.url).search}`, import.meta.url));

// Each outcome's mark and colour, worst first: the order of a list and of the bar.
const BUCKETS = [
  ["failed", "var(--error-color, #db4437)", "mdi:close-circle"],
  ["inconclusive", "var(--warning-color, #ff9800)", "mdi:help-circle"],
  ["not_run", "var(--info-color, #039be5)", "mdi:timer-sand"],
  ["passed", "var(--success-color, #43a047)", "mdi:check-circle"],
  ["not_supported", "var(--disabled-color, #9e9e9e)", "mdi:minus-circle-outline"],
];
const LOOK = Object.fromEntries(BUCKETS.map(([bucket, color, icon], rank) => [bucket, { color, icon, rank }]));
// The lists, by what a check is: a setting read back, what the device then
// does, what the readings say of each other, the wallbox.
const KINDS = ["effect", "readback", "plausibility", "wallbox"];
const EVIDENCE = ["observable", "commanded", "before", "during", "after", "original", "written", "library_read", "detail"];
const MEASURED = new Set(["before", "during", "after", "commanded", "original", "written", "library_read"]);

const LOG_HOURS = 24;
const LOG_LINES = 1500;
const DOT_MS = 5 * 60_000;
const HOUR_MS = 60 * 60_000;

// The step's recorded states as log lines. Waiting is one line an hour with a
// dot for every five minutes of it, or the log of a night would be nothing else.
const logLines = (states, now) => {
  const lines = [];
  // A restart leaves a gap and the same state again: that is one state.
  const known = states
    .filter(({ state }) => !["unknown", "unavailable", ""].includes(state))
    .filter(({ state }, index, all) => state !== all[index - 1]?.state);
  known.forEach(({ at, state }, index) => {
    if (!isWaiting(state)) {
      lines.push({ at, text: state });
      return;
    }
    const end = known[index + 1]?.at ?? now;
    for (let from = at; from === at || from < end; from += HOUR_MS) {
      const dots = Math.floor((Math.min(end, from + HOUR_MS) - from) / DOT_MS);
      lines.push({ at: from, text: from === at ? state : WAITING, dots: ".".repeat(dots) });
    }
  });
  return lines.slice(-LOG_LINES);
};

export class SungrowModbusTestsCard extends HTMLElement {
  static getStubConfig() {
    return { device_id: "" };
  }

  setConfig(config) {
    if (!config?.device_id) throw new Error("`device_id` is required: the inverter's or the wallbox's");
    this._config = config;
    this._seen = undefined;
    this._open = new Set(KINDS);
  }

  set hass(hass) {
    this._hass = hass;
    const status = this._config.status ? hass.states[this._config.status] : undefined;
    // `runs` and the readings move the status' attributes as well as its state.
    const seen = `${language(hass)} ${status?.last_updated}`;
    if (seen !== this._seen) {
      this._seen = seen;
      this._fetch();
    }
    this._updateStep();
    const step = this._config.step ? hass.states[this._config.step]?.last_updated : undefined;
    if (step !== this._logSeen && this._open.has("log")) this._fetchLog();
  }

  getCardSize() {
    return 8;
  }

  getGridOptions() {
    return { columns: "full", rows: "auto" };
  }

  async _fetch() {
    const lang = language(this._hass);
    const mine = (this._request = (this._request ?? 0) + 1);
    let view;
    try {
      view = await this._hass.callWS({ type: "sungrow_modbus/diagnosis/results", device_id: this._config.device_id });
    } catch (err) {
      console.warn("sungrow-modbus: no results", err);
    }
    // An answer overtaken by a later question is dropped.
    if (mine === this._request) this._render(view, lang);
  }

  async _fetchLog() {
    if (!this._log || !this._config.step) return;
    const lang = language(this._hass);
    this._logSeen = this._hass.states[this._config.step]?.last_updated;
    const box = this._log;
    const now = Date.now();
    let lines;
    try {
      const history = await this._hass.callWS({
        type: "history/history_during_period",
        start_time: new Date(now - LOG_HOURS * HOUR_MS).toISOString(),
        entity_ids: [this._config.step],
        minimal_response: true, no_attributes: true, significant_changes_only: false,
      });
      lines = logLines((history[this._config.step] ?? []).map((row) => ({ at: (row.lc ?? row.lu) * 1000, state: row.s })), now);
    } catch (err) {
      console.warn("sungrow-modbus: no log", err);
      box.textContent = say("log_unavailable", lang);
      return;
    }
    // Kept at the end while the reader is there, left alone while they are not.
    const atEnd = box.scrollHeight - box.scrollTop - box.clientHeight < 24;
    box.replaceChildren(...lines.map(({ at, text, dots }) => {
      const line = el("div", "line");
      line.append(el("span", "time", this._when(at)), el("span", "", dots ? `${text} ${dots}` : text));
      return line;
    }));
    if (!lines.length) box.textContent = say("log_empty", lang);
    if (atEnd) box.scrollTop = box.scrollHeight;
  }

  _updateStep() {
    if (!this._step) return;
    const state = this._config.step ? this._hass.states[this._config.step]?.state : undefined;
    this._markRunning(state ?? "");
    const lang = language(this._hass);
    const { running, waiting, what } = readStep(state);
    if (running) {
      const label = this._labels.get(this._running);
      this._step.textContent = say("measuring", lang, { what: label?.[lang] ?? label?.en ?? (what || say("starting", lang)) });
    } else this._step.textContent = waiting ? say("auto_waits", lang) : what;
  }

  // Turn the mark of the check being measured into a moving one, and back.
  _markRunning(state) {
    const name = checkOf(state, this._names, this._steps);
    if (name === this._running) return;
    for (const [key, marks] of this._marks) {
      if (key !== this._running && key !== name) continue;
      marks.running.hidden = key !== name;
      marks.result.hidden = key === name;
    }
    this._running = name;
  }

  _render(view, lang) {
    this._root ??= this.attachShadow({ mode: "open" });
    const card = el("ha-card");
    const style = el("style");
    style.textContent = `
      .content { padding: 16px; }
      .title { font-size: 18px; font-weight: 500; }
      .step, .note, .why { color: var(--secondary-text-color); font-size: 13px; overflow-wrap: anywhere; }
      .step { margin-top: 2px; }
      .bar { display: flex; height: 12px; border-radius: 6px; overflow: hidden; margin: 12px 0; background: var(--divider-color); }
      .legend { display: flex; flex-wrap: wrap; gap: 4px 16px; margin-bottom: 12px; font-size: 13px; color: var(--secondary-text-color); }
      .legend span { display: inline-flex; align-items: center; gap: 4px; }
      ha-icon { --mdc-icon-size: 18px; flex: none; }
      ha-icon[hidden] { display: none; }
      .spin { color: var(--primary-color); animation: spin 1.2s linear infinite; }
      @keyframes spin { to { transform: rotate(360deg); } }
      @media (prefers-reduced-motion: reduce) { .spin { animation: none; } }
      summary { display: flex; align-items: center; gap: 8px; cursor: pointer; list-style: none; min-width: 0; }
      summary::-webkit-details-marker { display: none; }
      .group { border-top: 1px solid var(--divider-color); padding: 2px 0; }
      .group > summary { padding: 10px 0; font-weight: 500; }
      .group > summary::after { color: var(--secondary-text-color); content: "▸"; font-size: 12px; }
      .group[open] > summary::after { content: "▾"; }
      .count { margin-inline-start: auto; color: var(--secondary-text-color); font-weight: 400; white-space: nowrap; }
      .list { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(280px, 100%), 1fr)); gap: 0 24px; align-items: start; padding-bottom: 8px; }
      .row > summary { padding: 5px 0; }
      .row .name { overflow-wrap: anywhere; }
      .row dl { margin-inline-start: 26px; }
      .waits { margin: -2px 0 6px 26px; color: var(--secondary-text-color); font-size: 12px; overflow-wrap: anywhere; }
      .runs .row > summary::before { color: var(--secondary-text-color); content: "▸"; font-size: 12px; }
      .runs .row[open] > summary::before { content: "▾"; }
      ul { margin: 0 0 10px; padding-inline-start: 34px; }
      .log { max-height: 360px; overflow-y: auto; padding-bottom: 12px; font-family: var(--code-font-family, monospace); font-size: 12px; }
      .log .line { display: flex; gap: 12px; padding: 1px 0; }
      .log .line span:last-child { overflow-wrap: anywhere; min-width: 0; }
      .log .time { color: var(--secondary-text-color); white-space: nowrap; flex: none; }
      .warn { color: var(--error-color); }
      dl { display: grid; grid-template-columns: max-content 1fr; gap: 2px 12px; margin: 0 0 10px; font-size: 13px; }
      dt { color: var(--secondary-text-color); }
      dd { margin: 0; overflow-wrap: anywhere; }
      .links { display: flex; flex-wrap: wrap; gap: 4px 20px; border-top: 1px solid var(--divider-color); padding-top: 12px; }
      a { color: var(--primary-color); }
    `;
    const content = el("div", "content");
    card.append(content);
    this._root.replaceChildren(style, card);
    if (!view) {
      content.append(el("div", "note", say("tests_unavailable", lang)));
      return;
    }
    content.append(el("div", "title", view.total ? say("tests_done", lang, { n: view.established, total: view.total }) : say("tests_none", lang)));
    this._step = el("div", "step");
    content.append(this._step);
    this._marks = new Map();
    this._running = undefined;
    this._steps = view.steps;
    // Longest first: one name may start another.
    this._labels = new Map(view.rows.map((row) => [row.name, row.label]));
    this._names = view.rows.map((row) => row.name).sort((a, b) => b.length - a.length);
    if (view.total) content.append(this._bar(view, lang));
    if (view.total) content.append(this._legend(view, lang));
    for (const kind of KINDS) {
      const rows = view.rows.filter((row) => row.kind === kind);
      if (rows.length) content.append(this._group(kind, rows, lang));
    }
    if (view.runs.length) content.append(this._runs(view.runs, lang));
    if (this._config.step) content.append(this._logGroup(lang));
    const links = el("div", "links");
    if (view.document_url) {
      const link = el("a", "", say("download", lang));
      link.href = "#";
      link.addEventListener("click", (event) => {
        event.preventDefault();
        this._download(link, lang);
      });
      links.append(link);
    }
    const docs = el("a", "", say("test_docs", lang));
    docs.href = `${DOCS}/capability_tests.md`;
    docs.target = "_blank";
    docs.rel = "noreferrer";
    links.append(docs);
    content.append(links);
    this._updateStep();
  }

  // The link is signed for a limited time, so a fresh one is asked for.
  async _download(link, lang) {
    try {
      const { document_url: url } = await this._hass.callWS({
        type: "sungrow_modbus/diagnosis/results", device_id: this._config.device_id,
      });
      if (!url) throw new Error("no document");
      const file = el("a");
      file.href = url;
      file.target = "_blank";
      file.download = "";
      document.body.append(file);
      file.click();
      file.remove();
    } catch (err) {
      console.warn("sungrow-modbus: no document", err);
      link.replaceWith(el("span", "note", say("download_failed", lang)));
    }
  }

  _bar(view, lang) {
    const bar = el("div", "bar");
    for (const [bucket, color] of BUCKETS) {
      const part = el("div");
      part.style.cssText = `flex:${view.counts[bucket] ?? 0} 0 0;background:${color}`;
      part.title = `${say(`bucket_${bucket}`, lang)}: ${view.counts[bucket] ?? 0}`;
      bar.append(part);
    }
    return bar;
  }

  // Folded state is kept across refetches, by key.
  _details(key, className) {
    const details = el("details", className);
    details.open = this._open.has(key);
    details.addEventListener("toggle", () => (details.open ? this._open.add(key) : this._open.delete(key)));
    return details;
  }

  _mark(bucket, lang) {
    const mark = el("ha-icon");
    mark.setAttribute("icon", LOOK[bucket].icon);
    mark.style.color = LOOK[bucket].color;
    mark.title = say(`bucket_${bucket}`, lang);
    return mark;
  }

  _legend(view, lang) {
    const legend = el("div", "legend");
    for (const [bucket] of BUCKETS) {
      if (!view.counts[bucket]) continue;
      const item = el("span");
      item.append(this._mark(bucket, lang), `${say(`bucket_${bucket}`, lang)} ${view.counts[bucket]}`);
      legend.append(item);
    }
    return legend;
  }

  _group(kind, rows, lang) {
    const group = this._details(kind, "group");
    const summary = el("summary");
    const done = rows.filter((row) => row.established).length;
    summary.append(el("span", "", say(`kind_${kind}`, lang)), el("span", "count", `${done}/${rows.length}`));
    const list = el("div", "list");
    group.append(summary, list);
    const name = (row) => row.label[lang] ?? row.label.en;
    rows.sort((a, b) => LOOK[a.bucket].rank - LOOK[b.bucket].rank || name(a).localeCompare(name(b), lang));
    for (const row of rows) list.append(this._row(row, name(row), lang));
    return group;
  }

  _row(row, name, lang) {
    const details = this._details(`row ${row.name}`, "row");
    const summary = el("summary");
    const result = this._mark(row.bucket, lang);
    const running = el("ha-icon", "spin");
    running.setAttribute("icon", "mdi:loading");
    running.title = say("running", lang);
    running.hidden = true;
    this._marks.set(row.name, { result, running });
    summary.append(result, running, el("span", "name", name));
    if (row.disputed) summary.append(el("span", "count warn", say("disputed", lang)));
    details.append(summary);
    const list = el("dl");
    const line = (key, value) => list.append(el("dt", "", say(`ev_${key}`, lang)), el("dd", "", String(value)));
    line("name", row.name);
    if (row.verdict) line("verdict", row.verdict_label?.[lang] ?? row.verdict);
    const unit = row.evidence.commanded_unit ?? row.evidence.unit ?? "";
    for (const key of EVIDENCE) {
      if (key in row.evidence) line(key, MEASURED.has(key) ? `${row.evidence[key]} ${unit}`.trim() : row.evidence[key]);
    }
    if (row.run) line("run", `${row.run} · ${this._when(row.read_at)}`);
    details.append(list);
    if (!row.waits_for) return details;
    // What it waits for is the point of the row, so it shows without opening.
    const both = el("div");
    both.append(details, el("div", "waits", `${say("waits_for", lang)}: ${row.waits_label?.[lang] ?? row.waits_for}`));
    return both;
  }

  _logGroup(lang) {
    const group = this._details("log", "group");
    const summary = el("summary");
    summary.append(el("span", "", say("log", lang)));
    this._log = el("div", "log");
    group.append(summary, this._log);
    group.addEventListener("toggle", () => group.open && this._fetchLog());
    if (group.open) this._fetchLog();
    return group;
  }

  _runs(runs, lang) {
    const group = this._details("runs", "group runs");
    const summary = el("summary");
    summary.append(el("span", "", say("runs", lang, { n: runs.length })));
    const last = runs[runs.length - 1];
    summary.append(el("span", "count", this._when(last.read_at)));
    group.append(summary);
    if (last.not_restored?.length) group.open = true;
    for (const run of [...runs].reverse()) {
      const line = this._details(`run ${run.read_at}`, "row");
      const head = `${run.number ? say("run", lang, { n: run.number }) : ""} · ${this._when(run.read_at)}: ${run.label?.[lang] ?? run.means ?? ""}`;
      const title = el("summary", "why");
      const said = el("span", "name", run.restored && !run.not_restored?.length ? `${head}, ${say("put_back", lang, { n: run.restored })}` : head);
      title.append(said);
      if (run.not_restored?.length) title.append(el("span", "warn", say("not_put_back", lang, { fields: run.not_restored.join(", ") })));
      line.append(title);
      const notes = el("ul", "why");
      for (const note of run.notes ?? []) notes.append(el("li", "", note));
      line.append(notes);
      group.append(line);
    }
    return group;
  }

  _when(iso) {
    if (!iso) return "";
    return new Date(iso).toLocaleString(this._hass.locale?.language, {
      dateStyle: "short", timeStyle: "short",
      ...(this._hass.locale?.time_zone === "server" ? { timeZone: this._hass.config.time_zone } : {}),
    });
  }
}
