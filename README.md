# KDE Connect for Home Assistant

Control your computers and phones from Home Assistant with [KDE Connect](https://kdeconnect.kde.org/). Home Assistant shows up as a regular KDE Connect device on your network, so there is nothing extra to install on your devices.

Everything is set up in the Home Assistant UI: no YAML, no SSH.

## What you get

For every paired device:

| Entity | What it does |
| --- | --- |
| **Connected** (binary sensor) | Whether the device is connected to Home Assistant. |
| **Screen** (lock) | Lock or unlock the screen, and see whether it is locked. |
| **Notify** | Show a notification on the device. |
| **Ring** (button) | Play the find-my-device sound. |
| **Wake up** (button) | Turn the device on with Wake-on-LAN. Shows up once a MAC address is known. |
| **Run command** (one button per command) | Run the commands you set up under *Run command* in KDE Connect on the device. |

It also works the other way around: share Home Assistant scripts with a device, and they show up under *Run command* in KDE Connect on that device.

## Installation

### HACS

1. In HACS, open the menu and choose **Custom repositories**.
2. Add `https://github.com/Radeaus/kdeforhomeassistant` with the type **Integration**.
3. Install **KDE Connect** and restart Home Assistant.

### Manually

Copy `custom_components/kdeforhomeassistant` into the `custom_components` folder of your Home Assistant configuration and restart Home Assistant.

## Setup

1. Go to **Settings** > **Devices & services** > **Add integration** and choose **KDE Connect**.
2. Choose the name your devices will see for Home Assistant.
3. On the integration page, select **Pair device**. Home Assistant looks for KDE Connect devices on your network.
4. Pick your device and accept the pairing request on it within 30 seconds. Both sides show the same verification key.

To change a device's settings, open the integration, find the device and select the settings icon. There you can:

- set the **MAC address** for Wake-on-LAN (filled in automatically when Home Assistant can find it);
- choose the **scripts** the device may run.

### Moving from the older KDE Connect integration

If the older [bartv2/kde_connect](https://github.com/bartv2/kde_connect) integration was installed, setup offers to **take over its pairings**. Your devices stay paired and you don't need to accept anything again. Remove the older integration first: both use the same network ports.

## Requirements

- KDE Connect 23.08 or newer on your devices (protocol 7 and 8 are supported).
- The devices and Home Assistant are on the same network, or the device can reach Home Assistant directly. KDE Connect uses UDP port 1716 for discovery and TCP ports 1716 to 1764 for the connection.

## Examples

Turn on the computer, wait until it is connected, then unlock it:

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

## Troubleshooting

- **Pair device finds nothing**: make sure KDE Connect is running and the device is on the same network. Use **Enter the address myself** to reach it by IP address.
- **Could not open the KDE Connect network ports**: another KDE Connect integration is still running. Remove it and restart Home Assistant.
- Diagnostics can be downloaded from the integration page. They contain no keys or certificates.

## License

MIT
