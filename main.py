# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Mintstrap contributors
#
# Mintstrap is free software, distributed under the GNU General Public
# License version 3 only. See LICENSE in the source repository, or the
# installed license at /usr/share/licenses/mintstrap/LICENSE.
#
# This program is distributed WITHOUT ANY WARRANTY.

import os
import json
import shutil
import hashlib
import tempfile
import zipfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
from datetime import datetime

DATA_HOME = Path(
    os.environ.get(
        "XDG_DATA_HOME",
        str(Path.home() / ".local" / "share")
    )
)
APP = DATA_HOME / "mintstrap"
LEGACY_APP = Path.home() / "Mintstrap"

# Copy existing user data without overwriting or deleting originals.
for _folder_name in ("mods", "backups", "config"):
    _legacy_folder = LEGACY_APP / _folder_name
    _new_folder = APP / _folder_name

    if (
        _legacy_folder.is_dir()
        and not _legacy_folder.is_symlink()
        and not _new_folder.exists()
        and not _new_folder.is_symlink()
    ):
        _new_folder.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(_legacy_folder, _new_folder)

MODS = APP / "mods"
BACKUPS = APP / "backups"
CONFIG = APP / "config"
STATE_FILE = CONFIG / "active_mods.json"
SOBER = Path.home() / ".var/app/org.vinegarhq.Sober/data/sober"
OVERLAY = SOBER / "asset_overlay"

for folder in (MODS, BACKUPS, CONFIG):
    folder.mkdir(parents=True, exist_ok=True)

SOBER_CONFIG = (
    Path.home()
    / ".var/app/org.vinegarhq.Sober/config/sober/config.json"
)

DOCUMENTED_FFLAGS = {
    "DFIntCSGLevelOfDetailSwitchingDistance",
    "DFIntCSGLevelOfDetailSwitchingDistanceL12",
    "DFIntCSGLevelOfDetailSwitchingDistanceL23",
    "DFIntCSGLevelOfDetailSwitchingDistanceL34",
    "FFlagHandleAltEnterFullscreenManually",
    "DFFlagTextureQualityOverrideEnabled",
    "DFIntTextureQualityOverride",
    "FIntDebugForceMSAASamples",
    "DFFlagDisableDPIScale",
    "FFlagDebugGraphicsPreferD3D11",
    "FFlagDebugSkyGray",
    "DFFlagDebugPauseVoxelizer",
    "DFIntDebugFRMQualityLevelOverride",
    "FIntFRMMaxGrassDistance",
    "FIntFRMMinGrassDistance",
    "FFlagDebugGraphicsPreferVulkan",
    "FFlagDebugGraphicsPreferOpenGL",
    "FIntGrassMovementReducedMotionFactor",
}


FFLAG_INTEGER_RANGES = {
    "DFIntCSGLevelOfDetailSwitchingDistance": (0, 1000),
    "DFIntCSGLevelOfDetailSwitchingDistanceL12": (0, 1000),
    "DFIntCSGLevelOfDetailSwitchingDistanceL23": (0, 1000),
    "DFIntCSGLevelOfDetailSwitchingDistanceL34": (0, 1000),
    "DFIntTextureQualityOverride": (0, 3),
    "DFIntDebugFRMQualityLevelOverride": (0, 21),
    "FIntFRMMaxGrassDistance": (0, 1000),
    "FIntFRMMinGrassDistance": (0, 1000),
}

FFLAG_INTEGER_CHOICES = {
    "FIntDebugForceMSAASamples": (1, 2, 4),
}


FFLAG_PRESETS = {
    "Rendimiento": {
        "DFFlagTextureQualityOverrideEnabled": True,
        "DFIntTextureQualityOverride": 1,
        "DFIntCSGLevelOfDetailSwitchingDistance": 100,
        "DFIntCSGLevelOfDetailSwitchingDistanceL12": 75,
        "DFIntCSGLevelOfDetailSwitchingDistanceL23": 100,
        "DFIntCSGLevelOfDetailSwitchingDistanceL34": 150,
        "FIntFRMMaxGrassDistance": 0,
    },
    "Equilibrado": {
        "DFFlagTextureQualityOverrideEnabled": True,
        "DFIntTextureQualityOverride": 2,
        "DFIntCSGLevelOfDetailSwitchingDistance": 400,
        "DFIntCSGLevelOfDetailSwitchingDistanceL12": 200,
        "DFIntCSGLevelOfDetailSwitchingDistanceL23": 350,
        "DFIntCSGLevelOfDetailSwitchingDistanceL34": 500,
        "FIntDebugForceMSAASamples": 2,
        "FIntFRMMaxGrassDistance": 200,
    },
}


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_state():
    if not STATE_FILE.exists():
        return {}

    def preserve_state(suffix):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        saved = STATE_FILE.with_name(
            f"{STATE_FILE.name}.{suffix}_{stamp}"
        )
        try:
            shutil.copy2(STATE_FILE, saved)
        except OSError as e:
            raise RuntimeError(
                f"No se pudo crear una copia de seguridad del estado: {e}"
            ) from e
        return saved

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        saved = preserve_state("corrupto")
        raise RuntimeError(
            f"El archivo de estado está dañado. "
            f"Se conservó una copia en:\n{saved}\n"
            "Mintstrap no cargará un estado vacío automáticamente."
        ) from e
    except OSError as e:
        raise RuntimeError(
            f"No se pudo leer el estado de Mintstrap: {e}"
        ) from e

    reason = None

    if not isinstance(data, dict):
        reason = "el contenido principal no es un objeto JSON"
    else:
        for name, mod_state in data.items():
            if (
                not isinstance(name, str)
                or not name
                or not isinstance(mod_state, dict)
                or not isinstance(mod_state.get("files"), list)
            ):
                reason = f"el registro del mod {name!r} no es válido"
                break

            for record in mod_state["files"]:
                if not isinstance(record, dict):
                    reason = f"hay un registro de archivo inválido en {name!r}"
                    break

                target = record.get("target")
                if not isinstance(target, str) or not target:
                    reason = f"falta la ruta de un archivo en {name!r}"
                    break

                relative = Path(target)
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or str(relative) in ("", ".")
                ):
                    reason = f"hay una ruta insegura en {name!r}"
                    break

                backup_path = record.get("backup")
                if backup_path is not None and not isinstance(
                    backup_path, str
                ):
                    reason = f"la copia de seguridad de {name!r} no es válida"
                    break

            if reason:
                break

    if reason:
        saved = preserve_state("invalido")
        raise RuntimeError(
            f"El archivo de estado no tiene una estructura válida: {reason}.\n"
            f"Se conservó una copia en:\n{saved}\n"
            "Revisa el estado antes de volver a activar o desactivar mods."
        )

    return data

def save_state():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=STATE_FILE.parent,
            prefix=f".{STATE_FILE.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(active, temporary, indent=2, ensure_ascii=False)
            temporary.write("\\n")
            temporary.flush()
            os.fsync(temporary.fileno())

        os.replace(temporary_path, STATE_FILE)
        temporary_path = None

    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass

active = load_state()

class Mintstrap(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mintstrap")
        self.geometry("780x540")
        self.minsize(650, 440)
        self.configure(bg="#17191f")

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background="#17191f", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(15, 8))
        style.configure("TFrame", background="#20232b")
        style.configure("TLabel", background="#20232b", foreground="#eeeeee")
        style.configure("TButton", padding=7)
        style.configure("Treeview", rowheight=25)

        header = tk.Label(
            self, text="MINTSTRAP", font=("Sans", 20, "bold"),
            bg="#17191f", fg="#e34b55"
        )
        header.pack(pady=(12, 4))

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=10)

        self.home = ttk.Frame(self.tabs, padding=20)
        self.mods_tab = ttk.Frame(self.tabs, padding=12)
        self.flags_tab = ttk.Frame(self.tabs, padding=20)
        self.backup_tab = ttk.Frame(self.tabs, padding=20)
        self.settings_tab = ttk.Frame(self.tabs, padding=20)

        for frame, name in [
            (self.home, "Inicio"),
            (self.mods_tab, "Mods"),
            (self.flags_tab, "FastFlags"),
            (self.backup_tab, "Copias de seguridad"),
            (self.settings_tab, "Configuración"),
        ]:
            self.tabs.add(frame, text=name)

        self.build_home()
        self.build_mods()
        self.build_other_tabs()
        self.refresh_mods()
        self.refresh_flags()

    def build_home(self):
        ttk.Label(
            self.home, text="Administrador de Roblox para Linux",
            font=("Sans", 15, "bold")
        ).pack(anchor="w", pady=(0, 12))

        self.status = ttk.Label(self.home, text="")
        self.status.pack(anchor="w", pady=4)

        ttk.Label(
            self.home, text=f"Carpeta de mods:\n{MODS}"
        ).pack(anchor="w", pady=10)

        ttk.Label(
            self.home,
            text="Importa mods, selecciónalos y actívalos desde la pestaña Mods."
        ).pack(anchor="w", pady=8)

        self.update_status()

    def update_status(self):
        if SOBER.is_dir():
            text = "Sober: carpeta de datos encontrada"
        else:
            text = "Sober: no se encontró su carpeta de datos"
        self.status.configure(text=text)

    def apply_flag_preset(self):
        profile = self.preset_choice.get()
        preset = FFLAG_PRESETS.get(profile)

        if not preset:
            messagebox.showwarning(
                "FastFlags", "Selecciona un perfil primero."
            )
            return

        if not messagebox.askyesno(
            "Confirmar perfil",
            f"Perfil: {profile}\n\n"
            f"Se modificarán {len(preset)} FastFlags permitidas por "
            "la lista de Mintstrap.\n"
            "Las demás banderas y opciones de Sober se conservarán.\n"
            "Se guardará una copia de seguridad antes de aplicar.\n\n"
            "¿Continuar?"
        ):
            return

        temporary_path = None
        backup_path = None

        try:
            raw = SOBER_CONFIG.read_text(encoding="utf-8")
            lines = [
                line for line in raw.splitlines()
                if not line.lstrip().startswith("//")
            ]
            config = json.loads("\n".join(lines))

            if not isinstance(config, dict):
                raise ValueError("La configuración no es un objeto JSON.")

            flags = config.get("fflags")
            if flags is None:
                flags = {}
                config["fflags"] = flags

            if not isinstance(flags, dict):
                raise ValueError("La sección fflags no es válida.")

            for name, value in preset.items():
                if name not in DOCUMENTED_FFLAGS:
                    raise ValueError(
                        f"El perfil contiene una bandera no confirmada: {name}"
                    )

                if name in FFLAG_INTEGER_RANGES:
                    low, high = FFLAG_INTEGER_RANGES[name]
                    if type(value) is not int or not low <= value <= high:
                        raise ValueError(f"Valor fuera de rango: {name}")

                if name in FFLAG_INTEGER_CHOICES:
                    if value not in FFLAG_INTEGER_CHOICES[name]:
                        raise ValueError(f"Valor no permitido: {name}")

            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_dir = BACKUPS / "fastflags" / f"antes_perfil_{stamp}"
            backup_dir.mkdir(parents=True, exist_ok=False)
            backup_path = backup_dir / "config.json"
            shutil.copy2(SOBER_CONFIG, backup_path)

            # Merge only the profile's flags; retain all other settings.
            flags.update(preset)

            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=SOBER_CONFIG.parent,
                prefix=f".{SOBER_CONFIG.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                json.dump(config, temporary, indent=2, ensure_ascii=False)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())

            os.chmod(
                temporary_path,
                SOBER_CONFIG.stat().st_mode & 0o777
            )
            os.replace(temporary_path, SOBER_CONFIG)
            temporary_path = None

            self.refresh_flags()
            messagebox.showinfo(
                "FastFlags",
                f"Perfil «{profile}» aplicado.\n\n"
                f"Copia de seguridad:\n{backup_path}\n\n"
                "Los resultados dentro de Roblox pueden variar. "
                "Cierra y vuelve a abrir Sober para probarlos."
            )

        except Exception as e:
            messagebox.showerror(
                "Error al aplicar perfil",
                f"No se pudo aplicar el perfil:\n{e}\n\n"
                + (
                    f"Copia de seguridad creada en:\n{backup_path}"
                    if backup_path is not None and backup_path.exists()
                    else "No se confirmó una copia de seguridad."
                )
            )

        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink()
                except OSError:
                    pass

    def edit_selected_flag(self):
        selection = self.flags_tree.selection()
        if not selection:
            messagebox.showwarning(
                "FastFlags", "Selecciona una bandera de la lista."
            )
            return

        item = self.flags_tree.item(selection[0])
        name = item.get("text", "")
        values = item.get("values", [])

        if not name or not values:
            messagebox.showerror(
                "FastFlags", "No se pudo leer la bandera seleccionada."
            )
            return

        try:
            raw_config = SOBER_CONFIG.read_text(encoding="utf-8")
            config_lines = [
                line for line in raw_config.splitlines()
                if not line.lstrip().startswith("//")
            ]
            current_config = json.loads("\n".join(config_lines))
            current_flags = current_config.get("fflags")

            if not isinstance(current_flags, dict) or name not in current_flags:
                raise ValueError(
                    "La bandera ya no está en la configuración. "
                    "Pulsa Actualizar lista."
                )

            old_value = current_flags[name]

        except (OSError, json.JSONDecodeError, ValueError, TypeError) as e:
            messagebox.showerror(
                "FastFlags",
                f"No se pudo leer el valor actual de {name}:\\n{e}"
            )
            return

        if name not in DOCUMENTED_FFLAGS:
            proceed = messagebox.askyesno(
                "FastFlag no confirmada",
                f"{name} no aparece en la lista documentada de Mintstrap.\n\n"
                "Roblox podría ignorarla. ¿Quieres editarla de todos modos?"
            )
            if not proceed:
                return

        if isinstance(old_value, bool):
            initial = str(old_value).lower()
        elif isinstance(old_value, (int, float, str)):
            initial = str(old_value)
        else:
            messagebox.showerror(
                "FastFlags", "Este tipo de valor no se puede editar aquí."
            )
            return

        entered = simpledialog.askstring(
            "Editar FastFlag",
            f"Nuevo valor para {name}:\n\n"
            "Booleanos: true o false.\n"
            "Números: escribe un valor numérico.",
            initialvalue=initial,
            parent=self
        )
        if entered is None:
            return

        try:
            if isinstance(old_value, bool):
                normalized = entered.strip().lower()
                if normalized not in ("true", "false"):
                    raise ValueError("Escribe true o false.")
                new_value = normalized == "true"
            elif isinstance(old_value, int):
                new_value = int(entered.strip())
            elif isinstance(old_value, float):
                new_value = float(entered.strip())
                if new_value != new_value or abs(new_value) == float("inf"):
                    raise ValueError("El número debe ser finito.")
            elif isinstance(old_value, str):
                new_value = entered
            else:
                raise ValueError("Tipo de valor no admitido.")
        except ValueError as e:
            messagebox.showerror("Valor inválido", str(e))
            return

        if name in FFLAG_INTEGER_RANGES:
            minimum, maximum = FFLAG_INTEGER_RANGES[name]
            if type(new_value) is not int or not minimum <= new_value <= maximum:
                messagebox.showerror(
                    "Valor fuera de rango",
                    f"{name} debe ser un entero entre {minimum} y {maximum}."
                )
                return

        if name in FFLAG_INTEGER_CHOICES:
            allowed = FFLAG_INTEGER_CHOICES[name]
            if type(new_value) is not int or new_value not in allowed:
                messagebox.showerror(
                    "Valor no permitido",
                    f"{name} solo admite: {', '.join(map(str, allowed))}."
                )
                return

        if not messagebox.askyesno(
            "Confirmar cambio",
            f"FastFlag: {name}\n"
            f"Valor actual: {old_value!r}\n"
            f"Nuevo valor: {new_value!r}\n\n"
            "Se guardará una copia de seguridad de la configuración.\n"
            "¿Aplicar el cambio?"
        ):
            return

        temporary_path = None
        backup_path = None

        try:
            raw = SOBER_CONFIG.read_text(encoding="utf-8")
            lines = [
                line for line in raw.splitlines()
                if not line.lstrip().startswith("//")
            ]
            data = json.loads("\n".join(lines))

            if not isinstance(data, dict):
                raise ValueError("La configuración no es un objeto JSON.")

            flags = data.get("fflags")
            if not isinstance(flags, dict) or name not in flags:
                raise ValueError(
                    "La bandera ya no existe en la configuración. "
                    "Actualiza la lista e inténtalo de nuevo."
                )

            current_value = flags[name]
            if (
                type(current_value) is not type(old_value)
                or current_value != old_value
            ):
                raise ValueError(
                    "La configuración cambió desde que cargaste la lista. "
                    "Pulsa Actualizar lista y vuelve a intentarlo."
                )

            flags[name] = new_value

            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_dir = BACKUPS / "fastflags" / stamp
            backup_dir.mkdir(parents=True, exist_ok=False)
            backup_path = backup_dir / "config.json"
            shutil.copy2(SOBER_CONFIG, backup_path)

            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=SOBER_CONFIG.parent,
                prefix=f".{SOBER_CONFIG.name}.",
                suffix=".tmp",
                delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                json.dump(data, temporary, indent=2, ensure_ascii=False)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())

            os.chmod(
                temporary_path,
                SOBER_CONFIG.stat().st_mode & 0o777
            )
            os.replace(temporary_path, SOBER_CONFIG)
            temporary_path = None

            self.refresh_flags()
            messagebox.showinfo(
                "FastFlags",
                f"Se actualizó {name}.\n\n"
                f"Copia de seguridad:\n{backup_path}\n\n"
                "Si Sober está abierto, cierra y vuelve a abrirlo "
                "para comprobar si aplica el cambio."
            )

        except Exception as e:
            messagebox.showerror(
                "Error al guardar FastFlag",
                f"No se pudo guardar el cambio:\n{e}\n\n"
                + (
                    f"La configuración original se respaldó en:\n{backup_path}"
                    if backup_path is not None and backup_path.exists()
                    else "No se confirmó la creación de la copia de seguridad."
                )
            )

        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink()
                except OSError:
                    pass

    def restore_flags_backup(self):
        backup_root = (BACKUPS / "fastflags").resolve()

        if not backup_root.is_dir():
            messagebox.showinfo(
                "FastFlags", "Todavía no hay copias de seguridad."
            )
            return

        filename = filedialog.askopenfilename(
            parent=self,
            title="Selecciona una copia de FastFlags",
            initialdir=str(backup_root),
            filetypes=[
                ("Copias de configuración", "config.json"),
                ("Archivos JSON", "*.json")
            ]
        )
        if not filename:
            return

        selected = Path(filename)

        try:
            if (
                not selected.resolve().is_relative_to(backup_root)
                or selected.name != "config.json"
                or not selected.is_file()
            ):
                raise ValueError(
                    "Selecciona un config.json dentro de las copias "
                    "de seguridad de FastFlags de Mintstrap."
                )

            def read_config(path):
                raw = path.read_text(encoding="utf-8")
                lines = [
                    line for line in raw.splitlines()
                    if not line.lstrip().startswith("//")
                ]
                result = json.loads("\n".join(lines))
                if not isinstance(result, dict):
                    raise ValueError(
                        f"{path.name} no contiene un objeto JSON."
                    )
                return result

            saved_config = read_config(selected)
            saved_flags = saved_config.get("fflags")

            if not isinstance(saved_flags, dict):
                raise ValueError(
                    "La copia seleccionada no contiene una sección "
                    "'fflags' válida."
                )

            current_config = read_config(SOBER_CONFIG)
            current_flags = current_config.get("fflags")

            if not isinstance(current_flags, dict):
                raise ValueError(
                    "La configuración actual no contiene una sección "
                    "'fflags' válida."
                )

            if not messagebox.askyesno(
                "Confirmar restauración",
                f"Copia seleccionada:\n{selected}\n\n"
                f"Se restaurarán {len(saved_flags)} FastFlags de esa copia.\n"
                "Las demás opciones de Sober se conservarán.\n\n"
                "Mintstrap guardará primero una copia de la configuración "
                "actual. ¿Continuar?"
            ):
                return

            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            before_dir = BACKUPS / "fastflags" / f"antes_restaurar_{stamp}"
            before_dir.mkdir(parents=True, exist_ok=False)
            current_backup = before_dir / "config.json"
            shutil.copy2(SOBER_CONFIG, current_backup)

            # Replace only the FastFlags section; preserve other settings.
            current_config["fflags"] = saved_flags

            temporary_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=SOBER_CONFIG.parent,
                    prefix=f".{SOBER_CONFIG.name}.",
                    suffix=".tmp",
                    delete=False
                ) as temporary:
                    temporary_path = Path(temporary.name)
                    json.dump(
                        current_config,
                        temporary,
                        indent=2,
                        ensure_ascii=False
                    )
                    temporary.write("\n")
                    temporary.flush()
                    os.fsync(temporary.fileno())

                os.chmod(
                    temporary_path,
                    SOBER_CONFIG.stat().st_mode & 0o777
                )
                os.replace(temporary_path, SOBER_CONFIG)
                temporary_path = None

            finally:
                if temporary_path is not None:
                    try:
                        temporary_path.unlink()
                    except OSError:
                        pass

            self.refresh_flags()
            messagebox.showinfo(
                "FastFlags",
                "FastFlags restauradas correctamente.\n\n"
                f"Copia de la configuración anterior:\n{current_backup}\n\n"
                "Si Sober está abierto, ciérralo y vuelve a abrirlo "
                "para comprobar los cambios."
            )

        except Exception as e:
            messagebox.showerror(
                "Error al restaurar",
                f"No se pudo completar la restauración:\n{e}"
            )

    def refresh_flags(self):
        for item in self.flags_tree.get_children():
            self.flags_tree.delete(item)

        if not SOBER_CONFIG.is_file():
            self.flags_status.configure(
                text="No se encontró el archivo de configuración de Sober."
            )
            return

        try:
            raw = SOBER_CONFIG.read_text(encoding="utf-8")
            lines = [
                line for line in raw.splitlines()
                if not line.lstrip().startswith("//")
            ]
            data = json.loads("\n".join(lines))

            if not isinstance(data, dict):
                raise ValueError("La configuración principal no es un objeto.")

            flags = data.get("fflags", {})
            if not isinstance(flags, dict):
                raise ValueError("La sección fflags no es un objeto.")

            for name, value in sorted(flags.items()):
                if isinstance(value, bool):
                    flag_type = "Booleano"
                elif isinstance(value, int):
                    flag_type = "Entero"
                elif isinstance(value, float):
                    flag_type = "Decimal"
                elif isinstance(value, str):
                    flag_type = "Texto"
                else:
                    flag_type = type(value).__name__

                support = (
                    "Documentada"
                    if name in DOCUMENTED_FFLAGS
                    else "No confirmada"
                )

                self.flags_tree.insert(
                    "",
                    "end",
                    text=str(name),
                    values=(
                        json.dumps(value, ensure_ascii=False),
                        flag_type,
                        support
                    )
                )

            self.flags_status.configure(
                text=f"{len(flags)} FastFlags leídas. No se modificó la configuración."
            )

        except (OSError, json.JSONDecodeError, ValueError) as e:
            self.flags_status.configure(
                text=f"No se pudieron leer las FastFlags: {e}"
            )

    def build_mods(self):
        ttk.Label(
            self.mods_tab, text="Mods importados",
            font=("Sans", 13, "bold")
        ).pack(anchor="w", pady=(0, 8))

        columns = ("status", "files")
        self.tree = ttk.Treeview(
            self.mods_tab, columns=columns, show="tree headings",
            selectmode="browse"
        )
        self.tree.heading("#0", text="Mod")
        self.tree.heading("status", text="Estado")
        self.tree.heading("files", text="Archivos")
        self.tree.column("#0", width=300)
        self.tree.column("status", width=110, anchor="center")
        self.tree.column("files", width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, pady=5)

        buttons = ttk.Frame(self.mods_tab)
        buttons.pack(fill="x", pady=(8, 0))

        ttk.Button(
            buttons, text="Importar ZIP", command=self.import_zip
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            buttons, text="Ver detalles", command=self.show_details
        ).pack(side="left", padx=6)
        ttk.Button(
            buttons, text="Eliminar", command=self.remove_mod
        ).pack(side="left", padx=6)
        ttk.Button(
            buttons, text="Restaurar retirado",
            command=self.restore_removed_mod
        ).pack(side="left", padx=6)
        ttk.Button(
            buttons, text="Activar", command=self.activate_mod
        ).pack(side="left", padx=6)
        ttk.Button(
            buttons, text="Desactivar", command=self.deactivate_mod
        ).pack(side="left", padx=6)
        ttk.Button(
            buttons, text="Actualizar", command=self.refresh_mods
        ).pack(side="right")

    def build_other_tabs(self):
        ttk.Label(
            self.flags_tab, text="FastFlags",
            font=("Sans", 15, "bold")
        ).pack(anchor="w")

        ttk.Label(
            self.flags_tab,
            text=f"Configuración de Sober:\n{SOBER_CONFIG}"
        ).pack(anchor="w", pady=(5, 8))

        ttk.Label(
            self.flags_tab,
            text="Vista de solo lectura. Las banderas no documentadas "
                 "pueden ser ignoradas por Roblox."
        ).pack(anchor="w", pady=(0, 8))

        columns = ("value", "type", "support")
        self.flags_tree = ttk.Treeview(
            self.flags_tab,
            columns=columns,
            show="tree headings",
            selectmode="browse"
        )
        self.flags_tree.heading("#0", text="FastFlag")
        self.flags_tree.heading("value", text="Valor")
        self.flags_tree.heading("type", text="Tipo")
        self.flags_tree.heading("support", text="Lista documentada")
        self.flags_tree.column("#0", width=300)
        self.flags_tree.column("value", width=100, anchor="center")
        self.flags_tree.column("type", width=100, anchor="center")
        self.flags_tree.column("support", width=160, anchor="center")
        self.flags_tree.pack(fill="both", expand=True, pady=5)

        self.flags_status = ttk.Label(self.flags_tab, text="")
        self.flags_status.pack(anchor="w", pady=4)

        flag_buttons = ttk.Frame(self.flags_tab)
        flag_buttons.pack(anchor="w", pady=5)

        ttk.Button(
            flag_buttons,
            text="Actualizar lista",
            command=self.refresh_flags
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            flag_buttons,
            text="Editar valor",
            command=self.edit_selected_flag
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            flag_buttons,
            text="Restaurar copia",
            command=self.restore_flags_backup
        ).pack(side="left", padx=(0, 6))

        preset_row = ttk.Frame(self.flags_tab)
        preset_row.pack(anchor="w", pady=(4, 8))

        ttk.Label(
            preset_row, text="Perfil:"
        ).pack(side="left", padx=(0, 6))

        self.preset_choice = ttk.Combobox(
            preset_row,
            state="readonly",
            width=25,
            values=tuple(FFLAG_PRESETS.keys())
        )
        self.preset_choice.pack(side="left", padx=(0, 6))

        ttk.Button(
            preset_row,
            text="Aplicar perfil",
            command=self.apply_flag_preset
        ).pack(side="left")


        ttk.Label(
            self.backup_tab, text="Copias de seguridad",
            font=("Sans", 15, "bold")
        ).pack(anchor="w")
        ttk.Label(
            self.backup_tab,
            text=f"Las copias de archivos reemplazados se guardan en:\n{BACKUPS}"
        ).pack(anchor="w", pady=10)
        ttk.Button(
            self.backup_tab, text="Abrir carpeta de copias",
            command=lambda: self.open_folder(BACKUPS)
        ).pack(anchor="w", pady=5)

        ttk.Label(
            self.settings_tab, text="Configuración",
            font=("Sans", 15, "bold")
        ).pack(anchor="w")
        ttk.Label(
            self.settings_tab, text=f"Carpeta de Sober:\n{SOBER}"
        ).pack(anchor="w", pady=8)
        ttk.Label(
            self.settings_tab, text=f"Asset overlay:\n{OVERLAY}"
        ).pack(anchor="w", pady=8)
        ttk.Button(
            self.settings_tab, text="Abrir carpeta de mods",
            command=lambda: self.open_folder(MODS)
        ).pack(anchor="w", pady=5)

        ttk.Button(
            self.settings_tab, text="Verificar estado",
            command=self.verify_state
        ).pack(anchor="w", pady=5)

    def verify_state(self):
        errors = []
        warnings = []
        info = []
        checks_ok = 0

        def ok():
            nonlocal checks_ok
            checks_ok += 1

        # Check the main folders without changing them.
        for label, path in (
            ("Sober", SOBER),
            ("Asset overlay", OVERLAY),
            ("Carpeta de mods", MODS),
            ("Copias de seguridad", BACKUPS),
        ):
            if path.is_symlink():
                errors.append(f"{label}: la ruta es un enlace simbólico.")
            elif path.is_dir():
                ok()
            else:
                warnings.append(f"{label}: no se encontró {path}")

        # Validate the saved active-mod registry.
        state = {}
        if STATE_FILE.is_symlink():
            errors.append("El archivo de estado es un enlace simbólico.")
        elif STATE_FILE.is_file():
            try:
                state = json.loads(
                    STATE_FILE.read_text(encoding="utf-8")
                )
                if not isinstance(state, dict):
                    raise ValueError(
                        "el contenido principal no es un objeto JSON"
                    )
                ok()
                if state != active:
                    warnings.append(
                        "El estado guardado en disco no coincide con "
                        "el estado que Mintstrap tiene en memoria."
                    )
            except (OSError, json.JSONDecodeError, ValueError) as e:
                errors.append(f"No se pudo validar el estado de mods: {e}")
                state = {}
        else:
            info.append("Aún no existe un archivo de estado de mods.")

        # Validate active mods and their paths/backups.
        overlay_root = OVERLAY.resolve()
        backups_root = BACKUPS.resolve()

        for name, mod_state in state.items():
            if (
                not isinstance(name, str)
                or not name
                or Path(name).name != name
                or name in (".", "..")
            ):
                errors.append(f"Nombre de mod inseguro en el registro: {name!r}")
                continue

            folder = MODS / name
            if folder.is_symlink():
                errors.append(f"El mod activo «{name}» es un enlace simbólico.")
            elif not folder.is_dir():
                warnings.append(
                    f"El mod activo «{name}» no está en la carpeta Mods."
                )

            if not isinstance(mod_state, dict):
                errors.append(f"El registro del mod «{name}» no es válido.")
                continue

            records = mod_state.get("files")
            if not isinstance(records, list):
                errors.append(f"El mod «{name}» no tiene una lista de archivos válida.")
                continue

            for record in records:
                if not isinstance(record, dict):
                    errors.append(f"Registro de archivo inválido en «{name}».")
                    continue

                raw = record.get("target")
                if not isinstance(raw, str) or not raw:
                    errors.append(f"Falta una ruta de destino en «{name}».")
                    continue

                rel = Path(raw)
                if rel.is_absolute() or ".." in rel.parts or str(rel) in ("", "."):
                    errors.append(f"Ruta insegura en «{name}»: {raw}")
                    continue

                cursor = OVERLAY
                unsafe_link = False
                for part in rel.parts:
                    cursor = cursor / part
                    if cursor.is_symlink():
                        unsafe_link = True
                        break

                if unsafe_link:
                    errors.append(
                        f"El destino atraviesa un enlace simbólico: {raw}"
                    )
                    continue

                target = OVERLAY / rel
                try:
                    if not target.resolve().is_relative_to(overlay_root):
                        errors.append(f"Destino fuera del overlay: {raw}")
                        continue
                except OSError as e:
                    errors.append(f"No se pudo comprobar {raw}: {e}")
                    continue

                if target.is_file():
                    ok()
                elif target.exists():
                    warnings.append(f"El destino no es un archivo: {raw}")
                else:
                    warnings.append(
                        f"Falta un archivo registrado como activo: {raw}"
                    )

                backup_value = record.get("backup")
                if backup_value is not None:
                    if not isinstance(backup_value, str):
                        errors.append(
                            f"Ruta de copia inválida para {raw}."
                        )
                        continue

                    backup_path = Path(backup_value)
                    try:
                        safe_backup = (
                            not backup_path.is_symlink()
                            and backup_path.resolve().is_relative_to(backups_root)
                        )
                    except OSError:
                        safe_backup = False

                    if not safe_backup or not backup_path.is_file():
                        warnings.append(
                            f"No se encontró una copia válida para {raw}."
                        )
                    else:
                        ok()
                elif record.get("existed_before") is True:
                    warnings.append(
                        f"Falta la copia original registrada para {raw}."
                    )

        # Read FastFlags configuration without writing it.
        if SOBER_CONFIG.is_symlink():
            errors.append(
                "La configuración de Sober es un enlace simbólico."
            )
        elif SOBER_CONFIG.is_file():
            try:
                raw = SOBER_CONFIG.read_text(encoding="utf-8")
                lines = [
                    line for line in raw.splitlines()
                    if not line.lstrip().startswith("//")
                ]
                config = json.loads("\n".join(lines))

                if not isinstance(config, dict):
                    raise ValueError("la configuración no es un objeto JSON")

                flags = config.get("fflags", {})
                if not isinstance(flags, dict):
                    raise ValueError("la sección fflags no es válida")

                info.append(f"FastFlags encontradas: {len(flags)}.")
                ok()
            except (OSError, json.JSONDecodeError, ValueError) as e:
                errors.append(f"No se pudo validar la configuración de Sober: {e}")
        else:
            warnings.append(
                f"No se encontró la configuración de Sober en {SOBER_CONFIG}."
            )

        if BACKUPS.is_dir() and not BACKUPS.is_symlink():
            try:
                backup_count = sum(
                    1 for item in BACKUPS.rglob("*")
                    if item.is_file() and not item.is_symlink()
                )
                info.append(f"Archivos de respaldo encontrados: {backup_count}.")
            except OSError as e:
                warnings.append(f"No se pudieron contar los respaldos: {e}")

        report = [
            "DIAGNÓSTICO DE MINTSTRAP",
            "",
            f"Comprobaciones correctas: {checks_ok}",
            f"Advertencias: {len(warnings)}",
            f"Problemas: {len(errors)}",
            "",
        ]

        if errors:
            report.append("PROBLEMAS")
            report.extend(f"- {item}" for item in errors)
            report.append("")

        if warnings:
            report.append("ADVERTENCIAS")
            report.extend(f"- {item}" for item in warnings)
            report.append("")

        if info:
            report.append("INFORMACIÓN")
            report.extend(f"- {item}" for item in info)
            report.append("")

        if not errors and not warnings:
            report.append("No se detectaron problemas en estas comprobaciones.")

        window = tk.Toplevel(self)
        window.title("Diagnóstico de Mintstrap")
        window.geometry("760x520")
        window.minsize(520, 350)
        window.transient(self)

        area_frame = ttk.Frame(window, padding=10)
        area_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(area_frame, orient="vertical")
        area = tk.Text(
            area_frame,
            wrap="word",
            yscrollcommand=scrollbar.set,
            font=("Monospace", 10)
        )
        scrollbar.configure(command=area.yview)
        scrollbar.pack(side="right", fill="y")
        area.pack(side="left", fill="both", expand=True)

        area.insert("1.0", "\n".join(report))
        area.configure(state="disabled")

        ttk.Button(
            window, text="Cerrar", command=window.destroy
        ).pack(anchor="e", padx=12, pady=(0, 10))

    def open_folder(self, path):
        path.mkdir(parents=True, exist_ok=True)
        os.system(f'xdg-open "{path}" >/dev/null 2>&1 &')

    def inspect_mod_security(self, folder):
        warnings = []
        dangerous = []
        root = folder.resolve()

        risky_extensions = {
            ".sh", ".bash", ".py", ".pyc", ".so",
            ".dll", ".exe", ".appimage", ".desktop"
        }

        try:
            for path in folder.rglob("*"):
                relative = path.relative_to(folder)

                if path.is_symlink():
                    dangerous.append(
                        f"Enlace simbólico: {relative}"
                    )
                    continue

                try:
                    resolved = path.resolve()
                    resolved.relative_to(root)
                except (OSError, ValueError):
                    dangerous.append(
                        f"Ruta fuera de la carpeta del mod: {relative}"
                    )
                    continue

                if not path.is_file():
                    continue

                if any(part.startswith(".") for part in relative.parts):
                    warnings.append(f"Archivo oculto: {relative}")

                if path.suffix.lower() in risky_extensions:
                    warnings.append(
                        f"Archivo que requiere revisión: {relative}"
                    )

                try:
                    if path.stat().st_mode & 0o111:
                        warnings.append(
                            f"Archivo con permisos de ejecución: {relative}"
                        )
                except OSError:
                    dangerous.append(
                        f"No se pudieron comprobar los permisos: {relative}"
                    )

        except OSError as e:
            dangerous.append(f"No se pudo revisar el mod: {e}")

        return dangerous, warnings

    def review_mod(self, folder):
        dangerous, warnings = self.inspect_mod_security(folder)

        if dangerous:
            messagebox.showerror(
                "Mod bloqueado",
                "Se detectaron elementos peligrosos. No se instalará:\\n\\n"
                + "\\n".join(dangerous[:20])
            )
            return False

        if warnings:
            report = "\\n".join(warnings[:20])
            if len(warnings) > 20:
                report += f"\\n... y {len(warnings) - 20} advertencias más."
            return messagebox.askyesno(
                "Revisión de seguridad",
                "El mod contiene archivos que requieren revisión:\\n\\n"
                + report
                + "\\n\\n¿Quieres continuar? Recuerda que Mintstrap "
                  "no ejecutará esos archivos."
            )

        return True

    def import_zip(self):
        filename = filedialog.askopenfilename(
            title="Selecciona un mod ZIP",
            initialdir=Path.home() / "Descargas",
            filetypes=[("Archivos ZIP", "*.zip")]
        )
        if not filename:
            return

        dest = None
        created_dest = False
        try:
            with zipfile.ZipFile(filename) as z:
                entries = z.infolist()

                if len(entries) > 5000:
                    raise ValueError("El ZIP contiene demasiados archivos.")

                total_size = sum(e.file_size for e in entries)
                if total_size > 500 * 1024 * 1024:
                    raise ValueError(
                        "El ZIP supera los 500 MiB descomprimidos."
                    )

                validated = []
                seen = set()

                for entry in entries:
                    raw_name = entry.filename
                    normalized = raw_name.replace("\\", "/")
                    parts = normalized.split("/")
                    path = Path(normalized)

                    if (
                        not normalized
                        or normalized.startswith("/")
                        or path.is_absolute()
                        or "\x00" in normalized
                        or any(part in ("", ".", "..") for part in parts[:-1])
                        or ".." in parts
                        or (parts and ":" in parts[0])
                    ):
                        raise ValueError(
                            f"Ruta insegura en el ZIP: {raw_name}"
                        )

                    mode = entry.external_attr >> 16
                    file_type = mode & 0o170000
                    if file_type not in (0, 0o100000, 0o040000):
                        raise ValueError(
                            f"Tipo de archivo no permitido: {raw_name}"
                        )

                    key = normalized.rstrip("/").casefold()
                    if key in seen:
                        raise ValueError(
                            f"Ruta duplicada en el ZIP: {raw_name}"
                        )
                    seen.add(key)

                    if entry.flag_bits & 0x1:
                        raise ValueError(
                            f"Archivo cifrado no permitido: {raw_name}"
                        )

                    validated.append((entry, Path(*parts)))

                base_name = Path(filename).stem
                name = base_name
                dest = MODS / name

                if dest.exists():
                    suffix = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    name = f"{base_name}_{suffix}"
                    dest = MODS / name
                    counter = 1

                    while dest.exists():
                        name = f"{base_name}_{suffix}_{counter}"
                        dest = MODS / name
                        counter += 1

                dest.mkdir(parents=True, exist_ok=False)
                created_dest = True

                for entry, relative in validated:
                    target = dest / relative

                    if not target.resolve().is_relative_to(dest.resolve()):
                        raise ValueError(
                            f"Destino fuera de la carpeta del mod: {entry.filename}"
                        )

                    if entry.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue

                    target.parent.mkdir(parents=True, exist_ok=True)

                    written = 0
                    with z.open(entry) as source, target.open("xb") as output:
                        while True:
                            chunk = source.read(1024 * 1024)
                            if not chunk:
                                break
                            written += len(chunk)
                            if written > entry.file_size:
                                raise ValueError(
                                    f"Tamaño inesperado: {entry.filename}"
                                )
                            output.write(chunk)

                    if written != entry.file_size:
                        raise ValueError(
                            f"El tamaño no coincide: {entry.filename}"
                        )

            messagebox.showinfo("Mintstrap", f"Mod importado:\n{name}")
            self.refresh_mods()

        except Exception as e:
            if (
                created_dest
                and dest is not None
                and dest.is_dir()
                and not dest.is_symlink()
            ):
                try:
                    shutil.rmtree(dest)
                except OSError:
                    pass
            messagebox.showerror("Error al importar", str(e))

    def show_details(self):
        name = self.get_selected_mod()
        if name is None:
            return

        folder = MODS / name
        if not self.review_mod(folder):
            return

        files = self.mod_files(folder)

        window = tk.Toplevel(self)
        window.title(f"Detalles del mod: {name}")
        window.geometry("800x450")
        window.minsize(550, 300)

        ttk.Label(
            window,
            text=f"{name} — {len(files)} archivos",
            font=("Sans", 12, "bold")
        ).pack(anchor="w", padx=12, pady=10)

        columns = ("extension", "size", "path")
        table = ttk.Treeview(
            window, columns=columns, show="headings"
        )
        table.heading("extension", text="Extensión")
        table.heading("size", text="Tamaño")
        table.heading("path", text="Ruta dentro del mod")
        table.column("extension", width=100)
        table.column("size", width=120, anchor="e")
        table.column("path", width=520)
        table.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        for file_path, relative_path in sorted(
            files, key=lambda item: str(item[1]).lower()
        ):
            extension = file_path.suffix.lower() or "(sin extensión)"
            try:
                size = file_path.stat().st_size
            except OSError:
                size = 0
            table.insert(
                "", "end",
                values=(extension, f"{size:,} bytes", str(relative_path))
            )

        if not files:
            ttk.Label(window, text="No se encontraron archivos.").pack()

    def restore_removed_mod(self):
        if MODS.is_symlink() or BACKUPS.is_symlink():
            messagebox.showerror(
                "Ruta insegura",
                "La carpeta de mods o copias de seguridad es un "
                "enlace simbólico. No se hizo ningún cambio."
            )
            return

        archive_root = BACKUPS / "removed_mods"

        if archive_root.is_symlink():
            messagebox.showerror(
                "Ruta insegura",
                "La carpeta de mods retirados es un enlace simbólico."
            )
            return

        if not archive_root.is_dir():
            messagebox.showinfo(
                "Mintstrap",
                "Todavía no hay mods retirados para restaurar."
            )
            return

        selected = filedialog.askdirectory(
            parent=self,
            title="Selecciona la carpeta del mod retirado",
            initialdir=str(archive_root),
            mustexist=True
        )
        if not selected:
            return

        try:
            source = Path(selected)
            archive_resolved = archive_root.resolve(strict=True)

            if source.is_symlink() or source.parent.is_symlink():
                raise ValueError(
                    "La carpeta elegida o su carpeta contenedora "
                    "es un enlace simbólico."
                )

            if not source.is_dir():
                raise ValueError("La selección no es una carpeta.")

            resolved_source = source.resolve(strict=True)

            if (
                not resolved_source.is_relative_to(archive_resolved)
                or resolved_source == archive_resolved
                or resolved_source.parent.parent != archive_resolved
            ):
                raise ValueError(
                    "Selecciona la carpeta de un mod dentro de "
                    "backups/removed_mods/<fecha>/<mod>."
                )

            for path in source.rglob("*"):
                if path.is_symlink():
                    raise ValueError(
                        "Se encontró un enlace simbólico dentro del mod: "
                        f"{path.relative_to(source)}"
                    )

            name = source.name
            destination = MODS / name

            if destination.exists() or destination.is_symlink():
                raise ValueError(
                    f"Ya existe una carpeta llamada «{name}» en Mods. "
                    "No se sobrescribió."
                )

            if name in active:
                raise ValueError(
                    "El registro indica que ese mod está activo. "
                    "No se restaurará hasta resolver ese estado."
                )

            if not messagebox.askyesno(
                "Restaurar mod",
                f"¿Restaurar «{name}» a la lista de Mods?\n\n"
                "El mod no se activará en Sober.\n"
                "La carpeta se moverá fuera de los archivos retirados."
            ):
                return

            source.rename(destination)
            self.refresh_mods()

            messagebox.showinfo(
                "Mintstrap",
                f"Mod «{name}» restaurado a la lista de Mods.\n\n"
                "Sigue inactivo; tendrás que activarlo manualmente."
            )

        except Exception as e:
            messagebox.showerror(
                "Error al restaurar",
                f"No se pudo restaurar el mod:\n{e}"
            )

    def remove_mod(self):
        name = self.get_selected_mod()
        if name is None:
            return

        if name in active:
            messagebox.showwarning(
                "Mod activo",
                "No se puede retirar un mod activo.\n\n"
                "Desactívalo primero para evitar dejar archivos "
                "instalados en Sober."
            )
            return

        if MODS.is_symlink() or BACKUPS.is_symlink():
            messagebox.showerror(
                "Ruta insegura",
                "La carpeta de mods o copias de seguridad es un "
                "enlace simbólico. No se hizo ningún cambio."
            )
            return

        folder = MODS / name

        try:
            mods_root = MODS.resolve()
            if folder.is_symlink() or not folder.is_dir():
                raise ValueError("El mod no es una carpeta normal.")

            resolved_folder = folder.resolve(strict=True)
            if (
                not resolved_folder.is_relative_to(mods_root)
                or resolved_folder == mods_root
            ):
                raise ValueError(
                    "La carpeta seleccionada está fuera de Mods."
                )

            # Refuse unexpected symbolic links within an imported mod.
            for path in folder.rglob("*"):
                if path.is_symlink():
                    raise ValueError(
                        f"Se encontró un enlace simbólico: "
                        f"{path.relative_to(folder)}"
                    )

            count = len(self.mod_files(folder))

            if not messagebox.askyesno(
                "Retirar mod",
                f"¿Retirar «{name}»?\n\n"
                f"Archivos: {count}\n\n"
                "La carpeta se moverá a respaldos de mods retirados. "
                "No se eliminará definitivamente."
            ):
                return

            backup_root = BACKUPS.resolve()
            archive_root = BACKUPS / "removed_mods"

            if archive_root.is_symlink():
                raise ValueError(
                    "La carpeta de mods retirados es un enlace simbólico."
                )

            archive_root.mkdir(parents=True, exist_ok=True)
            if not archive_root.resolve().is_relative_to(backup_root):
                raise ValueError(
                    "La carpeta de archivo está fuera de BACKUPS."
                )

            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            destination_parent = archive_root / stamp
            destination_parent.mkdir(exist_ok=False)
            destination = destination_parent / name

            try:
                folder.rename(destination)
            except Exception:
                try:
                    destination_parent.rmdir()
                except OSError:
                    pass
                raise

            self.refresh_mods()
            messagebox.showinfo(
                "Mintstrap",
                f"Mod «{name}» retirado.\n\n"
                f"Carpeta conservada en:\n{destination}"
            )

        except Exception as e:
            messagebox.showerror(
                "No se pudo retirar el mod",
                f"No se completó la operación:\n{e}"
            )

    def get_selected_mod(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Mintstrap", "Selecciona un mod primero.")
            return None
        return selection[0]

    def mod_files(self, folder):
        files = []
        for path in folder.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(folder)
            if rel.parts and rel.parts[0] == "__MACOSX":
                continue
            if path.name == ".DS_Store":
                continue
            files.append((path, rel))
        return files

    def refresh_mods(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for folder in sorted(MODS.iterdir()):
            if not folder.is_dir():
                continue
            count = len(self.mod_files(folder))
            status = "Activo" if folder.name in active else "Inactivo"
            self.tree.insert(
                "", "end", iid=folder.name,
                text=folder.name, values=(status, count)
            )

        self.update_status()

    def activate_mod(self):
        name = self.get_selected_mod()
        if name is None:
            return
        if name in active:
            messagebox.showinfo("Mintstrap", "Este mod ya está activo.")
            return
        if not SOBER.is_dir():
            messagebox.showerror(
                "Mintstrap", f"No se encontró Sober en:\\n{SOBER}"
            )
            return

        folder = MODS / name
        if not self.review_mod(folder):
            return

        files = self.mod_files(folder)
        if not files:
            messagebox.showerror("Mintstrap", "El mod no contiene archivos.")
            return

        occupied = {
            entry["target"]
            for mod_state in active.values()
            for entry in mod_state.get("files", [])
        }

        planned = []
        total_size = 0
        conflicts = []

        for source, rel in files:
            target = OVERLAY / rel
            if not target.resolve().is_relative_to(OVERLAY.resolve()):
                messagebox.showerror(
                    "Ruta insegura", f"Destino fuera del overlay: {rel}"
                )
                return

            if str(rel) in occupied:
                conflicts.append(str(rel))

            try:
                if source.is_symlink() or not source.is_file():
                    raise ValueError("El origen no es un archivo normal.")
                size = source.stat().st_size
                file_hash = sha256_file(source)
            except (OSError, ValueError) as e:
                messagebox.showerror(
                    "No se pudo revisar el archivo",
                    f"No se pudo calcular la huella de {rel}:\n{e}"
                )
                return

            total_size += size
            planned.append((source, rel, target, size, file_hash))

        if conflicts:
            messagebox.showerror(
                "Conflicto de mods",
                "Otro mod activo administra estos archivos:\\n\\n"
                + "\\n".join(conflicts[:15])
                + "\\n\\nDesactiva el otro mod antes de continuar."
            )
            return

        existing = [str(rel) for _, rel, target, _, _ in planned if target.exists()]
        new_files = [str(rel) for _, rel, target, _, _ in planned if not target.exists()]

        report = [
            f"Mod: {name}",
            f"Archivos: {len(planned)}",
            f"Tamaño total: {total_size:,} bytes",
            "",
            f"Archivos nuevos: {len(new_files)}",
            f"Archivos que se reemplazarían: {len(existing)}",
            "",
            f"Destino: {OVERLAY}",
            "",
            "Archivos del mod:"
        ]
        for _, rel, target, size, _ in planned[:40]:
            state = "REEMPLAZAR" if target.exists() else "NUEVO"
            report.append(f"[{state}] {rel} ({size:,} bytes)")
        if len(planned) > 40:
            report.append(f"... y {len(planned) - 40} archivos más.")

        report.extend([
            "",
            "Mintstrap guardará copias de seguridad de los archivos "
            "existentes antes de reemplazarlos.",
            "Los archivos del mod no se ejecutarán."
        ])

        preview = tk.Toplevel(self)
        preview.title(f"Vista previa: {name}")
        preview.geometry("700x540")
        preview.transient(self)

        ttk.Label(
            preview, text="Informe previo a la instalación",
            font=("Sans", 13, "bold")
        ).pack(anchor="w", padx=12, pady=10)

        area = tk.Text(preview, wrap="word", height=22, width=80)
        area.pack(fill="both", expand=True, padx=12, pady=4)
        area.insert("1.0", "\\n".join(report))
        area.configure(state="disabled")

        buttons = ttk.Frame(preview)
        buttons.pack(fill="x", padx=12, pady=12)

        def confirm_install():
            preview.destroy()
            self.install_reviewed_mod(name, planned)

        ttk.Button(
            buttons, text="Cancelar", command=preview.destroy
        ).pack(side="right", padx=5)
        ttk.Button(
            buttons, text="Confirmar instalación",
            command=confirm_install
        ).pack(side="right", padx=5)

    def install_reviewed_mod(self, name, planned):
        folder = MODS / name

        if folder.is_symlink() or not folder.is_dir():
            messagebox.showerror(
                "Mod no disponible",
                "La carpeta del mod ya no existe o no es segura."
            )
            return

        # Recheck the mod after the preview, before making any changes.
        if not self.review_mod(folder):
            return

        try:
            current_files = self.mod_files(folder)
            current_paths = sorted(str(rel) for _, rel in current_files)
            planned_paths = sorted(str(rel) for _, rel, _, _, _ in planned)

            if current_paths != planned_paths:
                raise ValueError(
                    "La lista de archivos cambió después de la vista previa. "
                    "Vuelve a revisar el mod e inténtalo otra vez."
                )

            source_root = folder.resolve(strict=True)

            for source, rel, target, size, expected_hash in planned:
                cursor = folder
                for part in rel.parts:
                    cursor = cursor / part
                    if cursor.is_symlink():
                        raise ValueError(
                            f"La ruta contiene un enlace simbólico: {rel}"
                        )

                if not source.resolve(strict=True).is_relative_to(source_root):
                    raise ValueError(f"El origen está fuera del mod: {rel}")

                if not source.is_file() or source.is_symlink():
                    raise ValueError(f"El origen ya no es un archivo normal: {rel}")

                if sha256_file(source) != expected_hash:
                    raise ValueError(
                        f"El contenido cambió después de la vista previa: {rel}"
                    )

        except (OSError, ValueError) as e:
            messagebox.showerror(
                "Mod modificado",
                f"No se instalará el mod porque falló la comprobación:\n{e}"
            )
            return

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_root = BACKUPS / stamp / name
        records = []
        temporary_files = []

        def atomic_copy(source, destination, expected_hash=None):
            destination.parent.mkdir(parents=True, exist_ok=True)
            temp = destination.with_name(
                destination.name + ".mintstrap_tmp_" + stamp
            )
            temporary_files.append(temp)
            shutil.copy2(source, temp)

            # Verify the temporary copy before replacing the destination.
            if (
                expected_hash is not None
                and sha256_file(temp) != expected_hash
            ):
                raise ValueError(
                    f"El archivo cambió mientras se copiaba: {source.name}"
                )

            os.replace(temp, destination)
            temporary_files.remove(temp)

        try:
            # Validate every destination before changing any files.
            overlay_root = OVERLAY.resolve()

            if OVERLAY.is_symlink():
                raise ValueError(
                    "La carpeta asset_overlay es un enlace simbólico."
                )

            for source, rel, target, size, expected_hash in planned:
                if rel.is_absolute() or ".." in rel.parts:
                    raise ValueError(f"Ruta relativa insegura: {rel}")

                cursor = OVERLAY
                for part in rel.parts:
                    cursor = cursor / part
                    if cursor.is_symlink():
                        raise ValueError(
                            f"El destino atraviesa un enlace simbólico: {rel}"
                        )

                if not target.resolve().is_relative_to(overlay_root):
                    raise ValueError(f"Ruta de destino insegura: {rel}")

                if target.exists() and not target.is_file():
                    raise ValueError(
                        f"El destino existe, pero no es un archivo: {rel}"
                    )

                if not source.is_file() or source.is_symlink():
                    raise ValueError(f"Archivo de origen no válido: {rel}")

            for source, rel, target, size, expected_hash in planned:
                existed_before = target.exists()
                backup = None

                if existed_before:
                    backup = backup_root / rel
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    atomic_copy(target, backup)

                record = {
                    "target": str(rel),
                    "backup": str(backup) if backup else None,
                    "existed_before": existed_before
                }
                # Register before replacing the destination so a failed
                # copy can still be rolled back.
                records.append(record)
                atomic_copy(source, target, expected_hash)

            active[name] = {"files": records}
            save_state()
            self.refresh_mods()
            messagebox.showinfo("Mintstrap", f"Mod «{name}» activado.")

        except Exception as e:
            active.pop(name, None)
            try:
                save_state()
            except Exception:
                pass

            rollback_errors = []
            for record in reversed(records):
                try:
                    target = OVERLAY / record["target"]
                    if not target.resolve().is_relative_to(OVERLAY.resolve()):
                        raise ValueError("Destino fuera del overlay")

                    backup = record.get("backup")
                    if backup and Path(backup).is_file():
                        restore_temp = target.with_name(
                            target.name + ".mintstrap_restore_" + stamp
                        )
                        temporary_files.append(restore_temp)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(backup, restore_temp)
                        os.replace(restore_temp, target)
                        temporary_files.remove(restore_temp)
                    elif not record.get("existed_before", False):
                        if target.exists():
                            target.unlink()
                except Exception as rollback_error:
                    rollback_errors.append(
                        f"{record.get('target')}: {rollback_error}"
                    )

            for temp in temporary_files:
                try:
                    if temp.exists():
                        temp.unlink()
                except OSError:
                    pass

            detail = f"No se pudo completar la instalación:\n{e}"
            if rollback_errors:
                detail += (
                    "\n\nATENCIÓN: algunos archivos no pudieron "
                    "restaurarse automáticamente:\n"
                    + "\n".join(rollback_errors[:10])
                )
            messagebox.showerror("Error al activar", detail)

    def deactivate_mod(self):
        name = self.get_selected_mod()
        if name is None:
            return
        if name not in active:
            messagebox.showinfo("Mintstrap", "Este mod no está activo.")
            return

        if not messagebox.askyesno(
            "Confirmar desactivación",
            f"¿Desactivar «{name}» y restaurar sus copias de seguridad?"
        ):
            return

        records = active[name].get("files", [])
        previous_state = active[name]
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        rollback_root = BACKUPS / ("deactivation_rollback_" + stamp) / name
        snapshots = []
        plan = []
        temporary_files = []
        rollback_errors = []
        overlay_root = OVERLAY.resolve()
        backups_root = BACKUPS.resolve()

        def atomic_copy(source, destination, label):
            destination.parent.mkdir(parents=True, exist_ok=True)
            temp = destination.with_name(
                destination.name + ".mintstrap_" + label + "_" + stamp
            )
            temporary_files.append(temp)
            shutil.copy2(source, temp)
            os.replace(temp, destination)
            temporary_files.remove(temp)

        try:
            # Validate every path before changing the overlay.
            for record in records:
                if not isinstance(record, dict):
                    raise ValueError("Registro de archivo no válido.")

                raw = record.get("target")
                if not isinstance(raw, str) or not raw:
                    raise ValueError("Falta la ruta de un archivo.")

                rel = Path(raw)
                if rel.is_absolute() or ".." in rel.parts:
                    raise ValueError(f"Ruta relativa insegura: {raw}")

                if OVERLAY.is_symlink():
                    raise ValueError(
                        "La carpeta asset_overlay es un enlace simbólico."
                    )

                cursor = OVERLAY
                for part in rel.parts:
                    cursor = cursor / part
                    if cursor.is_symlink():
                        raise ValueError(
                            f"La ruta atraviesa un enlace simbólico: {raw}"
                        )

                target = OVERLAY / rel
                if not target.resolve().is_relative_to(overlay_root):
                    raise ValueError(f"Destino fuera del overlay: {raw}")
                if target.exists() and not target.is_file():
                    raise ValueError(f"El destino no es un archivo: {raw}")

                backup_value = record.get("backup")
                backup = Path(backup_value) if backup_value else None

                if backup is not None:
                    if (
                        not backup.resolve().is_relative_to(backups_root)
                        or backup.is_symlink()
                        or not backup.is_file()
                    ):
                        raise ValueError(
                            f"No se encontró una copia segura para: {raw}"
                        )

                plan.append((rel, target, backup))

            # Snapshot the current files before restoring anything.
            for rel, target, backup in plan:
                existed = target.is_file()
                snapshot = rollback_root / rel if existed else None

                if existed:
                    snapshot.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, snapshot)

                snapshots.append({
                    "target": target,
                    "existed": existed,
                    "snapshot": snapshot,
                })

            # Restore original files or remove files created by the mod.
            for rel, target, backup in reversed(plan):
                if backup is not None:
                    atomic_copy(backup, target, "restore")
                elif target.exists():
                    target.unlink()

            del active[name]
            save_state()
            self.refresh_mods()

        except Exception as e:
            # Restore the pre-deactivation contents in reverse order.
            for snap in reversed(snapshots):
                try:
                    target = snap["target"]
                    if not target.parent.resolve().is_relative_to(overlay_root):
                        raise ValueError("La carpeta de destino cambió.")

                    if snap["existed"]:
                        atomic_copy(snap["snapshot"], target, "rollback")
                    elif target.exists() or target.is_symlink():
                        target.unlink()
                except Exception as rollback_error:
                    rollback_errors.append(str(rollback_error))

            active[name] = previous_state
            try:
                save_state()
            except Exception as state_error:
                rollback_errors.append(
                    f"No se pudo guardar el estado: {state_error}"
                )

            for temp in temporary_files:
                try:
                    if temp.exists():
                        temp.unlink()
                except OSError:
                    pass

            try:
                self.refresh_mods()
            except Exception:
                pass

            detail = f"No se pudo completar la desactivación:\n{e}"
            if rollback_errors:
                detail += (
                    "\n\nATENCIÓN: la recuperación tuvo problemas. "
                    "No borres esta carpeta de respaldo:\n"
                    + str(rollback_root)
                    + "\n\n"
                    + "\n".join(rollback_errors[:10])
                )
            else:
                try:
                    shutil.rmtree(rollback_root)
                except OSError:
                    pass
                detail += "\n\nSe intentó recuperar el estado anterior."

            messagebox.showerror("Error al desactivar", detail)
            return

        try:
            shutil.rmtree(rollback_root)
        except OSError:
            pass

        messagebox.showinfo(
            "Mintstrap", f"Mod «{name}» desactivado."
        )

if __name__ == "__main__":
    Mintstrap().mainloop()
