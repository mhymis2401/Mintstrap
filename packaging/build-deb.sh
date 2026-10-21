#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-0.1.5}"

if [[ ! "$VERSION" =~ ^[0-9]+(\.[0-9]+)*$ ]]; then
    echo "Uso: $0 [version]; ejemplo: $0 0.1.2" >&2
    exit 2
fi

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/dist"
OUTPUT="$OUTPUT_DIR/mintstrap_${VERSION}_all.deb"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT

if [[ -e "$OUTPUT" ]]; then
    echo "Ya existe el paquete: $OUTPUT" >&2
    echo "Usa otra versión para no sobrescribirlo." >&2
    exit 1
fi

if ! command -v dpkg-deb >/dev/null 2>&1; then
    echo "Falta dpkg-deb. Instala el paquete dpkg." >&2
    exit 1
fi

ROOT="$TEMP_DIR/root"
mkdir -p \
    "$ROOT/DEBIAN" \
    "$ROOT/usr/share/mintstrap" \
    "$ROOT/usr/bin" \
    "$ROOT/usr/share/applications" \
    "$ROOT/usr/share/doc/mintstrap" \
    "$ROOT/usr/share/licenses/mintstrap" \
    "$OUTPUT_DIR"

install -m 0644 "$SCRIPT_DIR/main.py" \
    "$ROOT/usr/share/mintstrap/main.py"

install -m 0644 "$SCRIPT_DIR/packaging/mintstrap.desktop" \
    "$ROOT/usr/share/applications/mintstrap.desktop"

if [[ ! -f "$SCRIPT_DIR/LICENSE" ]]; then
    echo "Falta LICENSE en el repositorio." >&2
    exit 1
fi

install -m 0644 "$SCRIPT_DIR/LICENSE" \
    "$ROOT/usr/share/licenses/mintstrap/LICENSE"

cat > "$ROOT/usr/share/doc/mintstrap/copyright" <<'EOF'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: Mintstrap
Upstream-Contact: Mintstrap contributors

Files: *
Copyright: 2026 Mintstrap contributors
License: GPL-3.0-only
 The full license text is installed at /usr/share/licenses/mintstrap/LICENSE.
EOF

cat > "$ROOT/DEBIAN/control" <<EOF
Package: mintstrap
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Maintainer: Mintstrap contributors
Depends: python3 (>= 3.9), python3-tk
Description: Roblox mod manager and Sober FastFlags tool
 Python/Tkinter application for Linux.
EOF

cat > "$TEMP_DIR/mintstrap" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 /usr/share/mintstrap/main.py "$@"
EOF

install -m 0755 "$TEMP_DIR/mintstrap" "$ROOT/usr/bin/mintstrap"

# Normalize packaged permissions, regardless of the user's umask.
find "$ROOT" -type d -exec chmod 0755 {} +
find "$ROOT" -type f -exec chmod 0644 {} +
chmod 0755 "$ROOT/usr/bin/mintstrap"

TEMP_PACKAGE="$TEMP_DIR/mintstrap.deb"
dpkg-deb --build --root-owner-group "$ROOT" "$TEMP_PACKAGE" >/dev/null
dpkg-deb --info "$TEMP_PACKAGE" >/dev/null
dpkg-deb --contents "$TEMP_PACKAGE" >/dev/null

mv "$TEMP_PACKAGE" "$OUTPUT"
echo "Paquete creado y verificado: $OUTPUT"
