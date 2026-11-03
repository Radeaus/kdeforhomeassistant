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

1. **Settings > Devices & services > Add integration > KDE for Home Assistant**, pick a name.
2. On the integration page, click **Pair device** and select your device (or enter its IP).
3. Accept the request on the device within 30 seconds.

Device settings (gear icon on the device) let you set the MAC address for Wake-on-LAN and choose which scripts the device may run.

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

## License

MIT
