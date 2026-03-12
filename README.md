# Dispatch

Map slide remote keystrokes to OSC commands over UDP — no code required.

Dispatch runs in the background and listens for global key events from any HID device (Logitech Spotlight, Clicker, presentation remote, etc.). When a mapped key is pressed, it fires an OSC message to a configurable host and port. Designed for live event, theatre, and AV workflows where a non-technical operator needs to trigger software via a handheld remote.

---

## Features

- **Key → OSC mappings** — bind any key to an OSC address and arguments
- **Short / long press** — each key can trigger different commands depending on hold duration
- **Per-row test button** — fire a mapping's OSC command instantly without pressing the remote
- **Master pause** — silence all OSC output without stopping the listener
- **OSC log** — collapsible timestamped history of every message sent
- **Duplicate mappings** — copy an existing mapping as a starting point
- **System tray** — closing the window hides to tray; the listener keeps running
- **Catppuccin Mocha** dark theme

---

## Download

Pre-built binaries for Linux and macOS are available on the [Releases page](https://github.com/glabutis/Dispatch/releases).

| Platform | File |
|----------|------|
| macOS | `Dispatch-x.x.x.dmg` — drag to Applications |
| Linux | `Dispatch-x.x.x-x86_64.AppImage` — `chmod +x` and run |

---

## Requirements

- Python 3.10+
- Linux (X11) or macOS

```
PySide6 >= 6.6.0
pynput >= 1.7.6
python-osc >= 1.8.3
```

---

## Running from source

```bash
git clone https://github.com/glabutis/Dispatch.git
cd Dispatch

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

### macOS — Accessibility permission

pynput requires Accessibility access to capture global key events. On first launch macOS will prompt you, or you can grant it manually:

**System Settings → Privacy & Security → Accessibility → enable Dispatch**

### Linux — Wayland

pynput has limited support under Wayland. Dispatch will show a warning if it detects a Wayland session. X11 (or XWayland) is recommended.

---

## Building a distributable

```bash
./build.sh
```

| Platform | Output |
|----------|--------|
| macOS | `dist/Dispatch.dmg` |
| Linux | `dist/Dispatch-0.1.0-x86_64.AppImage` |

Requires PyInstaller (`pip install pyinstaller`). The script installs it automatically inside the venv.

---

## Configuration

Settings are stored at `~/.config/dispatch/config.json` and saved automatically on every change.

---

## Usage

1. Set the **OSC Destination** host and port (default `127.0.0.1:3333`)
2. Click **+ Add Mapping**, then **Listen** and press a key on your remote
3. Choose short press, long press, or both
4. Enter an OSC address (e.g. `/atem/cut`) and optional arguments
5. Click **Save** — the mapping is live immediately

Use the **▶** button on any row to test a command without touching the remote. Use **⏸ Pause** to temporarily silence all output.

---

## License

MIT
