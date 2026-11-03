// KDE for Home Assistant: the sidebar page with the setup wizard and device settings.
// Plain web component, no build step. It is built from Home Assistant's own
// components (ha-card, ha-button, ha-alert, ha-switch, ...) and design tokens,
// following https://contributors.home-assistant.io/design/.

const DOMAIN = "kdeforhomeassistant";
const PANEL_PATH = "/kde-for-home-assistant";

const STRINGS = {
  en: {
    title: "KDE for Home Assistant",
    back: "Back",
    next: "Next",
    skip: "Skip",
    close: "Close",
    finish: "Finish",
    save: "Save",
    saved: "Saved",
    cancel: "Cancel",
    try_again: "Try again",
    step_of: "Step {step} of {total}",
    not_loaded:
      "KDE for Home Assistant is not running. Check the integration page for errors.",
    not_configured: "KDE for Home Assistant is not set up yet.",
    devices: "Devices",
    add_device: "Add device",
    connected: "Connected",
    not_connected: "Not connected",
    empty_title: "No devices yet",
    empty_text:
      "Add your computers and phones to lock them, run commands, and send notifications from Home Assistant.",
    settings: "Settings",
    ha_name: "Name of Home Assistant",
    ha_name_help: "The name your computers and phones show for Home Assistant.",
    rename: "Rename",
    request_title: "{name} wants to pair",
    request_text:
      "Check that {name} shows the same key, then select Accept. The request expires after 30 seconds.",
    accept: "Accept",
    decline: "Decline",
    request_expired: "The request expired. Select Pair on the device again.",
    // Wizard
    wizard_title: "Add device",
    step_name_title: "Name Home Assistant",
    step_name_text:
      "This is the name your computers and phones show for Home Assistant in KDE Connect.",
    name_label: "Name",
    name_invalid: "Enter a name.",
    step_prepare_title: "Open KDE Connect on your device",
    step_prepare_1: "Install KDE Connect on the computer or phone you want to add.",
    step_prepare_2: "Open KDE Connect on that device.",
    step_prepare_3: "Make sure the device is on the same network as Home Assistant.",
    step_prepare_install: "Download KDE Connect",
    step_prepare_firewall:
      "Using a firewall? Allow TCP and UDP ports 1714 to 1764 on the device.",
    step_choose_title: "Choose your device",
    step_choose_text: "These devices are running KDE Connect on your network.",
    searching: "Looking for devices…",
    reachable: "Ready to pair",
    not_reachable: "Waiting for a connection",
    manual_title: "Can't find your device?",
    manual_text: "Enter the IP address of the device. You can find it in your network settings.",
    ip_address: "IP address",
    connect: "Connect",
    manual_failed:
      "The device did not respond. Check that KDE Connect is open and that the address is right.",
    step_pair_title: "Accept the pairing request",
    pair_sending: "Sending the pairing request to {name}…",
    pair_text:
      "A notification appears on {name}. Check that it shows the key below, then select Accept.",
    pair_waiting: "Waiting for you to accept on {name}…",
    pair_incoming_text:
      "{name} sent a pairing request. Check that it shows the key below, then select Accept.",
    pair_error_timeout: "The request expired before it was accepted.",
    pair_error_rejected: "{name} declined the request.",
    pair_error_not_connected:
      "{name} is not connected to Home Assistant. Check that KDE Connect is open.",
    pair_error_other: "Pairing did not work. Try again.",
    paired: "{name} is paired.",
    step_commands_title: "Add buttons",
    step_commands_text:
      "Commands you set up in KDE Connect on {name} become buttons in Home Assistant, for example to lock the screen or shut down.",
    waiting_connect: "Waiting for {name} to connect…",
    no_commands: "No commands yet",
    no_commands_text: "Add a command on {name} and it shows up here right away.",
    add_command: "Add command on {name}",
    command_setup_opened:
      "The command settings opened on {name}. Add a command there with a name and the command to run.",
    step_scripts_title: "Share scripts",
    step_scripts_text:
      "Choose the Home Assistant scripts {name} may run. They show up under Run command in KDE Connect.",
    no_scripts: "No scripts yet",
    no_scripts_text: "Create a script in Home Assistant, then come back to share it.",
    create_script: "Create script",
    step_wake_title: "Turn on remotely",
    step_wake_text:
      "With Wake-on-LAN, Home Assistant can turn {name} on. Wake-on-LAN must be on in the BIOS or network settings of the device.",
    mac_label: "MAC address",
    mac_help: "For example AA:BB:CC:DD:EE:FF. Leave empty to turn this off.",
    mac_invalid: "Enter a MAC address like AA:BB:CC:DD:EE:FF.",
    step_done_title: "{name} is ready",
    step_done_text: "You can now use these entities in automations and dashboards.",
    // Device page
    status: "Status",
    ring: "Ring",
    lock: "Lock screen",
    unlock: "Unlock screen",
    turn_on: "Turn on",
    buttons: "Buttons",
    buttons_text: "Commands set up in KDE Connect on {name}.",
    run: "Run",
    scripts: "Shared scripts",
    wake: "Wake-on-LAN",
    remove: "Remove device",
    remove_text:
      "Removing {name} unpairs it and deletes its entities from Home Assistant.",
    remove_confirm: "Remove {name}?",
    unknown_device: "This device is no longer paired.",
    entities: "Entities",
    error: "Something went wrong: {error}",
  },
  nl: {
    title: "KDE for Home Assistant",
    back: "Terug",
    next: "Volgende",
    skip: "Overslaan",
    close: "Sluiten",
    finish: "Klaar",
    save: "Opslaan",
    saved: "Opgeslagen",
    cancel: "Annuleren",
    try_again: "Opnieuw proberen",
    step_of: "Stap {step} van {total}",
    not_loaded:
      "KDE for Home Assistant draait niet. Bekijk de integratiepagina voor fouten.",
    not_configured: "KDE for Home Assistant is nog niet ingesteld.",
    devices: "Apparaten",
    add_device: "Apparaat toevoegen",
    connected: "Verbonden",
    not_connected: "Niet verbonden",
    empty_title: "Nog geen apparaten",
    empty_text:
      "Voeg je computers en telefoons toe om ze vanuit Home Assistant te vergrendelen, opdrachten uit te voeren en meldingen te sturen.",
    settings: "Instellingen",
    ha_name: "Naam van Home Assistant",
    ha_name_help: "De naam die je computers en telefoons voor Home Assistant tonen.",
    rename: "Naam wijzigen",
    request_title: "{name} wil koppelen",
    request_text:
      "Controleer of {name} dezelfde sleutel toont en kies dan Accepteren. Het verzoek verloopt na 30 seconden.",
    accept: "Accepteren",
    decline: "Weigeren",
    request_expired: "Het verzoek is verlopen. Kies opnieuw Koppelen op het apparaat.",
    wizard_title: "Apparaat toevoegen",
    step_name_title: "Geef Home Assistant een naam",
    step_name_text:
      "Onder deze naam zien je computers en telefoons Home Assistant in KDE Connect.",
    name_label: "Naam",
    name_invalid: "Vul een naam in.",
    step_prepare_title: "Open KDE Connect op je apparaat",
    step_prepare_1: "Installeer KDE Connect op de computer of telefoon die je wilt toevoegen.",
    step_prepare_2: "Open KDE Connect op dat apparaat.",
    step_prepare_3: "Zorg dat het apparaat op hetzelfde netwerk zit als Home Assistant.",
    step_prepare_install: "KDE Connect downloaden",
    step_prepare_firewall:
      "Gebruik je een firewall? Sta dan TCP- en UDP-poort 1714 tot 1764 toe op het apparaat.",
    step_choose_title: "Kies je apparaat",
    step_choose_text: "Op deze apparaten in je netwerk draait KDE Connect.",
    searching: "Zoeken naar apparaten…",
    reachable: "Klaar om te koppelen",
    not_reachable: "Wacht op verbinding",
    manual_title: "Staat je apparaat er niet tussen?",
    manual_text: "Vul het IP-adres van het apparaat in. Je vindt het in de netwerkinstellingen.",
    ip_address: "IP-adres",
    connect: "Verbinden",
    manual_failed:
      "Het apparaat reageert niet. Controleer of KDE Connect open is en of het adres klopt.",
    step_pair_title: "Accepteer het koppelverzoek",
    pair_sending: "Koppelverzoek naar {name} sturen…",
    pair_text:
      "Er verschijnt een melding op {name}. Controleer of daar de sleutel hieronder staat en kies Accepteren.",
    pair_waiting: "Wachten tot je accepteert op {name}…",
    pair_incoming_text:
      "{name} heeft een koppelverzoek gestuurd. Controleer of daar de sleutel hieronder staat en kies Accepteren.",
    pair_error_timeout: "Het verzoek is verlopen voordat het werd geaccepteerd.",
    pair_error_rejected: "{name} heeft het verzoek geweigerd.",
    pair_error_not_connected:
      "{name} is niet verbonden met Home Assistant. Controleer of KDE Connect open is.",
    pair_error_other: "Koppelen is niet gelukt. Probeer het opnieuw.",
    paired: "{name} is gekoppeld.",
    step_commands_title: "Knoppen toevoegen",
    step_commands_text:
      "Opdrachten die je in KDE Connect op {name} instelt, worden knoppen in Home Assistant. Bijvoorbeeld om het scherm te vergrendelen of af te sluiten.",
    waiting_connect: "Wachten tot {name} verbinding maakt…",
    no_commands: "Nog geen opdrachten",
    no_commands_text: "Voeg een opdracht toe op {name}, dan verschijnt die hier meteen.",
    add_command: "Opdracht toevoegen op {name}",
    command_setup_opened:
      "De opdrachtinstellingen zijn geopend op {name}. Voeg daar een opdracht toe met een naam en de opdracht die moet worden uitgevoerd.",
    step_scripts_title: "Scripts delen",
    step_scripts_text:
      "Kies welke Home Assistant-scripts {name} mag uitvoeren. Ze verschijnen onder Opdracht uitvoeren in KDE Connect.",
    no_scripts: "Nog geen scripts",
    no_scripts_text: "Maak een script in Home Assistant en kom dan terug om het te delen.",
    create_script: "Script maken",
    step_wake_title: "Op afstand aanzetten",
    step_wake_text:
      "Met Wake-on-LAN kan Home Assistant {name} aanzetten. Wake-on-LAN moet aanstaan in het BIOS of de netwerkinstellingen van het apparaat.",
    mac_label: "MAC-adres",
    mac_help: "Bijvoorbeeld AA:BB:CC:DD:EE:FF. Laat leeg om dit uit te zetten.",
    mac_invalid: "Vul een MAC-adres in zoals AA:BB:CC:DD:EE:FF.",
    step_done_title: "{name} is klaar",
    step_done_text: "Je kunt deze entiteiten nu gebruiken in automatiseringen en dashboards.",
    status: "Status",
    ring: "Laten rinkelen",
    lock: "Scherm vergrendelen",
    unlock: "Scherm ontgrendelen",
    turn_on: "Aanzetten",
    buttons: "Knoppen",
    buttons_text: "Opdrachten die in KDE Connect op {name} zijn ingesteld.",
    run: "Uitvoeren",
    scripts: "Gedeelde scripts",
    wake: "Wake-on-LAN",
    remove: "Apparaat verwijderen",
    remove_text:
      "Als je {name} verwijdert, wordt de koppeling verbroken en worden de entiteiten uit Home Assistant verwijderd.",
    remove_confirm: "{name} verwijderen?",
    unknown_device: "Dit apparaat is niet meer gekoppeld.",
    entities: "Entiteiten",
    error: "Er ging iets mis: {error}",
  },
};

const TYPE_ICONS = {
  desktop: "mdi:monitor",
  laptop: "mdi:laptop",
  phone: "mdi:cellphone",
  smartphone: "mdi:cellphone",
  tablet: "mdi:tablet",
  tv: "mdi:television",
};

const MAC_RE = /^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$/;

const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );

const icon = (name, slot = "") =>
  `<ha-icon ${slot ? `slot="${slot}"` : ""} icon="${esc(name)}"></ha-icon>`;
const typeIcon = (type) => TYPE_ICONS[type] || "mdi:devices";

// Home Assistant only loads most of its components when a page needs them.
// Load the configuration panel once, which defines the form components we use.
const NEEDED = ["ha-card", "ha-button", "ha-alert", "ha-switch", "ha-spinner", "ha-icon-button"];
const textFieldTag = () =>
  customElements.get("ha-input") ? "ha-input" : "ha-textfield";

let componentsLoaded;
const loadComponents = () => {
  if (!componentsLoaded) componentsLoaded = doLoadComponents();
  return componentsLoaded;
};

async function doLoadComponents() {
  const ready = () =>
    NEEDED.every((tag) => customElements.get(tag)) &&
    (customElements.get("ha-input") || customElements.get("ha-textfield"));
  if (ready()) return;
  try {
    await customElements.whenDefined("partial-panel-resolver");
    const resolver = document.createElement("partial-panel-resolver");
    resolver.hass = { panels: [{ url_path: "tmp", component_name: "config" }] };
    resolver._updateRoutes();
    await resolver.routerOptions.routes.tmp.load();
    await customElements.whenDefined("ha-panel-config");
    const config = document.createElement("ha-panel-config");
    await config.routerOptions.routes.script.load();
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("KDE for Home Assistant: could not preload components", err);
  }
  await Promise.race([
    Promise.all(NEEDED.map((tag) => customElements.whenDefined(tag))),
    new Promise((resolve) => setTimeout(resolve, 5000)),
  ]);
}

class KdeForHomeAssistantPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._state = null;
    this._path = "";
    this._routeSet = false;
    this._stateJson = "";
    this._ready = false;
    this._wiz = null;
    this._notice = null;
    this._edit = {};
    this._busy = new Set();
    this._unsubs = {};
    this._scriptsKey = "";
    this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
    this.shadowRoot.addEventListener("input", (ev) => this._onInput(ev));
    this.shadowRoot.addEventListener("change", (ev) => this._onInput(ev));
    this.shadowRoot.addEventListener("keydown", (ev) => {
      const target = ev.composedPath().find((node) => node.dataset?.enter);
      if (ev.key === "Enter" && target) {
        ev.preventDefault();
        this._action(target.dataset.enter, target);
      }
    });
    loadComponents().then(() => {
      this._ready = true;
      this._render();
    });
  }

  // Properties Home Assistant sets on custom panels.

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    for (const el of this.shadowRoot.querySelectorAll("ha-menu-button")) el.hass = hass;
    if (first) {
      this._subscribe();
      this._render();
      return;
    }
    const key = this._scripts()
      .map((s) => s.entity_id + s.name)
      .join("|");
    const lock = Object.values(this._state?.devices || {})
      .map((d) => this._hass.states[d.entities?.screen_lock]?.state)
      .join("|");
    if (key + lock !== this._scriptsKey) {
      this._scriptsKey = key + lock;
      this._render();
    }
  }

  get hass() {
    return this._hass;
  }

  set narrow(value) {
    this._narrow = value;
    for (const el of this.shadowRoot.querySelectorAll("ha-menu-button")) el.narrow = value;
  }

  set route(route) {
    const before = this._path;
    const first = !this._routeSet;
    this._routeSet = true;
    this._route = route;
    this._path = route?.path || "";
    if (first || before !== this._path) this._routeChanged();
  }

  set panel(_panel) {}

  connectedCallback() {
    if (this._hass && !this._unsubs.state) this._subscribe();
  }

  disconnectedCallback() {
    for (const key of Object.keys(this._unsubs)) this._unsub(key);
  }

  // Helpers

  _t(key, vars = {}) {
    const lang = (this._hass?.language || "en").split("-")[0];
    const table = STRINGS[lang] || STRINGS.en;
    const text = table[key] ?? STRINGS.en[key] ?? key;
    return text.replace(/\{(\w+)\}/g, (_, name) => vars[name] ?? "");
  }

  _navigate(path, replace = false) {
    const url = PANEL_PATH + path;
    if (replace) history.replaceState(null, "", url);
    else history.pushState(null, "", url);
    window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace } }));
  }

  _ws(type, data = {}) {
    return this._hass.callWS({ type: `${DOMAIN}/${type}`, ...data });
  }

  async _sub(key, type, data, callback) {
    this._unsub(key);
    const promise = this._hass.connection.subscribeMessage(callback, {
      type: `${DOMAIN}/${type}`,
      ...data,
    });
    this._unsubs[key] = promise;
    try {
      await promise;
    } catch (err) {
      if (this._unsubs[key] === promise) delete this._unsubs[key];
      throw err;
    }
  }

  _unsub(key) {
    const promise = this._unsubs[key];
    if (!promise) return;
    delete this._unsubs[key];
    promise.then((unsub) => unsub()).catch(() => {});
  }

  _subscribe() {
    this._sub("state", "subscribe", {}, (state) => {
      const json = JSON.stringify(state);
      if (json === this._stateJson) return;
      this._stateJson = json;
      this._state = state;
      this._stateChanged();
    }).catch((err) => {
      this._state = { configured: false, error: err.message };
      this._render();
    });
  }

  _scripts() {
    if (!this._hass) return [];
    return Object.entries(this._hass.states)
      .filter(([entityId]) => entityId.startsWith("script."))
      .map(([entityId, s]) => ({
        entity_id: entityId,
        name: s.attributes?.friendly_name || entityId,
      }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  _device(id) {
    return this._state?.devices?.find((d) => d.id === id);
  }

  _view() {
    if (this._path.startsWith("/add")) return { name: "wizard" };
    const match = this._path.match(/^\/device\/([^/]+)/);
    if (match) return { name: "device", id: decodeURIComponent(match[1]) };
    return { name: "overview" };
  }

  // Reacting to changes

  _routeChanged() {
    this._notice = null;
    this._edit = {};
    if (this._view().name !== "wizard" && this._wiz) this._stopWizard();
    if (this._state) this._stateChanged();
  }

  _stateChanged() {
    const state = this._state;
    const view = this._view();
    if (!this._routeSet) {
      this._render();
      return;
    }
    // First visit without devices: go straight to the wizard.
    if (
      !this._autoStarted &&
      state.configured &&
      state.loaded &&
      !state.devices.length &&
      view.name === "overview"
    ) {
      this._autoStarted = true;
      this._navigate("/add", true);
      return;
    }
    this._autoStarted = true;
    if (view.name === "wizard" && !this._wiz) this._startWizard();
    if (this._wiz) this._wizardStateChanged();
    this._render();
  }

  // Wizard

  _startWizard() {
    if (!this._state) return;
    const firstRun = !this._state.devices?.length;
    this._wiz = {
      firstRun,
      step: firstRun ? "name" : "prepare",
      name: this._state.name || this._state.default_name || "",
      selected: null,
      manualHost: "",
      manualOpen: false,
      pair: null,
      subentryId: null,
      deviceName: "",
      deviceType: "unknown",
      scripts: [],
      mac: "",
      error: null,
    };
  }

  _stopWizard() {
    this._unsub("discover");
    this._unsub("pair");
    this._wiz = null;
  }

  _steps() {
    const wiz = this._wiz;
    const steps = [];
    if (wiz.firstRun) steps.push("name");
    steps.push("prepare", "choose", "pair", "commands", "scripts");
    if (["desktop", "laptop", "unknown"].includes(wiz.deviceType)) steps.push("wake");
    steps.push("done");
    return steps;
  }

  _goStep(step) {
    const wiz = this._wiz;
    wiz.step = step;
    wiz.error = null;
    this._notice = null;
    if (step === "choose") {
      this._sub("discover", "discover", {}, () => {}).catch(() => {});
    } else {
      this._unsub("discover");
    }
    const device = this._device(wiz.subentryId);
    if (step === "scripts" && device) wiz.scripts = [...device.scripts];
    if (step === "wake" && device) wiz.mac = device.mac || "";
    this._render();
    this.scrollTo?.(0, 0);
  }

  _wizardStateChanged() {
    const wiz = this._wiz;
    const state = this._state;
    // A device asked to pair while we are waiting for one: handle it here.
    if (["prepare", "choose"].includes(wiz.step) && state.requests?.length) {
      const request = state.requests[0];
      wiz.pair = { mode: "incoming", deviceId: request.device_id, key: request.key };
      wiz.deviceName = request.name;
      wiz.deviceType = request.type;
      this._goStep("pair");
      return;
    }
    if (wiz.step === "pair" && wiz.pair?.mode === "incoming" && !wiz.pair.done) {
      const still = state.requests?.find((r) => r.device_id === wiz.pair.deviceId);
      if (!still && !this._busy.has("accept")) wiz.pair.expired = true;
    }
    if (wiz.subentryId) {
      const device = this._device(wiz.subentryId);
      if (device) {
        wiz.deviceName = device.name;
        wiz.deviceType = device.type;
      }
    }
  }

  _startPair(deviceId) {
    const wiz = this._wiz;
    const found = this._state.discovered.find((d) => d.device_id === deviceId);
    wiz.deviceName = found?.name || wiz.deviceName || deviceId;
    wiz.deviceType = found?.type || wiz.deviceType;
    wiz.pair = { mode: "outgoing", deviceId, key: null, error: null };
    this._goStep("pair");
    this._sub("pair", "pair", { device_id: deviceId }, (event) => {
      if (!this._wiz || this._wiz.pair?.deviceId !== deviceId) return;
      if (event.key) wiz.pair.key = event.key;
      if (event.error) wiz.pair.error = event.error;
      if (event.paired) this._paired(event.paired);
      this._render();
    }).catch((err) => {
      wiz.pair.error = err.code || "other";
      this._render();
    });
  }

  _paired(subentryId) {
    const wiz = this._wiz;
    wiz.pair.done = true;
    wiz.subentryId = subentryId;
    this._unsub("pair");
    this._goStep("commands");
  }

  async _acceptIncoming() {
    const wiz = this._wiz;
    this._busy.add("accept");
    this._render();
    try {
      const result = await this._ws("accept", { device_id: wiz.pair.deviceId });
      this._paired(result.id);
    } catch (err) {
      wiz.pair.expired = true;
    } finally {
      this._busy.delete("accept");
      this._render();
    }
  }

  async _wizardNext() {
    const wiz = this._wiz;
    const steps = this._steps();
    const next = steps[steps.indexOf(wiz.step) + 1];
    try {
      if (wiz.step === "name") {
        const name = wiz.name.trim();
        if (!name) {
          wiz.error = this._t("name_invalid");
          this._render();
          return;
        }
        if (name !== this._state.name) {
          this._busy.add("next");
          this._render();
          await this._ws("set_name", { name });
        }
      } else if (wiz.step === "choose") {
        if (wiz.selected) this._startPair(wiz.selected);
        return;
      } else if (wiz.step === "scripts") {
        this._busy.add("next");
        this._render();
        await this._ws("update_device", { subentry_id: wiz.subentryId, scripts: wiz.scripts });
      } else if (wiz.step === "wake") {
        const mac = wiz.mac.trim();
        if (mac && !MAC_RE.test(mac)) {
          wiz.error = this._t("mac_invalid");
          this._render();
          return;
        }
        this._busy.add("next");
        this._render();
        await this._ws("update_device", { subentry_id: wiz.subentryId, mac: mac || null });
      } else if (wiz.step === "done") {
        const id = wiz.subentryId;
        this._stopWizard();
        this._navigate(id ? `/device/${encodeURIComponent(id)}` : "");
        return;
      }
    } catch (err) {
      wiz.error = this._t("error", { error: err.message || err.code });
      this._render();
      return;
    } finally {
      this._busy.delete("next");
    }
    if (next) this._goStep(next);
  }

  _wizardBack() {
    const wiz = this._wiz;
    const steps = this._steps();
    if (wiz.step === "pair") {
      this._unsub("pair");
      if (wiz.pair?.mode === "incoming" && !wiz.pair.done && !wiz.pair.expired) {
        this._ws("decline", { device_id: wiz.pair.deviceId }).catch(() => {});
      }
      wiz.pair = null;
      this._goStep("choose");
      return;
    }
    const index = steps.indexOf(wiz.step);
    if (index > 0) this._goStep(steps[index - 1]);
  }

  async _connectManual() {
    const wiz = this._wiz;
    const host = wiz.manualHost.trim();
    if (!host) return;
    wiz.error = null;
    this._busy.add("manual");
    this._render();
    try {
      const result = await this._ws("connect", { host });
      wiz.selected = result.device_id;
      this._startPair(result.device_id);
    } catch (err) {
      wiz.error = this._t("manual_failed");
    } finally {
      this._busy.delete("manual");
      this._render();
    }
  }

  // Events

  _onInput(ev) {
    const target = ev.composedPath().find((node) => node.dataset?.field);
    if (!target) return;
    const field = target.dataset.field;
    if (field.startsWith("wiz.")) {
      this._wiz[field.slice(4)] = target.value ?? "";
    } else if (field.startsWith("edit.")) {
      this._edit[field.slice(5)] = target.value ?? "";
    } else if (ev.type !== "change") {
      return;
    } else if (field === "wizScript") {
      const set = new Set(this._wiz.scripts);
      target.checked ? set.add(target.dataset.value) : set.delete(target.dataset.value);
      this._wiz.scripts = [...set];
    } else if (field === "deviceScript") {
      this._toggleDeviceScript(target.dataset.id, target.dataset.value, target.checked);
    }
  }

  _onClick(ev) {
    const el = ev.composedPath().find((node) => node.dataset?.action);
    if (!el || el.disabled || el.hasAttribute?.("loading")) return;
    ev.preventDefault();
    this._action(el.dataset.action, el);
  }

  async _action(action, el) {
    const data = el.dataset;
    switch (action) {
      case "add":
        this._navigate("/add");
        return;
      case "home":
        this._navigate("");
        return;
      case "device":
        this._navigate(`/device/${encodeURIComponent(data.id)}`);
        return;
      case "pick":
        this._wiz.selected = data.id;
        this._render();
        return;
      case "wiz-close":
        if (this._wiz?.step === "pair") this._wizardBack();
        this._stopWizard();
        this._navigate("");
        return;
      case "wiz-next":
        this._wizardNext();
        return;
      case "wiz-back":
        this._wizardBack();
        return;
      case "wiz-skip": {
        const steps = this._steps();
        this._goStep(steps[steps.indexOf(this._wiz.step) + 1]);
        return;
      }
      case "wiz-retry":
        this._startPair(this._wiz.pair.deviceId);
        return;
      case "wiz-accept":
        this._acceptIncoming();
        return;
      case "wiz-decline":
        this._wizardBack();
        return;
      case "manual":
        this._connectManual();
        return;
      case "manual-toggle":
        this._wiz.manualOpen = !this._wiz.manualOpen;
        this._render();
        if (this._wiz.manualOpen) this._focus("#wiz-host");
        return;
      case "accept":
      case "decline":
        await this._run(action + data.id, async () => {
          const result = await this._ws(action, { device_id: data.id });
          if (action === "accept" && result?.id) {
            this._navigate(`/device/${encodeURIComponent(result.id)}`);
          }
        });
        return;
      case "rename":
        this._edit.renaming = true;
        this._edit.name = this._state.name;
        this._render();
        this._focus("#name-input");
        return;
      case "rename-cancel":
        this._edit = {};
        this._render();
        return;
      case "rename-save":
        await this._run("rename", async () => {
          await this._ws("set_name", { name: this._edit.name || "" });
          this._edit = {};
        });
        return;
      case "command-setup":
        await this._run("setup" + data.id, async () => {
          await this._ws("command_setup", { subentry_id: data.id });
          this._notice = {
            type: "info",
            text: this._t("command_setup_opened", { name: data.name }),
          };
        });
        return;
      case "press":
        await this._run("press" + data.entity, () =>
          this._hass.callService("button", "press", { entity_id: data.entity })
        );
        return;
      case "lock":
      case "unlock":
        await this._run(action, () =>
          this._hass.callService("lock", action, { entity_id: data.entity })
        );
        return;
      case "more-info":
        this.dispatchEvent(
          new CustomEvent("hass-more-info", {
            detail: { entityId: data.entity },
            bubbles: true,
            composed: true,
          })
        );
        return;
      case "mac-save": {
        const mac = (this._edit.mac ?? "").trim();
        if (mac && !MAC_RE.test(mac)) {
          this._notice = { type: "error", text: this._t("mac_invalid") };
          this._render();
          return;
        }
        await this._run("mac", async () => {
          await this._ws("update_device", { subentry_id: data.id, mac: mac || null });
          this._notice = { type: "success", text: this._t("saved") };
        });
        return;
      }
      case "remove":
        this._edit.removing = true;
        this._render();
        return;
      case "remove-cancel":
        this._edit.removing = false;
        this._render();
        return;
      case "remove-confirm":
        await this._run("remove", async () => {
          await this._ws("remove_device", { subentry_id: data.id });
          this._navigate("", true);
        });
        return;
    }
  }

  async _toggleDeviceScript(id, entityId, checked) {
    const device = this._device(id);
    if (!device) return;
    const set = new Set(device.scripts);
    checked ? set.add(entityId) : set.delete(entityId);
    await this._run("scripts", () =>
      this._ws("update_device", { subentry_id: id, scripts: [...set] })
    );
  }

  async _run(key, fn) {
    this._busy.add(key);
    this._render();
    try {
      await fn();
    } catch (err) {
      this._notice = {
        type: "error",
        text:
          err?.code === "not_connected"
            ? this._t("not_connected")
            : this._t("error", { error: err?.message || err?.code || err }),
      };
    } finally {
      this._busy.delete(key);
      this._render();
    }
  }

  // Rendering

  _render() {
    if (!this._hass) return;
    const active = this.shadowRoot.activeElement;
    const focus = active?.id ? { id: active.id } : null;
    const view = this._view();
    let body;
    if (!this._state || !this._ready) body = this._loading();
    else if (!this._state.configured) body = this._message(this._t("not_configured"));
    else if (view.name === "wizard" && this._wiz) body = this._renderWizard();
    else if (view.name === "device") body = this._renderDevice(view.id);
    else body = this._renderOverview();
    this.shadowRoot.innerHTML = `<style>${STYLES}</style>${body}`;
    for (const el of this.shadowRoot.querySelectorAll("ha-menu-button")) {
      el.hass = this._hass;
      el.narrow = this._narrow;
    }
    if (focus) {
      const el = this.shadowRoot.getElementById(focus.id);
      if (el) {
        // Wait for the component to render before moving the cursor back.
        customElements.whenDefined(el.localName).then(() => el.updateComplete).then(() => {
          el.focus();
          const length = (el.value || "").length;
          try {
            el.setSelectionRange?.(length, length);
          } catch (_err) {
            // Not a text field.
          }
        });
      }
    }
  }

  async _focus(selector) {
    const el = this.shadowRoot.querySelector(selector);
    if (!el) return;
    await customElements.whenDefined(el.localName);
    await el.updateComplete;
    el.focus();
  }

  // Building blocks, all Home Assistant components.

  _toolbar(title, { back = false, close = false } = {}) {
    const lead = close
      ? `<ha-icon-button data-action="wiz-close" label="${esc(this._t("close"))}">${icon("mdi:close")}</ha-icon-button>`
      : back
        ? `<ha-icon-button data-action="home" label="${esc(this._t("back"))}">${icon("mdi:arrow-left")}</ha-icon-button>`
        : `<ha-menu-button></ha-menu-button>`;
    return `<div class="toolbar">${lead}<div class="main-title">${esc(title)}</div></div>`;
  }

  _loading() {
    return `${this._toolbar(this._t("title"))}<div class="content center"><ha-spinner></ha-spinner></div>`;
  }

  _message(text) {
    return `${this._toolbar(this._t("title"))}<div class="content"><div class="container">${this._alert("warning", esc(text))}</div></div>`;
  }

  _alert(type, text, { title = "", actions = "" } = {}) {
    return `<ha-alert alert-type="${type}" ${title ? `title="${esc(title)}"` : ""}>${text}${
      actions ? `<div slot="action" class="alert-actions">${actions}</div>` : ""
    }</ha-alert>`;
  }

  _button(label, action, { appearance = "accent", variant = "brand", busy = false, disabled = false, data = {}, iconName = null, size = "" } = {}) {
    const attrs = Object.entries(data)
      .map(([k, v]) => `data-${k}="${esc(v)}"`)
      .join(" ");
    return `<ha-button appearance="${appearance}" variant="${variant}" ${size ? `size="${size}"` : ""} data-action="${action}" ${attrs} ${disabled ? "disabled" : ""} ${busy ? "loading" : ""}>${
      iconName ? icon(iconName, "start") : ""
    }${esc(label)}</ha-button>`;
  }

  _link(label, href, { iconName = null, newTab = false } = {}) {
    return `<a class="button-link" href="${esc(href)}" ${newTab ? 'target="_blank" rel="noreferrer"' : ""}><ha-button appearance="outlined" variant="brand">${
      iconName ? icon(iconName, "start") : ""
    }${esc(label)}</ha-button></a>`;
  }

  _textField({ id, field, label, value, hint = "", placeholder = "", enter = "", data = {}, maxlength = 0, mono = false }) {
    const tag = textFieldTag();
    const attrs = Object.entries(data)
      .map(([k, v]) => `data-${k}="${esc(v)}"`)
      .join(" ");
    const help =
      tag === "ha-input"
        ? hint ? `hint="${esc(hint)}"` : ""
        : hint ? `helper="${esc(hint)}" helperpersistent` : "";
    return `<${tag} id="${id}" class="text-field ${mono ? "mono-field" : ""}" data-field="${field}" ${enter ? `data-enter="${enter}"` : ""} ${attrs}
      label="${esc(label)}" value="${esc(value)}" ${help} ${placeholder ? `placeholder="${esc(placeholder)}"` : ""}
      ${maxlength ? `maxlength="${maxlength}"` : ""} autocomplete="off"></${tag}>`;
  }

  _notices() {
    return this._notice ? this._alert(this._notice.type, esc(this._notice.text)) : "";
  }

  _status(connected) {
    return `<span class="status"><span class="dot ${connected ? "on" : ""}"></span>${esc(this._t(connected ? "connected" : "not_connected"))}</span>`;
  }

  _row({ iconName = null, headline, supporting = "", supportingMono = false, end = "", action = "", data = {}, selected = false }) {
    const attrs = Object.entries(data)
      .map(([k, v]) => `data-${k}="${esc(v)}"`)
      .join(" ");
    const tag = action ? "button" : "div";
    return `<${tag} class="row ${action ? "clickable" : ""} ${selected ? "selected" : ""}" ${action ? `data-action="${action}" type="button"` : ""} ${attrs}>
      ${iconName ? `<span class="row-icon">${icon(iconName)}</span>` : ""}
      <span class="row-text"><span class="headline">${esc(headline)}</span>${
        supporting ? `<span class="supporting ${supportingMono ? "mono" : ""}">${supporting}</span>` : ""
      }</span>${end ? `<span class="row-end">${end}</span>` : ""}</${tag}>`;
  }

  _requests() {
    return (this._state.requests || [])
      .map((r) =>
        this._alert(
          "info",
          `${esc(this._t("request_text", { name: r.name }))}<div class="key">${esc(r.key)}</div>`,
          {
            title: this._t("request_title", { name: r.name }),
            actions:
              this._button(this._t("decline"), "decline", { appearance: "plain", data: { id: r.device_id }, busy: this._busy.has("decline" + r.device_id) }) +
              this._button(this._t("accept"), "accept", { data: { id: r.device_id }, busy: this._busy.has("accept" + r.device_id) }),
          }
        )
      )
      .join("");
  }

  _renderOverview() {
    const state = this._state;
    const rows = state.devices
      .map((d) =>
        this._row({
          iconName: typeIcon(d.type),
          headline: d.name,
          supporting: this._status(d.connected),
          end: icon("mdi:chevron-right"),
          action: "device",
          data: { id: d.id },
        })
      )
      .join("");
    const devices = state.devices.length
      ? `<ha-card header="${esc(this._t("devices"))}"><div class="list">${rows}</div>
         <div class="card-actions">${this._button(this._t("add_device"), "add", { iconName: "mdi:plus", disabled: !state.loaded })}</div></ha-card>`
      : `<ha-card><div class="empty"><div class="empty-icon">${icon("mdi:monitor-cellphone")}</div>
         <h2>${esc(this._t("empty_title"))}</h2><p>${esc(this._t("empty_text"))}</p>
         ${this._button(this._t("add_device"), "add", { iconName: "mdi:plus", disabled: !state.loaded })}</div></ha-card>`;
    const nameRow = this._edit.renaming
      ? `<div class="card-content">${this._textField({ id: "name-input", field: "edit.name", enter: "rename-save", label: this._t("ha_name"), value: this._edit.name, hint: this._t("ha_name_help"), maxlength: 32 })}</div>
         <div class="card-actions">${this._button(this._t("cancel"), "rename-cancel", { appearance: "plain" })}${this._button(this._t("save"), "rename-save", { busy: this._busy.has("rename") })}</div>`
      : this._row({
          iconName: "mdi:home-assistant",
          headline: state.name,
          supporting: esc(this._t("ha_name_help")),
          end: this._button(this._t("rename"), "rename", { appearance: "plain" }),
        });
    return `${this._toolbar(this._t("title"))}
      <div class="content"><div class="container">
        ${state.loaded ? "" : this._alert("warning", esc(this._t("not_loaded")))}
        ${this._requests()}${this._notices()}${devices}
        <ha-card header="${esc(this._t("settings"))}">${nameRow}</ha-card>
      </div></div>`;
  }

  _renderDevice(id) {
    const d = this._device(id);
    if (!d) {
      return `${this._toolbar(this._t("title"), { back: true })}<div class="content"><div class="container">${this._alert("warning", esc(this._t("unknown_device")))}</div></div>`;
    }
    const ent = d.entities;
    const locked = ent.screen_lock && this._hass.states[ent.screen_lock]?.state === "locked";
    const status = `<ha-card>
      <div class="device-head"><span class="big-icon">${icon(typeIcon(d.type))}</span>
      <div class="device-text"><div class="device-name">${esc(d.name)}</div>${this._status(d.connected)}</div></div>
      <div class="card-actions start">
        ${ent.ring ? this._button(this._t("ring"), "press", { appearance: "filled", iconName: "mdi:bell-ring-outline", data: { entity: ent.ring }, disabled: !d.connected, busy: this._busy.has("press" + ent.ring) }) : ""}
        ${ent.screen_lock ? this._button(this._t(locked ? "unlock" : "lock"), locked ? "unlock" : "lock", { appearance: "filled", iconName: locked ? "mdi:lock-open-variant-outline" : "mdi:lock-outline", data: { entity: ent.screen_lock }, disabled: !d.connected, busy: this._busy.has("lock") || this._busy.has("unlock") }) : ""}
        ${ent.wake ? this._button(this._t("turn_on"), "press", { appearance: "filled", iconName: "mdi:power", data: { entity: ent.wake }, busy: this._busy.has("press" + ent.wake) }) : ""}
      </div></ha-card>`;

    const commands = d.commands.length
      ? `<div class="list">${d.commands
          .map((c) =>
            this._row({
              iconName: "mdi:gesture-tap-button",
              headline: c.name,
              supporting: c.command ? esc(c.command) : "",
              supportingMono: true,
              end: c.entity_id ? this._button(this._t("run"), "press", { appearance: "plain", data: { entity: c.entity_id }, disabled: !d.connected, busy: this._busy.has("press" + c.entity_id) }) : "",
            })
          )
          .join("")}</div>`
      : `<div class="inline-empty">${esc(this._t("no_commands_text", { name: d.name }))}</div>`;

    const scripts = this._scripts();
    const scriptList = scripts.length
      ? `<div class="list">${scripts
          .map((s) =>
            this._row({
              iconName: "mdi:script-text-outline",
              headline: s.name,
              supporting: esc(s.entity_id),
              supportingMono: true,
              end: `<ha-switch data-field="deviceScript" data-id="${esc(d.id)}" data-value="${esc(s.entity_id)}" ${d.scripts.includes(s.entity_id) ? "checked" : ""} ${this._busy.has("scripts") ? "disabled" : ""}></ha-switch>`,
            })
          )
          .join("")}</div>`
      : `<div class="inline-empty">${esc(this._t("no_scripts_text"))}</div>`;

    const removing = this._edit.removing
      ? `<div class="card-content">${this._alert("warning", esc(this._t("remove_confirm", { name: d.name })), {
          actions:
            this._button(this._t("cancel"), "remove-cancel", { appearance: "plain" }) +
            this._button(this._t("remove"), "remove-confirm", { variant: "danger", data: { id: d.id }, busy: this._busy.has("remove") }),
        })}</div>`
      : `<div class="card-actions">${this._button(this._t("remove"), "remove", { appearance: "plain", variant: "danger", iconName: "mdi:delete-outline" })}</div>`;

    const entityRows = Object.values(ent)
      .concat(d.commands.map((c) => c.entity_id).filter(Boolean))
      .map((entityId) => {
        const st = this._hass.states[entityId];
        return this._row({
          iconName: st?.attributes?.icon || this._domainIcon(entityId),
          headline: st?.attributes?.friendly_name || entityId,
          supporting: esc(entityId),
          supportingMono: true,
          end: icon("mdi:chevron-right"),
          action: "more-info",
          data: { entity: entityId },
        });
      })
      .join("");

    return `${this._toolbar(d.name, { back: true })}
      <div class="content"><div class="container">
        ${this._requests()}${this._notices()}${status}
        <ha-card header="${esc(this._t("buttons"))}">
          <p class="card-text">${esc(this._t("buttons_text", { name: d.name }))}</p>${commands}
          <div class="card-actions">${this._button(this._t("add_command", { name: d.name }), "command-setup", { appearance: "outlined", iconName: "mdi:plus", data: { id: d.id, name: d.name }, disabled: !d.connected, busy: this._busy.has("setup" + d.id) })}</div></ha-card>
        <ha-card header="${esc(this._t("scripts"))}">
          <p class="card-text">${esc(this._t("step_scripts_text", { name: d.name }))}</p>${scriptList}
          <div class="card-actions">${this._link(this._t("create_script"), "/config/script/edit/new", { iconName: "mdi:plus" })}</div></ha-card>
        <ha-card header="${esc(this._t("wake"))}">
          <p class="card-text">${esc(this._t("step_wake_text", { name: d.name }))}</p>
          <div class="card-content">${this._textField({ id: "mac-input", field: "edit.mac", enter: "mac-save", data: { id: d.id }, label: this._t("mac_label"), value: this._edit.mac ?? d.mac ?? "", hint: this._t("mac_help"), placeholder: "AA:BB:CC:DD:EE:FF", mono: true })}</div>
          <div class="card-actions">${this._button(this._t("save"), "mac-save", { data: { id: d.id }, busy: this._busy.has("mac") })}</div></ha-card>
        ${entityRows ? `<ha-card header="${esc(this._t("entities"))}"><div class="list">${entityRows}</div></ha-card>` : ""}
        <ha-card header="${esc(this._t("remove"))}">
          <p class="card-text">${esc(this._t("remove_text", { name: d.name }))}</p>${removing}</ha-card>
      </div></div>`;
  }

  _domainIcon(entityId) {
    const domain = entityId.split(".")[0];
    return (
      {
        binary_sensor: "mdi:lan-connect",
        lock: "mdi:monitor-lock",
        notify: "mdi:message-badge-outline",
        button: "mdi:gesture-tap-button",
      }[domain] || "mdi:shape-outline"
    );
  }

  _renderWizard() {
    const wiz = this._wiz;
    const steps = this._steps();
    const index = Math.max(0, steps.indexOf(wiz.step));
    const progress = ((index + 1) / steps.length) * 100;
    const name = wiz.deviceName;
    let title = "";
    let content = "";
    const next = { label: this._t("next"), disabled: false, show: true };
    let back = index > 0 && !["commands", "done"].includes(wiz.step);
    let skip = false;

    switch (wiz.step) {
      case "name":
        title = this._t("step_name_title");
        content = `<p>${esc(this._t("step_name_text"))}</p>
          ${this._textField({ id: "wiz-name", field: "wiz.name", enter: "wiz-next", label: this._t("name_label"), value: wiz.name, maxlength: 32 })}`;
        break;
      case "prepare":
        title = this._t("step_prepare_title");
        content = `<ol class="steps">
            <li>${esc(this._t("step_prepare_1"))}</li>
            <li>${esc(this._t("step_prepare_2"))}</li>
            <li>${esc(this._t("step_prepare_3"))}</li></ol>
          ${this._link(this._t("step_prepare_install"), "https://kdeconnect.kde.org/download.html", { iconName: "mdi:open-in-new", newTab: true })}
          <p class="hint">${esc(this._t("step_prepare_firewall"))}</p>`;
        break;
      case "choose": {
        title = this._t("step_choose_title");
        const found = this._state.discovered;
        const list = found.length
          ? `<div class="list bordered" role="radiogroup">${found
              .map((d) =>
                this._row({
                  iconName: typeIcon(d.type),
                  headline: d.name,
                  supporting: `${d.host ? esc(d.host) + " · " : ""}${esc(this._t(d.reachable ? "reachable" : "not_reachable"))}`,
                  end: icon(wiz.selected === d.device_id ? "mdi:radiobox-marked" : "mdi:radiobox-blank"),
                  action: "pick",
                  data: { id: d.device_id },
                  selected: wiz.selected === d.device_id,
                })
              )
              .join("")}</div>`
          : "";
        content = `<p>${esc(this._t("step_choose_text"))}</p>${list}
          <div class="searching"><ha-spinner size="tiny"></ha-spinner>${esc(this._t("searching"))}</div>
          <div class="manual">
            <button type="button" class="disclosure" data-action="manual-toggle" aria-expanded="${wiz.manualOpen}">
              ${icon(wiz.manualOpen ? "mdi:chevron-up" : "mdi:chevron-down")}${esc(this._t("manual_title"))}</button>
            ${wiz.manualOpen ? `<p class="hint">${esc(this._t("manual_text"))}</p>
              <div class="inline-form">${this._textField({ id: "wiz-host", field: "wiz.manualHost", enter: "manual", label: this._t("ip_address"), value: wiz.manualHost, placeholder: "192.168.1.20" })}
              ${this._button(this._t("connect"), "manual", { appearance: "outlined", busy: this._busy.has("manual") })}</div>` : ""}
          </div>`;
        next.disabled = !wiz.selected;
        break;
      }
      case "pair": {
        title = this._t("step_pair_title");
        const pair = wiz.pair || {};
        next.show = false;
        if (pair.mode === "incoming") {
          if (pair.expired) {
            content = this._alert("warning", esc(this._t("request_expired")));
          } else {
            content = `<p>${esc(this._t("pair_incoming_text", { name }))}</p>
              <div class="key big">${esc(pair.key)}</div>
              <div class="actions-row">${this._button(this._t("decline"), "wiz-decline", { appearance: "plain" })}${this._button(this._t("accept"), "wiz-accept", { busy: this._busy.has("accept") })}</div>`;
          }
        } else if (pair.error) {
          const key = {
            timeout: "pair_error_timeout",
            rejected: "pair_error_rejected",
            not_connected: "pair_error_not_connected",
          }[pair.error] || "pair_error_other";
          content = `${this._alert("error", esc(this._t(key, { name })))}
            <div class="actions-row">${this._button(this._t("try_again"), "wiz-retry", { appearance: "filled", iconName: "mdi:refresh" })}</div>`;
        } else if (!pair.key) {
          content = `<div class="waiting"><ha-spinner size="small"></ha-spinner><p>${esc(this._t("pair_sending", { name }))}</p></div>`;
        } else {
          content = `<p>${esc(this._t("pair_text", { name }))}</p>
            <div class="key big">${esc(pair.key)}</div>
            <div class="waiting"><ha-spinner size="tiny"></ha-spinner><p>${esc(this._t("pair_waiting", { name }))}</p></div>`;
        }
        break;
      }
      case "commands": {
        title = this._t("step_commands_title");
        const d = this._device(wiz.subentryId);
        const connected = d?.connected;
        let list;
        if (!connected) {
          list = `<div class="waiting"><ha-spinner size="tiny"></ha-spinner><p>${esc(this._t("waiting_connect", { name }))}</p></div>`;
        } else if (!d.commands.length) {
          list = `<div class="inline-empty bordered"><b>${esc(this._t("no_commands"))}</b><br>${esc(this._t("no_commands_text", { name }))}</div>`;
        } else {
          list = `<div class="list bordered">${d.commands
            .map((c) =>
              this._row({
                iconName: "mdi:gesture-tap-button",
                headline: c.name,
                supporting: c.command ? esc(c.command) : "",
                supportingMono: true,
                end: icon("mdi:check"),
              })
            )
            .join("")}</div>`;
        }
        content = `${this._alert("success", esc(this._t("paired", { name })))}
          <p>${esc(this._t("step_commands_text", { name }))}</p>${this._notices()}${list}
          <div class="actions-row start">${this._button(this._t("add_command", { name }), "command-setup", { appearance: "outlined", iconName: "mdi:plus", data: { id: wiz.subentryId, name }, disabled: !connected, busy: this._busy.has("setup" + wiz.subentryId) })}</div>`;
        break;
      }
      case "scripts": {
        title = this._t("step_scripts_title");
        const scripts = this._scripts();
        content = `<p>${esc(this._t("step_scripts_text", { name }))}</p>${
          scripts.length
            ? `<div class="list bordered">${scripts
                .map((s) =>
                  this._row({
                    iconName: "mdi:script-text-outline",
                    headline: s.name,
                    supporting: esc(s.entity_id),
                    supportingMono: true,
                    end: `<ha-switch data-field="wizScript" data-value="${esc(s.entity_id)}" ${wiz.scripts.includes(s.entity_id) ? "checked" : ""}></ha-switch>`,
                  })
                )
                .join("")}</div>`
            : `<div class="inline-empty bordered"><b>${esc(this._t("no_scripts"))}</b><br>${esc(this._t("no_scripts_text"))}</div>`
        }<div class="actions-row start">${this._link(this._t("create_script"), "/config/script/edit/new", { iconName: "mdi:plus", newTab: true })}</div>`;
        break;
      }
      case "wake":
        title = this._t("step_wake_title");
        skip = true;
        content = `<p>${esc(this._t("step_wake_text", { name }))}</p>
          ${this._textField({ id: "wiz-mac", field: "wiz.mac", enter: "wiz-next", label: this._t("mac_label"), value: wiz.mac, hint: this._t("mac_help"), placeholder: "AA:BB:CC:DD:EE:FF", mono: true })}`;
        break;
      case "done": {
        title = this._t("step_done_title", { name });
        back = false;
        next.label = this._t("finish");
        const d = this._device(wiz.subentryId);
        const ids = d
          ? Object.values(d.entities).concat(d.commands.map((c) => c.entity_id).filter(Boolean))
          : [];
        content = `<div class="done-icon">${icon("mdi:check-circle")}</div><p class="center-text">${esc(this._t("step_done_text"))}</p>
          ${ids.length ? `<div class="list bordered">${ids
            .map((entityId) => {
              const st = this._hass.states[entityId];
              return this._row({
                iconName: st?.attributes?.icon || this._domainIcon(entityId),
                headline: st?.attributes?.friendly_name || entityId,
                supporting: esc(entityId),
                supportingMono: true,
                end: icon("mdi:chevron-right"),
                action: "more-info",
                data: { entity: entityId },
              });
            })
            .join("")}</div>` : ""}`;
        break;
      }
    }

    const error = wiz.error ? this._alert("error", esc(wiz.error)) : "";
    const footer = `<div class="wizard-footer">
        <div>${back ? this._button(this._t("back"), "wiz-back", { appearance: "plain" }) : ""}</div>
        <div class="footer-end">${skip ? this._button(this._t("skip"), "wiz-skip", { appearance: "plain" }) : ""}
        ${next.show ? this._button(next.label, "wiz-next", { disabled: next.disabled, busy: this._busy.has("next") }) : ""}</div></div>`;

    return `${this._toolbar(this._t("wizard_title"), { close: true })}
      <div class="progress" role="progressbar" aria-label="${esc(this._t("step_of", { step: index + 1, total: steps.length }))}" aria-valuemin="0" aria-valuemax="${steps.length}" aria-valuenow="${index + 1}"><div class="progress-fill" style="width:${progress}%"></div></div>
      <div class="content"><div class="container narrow">
        <ha-card class="wizard"><div class="wizard-body">
          <div class="step-label">${esc(this._t("step_of", { step: index + 1, total: steps.length }))}</div>
          <h1>${esc(title)}</h1>
          ${wiz.step === "commands" ? "" : this._notices()}${error}${content}
          ${footer}
        </div></ha-card>
      </div></div>`;
  }
}

// Layout only; the components bring their own Home Assistant styling.
const STYLES = `
:host {
  display: block;
  min-height: 100%;
  background: var(--primary-background-color);
  color: var(--primary-text-color);
  font-family: var(--ha-font-family-body, Roboto, Noto, sans-serif);
  font-size: var(--ha-font-size-m, 14px);
  line-height: var(--ha-line-height-normal, 1.6);
  -webkit-font-smoothing: antialiased;
  --kde-space-1: var(--ha-space-1, 4px);
  --kde-space-2: var(--ha-space-2, 8px);
  --kde-space-3: var(--ha-space-3, 12px);
  --kde-space-4: var(--ha-space-4, 16px);
  --kde-space-6: var(--ha-space-6, 24px);
  --kde-space-8: var(--ha-space-8, 32px);
}
* { box-sizing: border-box; }
.toolbar {
  display: flex; align-items: center; gap: var(--kde-space-1);
  height: var(--header-height, 56px); padding: 0 var(--kde-space-1);
  background: var(--app-header-background-color, var(--primary-color));
  color: var(--app-header-text-color, var(--text-primary-color, #fff));
  border-bottom: var(--app-header-border-bottom, none);
  position: sticky; top: 0; z-index: 2;
}
.main-title {
  margin-inline-start: var(--kde-space-3); font-size: var(--ha-font-size-xl, 20px);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.progress { height: 4px; background: var(--divider-color); position: sticky; top: var(--header-height, 56px); z-index: 2; }
.progress-fill { height: 100%; background: var(--primary-color); transition: width 0.3s ease; }
@media (prefers-reduced-motion: reduce) { .progress-fill { transition: none; } }
.content { padding: var(--kde-space-4); }
.content.center { display: flex; justify-content: center; padding-top: 20vh; }
.container { max-width: 760px; margin: 0 auto; display: flex; flex-direction: column; gap: var(--kde-space-4); }
.container.narrow { max-width: 600px; }
ha-card { display: block; overflow: hidden; }
.card-content { padding: 0 var(--kde-space-4) var(--kde-space-2); }
.card-text { margin: 0; padding: 0 var(--kde-space-4) var(--kde-space-2); color: var(--secondary-text-color); }
.card-actions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: var(--kde-space-2); padding: var(--kde-space-2) var(--kde-space-4) var(--kde-space-4); }
.card-actions.start { justify-content: flex-start; }
.empty { text-align: center; padding: var(--kde-space-8) var(--kde-space-6); }
.empty h2 { font-size: var(--ha-font-size-xl, 20px); font-weight: var(--ha-font-weight-medium, 500); margin: var(--kde-space-4) 0 var(--kde-space-2); }
.empty p { color: var(--secondary-text-color); margin: 0 auto var(--kde-space-6); max-width: 420px; }
.empty-icon { color: var(--secondary-text-color); --mdc-icon-size: 64px; }
.list { display: flex; flex-direction: column; }
.bordered { border: 1px solid var(--divider-color); border-radius: var(--ha-border-radius-md, 8px); overflow: hidden; margin: var(--kde-space-2) 0; }
.list.bordered .row + .row { border-top: 1px solid var(--divider-color); }
.row {
  display: flex; align-items: center; gap: var(--kde-space-4); min-height: 56px; width: 100%;
  padding: var(--kde-space-2) var(--kde-space-4); border: none; background: none; color: inherit;
  font: inherit; text-align: start;
}
.row.clickable { cursor: pointer; }
.row.clickable:hover { background: var(--secondary-background-color); }
.row.clickable:focus-visible { outline: 2px solid var(--primary-color); outline-offset: -2px; }
.row.selected { background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.12); }
.row.selected .row-end { color: var(--primary-color); }
.row-icon { color: var(--state-icon-color, var(--secondary-text-color)); display: flex; }
.row-text { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.headline { font-size: var(--ha-font-size-l, 16px); overflow: hidden; text-overflow: ellipsis; }
.supporting { color: var(--secondary-text-color); font-size: var(--ha-font-size-m, 14px); overflow-wrap: anywhere; }
.mono { font-family: var(--ha-font-family-code, ui-monospace, monospace); font-size: var(--ha-font-size-s, 12px); }
.row-end { display: flex; align-items: center; color: var(--secondary-text-color); }
.status { display: inline-flex; align-items: center; gap: 6px; color: var(--secondary-text-color); }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--disabled-text-color, #9e9e9e); flex: none; }
.dot.on { background: var(--success-color, #4caf50); }
ha-alert { display: block; }
.alert-actions { display: flex; gap: var(--kde-space-2); flex-wrap: wrap; }
.key { font-family: var(--ha-font-family-code, ui-monospace, monospace); font-size: var(--ha-font-size-xl, 20px); letter-spacing: 0.15em; margin-top: var(--kde-space-2); }
.key.big {
  font-size: var(--ha-font-size-4xl, 32px); text-align: center; padding: var(--kde-space-4);
  margin: var(--kde-space-4) 0; border-radius: var(--ha-border-radius-md, 8px);
  background: var(--secondary-background-color);
}
.text-field { display: block; width: 100%; margin: var(--kde-space-2) 0; }
.inline-form { display: flex; align-items: center; gap: var(--kde-space-3); flex-wrap: wrap; }
.inline-form .text-field { flex: 1; min-width: 200px; }
.hint { font-size: var(--ha-font-size-s, 12px); color: var(--secondary-text-color); }
.inline-empty { padding: var(--kde-space-4); color: var(--secondary-text-color); text-align: center; }
a.button-link { text-decoration: none; }
.wizard-body { padding: var(--kde-space-6); }
.wizard h1 { font-size: var(--ha-font-size-2xl, 24px); font-weight: var(--ha-font-weight-normal, 400); margin: 0 0 var(--kde-space-4); line-height: var(--ha-line-height-condensed, 1.2); }
.wizard p { margin: 0 0 var(--kde-space-3); }
.wizard ha-alert { margin-bottom: var(--kde-space-4); }
.step-label { color: var(--secondary-text-color); font-size: var(--ha-font-size-s, 12px); margin-bottom: var(--kde-space-1); }
.steps { padding-inline-start: var(--kde-space-6); margin: 0 0 var(--kde-space-4); }
.steps li { margin-bottom: var(--kde-space-2); }
.searching, .waiting { display: flex; align-items: center; gap: var(--kde-space-3); color: var(--secondary-text-color); margin: var(--kde-space-3) 0; }
.waiting p { margin: 0; }
.manual { margin-top: var(--kde-space-4); border-top: 1px solid var(--divider-color); padding-top: var(--kde-space-2); }
.disclosure {
  display: inline-flex; align-items: center; gap: var(--kde-space-1); border: none; background: none; padding: var(--kde-space-2) 0;
  color: var(--primary-color); font: inherit; font-weight: var(--ha-font-weight-medium, 500); cursor: pointer;
}
.disclosure:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; border-radius: 4px; }
.actions-row { display: flex; justify-content: flex-end; gap: var(--kde-space-2); flex-wrap: wrap; margin-top: var(--kde-space-3); }
.actions-row.start { justify-content: flex-start; }
.wizard-footer { display: flex; justify-content: space-between; align-items: center; gap: var(--kde-space-2); margin-top: var(--kde-space-6); padding-top: var(--kde-space-4); border-top: 1px solid var(--divider-color); }
.footer-end { display: flex; gap: var(--kde-space-2); }
.done-icon { text-align: center; color: var(--success-color, #43a047); --mdc-icon-size: 72px; margin: var(--kde-space-2) 0 var(--kde-space-4); }
.center-text { text-align: center; }
.device-head { display: flex; align-items: center; gap: var(--kde-space-4); padding: var(--kde-space-4); }
.big-icon { --mdc-icon-size: 40px; color: var(--state-icon-color, var(--secondary-text-color)); display: flex; }
.device-name { font-size: var(--ha-font-size-xl, 20px); }
@media (max-width: 600px) {
  .content { padding: var(--kde-space-2); }
  .wizard-body { padding: var(--kde-space-4); }
  .key.big { font-size: var(--ha-font-size-3xl, 28px); }
}
`;

customElements.define("kde-for-home-assistant-panel", KdeForHomeAssistantPanel);
