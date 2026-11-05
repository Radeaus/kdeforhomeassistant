// The online demo: the real KDE for Home Assistant panel inside a small copy of
// Home Assistant's frontend, talking to a simulated backend with made-up devices.
//
// 1. Stand-ins for the Home Assistant components the panel uses (ha-card, ...).
// 2. A simulated "world": devices, the API the panel calls, and entity states.
// 3. The shell around the panel: sidebar, routing, more-info dialog, demo bar.

import { ICONS } from "./icons.js";

const PANEL_PATH = "/kde-for-home-assistant";
const PANEL_TAG = "kde-for-home-assistant-panel";

const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );
const sheet = (css) => {
  const s = new CSSStyleSheet();
  s.replaceSync(css);
  return s;
};
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const storage = {
  get(key) {
    try {
      return localStorage.getItem(key);
    } catch (_err) {
      return null;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (_err) {
      // Private window or blocked storage: the demo still works.
    }
  },
};

// ---------------------------------------------------------------------------
// 1. Home Assistant component stand-ins
// ---------------------------------------------------------------------------

const ICON_CSS = sheet(`
  :host { display: inline-flex; align-items: center; justify-content: center; vertical-align: middle;
    width: var(--mdc-icon-size, 24px); height: var(--mdc-icon-size, 24px); flex: none; fill: currentColor; }
  svg { width: 100%; height: 100%; display: block; }
`);

class HaIcon extends HTMLElement {
  static observedAttributes = ["icon"];
  constructor() {
    super();
    this.attachShadow({ mode: "open" }).adoptedStyleSheets = [ICON_CSS];
  }
  get icon() {
    return this.getAttribute("icon");
  }
  set icon(value) {
    this.setAttribute("icon", value);
  }
  connectedCallback() {
    this._draw();
  }
  attributeChangedCallback() {
    this._draw();
  }
  _draw() {
    const name = (this.getAttribute("icon") || "").replace(/^mdi:/, "");
    const path = ICONS[name] || ICONS["shape-outline"];
    this.shadowRoot.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${path}"></path></svg>`;
  }
}

const SPINNER_CSS = sheet(`
  :host { display: inline-block; --s: 48px; width: var(--s); height: var(--s); flex: none; }
  :host([size="tiny"]) { --s: 16px; }
  :host([size="small"]) { --s: 28px; }
  :host([size="large"]) { --s: 68px; }
  .s { width: 100%; height: 100%; box-sizing: border-box; border-radius: 50%;
    border: max(2px, calc(var(--s) / 10)) solid color-mix(in srgb, var(--ha-spinner-color, var(--primary-color)) 22%, transparent);
    border-top-color: var(--ha-spinner-color, var(--primary-color)); animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .s { animation-duration: 2.4s; } }
`);

class HaSpinner extends HTMLElement {
  constructor() {
    super();
    const root = this.attachShadow({ mode: "open" });
    root.adoptedStyleSheets = [SPINNER_CSS];
    root.innerHTML = `<div class="s" role="progressbar" aria-label="Loading"></div>`;
  }
}

const BUTTON_CSS = sheet(`
  :host { display: inline-flex; --c: var(--primary-color); vertical-align: middle; }
  :host([variant="danger"]) { --c: var(--error-color); }
  button { all: unset; box-sizing: border-box; position: relative; display: inline-flex; align-items: center;
    justify-content: center; gap: 8px; height: 40px; padding: 0 16px; border-radius: 999px; cursor: pointer;
    font-family: var(--ha-font-family-body); font-size: 14px; font-weight: 500; white-space: nowrap;
    color: var(--c); --mdc-icon-size: 18px; --ha-spinner-color: currentColor;
    transition: background-color 0.15s, filter 0.15s; -webkit-tap-highlight-color: transparent; }
  :host([size="small"]) button { height: 32px; padding: 0 12px; }
  :host(:not([appearance])) button, :host([appearance="accent"]) button { background: var(--c); color: #fff; }
  :host(:not([appearance])) button:hover, :host([appearance="accent"]) button:hover { filter: brightness(1.08); }
  :host([appearance="filled"]) button { background: color-mix(in srgb, var(--c) 16%, transparent); }
  :host([appearance="filled"]) button:hover { background: color-mix(in srgb, var(--c) 24%, transparent); }
  :host([appearance="outlined"]) button { box-shadow: inset 0 0 0 1px var(--outline-color); }
  :host([appearance="outlined"]) button:hover,
  :host([appearance="plain"]) button:hover { background: color-mix(in srgb, var(--c) 10%, transparent); }
  button:focus-visible { outline: 2px solid var(--c); outline-offset: 2px; }
  button:disabled { cursor: default; color: var(--disabled-text-color); filter: none; }
  :host([appearance="accent"]) button:disabled, :host(:not([appearance])) button:disabled,
  :host([appearance="filled"]) button:disabled { background: color-mix(in srgb, var(--disabled-text-color) 24%, transparent); }
  :host([appearance="outlined"]) button:disabled { box-shadow: inset 0 0 0 1px var(--divider-color); }
  :host([appearance="plain"]) button:disabled { background: none; }
  .content { display: inline-flex; align-items: center; gap: 8px; }
  ha-spinner { display: none; position: absolute; inset: 0; margin: auto; }
  :host([loading]) .content { visibility: hidden; }
  :host([loading]) ha-spinner { display: block; }
`);

class HaButton extends HTMLElement {
  static observedAttributes = ["disabled"];
  constructor() {
    super();
    const root = this.attachShadow({ mode: "open", delegatesFocus: true });
    root.adoptedStyleSheets = [BUTTON_CSS];
    root.innerHTML = `<button type="button"><span class="content"><slot name="start"></slot><slot></slot></span><ha-spinner size="tiny"></ha-spinner></button>`;
    this._button = root.querySelector("button");
  }
  get disabled() {
    return this.hasAttribute("disabled");
  }
  set disabled(value) {
    this.toggleAttribute("disabled", Boolean(value));
  }
  attributeChangedCallback() {
    this._button.disabled = this.disabled;
  }
}

const ICON_BUTTON_CSS = sheet(`
  :host { display: inline-flex; color: inherit; }
  button { all: unset; box-sizing: border-box; width: var(--mdc-icon-button-size, 48px); height: var(--mdc-icon-button-size, 48px);
    border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; color: inherit;
    -webkit-tap-highlight-color: transparent; }
  button:hover { background: rgba(127, 127, 127, 0.16); }
  button:focus-visible { outline: 2px solid var(--primary-color); }
`);

class HaIconButton extends HTMLElement {
  static observedAttributes = ["label"];
  constructor() {
    super();
    const root = this.attachShadow({ mode: "open", delegatesFocus: true });
    root.adoptedStyleSheets = [ICON_BUTTON_CSS];
    root.innerHTML = `<button type="button"><slot></slot></button>`;
    this._button = root.querySelector("button");
  }
  attributeChangedCallback() {
    const label = this.getAttribute("label") || "";
    this._button.setAttribute("aria-label", label);
    this._button.title = label;
  }
}

// Shows the sidebar toggle on narrow screens, like Home Assistant.
class HaMenuButton extends HTMLElement {
  constructor() {
    super();
    const root = this.attachShadow({ mode: "open" });
    root.adoptedStyleSheets = [sheet(`:host { display: none; } :host([narrow]) { display: inline-flex; }`)];
    root.innerHTML = `<ha-icon-button label="Sidebar"><ha-icon icon="mdi:menu"></ha-icon></ha-icon-button>`;
    root.addEventListener("click", () =>
      this.dispatchEvent(new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }))
    );
  }
  set narrow(value) {
    this.toggleAttribute("narrow", Boolean(value));
  }
  set hass(_hass) {}
}

const CARD_CSS = sheet(`
  :host { display: block; background: var(--card-background-color); color: var(--primary-text-color);
    border: 1px solid var(--divider-color); border-radius: 12px; }
  .card-header { margin: 0; padding: 20px 16px 12px; font-size: 24px; line-height: 32px; font-weight: 400; }
`);

class HaCard extends HTMLElement {
  static observedAttributes = ["header"];
  constructor() {
    super();
    this.attachShadow({ mode: "open" }).adoptedStyleSheets = [CARD_CSS];
    this._draw();
  }
  attributeChangedCallback() {
    this._draw();
  }
  _draw() {
    const header = this.getAttribute("header");
    this.shadowRoot.innerHTML = `${header ? `<h1 class="card-header">${esc(header)}</h1>` : ""}<slot></slot>`;
  }
}

const ALERT_ICONS = {
  info: "mdi:information-outline",
  warning: "mdi:alert-outline",
  error: "mdi:alert-circle-outline",
  success: "mdi:check-circle-outline",
};
const ALERT_CSS = sheet(`
  :host { display: block; --c: var(--info-color); }
  :host([alert-type="warning"]) { --c: var(--warning-color); }
  :host([alert-type="error"]) { --c: var(--error-color); }
  :host([alert-type="success"]) { --c: var(--success-color); }
  .alert { display: flex; gap: 12px; align-items: flex-start; padding: 10px 12px 10px 14px; border-radius: 8px;
    background: color-mix(in srgb, var(--c) 13%, transparent); color: var(--primary-text-color); line-height: 1.5; }
  .icon { color: var(--c); padding-top: 2px; }
  .main { flex: 1; min-width: 0; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px 12px; }
  .content { flex: 1 1 240px; min-width: 0; padding: 2px 0; overflow-wrap: anywhere; }
  .title { font-weight: 500; }
`);

class HaAlert extends HTMLElement {
  static observedAttributes = ["alert-type", "title"];
  constructor() {
    super();
    this.attachShadow({ mode: "open" }).adoptedStyleSheets = [ALERT_CSS];
    this._draw();
  }
  attributeChangedCallback() {
    this._draw();
  }
  _draw() {
    const type = this.getAttribute("alert-type") || "info";
    const title = this.getAttribute("title");
    this.shadowRoot.innerHTML = `<div class="alert" role="alert">
      <ha-icon class="icon" icon="${ALERT_ICONS[type] || ALERT_ICONS.info}"></ha-icon>
      <div class="main"><div class="content">${title ? `<div class="title">${esc(title)}</div>` : ""}<slot></slot></div>
      <slot name="action"></slot></div></div>`;
  }
  // Home Assistant's ha-alert keeps "title" from becoming a tooltip.
  get title() {
    return "";
  }
}

const SWITCH_CSS = sheet(`
  :host { display: inline-flex; align-items: center; }
  button { all: unset; position: relative; width: 52px; height: 32px; display: inline-flex; align-items: center;
    justify-content: center; cursor: pointer; border-radius: 16px; -webkit-tap-highlight-color: transparent; }
  button:focus-visible { outline: 2px solid var(--primary-color); }
  .track { width: 36px; height: 14px; border-radius: 7px; background: var(--outline-color); transition: background 0.15s; }
  .thumb { position: absolute; top: 6px; left: 6px; width: 20px; height: 20px; border-radius: 50%; background: #f5f5f5;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.45); transition: transform 0.15s, background 0.15s; }
  :host([checked]) .track { background: color-mix(in srgb, var(--primary-color) 50%, transparent); }
  :host([checked]) .thumb { transform: translateX(20px); background: var(--primary-color); }
  :host([disabled]) button { cursor: default; opacity: 0.5; }
  @media (prefers-reduced-motion: reduce) { .track, .thumb { transition: none; } }
`);

class HaSwitch extends HTMLElement {
  static observedAttributes = ["checked", "disabled"];
  constructor() {
    super();
    const root = this.attachShadow({ mode: "open", delegatesFocus: true });
    root.adoptedStyleSheets = [SWITCH_CSS];
    root.innerHTML = `<button type="button" role="switch"><span class="track"></span><span class="thumb"></span></button>`;
    this._button = root.querySelector("button");
    this._button.addEventListener("click", () => {
      if (this.disabled) return;
      this.checked = !this.checked;
      this.dispatchEvent(new Event("change", { bubbles: true, composed: true }));
    });
  }
  get checked() {
    return this.hasAttribute("checked");
  }
  set checked(value) {
    this.toggleAttribute("checked", Boolean(value));
  }
  get disabled() {
    return this.hasAttribute("disabled");
  }
  connectedCallback() {
    // Name the switch after the row it sits in.
    const row = this.closest(".row");
    const label = row?.querySelector(".headline")?.textContent;
    if (label) this._button.setAttribute("aria-label", label);
  }
  attributeChangedCallback() {
    this._button.setAttribute("aria-checked", String(this.checked));
    this._button.disabled = this.disabled;
  }
}

const INPUT_CSS = sheet(`
  :host { display: block; }
  label { display: block; }
  .label { display: block; font-size: 12px; font-weight: 500; color: var(--secondary-text-color); margin-bottom: 4px; }
  :host(:focus-within) .label { color: var(--primary-color); }
  input { box-sizing: border-box; width: 100%; height: 44px; padding: 0 12px; border-radius: 8px;
    border: 1px solid var(--outline-color); background: var(--card-background-color); color: var(--primary-text-color);
    font-family: var(--ha-font-family-body); font-size: 16px; outline: none; }
  input::placeholder { color: var(--disabled-text-color); }
  input:focus { border-color: var(--primary-color); box-shadow: 0 0 0 1px var(--primary-color); }
  :host(.mono-field) input { font-family: var(--ha-font-family-code); font-size: 15px; }
  .hint { font-size: 12px; color: var(--secondary-text-color); margin-top: 4px; }
  .hint:empty { display: none; }
`);

class HaInput extends HTMLElement {
  static observedAttributes = ["label", "value", "hint", "placeholder", "maxlength", "autocomplete"];
  constructor() {
    super();
    const root = this.attachShadow({ mode: "open", delegatesFocus: true });
    root.adoptedStyleSheets = [INPUT_CSS];
    root.innerHTML = `<label><span class="label"></span><input></label><div class="hint"></div>`;
    this._input = root.querySelector("input");
    this.updateComplete = Promise.resolve(true);
  }
  attributeChangedCallback(name, _old, value) {
    if (name === "label") this.shadowRoot.querySelector(".label").textContent = value || "";
    else if (name === "hint") this.shadowRoot.querySelector(".hint").textContent = value || "";
    else if (name === "value") this._input.value = value ?? "";
    else if (value === null) this._input.removeAttribute(name);
    else this._input.setAttribute(name, value);
  }
  get value() {
    return this._input.value;
  }
  set value(value) {
    this._input.value = value ?? "";
  }
  focus() {
    this._input.focus();
  }
  setSelectionRange(start, end) {
    this._input.setSelectionRange(start, end);
  }
}

const COMPONENTS = {
  "ha-icon": HaIcon,
  "ha-spinner": HaSpinner,
  "ha-button": HaButton,
  "ha-icon-button": HaIconButton,
  "ha-menu-button": HaMenuButton,
  "ha-card": HaCard,
  "ha-alert": HaAlert,
  "ha-switch": HaSwitch,
  "ha-input": HaInput,
};
for (const [tag, cls] of Object.entries(COMPONENTS)) customElements.define(tag, cls);

// ---------------------------------------------------------------------------
// 2. The simulated world
// ---------------------------------------------------------------------------

const TEXT = {
  en: {
    not_in_demo: "{page} is not part of this demo. Only the KDE for Home Assistant page is.",
    script_editor: "The script editor",
    ringing: "{name} is ringing",
    remote_sent: "Sent “{command}” to {name}",
    woke: "Wake-on-LAN sent. {name} is starting up…",
    ran: "Ran “{command}” on {name}",
    ran_hidden: "Pressed {button}",
    locked: "Locked the screen of {name}",
    unlocked: "Unlocked the screen of {name}",
    notified: "Notification sent to {name}: “{message}”",
    command_added: "On {name}, a new command “{command}” was added in KDE Connect (simulated).",
    request_toast: "{name} wants to pair with Home Assistant",
    request_waiting: "{name} is already waiting for an answer",
    no_workstation: "There is no paired computer to switch.",
    went_online: "{name} is connected",
    went_offline: "{name} is no longer connected",
    // More info
    connected: "Connected",
    disconnected: "Disconnected",
    locked_state: "Locked",
    unlocked_state: "Unlocked",
    unavailable: "Unavailable",
    lock: "Lock",
    unlock: "Unlock",
    press: "Press",
    never: "Never pressed",
    last_pressed: "Pressed at {time}",
    message: "Message",
    send: "Send",
    entity_id: "Entity ID",
    default_message: "Dinner is ready!",
    // Shell
    demo_text: "Made-up devices. Nothing here connects to a real computer or phone.",
    try_things: "Try things",
    install: "Install",
    theme: "Switch light/dark",
    controls_text: "These play the part of your devices, so you can see how the page reacts.",
    ctl_request: "A phone asks to pair",
    ctl_request_sub: "As if you tapped Pair in KDE Connect",
    ctl_toggle: "Workstation on/off",
    ctl_toggle_sub: "Connect or disconnect it",
    ctl_empty: "Start from scratch",
    ctl_empty_sub: "No devices yet, with the setup wizard",
    ctl_reset: "Reset the demo",
    ctl_reset_sub: "Back to the example devices",
    Overview: "Overview",
    Energy: "Energy",
    Map: "Map",
    Logbook: "Logbook",
    History: "History",
    Media: "Media",
    "To-do lists": "To-do lists",
    "Developer tools": "Developer tools",
    Settings: "Settings",
    Notifications: "Notifications",
    Profile: "Demo user",
  },
  nl: {
    not_in_demo: "{page} zit niet in deze demo. Alleen de pagina KDE for Home Assistant.",
    script_editor: "De scripteditor",
    ringing: "{name} gaat over",
    remote_sent: "„{command}” verstuurd naar {name}",
    woke: "Wake-on-LAN verstuurd. {name} start op…",
    ran: "“{command}” uitgevoerd op {name}",
    ran_hidden: "{button} ingedrukt",
    locked: "Scherm van {name} vergrendeld",
    unlocked: "Scherm van {name} ontgrendeld",
    notified: "Melding verstuurd naar {name}: “{message}”",
    command_added: "Op {name} is in KDE Connect een nieuwe opdracht “{command}” toegevoegd (gesimuleerd).",
    request_toast: "{name} wil koppelen met Home Assistant",
    request_waiting: "{name} wacht al op een antwoord",
    no_workstation: "Er is geen gekoppelde computer om aan of uit te zetten.",
    went_online: "{name} is verbonden",
    went_offline: "{name} is niet meer verbonden",
    connected: "Verbonden",
    disconnected: "Niet verbonden",
    locked_state: "Vergrendeld",
    unlocked_state: "Ontgrendeld",
    unavailable: "Niet beschikbaar",
    lock: "Vergrendelen",
    unlock: "Ontgrendelen",
    press: "Indrukken",
    never: "Nog nooit ingedrukt",
    last_pressed: "Ingedrukt om {time}",
    message: "Bericht",
    send: "Versturen",
    entity_id: "Entiteit-ID",
    default_message: "Het eten is klaar!",
    demo_text: "Verzonnen apparaten. Niets hier maakt verbinding met een echte computer of telefoon.",
    try_things: "Probeer uit",
    install: "Installeren",
    theme: "Licht/donker",
    controls_text: "Hiermee speel je zelf het apparaat, zodat je ziet hoe de pagina reageert.",
    ctl_request: "Een telefoon wil koppelen",
    ctl_request_sub: "Alsof je in KDE Connect op Koppelen tikt",
    ctl_toggle: "Workstation aan/uit",
    ctl_toggle_sub: "Verbinding maken of verbreken",
    ctl_empty: "Begin opnieuw",
    ctl_empty_sub: "Nog geen apparaten, met de installatiewizard",
    ctl_reset: "Demo herstellen",
    ctl_reset_sub: "Terug naar de voorbeeldapparaten",
    Overview: "Overzicht",
    Energy: "Energie",
    Map: "Kaart",
    Logbook: "Logboek",
    History: "Geschiedenis",
    Media: "Media",
    "To-do lists": "Takenlijsten",
    "Developer tools": "Ontwikkelhulpmiddelen",
    Settings: "Instellingen",
    Notifications: "Meldingen",
    Profile: "Demogebruiker",
  },
};

// English unless ?lang=nl is in the link or Dutch was picked with the NL button.
const pickLang = (value) => (value === "nl" || value === "en" ? value : null);
let lang =
  pickLang(new URLSearchParams(location.search).get("lang")) ||
  pickLang(storage.get("kde-demo-lang")) ||
  "en";
const t = (key, vars = {}) =>
  (TEXT[lang][key] ?? TEXT.en[key] ?? key).replace(/\{(\w+)\}/g, (_, name) => vars[name] ?? "");

const randomHex = (bytes) =>
  Array.from(crypto.getRandomValues(new Uint8Array(bytes)), (b) => b.toString(16).padStart(2, "0")).join("");
const randomMac = () =>
  ["3c", ...randomHex(5).match(/../g)].join(":");
const slug = (text) =>
  text.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "device";

const COMMANDS = {
  shutdown: ["Shut down", "systemctl poweroff"],
  sleep: ["Sleep", "systemctl suspend"],
  lock: ["Lock screen", "loginctl lock-session"],
  mute: ["Mute", "pactl set-sink-mute @DEFAULT_SINK@ toggle"],
  volup: ["Volume up", "pactl set-sink-volume @DEFAULT_SINK@ +5%"],
  voldown: ["Volume down", "pactl set-sink-volume @DEFAULT_SINK@ -5%"],
  steam: ["Open Steam", "steam"],
  screenshot: ["Take a screenshot", "spectacle --background --nonotify --fullscreen"],
};
const command = (id) => ({ key: randomHex(4), name: COMMANDS[id][0], command: COMMANDS[id][1] });

const SCRIPTS = {
  "script.movie_night": "Movie night",
  "script.good_night": "Good night",
  "script.coffee": "Start the coffee machine",
  "script.leave_home": "Leaving home",
};

const DISCOVERED = [
  { name: "Gaming PC", type: "desktop", host: "192.168.1.42", delay: 900 },
  { name: "Kitchen tablet", type: "tablet", host: "192.168.1.57", delay: 2200 },
  { name: "Robin's laptop", type: "laptop", host: "192.168.1.73", delay: 3600 },
];

const world = {};

function newDevice({ name, type, connected = true, mac = null, commands = [], hidden = [], scripts = [], host = null }) {
  const device = {
    id: "sub" + randomHex(6),
    device_id: randomHex(16),
    name,
    type,
    host,
    connected,
    mac,
    scripts,
    commands,
    hidden: new Set(hidden),
    lock: type !== "phone" && type !== "tablet" && type !== "tv" ? "unlocked" : null,
    entities: {},
    commandEntities: {},
    pressed: {},
  };
  assignEntities(device);
  return device;
}

function sampleWorld() {
  const shutdown = command("shutdown");
  const steam = command("steam");
  world.name = "Demo Home - Home Assistant";
  world.defaultName = "Demo Home - Home Assistant";
  world.devices = [];
  const specs = [
    {
      name: "Workstation",
      type: "desktop",
      mac: "3c:7c:3f:1a:2b:4d",
      commands: [shutdown, command("sleep"), command("lock"), command("mute"), command("volup"), command("voldown"), steam],
      hidden: [steam.key],
      scripts: ["script.movie_night"],
      host: "192.168.1.20",
    },
    {
      name: "Office laptop",
      type: "laptop",
      connected: false,
      mac: "f4:8e:38:5c:91:07",
      commands: [command("shutdown"), command("sleep")],
      host: "192.168.1.31",
    },
    { name: "Pixel phone", type: "phone", host: "192.168.1.66" },
  ];
  for (const spec of specs) world.devices.push(newDevice(spec));
  world.devices[0].id = "workstation";
  world.discovered = discoveredList();
  world.requests = [];
  world.revealed = false;
}

function emptyWorld() {
  sampleWorld();
  world.devices = [];
  world.discovered = discoveredList();
}

function discoveredList() {
  return DISCOVERED.map((d) => ({ ...d, device_id: randomHex(16), reachable: true, visible: false }));
}

function usedEntityIds() {
  const ids = new Set(Object.keys(SCRIPTS));
  for (const d of world.devices || []) {
    for (const id of Object.values(d.entities)) ids.add(id);
    for (const id of Object.values(d.commandEntities)) ids.add(id);
  }
  return ids;
}

function uniqueEntityId(base) {
  const used = usedEntityIds();
  let id = base;
  for (let n = 2; used.has(id); n++) id = `${base}_${n}`;
  return id;
}

// Entity ids follow the device name when it is added, like the registry does.
function assignEntities(device) {
  const s = slug(device.name);
  const ent = device.entities;
  ent.connected ??= uniqueEntityId(`binary_sensor.${s}_connected`);
  if (device.lock) ent.screen_lock ??= uniqueEntityId(`lock.${s}_screen`);
  ent.notify ??= uniqueEntityId(`notify.${s}`);
  ent.ring ??= uniqueEntityId(`button.${s}_ring`);
  ent.remote ??= uniqueEntityId(`remote.${s}_remote`);
  if (device.mac) ent.wake ??= uniqueEntityId(`button.${s}_wake_up`);
  else delete ent.wake;
  for (const c of device.commands) {
    if (device.hidden.has(c.key)) delete device.commandEntities[c.key];
    else device.commandEntities[c.key] ??= uniqueEntityId(`button.${s}_${slug(c.name)}`);
  }
}

function buildState() {
  const paired = new Set(world.devices.map((d) => d.device_id));
  const byName = (a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase());
  return {
    configured: true,
    loaded: true,
    name: world.name,
    default_name: world.defaultName,
    devices: world.devices
      .map((d) => ({
        id: d.id,
        device_id: d.device_id,
        name: d.name,
        type: d.type,
        connected: d.connected,
        mac: d.mac,
        scripts: [...d.scripts],
        commands: d.commands
          .map((c) => ({
            key: c.key,
            name: c.name,
            // Offline devices only have what the registry remembers.
            command: d.connected ? c.command : null,
            entity_id: d.hidden.has(c.key) ? null : d.commandEntities[c.key] || null,
            hidden: d.hidden.has(c.key),
          }))
          .sort(byName),
        entities: { ...d.entities },
      }))
      .sort(byName),
    discovered: world.discovered
      .filter((d) => d.visible && !paired.has(d.device_id))
      .map(({ device_id, name, type, host, reachable }) => ({ device_id, name, type, host, reachable }))
      .sort(byName),
    requests: world.requests.map((r) => ({ device_id: r.device_id, name: r.name, type: r.type, key: r.key })),
  };
}

function buildStates() {
  const states = {};
  const put = (entityId, state, attributes) => {
    states[entityId] = { entity_id: entityId, state, attributes, last_changed: new Date().toISOString() };
  };
  for (const [entityId, name] of Object.entries(SCRIPTS)) {
    put(entityId, "off", { friendly_name: name, icon: "mdi:script-text-outline" });
  }
  for (const d of world.devices) {
    const e = d.entities;
    const live = (state) => (d.connected ? state : "unavailable");
    put(e.connected, d.connected ? "on" : "off", { friendly_name: `${d.name} Connected`, device_class: "connectivity" });
    if (e.screen_lock) {
      put(e.screen_lock, live(d.lock), {
        friendly_name: `${d.name} Screen`,
        icon: d.lock === "unlocked" ? "mdi:monitor" : "mdi:monitor-lock",
      });
    }
    put(e.notify, live("unknown"), { friendly_name: d.name });
    put(e.ring, live(d.pressed[e.ring] || "unknown"), { friendly_name: `${d.name} Ring`, icon: "mdi:bell-ring" });
    put(e.remote, d.connected ? "on" : "off", { friendly_name: `${d.name} Remote`, icon: "mdi:remote-tv" });
    if (e.wake) put(e.wake, d.pressed[e.wake] || "unknown", { friendly_name: `${d.name} Wake up`, icon: "mdi:power" });
    for (const c of d.commands) {
      const entityId = d.commandEntities[c.key];
      if (!entityId) continue;
      put(entityId, live(d.pressed[entityId] || "unknown"), { friendly_name: `${d.name} ${c.name}`, icon: "mdi:console" });
    }
  }
  return states;
}

// --- Change notification (the real backend also waits a moment) ---

const stateListeners = new Set();
let changeTimer = null;
function changed() {
  if (changeTimer) return;
  changeTimer = setTimeout(() => {
    changeTimer = null;
    const state = buildState();
    for (const cb of stateListeners) cb(JSON.parse(JSON.stringify(state)));
    updateHass();
  }, 200);
}

const timers = new Set();
function later(ms, fn) {
  const id = setTimeout(() => {
    timers.delete(id);
    fn();
  }, ms);
  timers.add(id);
  return id;
}
function clearLater(id) {
  clearTimeout(id);
  timers.delete(id);
}
function clearAllTimers() {
  for (const id of timers) clearTimeout(id);
  timers.clear();
}

const wsError = (code, message) => Object.assign(new Error(message), { code });
const findDevice = (subentryId) => world.devices.find((d) => d.id === subentryId);

function setConnected(device, connected) {
  if (device.connected === connected) return;
  device.connected = connected;
  if (connected && device.lock) device.lock = "unlocked";
  toast(t(connected ? "went_online" : "went_offline", { name: device.name }));
  changed();
}

function pairDevice(info) {
  const computer = ["desktop", "laptop"].includes(info.type);
  const device = newDevice({
    name: info.name,
    type: info.type,
    connected: false,
    mac: computer ? randomMac() : null,
    host: info.host,
  });
  device.device_id = info.device_id;
  world.devices.push(device);
  changed();
  // The device reconnects as a trusted device and sends its commands.
  later(1500, () => {
    if (!world.devices.includes(device)) return;
    device.connected = true;
    if (computer && !device.commands.length) {
      device.commands = [command("shutdown"), command("sleep"), command("lock"), command("mute")];
      assignEntities(device);
    }
    changed();
  });
  return device.id;
}

// The panel's API, kdeforhomeassistant/<command>.
const COMMANDS_WS = {
  async input({ subentry_id, command }) {
    const device = findDevice(subentry_id);
    if (!device?.connected) throw wsError("not_connected", "Not connected");
    // Mouse moves are too many to show; a tap shows what a click would do.
    if (!command.startsWith("move:")) toast(t("remote_sent", { command, name: device.name }));
    return null;
  },
  async connect({ host }) {
    await wait(1400);
    host = host.trim();
    let found = world.discovered.find((d) => d.host === host);
    if (!found) {
      if (!/^\d{1,3}(\.\d{1,3}){3}$/.test(host) && !/^[\w.-]+$/.test(host)) {
        throw wsError("not_found", "The device did not connect");
      }
      found = { name: "Study PC", type: "desktop", host, device_id: randomHex(16), reachable: true, visible: true };
      world.discovered.push(found);
    }
    found.visible = true;
    changed();
    return { device_id: found.device_id };
  },
  async accept({ device_id }) {
    const request = world.requests.find((r) => r.device_id === device_id);
    await wait(500);
    if (!request || !world.requests.includes(request)) throw wsError("expired", "The request has expired");
    world.requests = world.requests.filter((r) => r !== request);
    clearLater(request.timer);
    return { id: pairDevice(request) };
  },
  async decline({ device_id }) {
    world.requests = world.requests.filter((r) => {
      if (r.device_id !== device_id) return true;
      clearLater(r.timer);
      return false;
    });
    changed();
    return null;
  },
  async set_name({ name }) {
    await wait(300);
    const clean = String(name).replace(/["',;:.!?()[\]<>]/g, "").trim().slice(0, 32).trim();
    if (!clean) throw wsError("invalid_name", "Enter a name");
    world.name = clean;
    changed();
    return { name: clean };
  },
  async update_device(msg) {
    await wait(300);
    const device = findDevice(msg.subentry_id);
    if (!device) throw wsError("not_found", "Unknown device");
    if ("mac" in msg) {
      const mac = (msg.mac || "").trim();
      if (mac && !/^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$/.test(mac)) throw wsError("invalid_mac", "Invalid MAC address");
      device.mac = mac ? mac.toLowerCase().replace(/-/g, ":") : null;
    }
    if ("scripts" in msg) device.scripts = [...new Set(msg.scripts)];
    if ("hidden_commands" in msg) device.hidden = new Set(msg.hidden_commands);
    assignEntities(device);
    changed();
    return null;
  },
  async remove_device({ subentry_id }) {
    await wait(400);
    const device = findDevice(subentry_id);
    if (!device) throw wsError("not_found", "Unknown device");
    world.devices = world.devices.filter((d) => d !== device);
    // It is still on the network, so it shows up again when adding a device.
    if (!world.discovered.some((d) => d.device_id === device.device_id)) {
      world.discovered.push({
        name: device.name,
        type: device.type,
        host: device.host,
        device_id: device.device_id,
        reachable: true,
        visible: true,
      });
    }
    changed();
    return null;
  },
  async command_setup({ subentry_id }) {
    await wait(300);
    const device = findDevice(subentry_id);
    if (!device?.connected) throw wsError("not_connected", "Not connected");
    // Pretend someone adds a command on the computer a few seconds later.
    later(4000, () => {
      if (!world.devices.includes(device) || device.commands.some((c) => c.name === COMMANDS.screenshot[0])) return;
      const added = command("screenshot");
      device.commands.push(added);
      assignEntities(device);
      toast(t("command_added", { name: device.name, command: added.name }));
      changed();
    });
    return null;
  },
};

// Subscriptions: the callback gets events until the returned function is called.
const SUBSCRIPTIONS = {
  subscribe(_msg, cb) {
    stateListeners.add(cb);
    setTimeout(() => cb(buildState()), 150);
    return () => stateListeners.delete(cb);
  },
  discover() {
    // Devices answer the broadcast one by one.
    const ids = world.discovered
      .filter((d) => !d.visible)
      .map((d) =>
        later(world.revealed ? 300 : d.delay ?? 600, () => {
          d.visible = true;
          changed();
        })
      );
    world.revealed = true;
    return () => ids.forEach(clearLater);
  },
  pair({ device_id }, cb) {
    const info = world.discovered.find((d) => d.device_id === device_id);
    if (!info) throw wsError("not_found", "Unknown device");
    if (world.devices.some((d) => d.device_id === device_id)) throw wsError("already_paired", "Already paired");
    const key = randomHex(4).toUpperCase();
    const ids = [
      later(1200, () => cb({ key })),
      // In the demo the device always accepts after a few seconds.
      later(5200, () => cb({ paired: pairDevice(info) })),
    ];
    return () => ids.forEach(clearLater);
  },
};

const connection = {
  async subscribeMessage(callback, msg) {
    const type = msg.type.split("/")[1];
    const handler = SUBSCRIPTIONS[type];
    if (!handler) throw wsError("unknown_command", `Unknown command ${msg.type}`);
    await wait(50);
    const unsub = handler(msg, callback);
    return () => unsub();
  },
};

async function callWS(msg) {
  const type = msg.type.split("/")[1];
  const handler = COMMANDS_WS[type];
  if (!handler) throw wsError("unknown_command", `Unknown command ${msg.type}`);
  return handler(msg);
}

function owner(entityId) {
  for (const d of world.devices) {
    for (const [key, id] of Object.entries(d.entities)) if (id === entityId) return { device: d, key };
    for (const c of d.commands) if (d.commandEntities[c.key] === entityId) return { device: d, command: c };
  }
  return {};
}

async function callService(domain, service, data) {
  const entityId = data.entity_id;
  const { device, key, command: cmd } = owner(entityId);
  await wait(350);
  if (!device) throw wsError("not_found", `Unknown entity ${entityId}`);
  if (!device.connected && key !== "wake") throw wsError("not_connected", "Not connected");
  if (domain === "button") device.pressed[entityId] = new Date().toISOString();

  if (domain === "lock") {
    device.lock = service === "lock" ? "locked" : "unlocked";
    toast(t(service === "lock" ? "locked" : "unlocked", { name: device.name }));
  } else if (domain === "notify") {
    toast(t("notified", { name: device.name, message: data.message }));
  } else if (domain === "remote") {
    const command = String(data.command).replace(/^text:/, "");
    toast(t("remote_sent", { command, name: device.name }));
  } else if (key === "ring") {
    toast(t("ringing", { name: device.name }));
  } else if (key === "wake") {
    toast(t("woke", { name: device.name }));
    later(4000, () => setConnected(device, true));
  } else if (cmd) {
    toast(t("ran", { command: cmd.command, name: device.name }));
    if (/^(shut down|sleep)$/i.test(cmd.name)) later(1500, () => setConnected(device, false));
    if (/^lock screen$/i.test(cmd.name) && device.lock) device.lock = "locked";
    if (/^unlock screen$/i.test(cmd.name) && device.lock) device.lock = "unlocked";
  }
  changed();
}

// ---------------------------------------------------------------------------
// 3. The shell
// ---------------------------------------------------------------------------

const main = document.getElementById("main");
const sidebar = document.getElementById("sidebar");
const scrim = document.getElementById("scrim");
const narrowQuery = matchMedia("(max-width: 870px)");
let hass;
let panel;

function darkMode() {
  const theme = document.documentElement.dataset.theme;
  return theme ? theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
}

function updateHass() {
  hass = {
    language: lang,
    locale: { language: lang },
    selectedLanguage: lang,
    states: buildStates(),
    user: { id: "demo", name: "Demo user", is_admin: true, is_owner: true },
    themes: { darkMode: darkMode() },
    panels: {},
    callWS,
    callService,
    connection,
  };
  if (panel) panel.hass = hass;
  refreshMoreInfo();
}

// The panel routes with real paths; here they live after the # so that the
// page works on any static host and survives a reload.
for (const fn of ["pushState", "replaceState"]) {
  const original = history[fn].bind(history);
  history[fn] = (state, title, url) => {
    if (typeof url === "string" && url.startsWith(PANEL_PATH)) {
      const rest = url.slice(PANEL_PATH.length);
      url = location.pathname + location.search + (rest ? `#${rest}` : "");
    }
    return original(state, title, url);
  };
}

const route = () => ({ prefix: PANEL_PATH, path: decodeURI(location.hash.slice(1)) });
const syncRoute = () => {
  if (panel) panel.route = route();
  closeSidebar();
};
window.addEventListener("location-changed", syncRoute);
window.addEventListener("popstate", syncRoute);

function goHome(replace = false) {
  history[replace ? "replaceState" : "pushState"](null, "", PANEL_PATH);
  window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace } }));
}

function mountPanel() {
  panel?.remove();
  panel = document.createElement(PANEL_TAG);
  panel.hass = hass;
  panel.narrow = narrowQuery.matches;
  panel.panel = { url_path: PANEL_PATH.slice(1), config: {} };
  panel.route = route();
  main.replaceChildren(panel);
}

function resetTo(builder) {
  clearAllTimers();
  stateListeners.clear();
  builder();
  updateHass();
  history.replaceState(null, "", PANEL_PATH);
  mountPanel();
}

// --- Sidebar ---

function openSidebar() {
  sidebar.classList.add("open");
  scrim.hidden = false;
}
function closeSidebar() {
  sidebar.classList.remove("open");
  scrim.hidden = true;
}
document.addEventListener("hass-toggle-menu", () =>
  sidebar.classList.contains("open") ? closeSidebar() : openSidebar()
);
scrim.addEventListener("click", closeSidebar);
narrowQuery.addEventListener("change", () => {
  if (panel) panel.narrow = narrowQuery.matches;
  closeSidebar();
});
sidebar.addEventListener("click", (ev) => {
  const link = ev.target.closest("a");
  if (!link) return;
  ev.preventDefault();
  if (link.hasAttribute("data-home")) goHome();
  else toast(t("not_in_demo", { page: t(link.dataset.fake) }));
  closeSidebar();
});

// Links to other Home Assistant pages (like the script editor) stay here.
document.addEventListener(
  "click",
  (ev) => {
    const link = ev.composedPath().find((node) => node instanceof HTMLAnchorElement);
    const href = link?.getAttribute("href") || "";
    if (href.startsWith("/")) {
      ev.preventDefault();
      toast(t("not_in_demo", { page: t("script_editor") }));
    }
  },
  true
);

// --- More info dialog ---

const dialog = document.getElementById("more-info");
let moreInfo = null;

dialog.addEventListener("click", (ev) => {
  if (ev.target === dialog || ev.target.closest("[data-close]")) dialog.close();
});
dialog.addEventListener("close", () => {
  moreInfo = null;
});
document.addEventListener("hass-more-info", (ev) => {
  moreInfo = { entityId: ev.detail.entityId, key: "" };
  refreshMoreInfo();
  if (!dialog.open) dialog.showModal();
});

function refreshMoreInfo() {
  if (!moreInfo || !hass) return;
  const st = hass.states[moreInfo.entityId];
  if (!st) {
    dialog.close();
    return;
  }
  const renderKey = JSON.stringify([st, lang]);
  if (renderKey === moreInfo.key) return;
  moreInfo.key = renderKey;
  const domain = moreInfo.entityId.split(".")[0];
  const unavailable = st.state === "unavailable";
  let iconName = st.attributes.icon || "mdi:shape-outline";
  let stateText = "";
  let on = !unavailable;
  let actions = "";
  if (domain === "binary_sensor") {
    on = st.state === "on";
    iconName = on ? "mdi:lan-connect" : "mdi:lan-disconnect";
    stateText = t(on ? "connected" : "disconnected");
  } else if (domain === "lock") {
    const locked = st.state === "locked";
    stateText = unavailable ? t("unavailable") : t(locked ? "locked_state" : "unlocked_state");
    actions = `<ha-button appearance="${locked ? "accent" : "filled"}" data-service="lock.unlock" ${unavailable || !locked ? "disabled" : ""}><ha-icon slot="start" icon="mdi:lock-open-variant-outline"></ha-icon>${esc(t("unlock"))}</ha-button>
      <ha-button appearance="${locked ? "filled" : "accent"}" data-service="lock.lock" ${unavailable || locked ? "disabled" : ""}><ha-icon slot="start" icon="mdi:lock-outline"></ha-icon>${esc(t("lock"))}</ha-button>`;
  } else if (domain === "button") {
    stateText = unavailable
      ? t("unavailable")
      : st.state === "unknown"
        ? t("never")
        : t("last_pressed", { time: new Date(st.state).toLocaleTimeString(lang) });
    actions = `<ha-button data-service="button.press" ${unavailable ? "disabled" : ""}><ha-icon slot="start" icon="mdi:gesture-tap-button"></ha-icon>${esc(t("press"))}</ha-button>`;
  } else if (domain === "notify") {
    iconName = "mdi:message-badge-outline";
    stateText = unavailable ? t("unavailable") : "";
    actions = unavailable
      ? ""
      : `<div class="mi-field"><ha-input id="mi-message" label="${esc(t("message"))}" value="${esc(t("default_message"))}"></ha-input>
         <ha-button data-service="notify.send_message"><ha-icon slot="start" icon="mdi:send"></ha-icon>${esc(t("send"))}</ha-button></div>`;
  }
  dialog.querySelector(".more-info-title").textContent = st.attributes.friendly_name || moreInfo.entityId;
  dialog.querySelector(".more-info-sub").textContent = domain;
  dialog.querySelector(".more-info-body").innerHTML = `
    <div class="mi-state"><div class="mi-state-icon ${on ? "" : "off"}"><ha-icon icon="${esc(iconName)}"></ha-icon></div>
      ${stateText ? `<div class="mi-state-text">${esc(stateText)}</div>` : ""}</div>
    ${actions.startsWith("<div") ? actions : actions ? `<div class="mi-actions">${actions}</div>` : ""}
    <div class="mi-row"><span>${esc(t("entity_id"))}</span><code>${esc(moreInfo.entityId)}</code></div>`;
}

dialog.addEventListener("click", async (ev) => {
  const button = ev.target.closest("[data-service]");
  if (!button || button.disabled || !moreInfo) return;
  const [domain, service] = button.dataset.service.split(".");
  const data = { entity_id: moreInfo.entityId };
  if (domain === "notify") data.message = dialog.querySelector("#mi-message")?.value || t("default_message");
  button.setAttribute("loading", "");
  try {
    await callService(domain, service, data);
  } catch (err) {
    toast(err.message);
  } finally {
    button.removeAttribute("loading");
  }
});

// --- Toast ---

const toastEl = document.getElementById("toast");
let toastTimer;
function toast(text) {
  // An open dialog sits in the top layer; show the toast inside it to stay visible.
  const host = dialog.open ? dialog : document.body;
  if (toastEl.parentNode !== host) host.append(toastEl);
  toastEl.textContent = text;
  toastEl.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove("show"), 3800);
}

// --- Demo bar ---

const controls = document.getElementById("demo-controls");
const controlsToggle = document.getElementById("demo-controls-toggle");
function setControls(open) {
  controls.hidden = !open;
  controlsToggle.setAttribute("aria-expanded", String(open));
}
controlsToggle.addEventListener("click", () => setControls(controls.hidden));
document.addEventListener("click", (ev) => {
  if (!controls.hidden && !ev.composedPath().some((n) => n === controls || n === controlsToggle)) setControls(false);
});
document.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape" && !controls.hidden) setControls(false);
});

controls.addEventListener("click", (ev) => {
  const button = ev.target.closest("[data-demo]");
  if (!button) return;
  setControls(false);
  const action = button.dataset.demo;
  if (action === "reset") resetTo(sampleWorld);
  else if (action === "empty") resetTo(emptyWorld);
  else if (action === "toggle") {
    const device = world.devices.find((d) => d.id === "workstation") || world.devices.find((d) => d.lock);
    if (!device) toast(t("no_workstation"));
    else setConnected(device, !device.connected);
  } else if (action === "request") {
    const name = lang === "nl" ? "Telefoon van Sam" : "Sam's phone";
    if (world.requests.length) {
      toast(t("request_waiting", { name: world.requests[0].name }));
      return;
    }
    const request = { device_id: randomHex(16), name, type: "phone", host: "192.168.1.88", key: randomHex(4).toUpperCase() };
    // Like KDE Connect, the request expires after 30 seconds.
    request.timer = later(30000, () => {
      world.requests = world.requests.filter((r) => r !== request);
      changed();
    });
    world.requests.push(request);
    toast(t("request_toast", { name }));
    changed();
  }
});

function applyLanguage() {
  document.documentElement.lang = lang;
  for (const el of document.querySelectorAll("[data-lang]")) {
    el.setAttribute("aria-pressed", String(el.dataset.lang === lang));
  }
  for (const el of document.querySelectorAll("[data-i18n]")) el.textContent = t(el.dataset.i18n);
  for (const el of document.querySelectorAll("[data-fake] span:last-child")) {
    el.textContent = t(el.closest("[data-fake]").dataset.fake);
  }
  const theme = document.getElementById("theme-toggle");
  theme.setAttribute("aria-label", t("theme"));
  theme.title = t("theme");
}

for (const el of document.querySelectorAll("[data-lang]")) {
  el.addEventListener("click", () => {
    if (el.dataset.lang === lang) return;
    lang = el.dataset.lang;
    storage.set("kde-demo-lang", lang);
    applyLanguage();
    updateHass();
    // The panel picks its language when it draws; start it fresh.
    mountPanel();
  });
}

document.getElementById("theme-toggle").addEventListener("click", () => {
  const theme = darkMode() ? "light" : "dark";
  document.documentElement.dataset.theme = theme;
  storage.set("kde-demo-theme", theme);
  updateHass();
});

// --- Start ---

const savedTheme = storage.get("kde-demo-theme");
if (savedTheme === "light" || savedTheme === "dark") document.documentElement.dataset.theme = savedTheme;
applyLanguage();
sampleWorld();
updateHass();
await import("./kde-panel.js");
mountPanel();
