"""Remote commands: keys, text and mouse actions as KDE Connect mousepad packets."""

from __future__ import annotations

from typing import Any

from .kdeconnect.protocol import SPECIAL_KEYS

MODIFIERS = ("ctrl", "alt", "shift", "super")

# Scroll distance of one step. Windows reads it as wheel units (120 is one
# notch), Wayland as pixels; X11 and GNOME scroll one notch per packet.
SCROLL_STEP = 60

# The buttons of the remote in the KDE Connect app, sent the same way.
REMOTE_BUTTONS: dict[str, dict[str, Any]] = {
    "up": {"specialKey": SPECIAL_KEYS["up"]},
    "down": {"specialKey": SPECIAL_KEYS["down"]},
    "left": {"specialKey": SPECIAL_KEYS["left"]},
    "right": {"specialKey": SPECIAL_KEYS["right"]},
    "select": {"specialKey": SPECIAL_KEYS["enter"]},
    "back": {"specialKey": SPECIAL_KEYS["escape"]},
    "home": {"super": True, "specialKey": SPECIAL_KEYS["super"]},
    "close": {"alt": True, "specialKey": SPECIAL_KEYS["f4"]},
}

MOUSE_ACTIONS: dict[str, dict[str, Any]] = {
    "click": {"singleclick": True},
    "double_click": {"doubleclick": True},
    "right_click": {"rightclick": True},
    "middle_click": {"middleclick": True},
    # Only the Android app reads these; middle click is home there.
    "android_back": {"backclick": True},
    "android_home": {"middleclick": True},
    "android_recents": {"forwardclick": True},
}

SCROLL_DIRECTIONS: dict[str, tuple[int, int]] = {
    "scroll_up": (0, 1),
    "scroll_down": (0, -1),
    "scroll_left": (-1, 0),
    "scroll_right": (1, 0),
}

COMMAND_NAMES = sorted(
    {*REMOTE_BUTTONS, *SPECIAL_KEYS, *MOUSE_ACTIONS, *SCROLL_DIRECTIONS}
)


def parse_command(command: str) -> dict[str, Any]:
    """Turn a command into the body of a mousepad packet.

    Raises ValueError for a command that is not understood.
    """
    if command.startswith("text:"):
        if not (text := command[len("text:") :]):
            raise ValueError(command)
        return {"key": text}
    name, _, argument = command.strip().partition(":")
    name = name.lower()
    if name == "move":
        try:
            dx, dy = (float(part) for part in argument.split(","))
        except ValueError:
            raise ValueError(command) from None
        if not dx and not dy:
            raise ValueError(command)
        return {"dx": dx, "dy": dy}
    if name in SCROLL_DIRECTIONS:
        try:
            step = float(argument) if argument else SCROLL_STEP
        except ValueError:
            raise ValueError(command) from None
        if step <= 0:
            raise ValueError(command)
        x, y = SCROLL_DIRECTIONS[name]
        return {"scroll": True, "dx": x * step, "dy": y * step}
    if argument:
        raise ValueError(command)
    if name in REMOTE_BUTTONS:
        return dict(REMOTE_BUTTONS[name])
    if name in MOUSE_ACTIONS:
        return dict(MOUSE_ACTIONS[name])

    # A key, with modifiers in front: "enter", "a", "ctrl+c", "alt+f4".
    stripped = command.strip()
    *modifiers, key = ["+"] if stripped == "+" else stripped.split("+")
    body: dict[str, Any] = {}
    for modifier in modifiers:
        if modifier.lower() not in MODIFIERS:
            raise ValueError(command)
        body[modifier.lower()] = True
    if key.lower() in SPECIAL_KEYS:
        body["specialKey"] = SPECIAL_KEYS[key.lower()]
    elif len(key) == 1:
        body["key"] = key
    else:
        raise ValueError(command)
    return body
