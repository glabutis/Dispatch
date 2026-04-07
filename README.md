# Dispatch

Map slide remote keystrokes to OSC commands over UDP — no code required.

Dispatch runs in the background and listens for global key events from any HID device (Logitech Spotlight, Clicker, presentation remote, etc.). When a mapped key is pressed, it fires an OSC message to a configurable host and port. Designed for live event, theatre, and AV workflows where a non-technical operator needs to trigger software via a handheld remote.

---

## Features

- **Key → OSC mappings** — bind any key to an OSC address and arguments
- **Short / long press** — each key can trigger different commands depending on hold duration
- **Toggle mode** — a single key alternates between two OSC commands (A on first press, B on second, and so on); useful for mute/unmute, on/off, and similar pairs
- **Profiles** — create multiple named sets of mappings and switch between them instantly; great for different show types or scenes
- **Multiple OSC destinations** — send to any number of hosts simultaneously; each mapping can target all enabled destinations or specific ones only
- **Export / Import profiles** — share a profile as a JSON file; referenced templates travel with it
- **OSC templates** — save OSC commands as reusable templates and link them to multiple mappings; editing the template updates all linked mappings at once
- **Per-row test button** — fire a mapping's OSC command instantly without pressing the remote
- **Master pause** — silence all OSC output without stopping the listener
- **OSC log** — collapsible timestamped history of every message sent
- **Duplicate mappings** — copy an existing mapping as a starting point
- **System tray** — closing the window hides to tray; the listener keeps running
- **Dark and light themes** — Catppuccin Mocha / Latte

---

## Download

Pre-built binaries for Linux and macOS are available on the [Releases page](https://github.com/glabutis/Dispatch/releases).

| Platform | File |
|----------|------|
| macOS | `Dispatch-x.x.x.dmg` — drag to Applications |
| Linux x86\_64 | `Dispatch-x.x.x-x86_64.AppImage` — `chmod +x` and run |
| Linux aarch64 | `Dispatch-x.x.x-aarch64.AppImage` — `chmod +x` and run |

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

### macOS — Input Monitoring permission

pynput requires **Input Monitoring** access to capture global key events. On first launch Dispatch will trigger the system permission dialog automatically. You can also grant it manually:

**System Settings → Privacy & Security → Input Monitoring → enable Dispatch**

Restart the app after enabling the permission. If Dispatch appears to be running but keys are not detected, this permission is the most likely cause.

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
| Linux | `dist/Dispatch-x.x.x-x86_64.AppImage` |

Requires PyInstaller (`pip install pyinstaller`). The script installs it automatically inside the venv.

---

## Configuration

Settings are stored at `~/.config/dispatch/config.json` and saved automatically on every change. Configs from earlier versions migrate automatically — your mappings and OSC target become a single "Default" profile and destination.

---

## Usage

### Basic setup

1. Under **OSC Destinations**, confirm or edit the host and port (default `127.0.0.1:3333`). Click **+ Add** to send to multiple devices simultaneously.
2. Click **+ Add Mapping**, then **Listen** and press a key on your remote.
3. Choose short press, long press, or both.
4. Enter an OSC address (e.g. `/atem/cut`) and optional arguments.
5. Click **Save** — the mapping is live immediately.

Use the **▶** button on any row to test a command without touching the remote. Use **⏸ Pause** to temporarily silence all output.

### Profiles

Click **+** next to the profile selector to create a new profile. Switch between profiles with the dropdown — toggle states reset and the mapping list reloads instantly. Use **Export…** / **Import…** to share profiles as JSON files.

### Toggle mode

Check **Toggle mode** in the mapping editor to define a second OSC command (B). The first key press fires command A, the second fires command B, alternating indefinitely. A **↕** badge appears on the row. The **▶** test button always fires command A without advancing the toggle state.

### Multiple destinations

Each mapping can target all enabled destinations (default) or specific ones — check the destinations you want in the mapping editor. Leave all unchecked to fire to every enabled destination.

### Templates

Open the **Templates** tab to create reusable OSC commands. Link a template to a mapping via the dropdown in the mapping editor. When you edit a template, all linked mappings update automatically.

---

## License

MIT
