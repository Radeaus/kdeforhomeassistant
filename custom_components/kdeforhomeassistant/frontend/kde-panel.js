// KDE for Home Assistant: the sidebar page with the setup wizard and device settings.
// Plain web component, no build step. Styling follows the Home Assistant design
// tokens (https://contributors.home-assistant.io/design/), with fallbacks for
// older releases that do not define them yet.

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

const icon = (name) => `<ha-icon icon="${esc(name)}"></ha-icon>`;
const typeIcon = (type) => TYPE_ICONS[type] || "mdi:devices";

class KdeForHomeAssistantPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._state = null;
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
      if (ev.key === "Enter" && ev.target.dataset?.enter) {
        ev.preventDefault();
        this._action(ev.target.dataset.enter, ev.target);
      }
    });
  }

  // Properties Home Assistant sets on custom panels.

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    if (menu) menu.hass = hass;
    if (first) {
      this._subscribe();
      this._render();
      return;
    }
    const key = this._scripts()
      .map((s) => s.entity_id + s.name)
      .join("|");
    if (key !== this._scriptsKey) {
      this._scriptsKey = key;
      this._render();
    }
  }

  get hass() {
    return this._hass;
  }

  set narrow(value) {
    this._narrow = value;
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    if (menu) menu.narrow = value;
  }

  set route(route) {
    const before = this._path;
    this._route = route;
    this._path = route?.path || "";
    if (before !== undefined && before !== this._path) this._routeChanged();
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
    const view = this._view();
    if (view.name === "wizard" && !this._wiz) this._startWizard();
    if (view.name !== "wizard" && this._wiz) this._stopWizard();
    this._notice = null;
    this._edit = {};
    this._render();
  }

  _stateChanged() {
    const state = this._state;
    const view = this._view();
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
    this.shadowRoot.querySelector(".content")?.scrollTo?.(0, 0);
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
      if (!still && !this._busy.has("accept")) {
        wiz.pair.expired = true;
      }
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
        if (!wiz.selected) return;
        this._startPair(wiz.selected);
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
    const target = ev.target;
    const field = target.dataset?.field;
    if (!field) return;
    if (field.startsWith("wiz.")) {
      this._wiz[field.slice(4)] = target.value;
    } else if (field.startsWith("edit.")) {
      this._edit[field.slice(5)] = target.value;
    } else if (field === "wizScript" && ev.type === "change") {
      const set = new Set(this._wiz.scripts);
      target.checked ? set.add(target.value) : set.delete(target.value);
      this._wiz.scripts = [...set];
    } else if (field === "deviceScript" && ev.type === "change") {
      this._toggleDeviceScript(target.dataset.id, target.value, target.checked);
    } else if (field === "pick" && ev.type === "change") {
      this._wiz.selected = target.value;
      this._render();
    }
  }

  _onClick(ev) {
    const el = ev.composedPath().find((node) => node.dataset?.action);
    if (!el || el.disabled) return;
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
        if (this._wiz.manualOpen) this.shadowRoot.querySelector("#wiz-host")?.focus();
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
        this.shadowRoot.querySelector("#name-input")?.focus();
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
          this._notice = { type: "info", text: this._t("command_setup_opened", { name: data.name }) };
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
    const focus = active?.id
      ? { id: active.id, start: active.selectionStart, end: active.selectionEnd }
      : null;
    const view = this._view();
    let body;
    if (!this._state) body = this._loading();
    else if (!this._state.configured) body = this._message(this._t("not_configured"));
    else if (view.name === "wizard" && this._wiz) body = this._renderWizard();
    else if (view.name === "device") body = this._renderDevice(view.id);
    else body = this._renderOverview();
    this.shadowRoot.innerHTML = `<style>${STYLES}</style>${body}`;
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    if (menu) {
      menu.hass = this._hass;
      menu.narrow = this._narrow;
    }
    if (focus) {
      const el = this.shadowRoot.getElementById(focus.id);
      if (el) {
        el.focus();
        try {
          el.setSelectionRange(focus.start, focus.end);
        } catch (_err) {
          // Not a text field.
        }
      }
    }
  }

  _toolbar(title, { back = false, close = false } = {}) {
    const lead = close
      ? `<button class="icon-button" data-action="wiz-close" aria-label="${esc(this._t("close"))}">${icon("mdi:close")}</button>`
      : back
        ? `<button class="icon-button" data-action="home" aria-label="${esc(this._t("back"))}">${icon("mdi:arrow-left")}</button>`
        : `<ha-menu-button></ha-menu-button>`;
    return `<div class="toolbar">${lead}<div class="main-title">${esc(title)}</div></div>`;
  }

  _loading() {
    return `${this._toolbar(this._t("title"))}<div class="content center"><div class="spinner" role="progressbar"></div></div>`;
  }

  _message(text) {
    return `${this._toolbar(this._t("title"))}<div class="content"><div class="container">${this._alert("warning", text)}</div></div>`;
  }

  _alert(type, text, actions = "") {
    const icons = {
      info: "mdi:information-outline",
      warning: "mdi:alert-outline",
      error: "mdi:alert-circle-outline",
      success: "mdi:check-circle-outline",
    };
    return `<div class="alert ${type}" role="${type === "error" ? "alert" : "status"}">
      ${icon(icons[type])}<div class="alert-text">${text}</div>${actions ? `<div class="alert-actions">${actions}</div>` : ""}
    </div>`;
  }

  _button(label, action, { appearance = "accent", variant = "brand", busy = false, disabled = false, data = {}, iconName = null } = {}) {
    const attrs = Object.entries(data)
      .map(([k, v]) => `data-${k}="${esc(v)}"`)
      .join(" ");
    return `<button class="btn ${appearance} ${variant}" data-action="${action}" ${attrs} ${disabled || busy ? "disabled" : ""}>
      ${busy ? `<span class="spinner small"></span>` : iconName ? icon(iconName) : ""}<span>${esc(label)}</span></button>`;
  }

  _notices() {
    return this._notice ? this._alert(this._notice.type, esc(this._notice.text)) : "";
  }

  _requests() {
    return (this._state.requests || [])
      .map((r) =>
        this._alert(
          "info",
          `<b>${esc(this._t("request_title", { name: r.name }))}</b><br>${esc(this._t("request_text", { name: r.name }))}<div class="key">${esc(r.key)}</div>`,
          this._button(this._t("decline"), "decline", { appearance: "plain", data: { id: r.device_id }, busy: this._busy.has("decline" + r.device_id) }) +
            this._button(this._t("accept"), "accept", { data: { id: r.device_id }, busy: this._busy.has("accept" + r.device_id) })
        )
      )
      .join("");
  }

  _renderOverview() {
    const state = this._state;
    const rows = state.devices
      .map(
        (d) => `<button class="row clickable" data-action="device" data-id="${esc(d.id)}">
          <span class="row-icon">${icon(typeIcon(d.type))}</span>
          <span class="row-text"><span class="headline">${esc(d.name)}</span>
          <span class="supporting"><span class="dot ${d.connected ? "on" : ""}"></span>${esc(this._t(d.connected ? "connected" : "not_connected"))}</span></span>
          <span class="row-end">${icon("mdi:chevron-right")}</span></button>`
      )
      .join("");
    const devices = state.devices.length
      ? `<div class="card"><div class="card-header">${esc(this._t("devices"))}</div><div class="list">${rows}</div>
         <div class="card-actions">${this._button(this._t("add_device"), "add", { iconName: "mdi:plus", disabled: !state.loaded })}</div></div>`
      : `<div class="card empty"><div class="empty-icon">${icon("mdi:monitor-cellphone")}</div>
         <h2>${esc(this._t("empty_title"))}</h2><p>${esc(this._t("empty_text"))}</p>
         ${this._button(this._t("add_device"), "add", { iconName: "mdi:plus", disabled: !state.loaded })}</div>`;
    const nameRow = this._edit.renaming
      ? `<div class="field"><label for="name-input">${esc(this._t("ha_name"))}</label>
         <input id="name-input" data-field="edit.name" data-enter="rename-save" value="${esc(this._edit.name)}" maxlength="32">
         <div class="help">${esc(this._t("ha_name_help"))}</div></div>
         <div class="card-actions">${this._button(this._t("cancel"), "rename-cancel", { appearance: "plain" })}${this._button(this._t("save"), "rename-save", { busy: this._busy.has("rename") })}</div>`
      : `<div class="row"><span class="row-icon">${icon("mdi:home-assistant")}</span>
         <span class="row-text"><span class="headline">${esc(state.name)}</span><span class="supporting">${esc(this._t("ha_name_help"))}</span></span>
         <span class="row-end">${this._button(this._t("rename"), "rename", { appearance: "plain" })}</span></div>`;
    return `${this._toolbar(this._t("title"))}
      <div class="content"><div class="container">
        ${state.loaded ? "" : this._alert("warning", esc(this._t("not_loaded")))}
        ${this._requests()}${this._notices()}${devices}
        <div class="card"><div class="card-header">${esc(this._t("settings"))}</div>${nameRow}</div>
      </div></div>`;
  }

  _renderDevice(id) {
    const d = this._device(id);
    if (!d) {
      return `${this._toolbar(this._t("title"), { back: true })}<div class="content"><div class="container">${this._alert("warning", esc(this._t("unknown_device")))}</div></div>`;
    }
    const ent = d.entities;
    const lockState = ent.screen_lock ? this._hass.states[ent.screen_lock]?.state : null;
    const status = `<div class="card">
      <div class="device-head"><span class="big-icon">${icon(typeIcon(d.type))}</span>
      <div><div class="device-name">${esc(d.name)}</div>
      <div class="supporting"><span class="dot ${d.connected ? "on" : ""}"></span>${esc(this._t(d.connected ? "connected" : "not_connected"))}</div></div></div>
      <div class="card-actions start">
        ${ent.ring ? this._button(this._t("ring"), "press", { appearance: "outlined", iconName: "mdi:bell-ring-outline", data: { entity: ent.ring }, disabled: !d.connected, busy: this._busy.has("press" + ent.ring) }) : ""}
        ${ent.screen_lock ? this._button(this._t(lockState === "locked" ? "unlock" : "lock"), lockState === "locked" ? "unlock" : "lock", { appearance: "outlined", iconName: lockState === "locked" ? "mdi:lock-open-variant-outline" : "mdi:lock-outline", data: { entity: ent.screen_lock }, disabled: !d.connected, busy: this._busy.has("lock") || this._busy.has("unlock") }) : ""}
        ${ent.wake ? this._button(this._t("turn_on"), "press", { appearance: "outlined", iconName: "mdi:power", data: { entity: ent.wake }, busy: this._busy.has("press" + ent.wake) }) : ""}
      </div></div>`;

    const commands = d.commands.length
      ? `<div class="list">${d.commands
          .map(
            (c) => `<div class="row"><span class="row-icon">${icon("mdi:gesture-tap-button")}</span>
            <span class="row-text"><span class="headline">${esc(c.name)}</span>${c.command ? `<span class="supporting mono">${esc(c.command)}</span>` : ""}</span>
            <span class="row-end">${c.entity_id ? this._button(this._t("run"), "press", { appearance: "plain", data: { entity: c.entity_id }, disabled: !d.connected, busy: this._busy.has("press" + c.entity_id) }) : ""}</span></div>`
          )
          .join("")}</div>`
      : `<div class="inline-empty">${esc(this._t("no_commands_text", { name: d.name }))}</div>`;

    const scripts = this._scripts();
    const scriptList = scripts.length
      ? `<div class="list">${scripts
          .map(
            (s) => `<label class="row clickable"><span class="row-icon">${icon("mdi:script-text-outline")}</span>
            <span class="row-text"><span class="headline">${esc(s.name)}</span><span class="supporting mono">${esc(s.entity_id)}</span></span>
            <span class="row-end"><input type="checkbox" class="switch" data-field="deviceScript" data-id="${esc(d.id)}" value="${esc(s.entity_id)}" ${d.scripts.includes(s.entity_id) ? "checked" : ""} ${this._busy.has("scripts") ? "disabled" : ""}></span></label>`
          )
          .join("")}</div>`
      : `<div class="inline-empty">${esc(this._t("no_scripts_text"))}</div>`;

    const macValue = this._edit.mac ?? d.mac ?? "";
    const removing = this._edit.removing
      ? `${this._alert("warning", esc(this._t("remove_confirm", { name: d.name })), this._button(this._t("cancel"), "remove-cancel", { appearance: "plain" }) + this._button(this._t("remove"), "remove-confirm", { variant: "danger", data: { id: d.id }, busy: this._busy.has("remove") }))}`
      : `<div class="card-actions">${this._button(this._t("remove"), "remove", { appearance: "outlined", variant: "danger", iconName: "mdi:delete-outline" })}</div>`;

    const entityRows = Object.values(ent)
      .concat(d.commands.map((c) => c.entity_id).filter(Boolean))
      .map((entityId) => {
        const st = this._hass.states[entityId];
        return `<button class="row clickable" data-action="more-info" data-entity="${esc(entityId)}">
          <span class="row-icon">${icon(st?.attributes?.icon || "mdi:shape-outline")}</span>
          <span class="row-text"><span class="headline">${esc(st?.attributes?.friendly_name || entityId)}</span><span class="supporting mono">${esc(entityId)}</span></span>
          <span class="row-end">${icon("mdi:chevron-right")}</span></button>`;
      })
      .join("");

    return `${this._toolbar(d.name, { back: true })}
      <div class="content"><div class="container">
        ${this._requests()}${this._notices()}${status}
        <div class="card"><div class="card-header">${esc(this._t("buttons"))}</div>
          <p class="card-text">${esc(this._t("buttons_text", { name: d.name }))}</p>${commands}
          <div class="card-actions">${this._button(this._t("add_command", { name: d.name }), "command-setup", { appearance: "outlined", iconName: "mdi:plus", data: { id: d.id, name: d.name }, disabled: !d.connected, busy: this._busy.has("setup" + d.id) })}</div></div>
        <div class="card"><div class="card-header">${esc(this._t("scripts"))}</div>
          <p class="card-text">${esc(this._t("step_scripts_text", { name: d.name }))}</p>${scriptList}
          <div class="card-actions"><a class="btn outlined brand" href="/config/script/edit/new">${icon("mdi:plus")}<span>${esc(this._t("create_script"))}</span></a></div></div>
        <div class="card"><div class="card-header">${esc(this._t("wake"))}</div>
          <p class="card-text">${esc(this._t("step_wake_text", { name: d.name }))}</p>
          <div class="field"><label for="mac-input">${esc(this._t("mac_label"))}</label>
          <input id="mac-input" data-field="edit.mac" data-enter="mac-save" data-id="${esc(d.id)}" value="${esc(macValue)}" placeholder="AA:BB:CC:DD:EE:FF" autocomplete="off" spellcheck="false">
          <div class="help">${esc(this._t("mac_help"))}</div></div>
          <div class="card-actions">${this._button(this._t("save"), "mac-save", { data: { id: d.id }, busy: this._busy.has("mac") })}</div></div>
        ${entityRows ? `<div class="card"><div class="card-header">${esc(this._t("entities"))}</div><div class="list">${entityRows}</div></div>` : ""}
        <div class="card"><div class="card-header">${esc(this._t("remove"))}</div>
          <p class="card-text">${esc(this._t("remove_text", { name: d.name }))}</p>${removing}</div>
      </div></div>`;
  }

  _renderWizard() {
    const wiz = this._wiz;
    const steps = this._steps();
    const index = Math.max(0, steps.indexOf(wiz.step));
    const progress = ((index + 1) / steps.length) * 100;
    const name = wiz.deviceName;
    let title = "";
    let content = "";
    let next = { label: this._t("next"), disabled: false, show: true };
    let back = index > 0 && !["commands", "done"].includes(wiz.step);
    let skip = false;

    switch (wiz.step) {
      case "name":
        title = this._t("step_name_title");
        content = `<p>${esc(this._t("step_name_text"))}</p>
          <div class="field"><label for="wiz-name">${esc(this._t("name_label"))}</label>
          <input id="wiz-name" data-field="wiz.name" data-enter="wiz-next" value="${esc(wiz.name)}" maxlength="32" autocomplete="off"></div>`;
        break;
      case "prepare":
        title = this._t("step_prepare_title");
        content = `<ol class="steps">
            <li>${esc(this._t("step_prepare_1"))}</li>
            <li>${esc(this._t("step_prepare_2"))}</li>
            <li>${esc(this._t("step_prepare_3"))}</li></ol>
          <a class="link" href="https://kdeconnect.kde.org/download.html" target="_blank" rel="noreferrer">${esc(this._t("step_prepare_install"))} ${icon("mdi:open-in-new")}</a>
          <p class="help">${esc(this._t("step_prepare_firewall"))}</p>`;
        break;
      case "choose": {
        title = this._t("step_choose_title");
        const found = this._state.discovered;
        const list = found.length
          ? `<div class="list bordered" role="radiogroup">${found
              .map(
                (d) => `<label class="row clickable ${wiz.selected === d.device_id ? "selected" : ""}">
                <span class="row-icon">${icon(typeIcon(d.type))}</span>
                <span class="row-text"><span class="headline">${esc(d.name)}</span>
                <span class="supporting">${d.host ? esc(d.host) + " · " : ""}${esc(this._t(d.reachable ? "reachable" : "not_reachable"))}</span></span>
                <span class="row-end"><input type="radio" name="pick" data-field="pick" value="${esc(d.device_id)}" ${wiz.selected === d.device_id ? "checked" : ""}></span></label>`
              )
              .join("")}</div>`
          : "";
        content = `<p>${esc(this._t("step_choose_text"))}</p>${list}
          <div class="searching"><span class="spinner small"></span>${esc(this._t("searching"))}</div>
          <details class="manual" ${wiz.manualOpen ? "open" : ""}><summary data-action="manual-toggle">${esc(this._t("manual_title"))}</summary>
            <p class="help">${esc(this._t("manual_text"))}</p>
            <div class="inline-form"><div class="field grow"><label for="wiz-host">${esc(this._t("ip_address"))}</label>
            <input id="wiz-host" data-field="wiz.manualHost" data-enter="manual" value="${esc(wiz.manualHost)}" placeholder="192.168.1.20" inputmode="decimal" autocomplete="off"></div>
            ${this._button(this._t("connect"), "manual", { appearance: "outlined", busy: this._busy.has("manual") })}</div>
          </details>`;
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
            <div class="actions-row">${this._button(this._t("try_again"), "wiz-retry", { appearance: "outlined", iconName: "mdi:refresh" })}</div>`;
        } else if (!pair.key) {
          content = `<div class="waiting"><span class="spinner"></span><p>${esc(this._t("pair_sending", { name }))}</p></div>`;
        } else {
          content = `<p>${esc(this._t("pair_text", { name }))}</p>
            <div class="key big">${esc(pair.key)}</div>
            <div class="waiting"><span class="spinner small"></span><p>${esc(this._t("pair_waiting", { name }))}</p></div>`;
        }
        break;
      }
      case "commands": {
        title = this._t("step_commands_title");
        const d = this._device(wiz.subentryId);
        const connected = d?.connected;
        let list;
        if (!connected) {
          list = `<div class="waiting"><span class="spinner small"></span><p>${esc(this._t("waiting_connect", { name }))}</p></div>`;
        } else if (!d.commands.length) {
          list = `<div class="inline-empty"><b>${esc(this._t("no_commands"))}</b><br>${esc(this._t("no_commands_text", { name }))}</div>`;
        } else {
          list = `<div class="list bordered">${d.commands
            .map(
              (c) => `<div class="row"><span class="row-icon">${icon("mdi:gesture-tap-button")}</span>
              <span class="row-text"><span class="headline">${esc(c.name)}</span>${c.command ? `<span class="supporting mono">${esc(c.command)}</span>` : ""}</span>
              <span class="row-end">${icon("mdi:check")}</span></div>`
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
                .map(
                  (s) => `<label class="row clickable"><span class="row-icon">${icon("mdi:script-text-outline")}</span>
                  <span class="row-text"><span class="headline">${esc(s.name)}</span><span class="supporting mono">${esc(s.entity_id)}</span></span>
                  <span class="row-end"><input type="checkbox" class="switch" data-field="wizScript" value="${esc(s.entity_id)}" ${wiz.scripts.includes(s.entity_id) ? "checked" : ""}></span></label>`
                )
                .join("")}</div>`
            : `<div class="inline-empty"><b>${esc(this._t("no_scripts"))}</b><br>${esc(this._t("no_scripts_text"))}</div>`
        }<div class="actions-row start"><a class="btn outlined brand" href="/config/script/edit/new" target="_blank">${icon("mdi:plus")}<span>${esc(this._t("create_script"))}</span></a></div>`;
        break;
      }
      case "wake":
        title = this._t("step_wake_title");
        skip = true;
        content = `<p>${esc(this._t("step_wake_text", { name }))}</p>
          <div class="field"><label for="wiz-mac">${esc(this._t("mac_label"))}</label>
          <input id="wiz-mac" data-field="wiz.mac" data-enter="wiz-next" value="${esc(wiz.mac)}" placeholder="AA:BB:CC:DD:EE:FF" autocomplete="off" spellcheck="false">
          <div class="help">${esc(this._t("mac_help"))}</div></div>`;
        break;
      case "done": {
        title = this._t("step_done_title", { name });
        back = false;
        next.label = this._t("finish");
        const d = this._device(wiz.subentryId);
        const ids = d ? Object.values(d.entities).concat(d.commands.map((c) => c.entity_id).filter(Boolean)) : [];
        content = `<div class="done-icon">${icon("mdi:check-circle")}</div><p class="center-text">${esc(this._t("step_done_text"))}</p>
          ${ids.length ? `<div class="list bordered">${ids
            .map((entityId) => {
              const st = this._hass.states[entityId];
              return `<button class="row clickable" data-action="more-info" data-entity="${esc(entityId)}">
                <span class="row-text"><span class="headline">${esc(st?.attributes?.friendly_name || entityId)}</span><span class="supporting mono">${esc(entityId)}</span></span>
                <span class="row-end">${icon("mdi:chevron-right")}</span></button>`;
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
      <div class="progress" role="progressbar" aria-valuemin="0" aria-valuemax="${steps.length}" aria-valuenow="${index + 1}"><div class="progress-fill" style="width:${progress}%"></div></div>
      <div class="content"><div class="container narrow">
        <div class="card wizard">
          <div class="step-label">${esc(this._t("step_of", { step: index + 1, total: steps.length }))}</div>
          <h1>${esc(title)}</h1>
          ${wiz.step === "commands" ? "" : this._notices()}${error}${content}
          ${footer}
        </div>
      </div></div>`;
  }
}

const STYLES = `
:host {
  display: block;
  height: 100%;
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
  --kde-radius: var(--ha-card-border-radius, var(--ha-border-radius-lg, 12px));
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
  font-weight: var(--ha-font-weight-normal, 400); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.icon-button {
  display: inline-flex; align-items: center; justify-content: center;
  width: 48px; height: 48px; border: none; border-radius: 50%;
  background: none; color: inherit; cursor: pointer;
}
.icon-button:hover { background: rgba(127, 127, 127, 0.15); }
.icon-button:focus-visible, .btn:focus-visible, .row.clickable:focus-visible, input:focus-visible, summary:focus-visible {
  outline: 2px solid var(--primary-color); outline-offset: 2px;
}
.progress { height: 4px; background: var(--divider-color, rgba(127,127,127,0.2)); position: sticky; top: var(--header-height, 56px); z-index: 2; }
.progress-fill { height: 100%; background: var(--primary-color); transition: width 0.3s ease; }
@media (prefers-reduced-motion: reduce) { .progress-fill { transition: none; } .spinner { animation-duration: 3s; } }
.content { padding: var(--kde-space-4); }
.content.center { display: flex; justify-content: center; padding-top: 20vh; }
.container { max-width: 760px; margin: 0 auto; display: flex; flex-direction: column; gap: var(--kde-space-4); }
.container.narrow { max-width: 600px; }
.card {
  background: var(--ha-card-background, var(--card-background-color, #fff));
  border-radius: var(--kde-radius);
  border: 1px solid var(--ha-card-border-color, var(--divider-color, #e0e0e0));
  box-shadow: var(--ha-card-box-shadow, none);
  overflow: hidden;
}
.card-header { font-size: var(--ha-font-size-2xl, 24px); padding: var(--kde-space-4) var(--kde-space-4) var(--kde-space-2); line-height: var(--ha-line-height-condensed, 1.2); }
.card-text { margin: 0; padding: 0 var(--kde-space-4) var(--kde-space-2); color: var(--secondary-text-color); }
.card-actions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: var(--kde-space-2); padding: var(--kde-space-2) var(--kde-space-4) var(--kde-space-4); }
.card-actions.start { justify-content: flex-start; }
.card > .alert { margin: 0 var(--kde-space-4) var(--kde-space-4); }
.card > .field { padding: 0 var(--kde-space-4); }
.card.empty { text-align: center; padding: var(--kde-space-8) var(--kde-space-6); }
.card.empty h2 { font-size: var(--ha-font-size-xl, 20px); font-weight: var(--ha-font-weight-medium, 500); margin: var(--kde-space-4) 0 var(--kde-space-2); }
.card.empty p { color: var(--secondary-text-color); margin: 0 auto var(--kde-space-6); max-width: 420px; }
.empty-icon { color: var(--secondary-text-color); --mdc-icon-size: 64px; }
.list { display: flex; flex-direction: column; }
.list.bordered { border: 1px solid var(--divider-color); border-radius: var(--ha-border-radius-md, 8px); overflow: hidden; margin: var(--kde-space-2) 0; }
.list.bordered .row + .row { border-top: 1px solid var(--divider-color); }
.row {
  display: flex; align-items: center; gap: var(--kde-space-4); min-height: 56px; width: 100%;
  padding: var(--kde-space-2) var(--kde-space-4); border: none; background: none; color: inherit;
  font: inherit; text-align: start; text-decoration: none;
}
.row.clickable { cursor: pointer; }
.row.clickable:hover { background: var(--secondary-background-color, rgba(127,127,127,0.08)); }
.row.selected { background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.12); }
.row-icon { color: var(--state-icon-color, var(--secondary-text-color)); display: flex; }
.row-text { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.headline { font-size: var(--ha-font-size-l, 16px); overflow: hidden; text-overflow: ellipsis; }
.supporting { color: var(--secondary-text-color); font-size: var(--ha-font-size-m, 14px); display: flex; align-items: center; gap: 6px; overflow-wrap: anywhere; }
.mono { font-family: var(--ha-font-family-code, ui-monospace, monospace); font-size: var(--ha-font-size-s, 12px); }
.row-end { display: flex; align-items: center; color: var(--secondary-text-color); }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--disabled-text-color, #9e9e9e); flex: none; }
.dot.on { background: var(--success-color, #4caf50); }
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: var(--kde-space-2);
  height: 40px; padding: 0 var(--kde-space-4); border-radius: var(--ha-border-radius-pill, 9999px);
  font: inherit; font-weight: var(--ha-font-weight-medium, 500); cursor: pointer; text-decoration: none;
  border: 1px solid transparent; --mdc-icon-size: 18px; white-space: nowrap;
}
.btn.accent { background: var(--btn-color); color: var(--text-primary-color, #fff); }
.btn.accent:hover { filter: brightness(1.08); }
.btn.outlined { background: none; color: var(--btn-color); border-color: var(--btn-color); }
.btn.plain { background: none; color: var(--btn-color); }
.btn.outlined:hover, .btn.plain:hover { background: rgba(127,127,127,0.1); }
.btn.brand { --btn-color: var(--primary-color); }
.btn.danger { --btn-color: var(--error-color, #db4437); }
.btn[disabled] { opacity: 0.5; cursor: default; pointer-events: none; }
.alert {
  display: flex; align-items: flex-start; gap: var(--kde-space-3); padding: var(--kde-space-3) var(--kde-space-4);
  border-radius: var(--ha-border-radius-md, 8px); flex-wrap: wrap;
  background: color-mix(in srgb, var(--alert-color) 12%, transparent);
}
.alert > ha-icon { color: var(--alert-color); flex: none; }
.alert-text { flex: 1; min-width: 200px; }
.alert-actions { display: flex; gap: var(--kde-space-2); margin-inline-start: auto; align-self: flex-end; }
.alert.info { --alert-color: var(--info-color, #039be5); }
.alert.warning { --alert-color: var(--warning-color, #ffa600); }
.alert.error { --alert-color: var(--error-color, #db4437); }
.alert.success { --alert-color: var(--success-color, #43a047); }
.key { font-family: var(--ha-font-family-code, ui-monospace, monospace); font-size: var(--ha-font-size-xl, 20px); letter-spacing: 0.15em; margin-top: var(--kde-space-2); }
.key.big {
  font-size: var(--ha-font-size-4xl, 32px); text-align: center; padding: var(--kde-space-4);
  margin: var(--kde-space-4) 0; border-radius: var(--ha-border-radius-md, 8px);
  background: var(--secondary-background-color, rgba(127,127,127,0.08));
}
.field { display: flex; flex-direction: column; gap: var(--kde-space-1); margin: var(--kde-space-2) 0; }
.field.grow { flex: 1; margin: 0; }
.field label { font-size: var(--ha-font-size-s, 12px); color: var(--secondary-text-color); }
.field input {
  height: 48px; padding: 0 var(--kde-space-3); font: inherit; font-size: var(--ha-font-size-l, 16px);
  color: var(--primary-text-color); background: var(--input-fill-color, var(--secondary-background-color, rgba(127,127,127,0.08)));
  border: none; border-bottom: 1px solid var(--input-idle-line-color, var(--secondary-text-color));
  border-radius: var(--ha-border-radius-sm, 4px) var(--ha-border-radius-sm, 4px) 0 0;
}
.field input:focus { outline: none; border-bottom: 2px solid var(--primary-color); }
.help { font-size: var(--ha-font-size-s, 12px); color: var(--secondary-text-color); }
.inline-form { display: flex; align-items: flex-end; gap: var(--kde-space-3); flex-wrap: wrap; }
.inline-empty { padding: var(--kde-space-4); color: var(--secondary-text-color); text-align: center; }
.wizard { padding: var(--kde-space-6); }
.wizard h1 { font-size: var(--ha-font-size-2xl, 24px); font-weight: var(--ha-font-weight-normal, 400); margin: 0 0 var(--kde-space-4); line-height: var(--ha-line-height-condensed, 1.2); }
.wizard p { margin: 0 0 var(--kde-space-3); }
.card.wizard > .alert { margin: 0 0 var(--kde-space-4); }
.step-label { color: var(--secondary-text-color); font-size: var(--ha-font-size-s, 12px); margin-bottom: var(--kde-space-1); text-transform: none; }
.steps { padding-inline-start: var(--kde-space-6); margin: 0 0 var(--kde-space-4); }
.steps li { margin-bottom: var(--kde-space-2); }
.link { color: var(--primary-color); display: inline-flex; align-items: center; gap: var(--kde-space-1); --mdc-icon-size: 16px; text-decoration: none; font-weight: var(--ha-font-weight-medium, 500); }
.link:hover { text-decoration: underline; }
.searching, .waiting { display: flex; align-items: center; gap: var(--kde-space-3); color: var(--secondary-text-color); margin: var(--kde-space-3) 0; }
.waiting p { margin: 0; }
.manual { margin-top: var(--kde-space-4); border-top: 1px solid var(--divider-color); padding-top: var(--kde-space-3); }
.manual summary { cursor: pointer; color: var(--primary-color); font-weight: var(--ha-font-weight-medium, 500); padding: var(--kde-space-1) 0; }
.manual .help { margin: var(--kde-space-2) 0; }
.actions-row { display: flex; justify-content: flex-end; gap: var(--kde-space-2); flex-wrap: wrap; margin-top: var(--kde-space-3); }
.actions-row.start { justify-content: flex-start; }
.wizard-footer { display: flex; justify-content: space-between; align-items: center; gap: var(--kde-space-2); margin-top: var(--kde-space-6); padding-top: var(--kde-space-4); border-top: 1px solid var(--divider-color); }
.footer-end { display: flex; gap: var(--kde-space-2); }
.done-icon { text-align: center; color: var(--success-color, #43a047); --mdc-icon-size: 72px; margin: var(--kde-space-2) 0 var(--kde-space-4); }
.center-text { text-align: center; }
.device-head { display: flex; align-items: center; gap: var(--kde-space-4); padding: var(--kde-space-4); }
.big-icon { --mdc-icon-size: 40px; color: var(--state-icon-color, var(--secondary-text-color)); }
.device-name { font-size: var(--ha-font-size-xl, 20px); }
.spinner {
  width: 40px; height: 40px; border-radius: 50%; flex: none;
  border: 4px solid color-mix(in srgb, var(--primary-color) 20%, transparent); border-top-color: var(--primary-color);
  animation: spin 0.9s linear infinite;
}
.spinner.small { width: 18px; height: 18px; border-width: 2px; }
.btn.accent .spinner { border-color: rgba(255,255,255,0.35); border-top-color: currentColor; }
@keyframes spin { to { transform: rotate(360deg); } }
input[type="radio"] { width: 20px; height: 20px; accent-color: var(--primary-color); cursor: pointer; }
input.switch {
  appearance: none; -webkit-appearance: none; width: 36px; height: 14px; border-radius: 7px; position: relative; cursor: pointer;
  background: var(--switch-unchecked-track-color, rgba(127,127,127,0.5)); margin: 0 4px;
}
input.switch::after {
  content: ""; position: absolute; top: -3px; left: -4px; width: 20px; height: 20px; border-radius: 50%;
  background: var(--switch-unchecked-button-color, #fafafa); box-shadow: 0 1px 3px rgba(0,0,0,0.4); transition: left 0.15s;
}
input.switch:checked { background: color-mix(in srgb, var(--switch-checked-color, var(--primary-color)) 50%, transparent); }
input.switch:checked::after { left: 20px; background: var(--switch-checked-button-color, var(--primary-color)); }
input.switch:disabled { opacity: 0.5; }
@media (max-width: 600px) {
  .content { padding: var(--kde-space-2); }
  .wizard { padding: var(--kde-space-4); }
  .key.big { font-size: var(--ha-font-size-3xl, 28px); }
}
`;

customElements.define("kde-for-home-assistant-panel", KdeForHomeAssistantPanel);
