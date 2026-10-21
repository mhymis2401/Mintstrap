# Mintstrap

Mintstrap is a Python/Tkinter Roblox mod manager and Sober FastFlags
configuration tool for Linux.

**Status:** Experimental, version 0.1.4.

## Features

- Import ZIP mods with archive path and size checks.
- Review mod files and preview changes before installation.
- Create backups when replacing existing files.
- Check mod contents using SHA-256 before installation.
- Restore files when deactivating mods.
- Edit, back up and restore Sober FastFlags.
- Run a read-only diagnostic of the local configuration.

These safeguards reduce common risks but do not guarantee that a mod is safe.
FastFlags are experimental; Roblox or Sober may ignore unsupported flags.
Mintstrap does not guarantee improved performance or compatibility.

## Requirements

- Linux Mint or Ubuntu
- Python 3.9 or later
- Python Tkinter (`python3-tk`)
- Sober installed in its default Flatpak location

## Run from source

```bash
sudo apt install python3-tk
python3 main.py
```

## Build a Debian package

```bash
bash packaging/build-deb.sh
```

The resulting `.deb` is written to `dist/`.

Install it with:

```bash
sudo apt install ./dist/mintstrap_0.1.4_all.deb
```

Run the installed application with:

```bash
mintstrap
```

User data is stored in `~/.local/share/mintstrap` (or the directory
specified by `XDG_DATA_HOME`). Sober configuration is read from the
current user's Sober configuration directory.

## Project status

This project is not affiliated with or endorsed by Roblox Corporation.
The application and its packaging are still under development.

Mintstrap is licensed under the GNU General Public License v3.0 (GPL-3.0-only). See `LICENSE` for the complete license terms.
