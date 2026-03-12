#!/usr/bin/env bash
# Build Dispatch into a distributable package for the current platform.
#
# macOS  → dist/Dispatch.dmg   (drag-to-Applications installer)
# Linux  → dist/Dispatch.AppImage  (single portable executable)
#
# Usage:
#   ./build.sh           — build for current platform
#   ./build.sh --clean   — wipe previous artifacts first

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="Dispatch"
APP_VERSION="0.1.1"
BUNDLE_ID="com.dispatch.Dispatch"
ENTRY="main.py"

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info() { echo -e "${GREEN}▶ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠ $*${NC}"; }
die()  { echo -e "${RED}✗ $*${NC}" >&2; exit 1; }

# ── Options ───────────────────────────────────────────────────────────────────
CLEAN=false
for arg in "$@"; do [[ "$arg" == "--clean" ]] && CLEAN=true; done

if $CLEAN; then
  info "Cleaning previous build artifacts..."
  rm -rf build dist __pycache__ *.spec
fi

# ── Virtual environment ───────────────────────────────────────────────────────
VENV_DIR=".venv"
[[ -d "$VENV_DIR" ]] || { info "Creating virtual environment..."; python3 -m venv "$VENV_DIR"; }
source "$VENV_DIR/bin/activate"

info "Installing/updating dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet pyinstaller

# ── PyInstaller ───────────────────────────────────────────────────────────────
info "Running PyInstaller..."

PLATFORM="$(uname -s)"
ARCH="$(uname -m)"
EXTRA_ARGS=()

if [[ "$PLATFORM" == "Darwin" ]]; then
  EXTRA_ARGS+=(
    "--windowed"
    "--osx-bundle-identifier" "$BUNDLE_ID"
  )
  [[ -f "assets/icon.icns" ]] && EXTRA_ARGS+=("--icon" "assets/icon.icns")
else
  [[ -f "assets/icon.png" ]] && EXTRA_ARGS+=("--icon" "assets/icon.png")
fi

pyinstaller \
  --name "$APP_NAME" \
  --noconfirm \
  --onedir \
  --collect-all PySide6 \
  "${EXTRA_ARGS[@]}" \
  "$ENTRY"

# ── macOS: build DMG ──────────────────────────────────────────────────────────
if [[ "$PLATFORM" == "Darwin" ]]; then
  APP_BUNDLE="dist/${APP_NAME}.app"
  [[ -d "$APP_BUNDLE" ]] || die "PyInstaller did not produce $APP_BUNDLE"

  DMG_OUT="dist/${APP_NAME}-${APP_VERSION}.dmg"
  info "Building DMG → $DMG_OUT"

  # Use create-dmg if installed (prettier), otherwise fall back to hdiutil
  if command -v create-dmg &>/dev/null; then
    create-dmg \
      --volname "$APP_NAME" \
      --volicon "assets/icon.icns" \
      --window-pos 200 120 \
      --window-size 600 400 \
      --icon-size 128 \
      --icon "${APP_NAME}.app" 150 185 \
      --hide-extension "${APP_NAME}.app" \
      --app-drop-link 450 185 \
      "$DMG_OUT" \
      "$APP_BUNDLE" \
    || warn "create-dmg failed; falling back to hdiutil"
  fi

  # hdiutil fallback (or sole method if create-dmg not installed)
  if [[ ! -f "$DMG_OUT" ]]; then
    STAGING="$(mktemp -d)"
    cp -R "$APP_BUNDLE" "$STAGING/"
    ln -s /Applications "$STAGING/Applications"
    hdiutil create \
      -volname "$APP_NAME" \
      -srcfolder "$STAGING" \
      -ov \
      -format UDZO \
      "$DMG_OUT"
    rm -rf "$STAGING"
  fi

  info "✓ macOS package: $DMG_OUT"
  echo ""
  warn "Note: Users on macOS 12+ may see a Gatekeeper warning on first launch."
  warn "They can right-click → Open to bypass it, or you can code-sign the app"
  warn "with an Apple Developer certificate to eliminate the warning entirely."

# ── Linux: build AppImage ─────────────────────────────────────────────────────
elif [[ "$PLATFORM" == "Linux" ]]; then
  PYINSTALLER_DIR="dist/${APP_NAME}"
  [[ -d "$PYINSTALLER_DIR" ]] || die "PyInstaller did not produce $PYINSTALLER_DIR"

  # ── Download appimagetool if needed ────────────────────────────────────────
  TOOLS_DIR=".build-tools"
  mkdir -p "$TOOLS_DIR"
  APPIMAGETOOL="$TOOLS_DIR/appimagetool"

  if [[ ! -x "$APPIMAGETOOL" ]]; then
    info "Downloading appimagetool..."
    APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${ARCH}.AppImage"
    curl -fsSL -o "$APPIMAGETOOL" "$APPIMAGETOOL_URL" \
      || die "Failed to download appimagetool from $APPIMAGETOOL_URL"
    chmod +x "$APPIMAGETOOL"
  fi

  # ── Assemble AppDir ────────────────────────────────────────────────────────
  info "Assembling AppDir..."
  APPDIR="dist/${APP_NAME}.AppDir"
  rm -rf "$APPDIR"
  mkdir -p "$APPDIR/usr/bin"

  # Copy PyInstaller output into AppDir
  cp -r "$PYINSTALLER_DIR"/. "$APPDIR/usr/bin/"

  # AppRun — entry point executed by the AppImage runtime
  cat > "$APPDIR/AppRun" <<'APPRUN'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/Dispatch" "$@"
APPRUN
  chmod +x "$APPDIR/AppRun"

  # .desktop file (required by AppImage spec)
  cat > "$APPDIR/${APP_NAME}.desktop" <<DESKTOP
[Desktop Entry]
Name=${APP_NAME}
Exec=Dispatch
Icon=Dispatch
Type=Application
Categories=AudioVideo;Utility;
Comment=Map slide remote keystrokes to OSC commands
DESKTOP

  # Icon — copy if available, otherwise create a minimal placeholder
  if [[ -f "assets/icon.png" ]]; then
    cp "assets/icon.png" "$APPDIR/${APP_NAME}.png"
  else
    # Minimal 1×1 white PNG (placeholder so appimagetool doesn't abort)
    printf '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82' \
      > "$APPDIR/${APP_NAME}.png"
    warn "No icon found at assets/icon.png — using placeholder."
    warn "Add a 256×256 PNG there for a proper icon."
  fi

  # ── Run appimagetool ───────────────────────────────────────────────────────
  APPIMAGE_OUT="dist/${APP_NAME}-${APP_VERSION}-${ARCH}.AppImage"
  info "Building AppImage → $APPIMAGE_OUT"

  # appimagetool needs FUSE; if unavailable use --appimage-extract-and-run
  APPIMAGE_ENV=""
  if ! fusermount -V &>/dev/null 2>&1; then
    export APPIMAGE_EXTRACT_AND_RUN=1
  fi

  "$APPIMAGETOOL" "$APPDIR" "$APPIMAGE_OUT" \
    || die "appimagetool failed"

  info "✓ Linux package: $APPIMAGE_OUT"
  echo ""
  info "Share $APPIMAGE_OUT — users just chmod +x it and double-click (or run it)."
  warn "On some systems users need: sudo apt install libfuse2  (Ubuntu/Debian)"

else
  die "Unsupported platform: $PLATFORM"
fi
