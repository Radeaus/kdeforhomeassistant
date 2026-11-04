<p align="center"><img src="assets/icon.svg" alt="" width="96" height="96"></p>

# KDE for Home Assistant

A Home Assistant integration that speaks the [KDE Connect](https://kdeconnect.kde.org/) protocol. Home Assistant joins your network as a regular KDE Connect device, so your PCs and phones only need the normal KDE Connect app.

## Entities

Per paired device:

| Entity | |
| --- | --- |
| `binary_sensor` Connected | Device is connected |
| `lock` Screen | Lock/unlock the screen, shows lock state |
| `notify` | Send a notification |
| `button` Ring | Find-my-device sound |
| `button` Wake up | Wake-on-LAN (needs a MAC address) |
| `button` per run command | Runs the commands configured in KDE Connect on the device |

Home Assistant scripts can also be shared with a device. They then show up under *Run command* in KDE Connect.

## Install

**HACS:** add `https://github.com/Radeaus/kdeforhomeassistant` as a custom repository (type *Integration*), install **KDE for Home Assistant**, restart.

**Manual:** copy `custom_components/kdeforhomeassistant` into your `custom_components` folder and restart.

## Setup

1. **Settings > Devices & services > Add integration > KDE for Home Assistant**. Home Assistant shows up on your network as "*your home name* - Home Assistant".
2. Open **KDE for Home Assistant** in the sidebar. A wizard takes you through it step by step: name, open KDE Connect, choose your device, accept the pairing request, then choose buttons, scripts and Wake-on-LAN.

You can also select **Pair** in KDE Connect on the device itself. Home Assistant then shows the request in the sidebar page and as a notification; accept it within 30 seconds.

The sidebar page also lets you manage each device: run its commands, add new commands on the device, share scripts, set the MAC address for Wake-on-LAN, and remove it.

Not sure which commands to use? On a computer's page, select **Which buttons can I make?**. Choose your Linux distribution and the buttons you want (shut down, sleep, volume, ...), and the page writes a prompt to paste into any AI chat. The AI answers with a table of names and commands, and if it can, a file to load with *Import* under *Run commands* in KDE Connect. Import replaces the commands already in the list.

The built-in ring and screen lock do not work on every desktop (on Cinnamon, for example, there is no ring sound and the lock state is never reported). A run command named **Lock screen**, **Unlock screen** or **Ring** (or Dutch: *Scherm vergrendelen*, *Scherm ontgrendelen*, *Laten rinkelen*) takes over that button and the screen lock entity. The button helper uses these names.

Coming from [bartv2/kde_connect](https://github.com/bartv2/kde_connect)? Setup can take over its pairings. Remove that integration first, since both need the same ports.

## Requirements

- KDE Connect 23.08+ (protocol 7 or 8)
- UDP 1716 and TCP 1716–1764 reachable between Home Assistant and the device

## Example

Wake a PC, wait for it to connect, unlock it:

```yaml
sequence:
  - action: button.press
    target:
      entity_id: button.my_pc_wake_up
  - wait_for_trigger:
      - trigger: state
        entity_id: binary_sensor.my_pc_connected
        to: "on"
    timeout: "00:03:00"
  - action: lock.unlock
    target:
      entity_id: lock.my_pc_screen
```

## Credits

Inspired by [bartv2/kde_connect](https://github.com/bartv2/kde_connect), the original KDE Connect integration for Home Assistant by [bartv2](https://github.com/bartv2). Its approach of letting Home Assistant join the network as a KDE Connect device is where this project started.

Thanks to the [KDE Connect](https://kdeconnect.kde.org/) team for the app and protocol this builds on.

## License

MIT
