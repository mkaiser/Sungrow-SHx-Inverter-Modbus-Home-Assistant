// Sungrow Modbus: the integration's dashboard strategy and its cards.
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
const FLOW_CARD = "sungrow-modbus-flow-card";
const TESTS_CARD = "sungrow-modbus-tests-card";
const UPDATE_CARD = "sungrow-modbus-update-card";
const HERE = new URL(import.meta.url);
// The views were named `overview` before; an option that still says so is read as `home`.
const RENAMED = { overview: "home" };
const VIEW_ORDER = ["home", "energy", "battery", "inverter", "wallbox", "controls", "diagnosis"];

const MAX_COLUMNS = 3;

const { DOCS, language, say, text } = await import(new URL(`shared.js${HERE.search}`, HERE));

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
// its own is a family of its own, which `guests` then takes into the inverter's
// views.
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

const numbered = (value, n) => JSON.parse(JSON.stringify(value).replaceAll("{n}", String(n)));

const expand = (card) => {
  if (!card.repeat) return [card];
  const { repeat, ...one } = card;
  const numbers = Array.from({ length: repeat[1] - repeat[0] + 1 }, (_, i) => repeat[0] + i);
  // A tile becomes one card per number; a list keeps one card with every row.
  if (card.entity) return numbers.map((n) => numbered(one, n));
  return [{ ...one, entities: numbers.flatMap((n) => numbered(card.entities, n)) }];
};

const PASSED_ON = ["hours_to_show", "days_to_show", "period", "chart_type", "stat_types", "min_y_axis", "max_y_axis"];

const navigate = (path) => ({ action: "navigate", navigation_path: path });
const linkButton = (name, icon, path) => ({
  type: "shortcut", label: name, icon, tap_action: navigate(path), grid_options: { columns: 6 },
});

// The energy flow is Home Assistant's own card, which shows what the user's
// Energy dashboard is set up with; without one, how to set it up.
const energyCards = (ctx) => {
  if (ctx.energy) {
    return ["energy-date-selection", "energy-distribution", "energy-usage-graph", "energy-sources-table"].map((type) => ({
      anchor: false,
      config: { type, grid_options: { columns: type === "energy-distribution" || type === "energy-usage-graph" ? 18 : "full" } },
    }));
  }
  return [{
    anchor: false,
    config: {
      type: "markdown",
      content: `${say("energy_hint", ctx.lang)}\n\n[${say("energy_setup", ctx.lang)}](/config/energy) · [${say("energy_guide", ctx.lang)}](${DOCS}/energy_dashboard.md)`,
    },
  }];
};

// One layout card to zero or more Lovelace cards, each with `anchor`: whether
// it shows something of this family, which is what keeps a section.
const buildCard = (card, ctx) => {
  const { family, everywhere, lang, root } = ctx;
  if (card.type === "energy") return energyCards(ctx);
  if (card.type === "markdown") return [{ anchor: false, config: { type: "markdown", content: text(card.content, lang) } }];
  if (card.type === "device-link") {
    return [{ anchor: false, config: linkButton(say("device_page", lang), "mdi:chip", `/config/devices/device/${root}`) }];
  }
  if (card.type === "integration-link") {
    return [{
      anchor: false,
      config: linkButton(say("integration_page", lang), "mdi:puzzle", `/config/integrations/integration/${DOMAIN}`),
    }];
  }
  if (card.type === "tests") {
    const status = resolve(card.status, family, everywhere);
    if (!status?.anchor) return [];
    const step = resolve(card.step, family, everywhere);
    return [{
      anchor: true,
      config: {
        type: `custom:${TESTS_CARD}`, device_id: ctx.hass.entities[status.entity].device_id,
        status: status.entity, step: step?.entity, grid_options: { columns: "full" },
      },
    }];
  }
  if (card.type === "flow") {
    const found = Object.entries(card.roles).map(([role, ref]) => [role, resolve(ref, family, everywhere)]).filter(([, f]) => f);
    if (!found.some(([, f]) => f.anchor)) return [];
    const entities = Object.fromEntries(found.map(([role, f]) => [role, f.entity]));
    return [{
      anchor: true,
      config: { type: `custom:${FLOW_CARD}`, entities, style: ctx.options.power_flow, grid_options: { columns: "full" } },
    }];
  }
  const grid = card.columns ? { grid_options: { columns: card.columns } } : {};
  if (card.entity) {
    const found = resolve(card.entity, family, everywhere);
    if (!found) return [];
    const config = { type: card.type, entity: found.entity, name: card.name ? text(card.name, lang) : { type: "entity" }, ...grid };
    for (const key of ["color", "icon", "features", "vertical", "hide_state"]) if (key in card) config[key] = card[key];
    if (card.below) config.features_position = "bottom";
    if (card.view && ctx.paths[card.view]) config.tap_action = navigate(ctx.paths[card.view]);
    // A setting shown for reading: its dialog could change it past the lock.
    if (card.more_info === false) {
      const action = ctx.paths.controls ? navigate(ctx.paths.controls) : { action: "none" };
      Object.assign(config, { tap_action: action, icon_tap_action: action, hold_action: { action: "none" } });
    }
    return [{ anchor: found.anchor, config }];
  }
  const seen = new Set();
  const rows = card.entities
    .map((item) => ({ item, found: resolve(item.entity ?? item, family, everywhere) }))
    .filter(({ found }) => found && !seen.has(found.entity) && seen.add(found.entity));
  if (!rows.some(({ found }) => found.anchor)) return [];
  const config = {
    type: card.type,
    entities: rows.map(({ item, found }) => ({
      entity: found.entity,
      name: item.name ? text(item.name, lang) : { type: "entity" },
      ...(item.color ? { color: item.color } : {}),
    })),
    ...grid,
  };
  for (const key of PASSED_ON) if (key in card) config[key] = card[key];
  if (card.type === "entities") {
    config.show_header_toggle = false;
    // A small heading above the list, instead of the card's own large title.
    if (card.title) {
      const heading = { type: "heading", heading: text(card.title, lang), heading_style: "subtitle" };
      return [{ anchor: true, config: heading }, { anchor: true, config }];
    }
  } else if (card.title) config.title = text(card.title, lang);
  return [{ anchor: true, config }];
};

// Inside the lock the section's grid is gone, so the tiles are stacked, each
// with its input beside the name.
const lockCard = (cards, options, group) => ({
  type: `custom:${LOCK_CARD}`,
  group,
  hold_seconds: options.hold_seconds,
  unlock_seconds: options.unlock_seconds,
  grid_options: { columns: "full" },
  card: {
    type: "vertical-stack",
    cards: cards.map((card) => (card.type === "tile" ? { features_position: "inline", ...card } : card)),
  },
});

// The cards of a section, or of one group of it, and whether they show
// something of this family; null where they name entities and found none.
const buildCards = (layoutCards, ctx, locked) => {
  const built = layoutCards.flatMap(expand).flatMap((card) => buildCard(card, ctx));
  const anchor = built.some((card) => card.anchor);
  // Cards without any entity (the energy flow) stay, but do not make a view.
  if (!anchor && layoutCards.some((card) => card.entity || card.entities || card.roles || card.status)) return null;
  let cards = built.map((card) => card.config);
  if (locked && ctx.options.controls !== "admin") cards = [lockCard(cards, ctx.options, ctx.view)];
  else if (locked) {
    cards = cards.map((card) =>
      card.type === "tile" ? { features_position: "inline", ...card, grid_options: { columns: "full" } } : card);
  }
  return { cards, anchor };
};

const buildSection = (section, ctx, locked) => {
  let cards;
  let anchor;
  if (section.groups) {
    // Side by side where there is room, one column each.
    cards = section.groups.flatMap((group) => {
      const built = buildCards(group.cards, ctx, locked || Boolean(group.locked));
      if (!built) return [];
      const title = { type: "heading", heading: text(group.heading, ctx.lang), heading_style: "subtitle" };
      return [{ type: "vertical-stack", grid_options: { columns: 12 }, cards: [title, ...built.cards] }];
    });
    anchor = cards.length > 0;
    if (!anchor) return null;
  } else {
    const built = buildCards(section.cards, ctx, locked);
    if (!built) return null;
    ({ cards, anchor } = built);
  }
  const heading = { type: "heading", heading: text(section.heading, ctx.lang), heading_style: "title", icon: section.icon };
  if (section.view && ctx.paths[section.view]) heading.tap_action = navigate(ctx.paths[section.view]);
  const grid = { type: "grid", cards: [heading, ...cards] };
  if (section.column_span) grid.column_span = section.column_span; // "fill" is settled by buildView
  return { grid, anchor };
};

const buildBadge = (badge, ctx) => {
  const found = resolve(badge.entity, ctx.family, ctx.everywhere);
  if (!found) return [];
  const config = {
    type: "entity", entity: found.entity, name: text(badge.name, ctx.lang), show_name: true, show_state: !badge.only, show_icon: true,
  };
  for (const key of ["icon", "color"]) if (key in badge) config[key] = badge[key];
  if (badge.only) config.visibility = [{ condition: "state", entity: found.entity, state: badge.only }];
  if (badge.view && ctx.paths[badge.view]) config.tap_action = navigate(ctx.paths[badge.view]);
  return [config];
};

const buildView = (view, ctx) => {
  const locked = Boolean(view.locked);
  const here = { ...ctx, view: view.id };
  const sections = view.sections.map((section) => buildSection(section, here, locked)).filter(Boolean);
  if (!sections.some((section) => section.anchor)) return null;
  // A "fill" section takes what its row has left beside the ones before it.
  let column = 0;
  for (const { grid } of sections) {
    if (grid.column_span === "fill") grid.column_span = MAX_COLUMNS - (column % MAX_COLUMNS);
    column += grid.column_span ?? 1;
  }
  return {
    title: text(view.title, ctx.lang),
    path: view.id,
    icon: view.icon,
    type: "sections",
    max_columns: MAX_COLUMNS,
    badges: (view.badges ?? []).flatMap((badge) => buildBadge(badge, ctx)),
    sections: sections.map((section) => section.grid),
    ...(view.admin && ctx.admins ? { visible: ctx.admins } : {}),
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

// Whether the Energy dashboard has any source, which its cards need.
const energyIsSetUp = async (hass) => {
  if (!hass.config.components.includes("energy")) return false;
  try {
    return Boolean((await hass.callWS({ type: "energy/get_prefs" })).energy_sources?.length);
  } catch {
    // Home Assistant answers an error while nothing is set up.
    return false;
  }
};

// A wallbox entry beside inverters: which families are wallboxes of their own,
// which inverter they are the guests of -- the only one, or none, since nothing
// says which of several a wallbox belongs to -- and that inverter's family with
// the first wallbox's entities lent to it.
const guests = (layout, roots, context, families) => {
  const fills = (id, root) => Boolean(buildView(layout.views.find((view) => view.id === id), context(root, {})));
  const inverters = roots.filter((root) => fills("inverter", root));
  const wallboxes = roots.filter((root) => !inverters.includes(root) && fills("wallbox", root));
  const host = inverters.length === 1 ? inverters[0] : null;
  const lent = new Map(host ? families.get(host) : []);
  // A wallbox whose entities the inverter already shows keeps its own controls.
  const merged = new Set();
  for (const root of host ? wallboxes : []) {
    const own = [...families.get(root)].filter(([ref]) => ref.split(".")[1].startsWith("wallbox_"));
    if (own.some(([ref]) => lent.has(ref))) continue;
    for (const [ref, ids] of own) lent.set(ref, ids);
    merged.add(root);
  }
  return { inverters, wallboxes, host, lent, merged };
};

// A wallbox's sections under the inverter's, each named by its device.
const joinViews = (parts, names) => ({
  ...parts[0],
  sections: parts.flatMap((part, index) => part.sections.map((section) => {
    const [heading, ...cards] = section.cards;
    return { ...section, cards: [{ ...heading, heading: `${heading.heading} · ${names[index]}` }, ...cards] };
  })),
});

class SungrowModbusDashboardStrategy extends HTMLElement {
  static registryDependencies = ["entities", "devices"];

  static async generate(config, hass) {
    const lang = language(hass);
    const options = {
      controls: ["hold", "admin", "hidden"].includes(config.controls) ? config.controls : "hold",
      hold_seconds: Number(config.hold_seconds) > 0 ? Number(config.hold_seconds) : 2,
      unlock_seconds: Number(config.unlock_seconds) > 0 ? Number(config.unlock_seconds) : 60,
      power_flow: config.power_flow === "tiles" ? "tiles" : "auto",
    };
    const asked = Array.isArray(config.views) ? config.views.map((id) => RENAMED[id] ?? id) : VIEW_ORDER;
    const wanted = asked.filter(
      (id) => VIEW_ORDER.includes(id) && !(id === "controls" && options.controls === "hidden"),
    );
    const layout = await loadLayout();
    const views = wanted
      .map((id) => layout.views.find((view) => view.id === id))
      .filter((view) => view && (!view.admin || hass.user?.is_admin));
    const house = indexHouse(hass);
    // `device_id` pins one family: the inverter's, or the one a named battery
    // or wallbox belongs to.
    const roots = config.device_id
      ? house.roots.filter((root) => root === house.rootOf(config.device_id))
      : house.roots;
    const admins = views.some((view) => view.admin) ? await adminVisibility(hass) : null;

    const energy = wanted.includes("energy") && (await energyIsSetUp(hass));
    const context = (root, paths, family = house.families.get(root)) => ({
      family, everywhere: house.everywhere, hass, lang, root, options, admins, energy, paths,
    });

    const { inverters, wallboxes, host, lent, merged } = guests(layout, roots, context, house.families);
    // Inverters first, so that a wallbox never takes the first tab.
    roots.sort((a, b) => inverters.includes(b) - inverters.includes(a));
    const familyFor = (view, root) =>
      root === host && ["home", "controls"].includes(view.id) ? lent : house.families.get(root);
    // What a wallbox entry gives to the inverter's view instead of a tab of its own.
    const isGuest = (view, root) =>
      wallboxes.includes(root) &&
      ((view.id === "home" && inverters.length > 0) || (view.id === "controls" && merged.has(root)));

    // Which views each family fills, first, so that a tap can name another
    // view by its path; a wallbox entry of its own lends its view to the rest.
    const plan = [];
    const dashboard = location.pathname.split("/")[1];
    for (const view of views) {
      let filled = roots.filter((root) => !isGuest(view, root) && buildView(view, context(root, {}, familyFor(view, root))));
      let joined = [];
      if (view.id === "diagnosis" && filled.includes(host)) {
        joined = filled.filter((root) => wallboxes.includes(root));
        filled = filled.filter((root) => !joined.includes(root));
      }
      for (const [index, root] of filled.entries()) {
        plan.push({ view, root, joined: root === host ? joined : [], many: filled.length > 1, path: filled.length > 1 ? `${view.id}-${index + 1}` : view.id });
      }
    }
    const built = plan.map(({ view, root, joined, many, path }) => {
      const paths = {};
      for (const other of plan) {
        if (other.root === root || !other.many) paths[other.view.id] = `/${dashboard}/${other.path}`;
      }
      let result = buildView(view, context(root, paths, familyFor(view, root)));
      if (joined.length) {
        result = joinViews(
          [result, ...joined.map((other) => buildView(view, context(other, paths)))],
          [root, ...joined].map(house.deviceName),
        );
      }
      return { ...result, path, ...(many ? { title: `${result.title} · ${house.deviceName(root)}` } : {}) };
    });
    if (!built.length) {
      return {
        views: [{ title: "Sungrow", path: "sungrow", type: "sections",
          sections: [{ type: "grid", cards: [{ type: "markdown", content: say("empty", lang) }] }] }],
      };
    }
    const { type: _type, ...chosen } = config;
    built[0].sections[0].cards.splice(1, 0, {
      type: `custom:${UPDATE_CARD}`, revision: layout.revision, options: chosen, grid_options: { columns: "full" },
    });
    return { views: built };
  }
}

// ---------------------------------------------------------------- register

if (!customElements.get(`ll-strategy-dashboard-${STRATEGY}`)) {
  customElements.define(`ll-strategy-dashboard-${STRATEGY}`, SungrowModbusDashboardStrategy);
}

const { SungrowModbusLockCard } = await import(new URL(`lock.js${HERE.search}`, HERE));
const { SungrowModbusFlowCard } = await import(new URL(`flow.js${HERE.search}`, HERE));
const { SungrowModbusTestsCard } = await import(new URL(`tests.js${HERE.search}`, HERE));
const { SungrowModbusUpdateCard } = await import(new URL(`update.js${HERE.search}`, HERE));

// For the card picker: the flow of the first family that has one.
SungrowModbusFlowCard.getStubConfig = async (hass) => {
  const layout = await loadLayout();
  const house = indexHouse(hass);
  const flow = layout.views.flatMap((view) => view.sections).flatMap((section) => section.cards ?? []).find((card) => card.type === "flow");
  for (const root of house.roots) {
    const ctx = { family: house.families.get(root), everywhere: house.everywhere, lang: language(hass), root, options: {}, paths: {} };
    const [card] = buildCard(flow, ctx);
    if (card) return { entities: card.config.entities };
  }
  return { entities: {} };
};

const CARDS = [
  [LOCK_CARD, SungrowModbusLockCard, "Sungrow Modbus lock", "lock_description"],
  [FLOW_CARD, SungrowModbusFlowCard, "Sungrow power flow", "flow_description"],
];
// Parts of the dashboard, of no use in the card picker.
for (const [tag, element] of [[TESTS_CARD, SungrowModbusTestsCard], [UPDATE_CARD, SungrowModbusUpdateCard]]) {
  if (!customElements.get(tag)) customElements.define(tag, element);
}
const lang = language(document.querySelector("home-assistant")?.hass);
window.customCards ??= [];
for (const [tag, element, name, description] of CARDS) {
  if (!customElements.get(tag)) customElements.define(tag, element);
  if (!window.customCards.some((card) => card.type === tag)) {
    window.customCards.push({ type: tag, name, description: say(description, lang) });
  }
}
window.customStrategies ??= [];
if (!window.customStrategies.some((s) => s.type === STRATEGY && s.strategyType === "dashboard")) {
  window.customStrategies.push({
    type: STRATEGY,
    strategyType: "dashboard",
    name: "Sungrow Modbus",
    description: say("strategy_description", lang),
    documentationURL: `${DOCS}/dashboard.md`,
  });
}
