import sys
import os
import shutil
import subprocess
import platform
import threading
import time
import tkinter as tk 

# --- CustomTkinter ---
import customtkinter as ctk
from tkinter import messagebox, filedialog
from tkinter import ttk

# --- Otras dependencias ---
from dotenv import load_dotenv
from pathlib import Path
import psutil
import openai
import math
try:
    from PIL import Image, ImageTk # Necesario para el logo
except ImportError:
    # Usar CTkToplevel para el error si CTk ya está importado
    error_win = ctk.CTk()
    error_win.withdraw() # Ocultar ventana raíz temporal
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # APLICAR ICONO A LA VENTANA DE ERROR TEMPORAL
    try:
        # Definir ICON_PATH aquí temporalmente si no está definido globalmente aún
        _ICON_PATH_TEMP = "img/icono.ico"
        if _ICON_PATH_TEMP and os.path.exists(_ICON_PATH_TEMP) and platform.system() == "Windows":
            error_win.iconbitmap(_ICON_PATH_TEMP)
    except Exception as e:
        print(f"Advertencia: No se pudo aplicar el icono a la ventana de error: {e}")
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    messagebox.showerror("Error de Dependencia",
                         "La biblioteca Pillow no está instalada.\n"
                         "Por favor, instálala ejecutando: pip install Pillow")
    error_win.destroy()
    sys.exit(1) # Salir si Pillow no está instalado

# --- Manejo de versiones de OpenAI ---
# Intentar importar errores específicos de v0.x si existen
try:
    from openai import error as openai_error_v0
    AuthenticationError_v0 = openai_error_v0.AuthenticationError
    InvalidRequestError_v0 = openai_error_v0.InvalidRequestError
    APIConnectionError_v0 = openai_error_v0.APIConnectionError
    OPENAI_V0_ERROR_IMPORTED = True
except ImportError:
    OPENAI_V0_ERROR_IMPORTED = False
    # Definir placeholders si v0.x no está o no tiene 'error'
    class OpenAIError_v0(Exception): pass
    class AuthenticationError_v0(OpenAIError_v0): pass
    class InvalidRequestError_v0(OpenAIError_v0): pass
    class APIConnectionError_v0(OpenAIError_v0): pass

# Asumir que si openai.OpenAI existe, es v1.x+
# Los errores en v1.x se importan directamente desde openai
try:
    from openai import AuthenticationError, InvalidRequestError, APIConnectionError, OpenAIError
    OPENAI_V1_CLIENT_EXISTS = hasattr(openai, 'OpenAI')
except ImportError:
    # Si la importación directa falla, probablemente sea v0.x o muy antiguo
    OPENAI_V1_CLIENT_EXISTS = False
    # Definir placeholders para v1 si no se pudieron importar (aunque si v0 existe, esto no debería pasar)
    class OpenAIError(Exception): pass
    class AuthenticationError(OpenAIError): pass
    class InvalidRequestError(OpenAIError): pass
    class APIConnectionError(OpenAIError): pass

import webbrowser

# ======================================================
# Global State & Config Variables
# ======================================================
unity_path_ok = False
unity_version_ok = False
unity_projects_path_ok = False
apis_key_ok = False
apis_models_ok = False
initial_verification_complete = False
is_build_running = False # Flag to track build process

UNITY_EXECUTABLE = None
UNITY_PROJECTS_PATH = None
OPENAI_API_KEY = None
FINE_TUNED_MODEL_NAME = None
SECONDARY_FINE_TUNED_MODEL_NAME = None
UNITY_REQUIRED_VERSION_STRING = "6000.0.32f1" # Versión requerida

SIMULATIONS_DIR = "./Simulations"
SIMULATION_PROJECT_NAME = "Simulation"
SIMULATION_PROJECT_PATH = None
ASSETS_FOLDER = None
STREAMING_ASSETS_FOLDER = None
SIMULATION_LOADED_FILE = None
last_simulation_loaded = None
all_simulations_data = [] # Para almacenar la lista completa de simulaciones para búsqueda

# Icons (text fallback)
play_icon_text = "▶" # "Play"
delete_icon_text = "🗑️" # "Delete"
loaded_indicator_text = "✓" # "Loaded"

# Tooltip handling
tooltip_window = None
tooltip_delay = 700
tooltip_job_id = None

# Referencia global para la imagen del logo
logo_photo_ref = None
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# DEFINIR RUTA DEL ICONO GLOBALMENTE
ICON_PATH = "img/icono.ico" # Ruta al icono .ico
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
LOGO_PATHS = ["img/logo_light.png", "img/logo_dark.png"]
LOGO_WIDTH = 200

# --- CustomTkinter Theme & Font ---
ctk.set_appearance_mode("System") # Modes: system (default), light, dark
ctk.set_default_color_theme("blue") # Themes: blue (default), dark-blue, green

APP_FONT = ("Segoe UI", 11)
APP_FONT_BOLD = ("Segoe UI", 11, "bold")
TITLE_FONT = ("Times New Roman", 22, "bold")
STATUS_FONT = ("Segoe UI", 10)
TREEVIEW_FONT = ("Segoe UI", 10)
TREEVIEW_HEADER_FONT = ("Segoe UI", 10, "bold")

# --- Colores para Botones (Light, Dark) ---
# Mantener colores generales para diálogos u otros elementos si es necesario
COLOR_SUCCESS_GENERAL = ("#28a745", "#4CAF50")
COLOR_DANGER_GENERAL = ("#C62828", "#EF5350")
COLOR_INFO_GENERAL = ("#218838", "#66BB6A") # Azul info más estándar
COLOR_WARNING_GENERAL = ("#E53935", "#E53935") # Naranja warning
COLOR_DISABLED_GENERAL = ("#BDBDBD", "#757575") # Grises para deshabilitado
COLOR_SIDEBAR_BG = None # Se determinará por tema

# --- Helper para obtener color actual (Light=0, Dark=1) ---
def get_color_mode_index():
    return 1 if ctk.get_appearance_mode() == "Dark" else 0

# ======================================================
# INDIVIDUAL BUTTON COLOR DEFINITIONS (FG, HOVER, TEXT)
# Cada tupla contiene (Light Mode Color, Dark Mode Color)
# ======================================================

# --- Sidebar Buttons ---
# Settings Button
# ================================================================
# Refined Button Colors for Modern UI
# Backgrounds: Light Mode ~ #dbdbdb | Dark Mode ~ #2b2b2b
# Format: (light_mode_color, dark_mode_color)
# ================================================================

# --- Neutral Buttons Palette (Used for Settings, Verify, About) ---
# Ensures consistency for standard/secondary actions.
_NEUTRAL_FG_COLOR = ("#A0A0A0", "#616161")     # Light: Med-Gray / Dark: Darker Gray (visible on #2b2b2b)
_NEUTRAL_HOVER_COLOR = ("#888888", "#757575")  # Light: Darker Gray / Dark: Lighter Gray
_NEUTRAL_TEXT_COLOR = ("#000000", "#FFFFFF")   # Light: Black / Dark: White

# Settings Button
BTN_SETTINGS_FG_COLOR = _NEUTRAL_FG_COLOR
BTN_SETTINGS_HOVER_COLOR = _NEUTRAL_HOVER_COLOR
BTN_SETTINGS_TEXT_COLOR = _NEUTRAL_TEXT_COLOR

# Verify Button
BTN_VERIFY_FG_COLOR = _NEUTRAL_FG_COLOR
BTN_VERIFY_HOVER_COLOR = _NEUTRAL_HOVER_COLOR
BTN_VERIFY_TEXT_COLOR = _NEUTRAL_TEXT_COLOR

# About Button
BTN_ABOUT_FG_COLOR = _NEUTRAL_FG_COLOR
BTN_ABOUT_HOVER_COLOR = _NEUTRAL_HOVER_COLOR
BTN_ABOUT_TEXT_COLOR = _NEUTRAL_TEXT_COLOR

# --- Specific Action Buttons ---

# Download Unity Hub Button (Green)
BTN_UNITY_DOWN_FG_COLOR = ("#4CAF50", "#4CAF50") # Light: Std Green / Dark: Std Green (visible on dark bg)
BTN_UNITY_DOWN_HOVER_COLOR = ("#388E3C", "#66BB6A") # Light: Darker Green / Dark: Lighter Green
BTN_UNITY_DOWN_TEXT_COLOR = ("#FFFFFF", "#FFFFFF") # Light: White / Dark: White

# Exit Button (Red)
BTN_EXIT_FG_COLOR = ("#E53935", "#E53935")     # Light: Std Red / Dark: Std Red (visible on dark bg)
BTN_EXIT_HOVER_COLOR = ("#C62828", "#EF5350")     # Light: Darker Red / Dark: Lighter Red
BTN_EXIT_TEXT_COLOR = ("#FFFFFF", "#FFFFFF")     # Light: White / Dark: White

# Reload List Button (Blue)
BTN_RELOAD_FG_COLOR = ("#1E88E5", "#1E88E5")     # Light: Std Blue / Dark: Std Blue (visible on dark bg)
BTN_RELOAD_HOVER_COLOR = ("#1565C0", "#42A5F5")     # Light: Darker Blue / Dark: Lighter Blue
BTN_RELOAD_TEXT_COLOR = ("#FFFFFF", "#FFFFFF")     # Light: White / Dark: White

# Show Graphs Button (Purple)
BTN_GRAPH_FG_COLOR = ("#673AB7", "#673AB7")     # Light: Std Purple / Dark: Std Purple (visible on dark bg)
BTN_GRAPH_HOVER_COLOR = ("#512DA8", "#7E57C2")     # Light: Darker Purple / Dark: Lighter Purple
BTN_GRAPH_TEXT_COLOR = ("#FFFFFF", "#FFFFFF")     # Light: White / Dark: White

# Create Sim (API) Button (Green - Primary/Positive Action)
BTN_CREATE_FG_COLOR = ("#28a745", "#4CAF50")     # Light: Bright Green (Bootstrap) / Dark: Std Green (Material)
BTN_CREATE_HOVER_COLOR = ("#218838", "#66BB6A")     # Light: Darker Green / Dark: Lighter Green
BTN_CREATE_TEXT_COLOR = ("#FFFFFF", "#FFFFFF")     # Light: White / Dark: White

# --- Search Bar ---
# Clear Search Button (Orange/Amber - Warning/Utility)
BTN_CLEARSEARCH_FG_COLOR = ("#E53935", "#E53935") # Light: Amber / Dark: Orange
BTN_CLEARSEARCH_HOVER_COLOR = ("#C62828", "#EF5350") # Light: Orange / Dark: Lighter Orange/Amber
BTN_CLEARSEARCH_TEXT_COLOR = ("#FFFFFF", "#FFFFFF") # Light: Black (Good contrast on Amber) / Dark: White (Better harmony)
# ================================================================

# ======================================================
# GUI Utilities & Interaction Control
# ======================================================
def center_window(window, width, height):
    window.update_idletasks()
    sw, sh = window.winfo_screenwidth(), window.winfo_screenheight()
    x, y = (sw - width) // 2, (sh - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# FUNCIÓN PARA APLICAR EL ICONO
def apply_icon(window):
    """Aplica el icono global (ICON_PATH) a la ventana dada."""
    try:
        # Comprobar si la ruta del icono está definida, existe el archivo y estamos en Windows
        if ICON_PATH and os.path.exists(ICON_PATH) and platform.system() == "Windows":
            window.iconbitmap(ICON_PATH)
        # Opcional: Podrías añadir lógica para otros OS aquí usando iconphoto si tuvieras un .png
        # elif ICON_PATH_PNG and os.path.exists(ICON_PATH_PNG):
        #     img = tk.PhotoImage(file=ICON_PATH_PNG)
        #     # Para que funcione en Toplevels después de cerrar main, la imagen debe ser referenciada
        #     window.tk.call('wm', 'iconphoto', window._w, img) # Forma estándar
        #     # O almacenar la referencia en la ventana misma si es necesario:
        #     # window.iconphoto(True, img) # CTk/Tkinter forma
        #     # window._icon_photo_ref = img # Mantener referencia explícita
    except tk.TclError as e:
        # Error común si el formato del icono es inválido o la ventana no lo soporta
        print(f"Advertencia: Icono '{ICON_PATH}' no aplicable a una ventana. Error: {e}")
    except Exception as e:
        # Captura cualquier otro error inesperado
        print(f"Error inesperado al aplicar icono: {e}")
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

class CustomInputDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, prompt, width=400, height=170):
        super().__init__(parent)
        self.title(title)
        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        apply_icon(self) # Aplicar icono al crear el diálogo
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        center_window(self, width, height)
        self.resizable(False, False); self.transient(parent); self.grab_set()
        self.result = None

        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure((0, 1), weight=1); self.grid_rowconfigure(2, weight=0)
        ctk.CTkLabel(self, text=prompt, font=APP_FONT).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.entry = ctk.CTkEntry(self, font=APP_FONT, width=width-40); self.entry.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        button_frame = ctk.CTkFrame(self, fg_color="transparent"); button_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="e")
        # Usar colores generales para diálogos por simplicidad
        mode_idx = get_color_mode_index()
        ok_button = ctk.CTkButton(button_frame, text="OK", command=self.ok, width=80, font=APP_FONT, fg_color=COLOR_SUCCESS_GENERAL[mode_idx]); ok_button.pack(side="left", padx=(0, 10))
        cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=self.cancel, width=80, font=APP_FONT, fg_color=COLOR_WARNING_GENERAL[mode_idx], hover_color=COLOR_DANGER_GENERAL[mode_idx]); cancel_button.pack(side="left")
        self.bind("<Return>", lambda e: self.ok()); self.bind("<Escape>", lambda e: self.cancel())
        self.entry.focus(); self.wait_window()
    def ok(self): self.result = self.entry.get(); self.destroy()
    def cancel(self): self.destroy()

def custom_askstring(title, prompt):
    if 'main_window' in globals() and main_window.winfo_exists(): return CustomInputDialog(main_window, title, prompt).result
    print(f"Warn: Main window N/A for dialog '{title}'."); return None

# --- Tooltip Functions ---
def show_tooltip(widget, text):
    global tooltip_window; hide_tooltip()
    try: x, y = widget.winfo_pointerxy(); x += 20; y += 10 # Default position near cursor
    except: return # If widget destroyed
    if isinstance(widget, ttk.Treeview): pass # Keep cursor position for treeview
    else:
        try: x, y, h = widget.winfo_rootx(), widget.winfo_rooty(), widget.winfo_height(); y += h + 5 # Below widget
        except: pass # Use cursor pos if fails
    tooltip_window = tk.Toplevel(widget); tooltip_window.wm_overrideredirect(True); tooltip_window.wm_geometry(f"+{x}+{y}")
    # Nota: Las ventanas con overrideredirect(True) normalmente no muestran icono. No llamamos a apply_icon aquí.
    label = tk.Label(tooltip_window, text=text, justify='left', background="#ffffe0", relief='solid', borderwidth=1, font=("Segoe UI", 9)); label.pack(ipadx=1)

def hide_tooltip():
    global tooltip_window
    if tooltip_window:
        try: tooltip_window.destroy()
        except tk.TclError: pass
        tooltip_window = None

def schedule_tooltip(widget, text):
    global tooltip_job_id; cancel_tooltip(widget)
    tooltip_job_id = widget.after(tooltip_delay, lambda: show_tooltip(widget, text))

def cancel_tooltip(widget):
    global tooltip_job_id
    if tooltip_job_id: widget.after_cancel(tooltip_job_id); tooltip_job_id = None
    hide_tooltip()

# --- Interaction Control ---
def disable_all_interactions():
    global is_build_running; is_build_running = True
    try:
        for btn in [reload_btn, graph_btn, create_btn]: btn.configure(state="disabled")
        if 'sidebar_frame' in globals():
            for w in sidebar_frame.winfo_children():
                if isinstance(w, (ctk.CTkButton, ctk.CTkSwitch)): w.configure(state="disabled")
        if 'search_entry' in globals(): search_entry.configure(state="disabled")
        if 'clear_search_btn' in globals(): clear_search_btn.configure(state="disabled")
        sim_tree.unbind("<Button-1>"); sim_tree.unbind("<Motion>"); sim_tree.configure(cursor="watch")
        update_status("Build in progress... Please wait.")
    except (NameError, tk.TclError) as e: print(f"Warning: Could not disable interactions: {e}")

def enable_all_interactions():
    global is_build_running; is_build_running = False
    try:
        if 'sidebar_frame' in globals():
            for w in sidebar_frame.winfo_children():
                if isinstance(w, (ctk.CTkButton, ctk.CTkSwitch)): w.configure(state="normal")
        if 'search_entry' in globals(): search_entry.configure(state="normal")
        if 'clear_search_btn' in globals(): clear_search_btn.configure(state="normal")
        sim_tree.bind("<Button-1>", handle_tree_click); sim_tree.bind("<Motion>", handle_tree_motion)
        sim_tree.configure(cursor="")
        update_button_states() # Update based on current state
    except (NameError, tk.TclError) as e: print(f"Warning: Could not re-enable interactions: {e}")


# ======================================================
# Core Utilities & Error Handling
# ======================================================
def update_status(message):
    if 'main_window' in globals() and main_window.winfo_exists(): main_window.after(0, lambda: status_label.configure(text=str(message)))
    else: print(f"Status (GUI !ready): {message}")

def handle_unity_execution_error(e, operation_name="operation"):
    err_msg = (f"Error during Unity {operation_name}.\n\nDetails: {type(e).__name__}: {str(e)}\n\n"
               f"Check Unity installation/version ({UNITY_REQUIRED_VERSION_STRING}) and path.\n"
               "Consider reinstalling Unity Editor.")
    print(f"Unity Error ({operation_name}): {e}")
    if 'main_window' in globals() and main_window.winfo_exists(): main_window.after(0, lambda: messagebox.showerror("Unity Execution Error", err_msg))
    else: print("Critical error: " + err_msg)

def ensure_unity_closed():
    if not unity_path_ok or not UNITY_EXECUTABLE: return
    procs = []
    try:
        norm_exe = os.path.normcase(UNITY_EXECUTABLE)
        for p in psutil.process_iter(['exe', 'pid']):
            try:
                if p.info['exe'] and os.path.normcase(p.info['exe']) == norm_exe: procs.append(p)
            except (psutil.Error, TypeError, AttributeError): continue
    except Exception as ex: print(f"Error listing procs: {ex}"); return
    if procs:
        t_start = time.time(); print(f"Attempting to close {len(procs)} Unity instances...")
        for p in procs:
            try: p.terminate()
            except psutil.Error: pass
        _, alive = psutil.wait_procs(procs, timeout=5)
        if alive:
            print(f"{len(alive)} instances did not terminate gracefully, killing...")
            for p in alive:
                try: p.kill()
                except psutil.Error: pass
            _, alive_after_kill = psutil.wait_procs(alive, timeout=3)
            if alive_after_kill: print(f"Warning: {len(alive_after_kill)} Unity instances could not be closed.")
        print(f"Unity close check took {time.time()-t_start:.2f}s")

def open_graphs_folder(simulation_name):
    try:
        fldr = Path.home()/"Documents"/"SimulationLoggerData"/simulation_name/"Graficos"
        fldr.mkdir(parents=True, exist_ok=True)
        if platform.system() == "Windows": os.startfile(str(fldr))
        elif platform.system() == "Darwin": subprocess.Popen(["open", str(fldr)])
        else: subprocess.Popen(["xdg-open", str(fldr)])
    except Exception as e: messagebox.showerror("Error", f"Could not open graphs folder '{fldr}':\n{e}")

def get_folder_size(path):
    total = 0;
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False): total += entry.stat(follow_symlinks=False).st_size
            elif entry.is_dir(follow_symlinks=False): total += get_folder_size(entry.path)
    except Exception: pass
    return total

def copy_directory(src, dst):
    try:
        if os.path.exists(dst): shutil.rmtree(dst, ignore_errors=True); time.sleep(0.1)
        shutil.copytree(src, dst, symlinks=False, ignore_dangling_symlinks=True); return True
    except Exception as e:
        msg = f"Error copying {src} to {dst}:\n{e}"; print(msg)
        if 'main_window' in globals() and main_window.winfo_exists(): main_window.after(0, lambda: messagebox.showerror("Copy Error", msg))
        return False

def get_build_target_and_executable(project_path):
    if not project_path: return "Unknown", None
    sistema = platform.system(); exe_name = SIMULATION_PROJECT_NAME
    if sistema == "Windows": target, pfolder, suff = "Win64", "Windows", ".exe"
    elif sistema == "Linux": target, pfolder, suff = "Linux64", "Linux", ""
    elif sistema == "Darwin": target, pfolder, suff = "OSXUniversal", "Mac", ".app"
    else: target, pfolder, suff = "Win64", "Windows", ".exe"
    build_base = os.path.join(project_path, "Build", pfolder)
    ejecutable = os.path.join(build_base, exe_name + suff)
    return target, ejecutable

# ======================================================
# Simulation Logic
# ======================================================
def get_simulations():
    sims = []
    if not os.path.isdir(SIMULATIONS_DIR): return sims
    try:
        for item in os.listdir(SIMULATIONS_DIR):
            p = os.path.join(SIMULATIONS_DIR, item)
            if os.path.isdir(p) and all(os.path.exists(os.path.join(p, r)) for r in ["Assets", "ProjectSettings"]):
                c_str, l_str = "???", "Never"; c_ts, l_ts = 0, 0
                try: c_ts = os.path.getctime(p); c_str = time.strftime("%y-%m-%d %H:%M", time.localtime(c_ts))
                except: pass
                l_file = os.path.join(p, "last_opened.txt")
                if os.path.exists(l_file):
                    try:
                        with open(l_file, "r") as f: l_ts = float(f.read().strip())
                        l_str = time.strftime("%y-%m-%d %H:%M", time.localtime(l_ts))
                    except: pass
                sims.append({"name": item, "creation": c_str, "last_opened": l_str, "creation_ts": c_ts})
    except Exception as e: print(f"Err reading sims: {e}"); return []
    return sims

def update_last_opened(sim_name):
    folder = os.path.join(SIMULATIONS_DIR, sim_name)
    try: os.makedirs(folder, exist_ok=True);
    except: pass
    try:
        with open(os.path.join(folder, "last_opened.txt"), "w") as f: f.write(str(time.time()))
    except Exception as e: print(f"[Err] update_last_opened({sim_name}): {e}")

def read_last_loaded_simulation_name():
    if SIMULATION_LOADED_FILE and os.path.exists(SIMULATION_LOADED_FILE):
        try:
            with open(SIMULATION_LOADED_FILE, "r") as f: return f.read().strip()
        except Exception as e: print(f"Error reading {SIMULATION_LOADED_FILE}: {e}")
    return None

def load_simulation(sim_name):
    global last_simulation_loaded, SIMULATION_PROJECT_PATH, ASSETS_FOLDER, STREAMING_ASSETS_FOLDER, SIMULATION_LOADED_FILE
    if not unity_projects_path_ok or not UNITY_PROJECTS_PATH: messagebox.showerror("Config Error", "Invalid Unity projects path."); return False
    SIMULATION_PROJECT_PATH = os.path.join(UNITY_PROJECTS_PATH, SIMULATION_PROJECT_NAME)
    ASSETS_FOLDER = os.path.join(SIMULATION_PROJECT_PATH, "Assets")
    STREAMING_ASSETS_FOLDER = os.path.join(ASSETS_FOLDER, "StreamingAssets")
    SIMULATION_LOADED_FILE = os.path.join(STREAMING_ASSETS_FOLDER, "simulation_loaded.txt")
    src_path = os.path.join(SIMULATIONS_DIR, sim_name)
    if not os.path.isdir(src_path): messagebox.showerror("Error", f"Simulation '{sim_name}' not found."); return False
    try: os.makedirs(SIMULATION_PROJECT_PATH, exist_ok=True)
    except Exception as e: messagebox.showerror("Error", f"Could not create Unity project dir: {e}"); return False

    current_persistent_loaded = read_last_loaded_simulation_name()
    needs_full_copy = (not current_persistent_loaded or current_persistent_loaded != sim_name or not os.path.exists(ASSETS_FOLDER))

    copy_ok = True
    if needs_full_copy:
        update_status("Full copy (Assets, Packages, Settings)...")
        folders = ["Assets", "Packages", "ProjectSettings"]
        for fldr in folders:
            src = os.path.join(src_path, fldr); dst = os.path.join(SIMULATION_PROJECT_PATH, fldr)
            if os.path.exists(src):
                if not copy_directory(src, dst): copy_ok = False; break
            elif fldr in ["Assets", "ProjectSettings"]: messagebox.showwarning("Warning", f"Missing '{fldr}' in sim '{sim_name}'.")
    else:
        update_status("Updating Assets...")
        src_assets = os.path.join(src_path, "Assets"); dst_assets = ASSETS_FOLDER
        if os.path.exists(src_assets): copy_ok = copy_directory(src_assets, dst_assets)
        else: messagebox.showerror("Error", f"Missing 'Assets' in sim '{sim_name}'."); copy_ok = False

    if not copy_ok: update_status("Copy error. Load cancelled."); return False
    try:
        os.makedirs(STREAMING_ASSETS_FOLDER, exist_ok=True);
        with open(SIMULATION_LOADED_FILE, "w") as f: f.write(sim_name)
        print(f"State file updated with: {sim_name}")
    except Exception as e: messagebox.showwarning("Error", f"Could not create StreamingAssets or state file:\n{e}")

    update_last_opened(sim_name); last_simulation_loaded = sim_name
    if 'main_window' in globals() and main_window.winfo_exists(): main_window.after(50, populate_simulations)
    return True

def delete_simulation(sim_name):
    # Corrected messagebox call:
    # Provide title and message as positional arguments, options as keywords.
    confirm = messagebox.askyesno(
        "Confirm Deletion",  # Argument 1: title
        f"Permanently delete '{sim_name}' and all associated data (logs, graphs)?\n\nThis action cannot be undone.", # Argument 2: message
        icon='warning'       # Keyword argument for options
        # Removed the duplicate title="Confirm Deletion" keyword argument
    )

    if not confirm:
        update_status("Deletion cancelled.")
        return

    update_status(f"Deleting '{sim_name}'...")
    errs = False
    global last_simulation_loaded, all_simulations_data

    # --- State file handling ---
    # Check SIMULATION_LOADED_FILE existence *before* trying to use it
    loaded_sim_path = SIMULATION_LOADED_FILE # Use a local variable for clarity
    if loaded_sim_path and os.path.exists(loaded_sim_path):
        try:
            # It's generally safer to read the file *once* if needed multiple times
            loaded = read_last_loaded_simulation_name()
            if loaded == sim_name:
                os.remove(loaded_sim_path)
                print(f"State file '{loaded_sim_path}' removed.")
                # Also clear the global if it matches, regardless of file content
                if last_simulation_loaded == sim_name:
                    last_simulation_loaded = None
            # If the file existed but didn't contain sim_name, we might still need to clear the global
            elif last_simulation_loaded == sim_name:
                 last_simulation_loaded = None

        except Exception as e:
            # Be more specific about the warning if possible
            print(f"Warn: Could not read or remove state file '{loaded_sim_path}': {e}")
    # Ensure global is cleared even if state file didn't exist or couldn't be read
    elif last_simulation_loaded == sim_name:
         last_simulation_loaded = None


    # --- Simulation directory deletion ---
    sim_p = os.path.join(SIMULATIONS_DIR, sim_name)
    if os.path.exists(sim_p):
        try:
            # Using ignore_errors=True might hide underlying issues.
            # It's often better to try rmtree once and handle specific exceptions if needed.
            # The time.sleep is unlikely to be necessary unless dealing with specific OS locking issues.
            shutil.rmtree(sim_p)
            print(f"Simulation directory '{sim_p}' removed.")
        except PermissionError as e:
             messagebox.showerror("Error", f"Permission denied deleting simulation folder:\n{sim_p}\n{e}")
             errs = True
        except OSError as e: # Catch other OS-level errors
             messagebox.showerror("Error", f"Could not delete simulation folder:\n{sim_p}\n{e}")
             errs = True
        except Exception as e: # Catch unexpected errors
             messagebox.showerror("Error", f"An unexpected error occurred deleting simulation folder:\n{sim_p}\n{e}")
             errs = True

    # --- Data directory deletion ---
    # Use try-except around Path.home() in case it fails (less likely but possible)
    try:
        # Use Path objects consistently for cleaner path handling
        data_p = Path.home() / "Documents" / "SimulationLoggerData" / sim_name
        if data_p.is_dir(): # Check if it exists *and* is a directory
            try:
                shutil.rmtree(data_p)
                print(f"Data directory '{data_p}' removed.")
            except PermissionError as e:
                messagebox.showerror("Error", f"Permission denied deleting data folder:\n{data_p}\n{e}")
                errs = True
            except OSError as e: # Catch other OS-level errors
                 messagebox.showerror("Error", f"Could not delete data folder:\n{data_p}\n{e}")
                 errs = True
            except Exception as e: # Catch unexpected errors
                messagebox.showerror("Error", f"An unexpected error occurred deleting data folder:\n{data_p}\n{e}")
                errs = True
    except Exception as e:
         print(f"Warn: Could not determine or access data directory path: {e}")
         # Decide if this constitutes an error for the final status message
         # errs = True # Optionally mark as error if data dir is critical

    # --- Update internal data structure ---
    # Create a new list excluding the deleted simulation
    all_simulations_data = [s for s in all_simulations_data if s.get('name') != sim_name] # Use .get for safety

    # --- Final status update and UI refresh ---
    if errs:
        update_status(f"Deletion of '{sim_name}' completed with errors.")
    else:
        update_status(f"Deletion of '{sim_name}' successful.")

    populate_simulations() # Refresh the UI list


# ======================================================
# Unity Batch Execution & Progress Monitoring
# ======================================================
def format_time(seconds):
    if seconds is None or seconds < 0 or math.isinf(seconds) or math.isnan(seconds): return "--:--:--"
    if seconds == 0: return "0s"
    seconds = int(seconds); h, rem = divmod(seconds, 3600); m, s = divmod(rem, 60)
    if h > 0: return f"{h:02d}:{m:02d}:{s:02d}"
    elif m > 0: return f"{m:02d}:{s:02d}"
    else: return f"{s}s"

def monitor_unity_progress(stop_event, operation_tag):
    if not SIMULATION_PROJECT_PATH or not os.path.exists(SIMULATION_PROJECT_PATH): print(f"\nWarn: '{SIMULATION_PROJECT_PATH}' missing on monitor start."); return
    TARGET_MB = 3000.0; MB = 1024*1024; TARGET_BYTES = TARGET_MB * MB
    last_update = 0; start_time = time.time(); initial_bytes = 0; eta_str = "Calculating..."
    try: initial_bytes = get_folder_size(SIMULATION_PROJECT_PATH)
    except Exception as e: print(f"\nError get initial size: {e}"); initial_bytes = 0
    initial_mb = initial_bytes / MB
    print(f"[{operation_tag}] Monitor... Initial: {initial_mb:.1f}MB. Target: {TARGET_MB:.0f}MB")
    while not stop_event.is_set():
        now = time.time()
        if now - last_update > 1.5:
            current_bytes = 0
            try:
                current_bytes = get_folder_size(SIMULATION_PROJECT_PATH); current_mb = current_bytes / MB
                elapsed = now - start_time; increase = current_bytes - initial_bytes
                if elapsed > 5 and increase > 1024:
                    rate = increase / elapsed; remaining = TARGET_BYTES - current_bytes
                    if rate > 0 and remaining > 0: eta_sec = remaining / rate; eta_str = f"ETA: {format_time(eta_sec)}"
                    elif remaining <= 0: eta_str = "ETA: Completed"
                    else: eta_str = "ETA: --"
                elif elapsed <= 5: eta_str = "ETA: Calculating..."
                else: eta_str = "ETA: --"
                progress = (current_mb / TARGET_MB) * 100 if TARGET_MB > 0 else 0; display_p = min(progress, 100.0)
                msg = (f"[{operation_tag}] {current_mb:.1f}/{TARGET_MB:.0f}MB ({display_p:.1f}%) - {eta_str}      ")
                update_status(msg)
            except Exception as e: err_msg = f"Err read size: {e}"[:30]; update_status(f"[{operation_tag}] {err_msg}... - {eta_str}      ")
            last_update = now
        time.sleep(0.5)
    final_mb = get_folder_size(SIMULATION_PROJECT_PATH) / MB
    print(f"\n[{operation_tag}] Monitor end. Final size: {final_mb:.1f}MB")

def run_unity_batchmode(exec_method, op_name, log_file, timeout=600, extra_args=None):
    if not all([unity_path_ok, unity_version_ok, unity_projects_path_ok, SIMULATION_PROJECT_PATH]): update_status(f"Error: Cannot {op_name}. Check Unity config."); return False, None
    log_path = os.path.join(SIMULATION_PROJECT_PATH, log_file)
    cmd = [UNITY_EXECUTABLE, "-batchmode", "-quit", "-projectPath", os.path.normpath(SIMULATION_PROJECT_PATH), "-executeMethod", exec_method, "-logFile", log_path]
    if extra_args: cmd.extend(extra_args)
    success = False; stop = threading.Event(); exe_path = None
    monitor = threading.Thread(target=monitor_unity_progress, args=(stop, op_name.capitalize()), daemon=True)
    try:
        update_status(f"[{op_name.capitalize()}] Starting Unity..."); monitor.start()
        flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        proc = subprocess.run(cmd, check=True, timeout=timeout, creationflags=flags, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        print(f"--- Unity Stdout ({op_name}) ---\n{proc.stdout[-1000:]}\n---");
        if proc.stderr: print(f"--- Unity Stderr ({op_name}) ---\n{proc.stderr[-1000:]}\n---")
        update_status(f"[{op_name.capitalize()}] Unity process finished."); success = True
        if "BuildScript.PerformBuild" in exec_method:
            update_status(f"[{op_name.capitalize()}] Verifying build output..."); _, exe_path = get_build_target_and_executable(SIMULATION_PROJECT_PATH); found = False
            for attempt in range(6):
                if exe_path and os.path.exists(exe_path): found = True; print(f"DEBUG build: OK (att {attempt+1}): {exe_path}"); break
                print(f"DEBUG build: Check att {attempt+1} fail for {exe_path}"); time.sleep(0.5)
            if found: update_status(f"[{op_name.capitalize()}] Executable verified.")
            else: print(f"WARN build: Executable NOT FOUND: {exe_path}"); success = False; handle_unity_execution_error(FileNotFoundError(f"Build output not found: {exe_path}"), op_name); update_status(f"[Error] {op_name.capitalize()} failed: Output missing.")
    except subprocess.CalledProcessError as e: handle_unity_execution_error(e, op_name); update_status(f"[Error] {op_name.capitalize()} fail (code {e.returncode}). Log: {log_path}"); print(f"--- Unity Output on Error ({op_name}) ---\n{e.stdout}\n{e.stderr}")
    except subprocess.TimeoutExpired as e: handle_unity_execution_error(e, op_name); update_status(f"[Error] {op_name.capitalize()} timed out. Log: {log_path}")
    except (FileNotFoundError, PermissionError) as e: handle_unity_execution_error(e, op_name); update_status(f"[Error] {op_name.capitalize()} fail (File/Perm).")
    except Exception as e: handle_unity_execution_error(e, f"{op_name} (unexpected)"); update_status(f"[Error] Unexpected error during {op_name}.")
    finally: stop.set(); monitor.join(timeout=1.0)
    return success, exe_path

def run_prefab_material_tool():
    success, _ = run_unity_batchmode("PrefabMaterialCreator.CreatePrefabsAndMaterials", "prefabs tool", "prefab_tool_log.txt", timeout=600)
    return success

def build_simulation_task(extra_args, callback):
    disable_all_interactions()
    success, final_exe = run_unity_batchmode("BuildScript.PerformBuild", "build", "build_log.txt", timeout=1800, extra_args=extra_args)
    if callback: main_window.after(0, lambda s=success, p=final_exe: callback(s, p))
    main_window.after(10, enable_all_interactions)

def build_simulation_threaded(callback=None):
    target, _ = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
    if not target: print("Error: Cound not determine build target"); update_status("Error: Build target unknown."); return
    threading.Thread(target=lambda: build_simulation_task(["-buildTarget", target], callback), daemon=True).start()

def open_simulation_executable():
    if not SIMULATION_PROJECT_PATH: update_status("Error: Project path not set."); return
    _, exe_path = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
    if not exe_path: messagebox.showerror("Error", "Could not determine executable path."); return
    if os.path.exists(exe_path):
        try:
            update_status(f"Launching: {os.path.basename(exe_path)}...")
            if platform.system() == "Darwin": subprocess.Popen(["open", exe_path])
            elif platform.system() == "Windows": os.startfile(exe_path)
            else:
                if not os.access(exe_path, os.X_OK): os.chmod(exe_path, 0o755)
                subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
        except Exception as e: handle_unity_execution_error(e, f"run built sim ({os.path.basename(exe_path)})"); update_status(f"Error launching: {e}")
    else: messagebox.showerror("Error", f"Executable not found:\n{exe_path}\nPlease build the simulation first."); update_status("Error: Executable not found.")

def open_in_unity():
    if not all([unity_path_ok, unity_projects_path_ok, UNITY_EXECUTABLE, SIMULATION_PROJECT_PATH]): messagebox.showerror("Error", "Cannot open in Unity. Check config."); return
    if not os.path.isdir(SIMULATION_PROJECT_PATH): messagebox.showerror("Error", f"Project path does not exist:\n{SIMULATION_PROJECT_PATH}"); return
    try:
        update_status(f"Opening project in Unity Editor..."); cmd = [UNITY_EXECUTABLE, "-projectPath", os.path.normpath(SIMULATION_PROJECT_PATH)]
        subprocess.Popen(cmd); update_status("Launching Unity Editor...")
    except Exception as e: handle_unity_execution_error(e, "open in Unity")

# ======================================================
# API Simulation Creation
# ======================================================
def create_simulation_thread(sim_name, sim_desc, original_states):
    update_status(f"Creating '{sim_name}' via API...");
    try: os.makedirs(SIMULATIONS_DIR, exist_ok=True)
    except Exception as e: messagebox.showerror("Critical Error", f"Could not create simulations dir: {e}"); update_status("Critical dir error."); main_window.after(0, enable_all_interactions); return
    success = False
    try:
        api_script = Path("./Scripts/api_manager.py").resolve()
        if not api_script.exists(): raise FileNotFoundError(f"API script not found: {api_script}")
        cmd = [sys.executable, str(api_script), sim_name, sim_desc]
        flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300, creationflags=flags, encoding='utf-8', errors='ignore')
        update_status(f"'{sim_name}' created successfully."); main_window.after(0, lambda: messagebox.showinfo("Success", f"Simulation '{sim_name}' created successfully via API.\n\nOutput:\n{result.stdout[:500]}..."))
        global all_simulations_data; all_simulations_data = get_simulations()
        main_window.after(50, populate_simulations); success = True
    except FileNotFoundError as e: main_window.after(0, lambda: messagebox.showerror("Critical Error", f"Required API script not found:\n{e}")); update_status("Error: Missing API script.")
    except subprocess.CalledProcessError as e:
        err_out = e.stderr if e.stderr else e.stdout; code=e.returncode; msg = f"API Script Error (Code: {code})"; details = f"Error creating simulation '{sim_name}'.\n\nReturn Code: {code}\n\nOutput/Error:\n{err_out}";
        print(f"--- API Script Error Output (Code {code}) ---\n{err_out}\n--- End API Script Error Output ---")
        main_window.after(0, lambda m=msg, d=details: messagebox.showerror(m, d))
        update_status(f"Error: API script failed (Code {code}). Check console.")
    except subprocess.TimeoutExpired: main_window.after(0, lambda: messagebox.showerror("Error", "Simulation creation via API timed out.")); update_status("Error: API creation timeout.")
    except Exception as e: main_window.after(0, lambda: messagebox.showerror("Unexpected Error", f"CRITICAL ERROR during API creation:\n{type(e).__name__}: {e}")); update_status("Critical API creation error."); print(f"Err create_sim_thread: {e}"); import traceback; traceback.print_exc()
    finally: main_window.after(100, enable_all_interactions)

# ======================================================
# Verification Logic (OpenAI v0.x/v1.x compatible)
# ======================================================
def perform_verification(show_results_box=False, on_startup=False):
    global unity_path_ok, unity_version_ok, unity_projects_path_ok, apis_key_ok, apis_models_ok, initial_verification_complete
    global UNITY_EXECUTABLE, UNITY_PROJECTS_PATH, OPENAI_API_KEY, FINE_TUNED_MODEL_NAME, SECONDARY_FINE_TUNED_MODEL_NAME
    global SIMULATION_PROJECT_PATH, ASSETS_FOLDER, STREAMING_ASSETS_FOLDER, SIMULATION_LOADED_FILE, last_simulation_loaded, all_simulations_data

    if not on_startup: update_status("Verifying configuration...")
    load_dotenv('.env', override=True)
    UNITY_EXECUTABLE = os.environ.get("UNITY_EXECUTABLE"); UNITY_PROJECTS_PATH = os.environ.get("UNITY_PROJECTS_PATH")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY"); FINE_TUNED_MODEL_NAME = os.getenv("FINE_TUNED_MODEL_NAME")
    SECONDARY_FINE_TUNED_MODEL_NAME = os.getenv("2ND_FINE_TUNED_MODEL_NAME")
    results = []; unity_path_ok=unity_version_ok=unity_projects_path_ok=apis_key_ok=apis_models_ok=False
    req_ver = UNITY_REQUIRED_VERSION_STRING

    # --- Verify Unity Executable and Version ---
    if not UNITY_EXECUTABLE: results.append("❌ Unity Exe: Path missing in .env file.")
    elif not os.path.isfile(UNITY_EXECUTABLE): results.append(f"❌ Unity Exe: Path invalid or not found:\n   '{UNITY_EXECUTABLE}'")
    else:
        unity_path_ok = True; results.append(f"✅ Unity Exe: Path OK.")
        try:
            editor_folder = "Editor"; exe_name = "Unity.exe" if platform.system() == "Windows" else "Unity"
            expected_suffix = os.path.join(req_ver, editor_folder, exe_name)
            normalized_exe_path = os.path.normcase(os.path.abspath(UNITY_EXECUTABLE))
            normalized_suffix = os.path.normcase(expected_suffix)
            if normalized_exe_path.endswith(normalized_suffix):
                unity_version_ok = True; results.append(f"✅ Unity Ver: Path ends correctly with '{expected_suffix}'.")
            else:
                parent_dir = os.path.dirname(normalized_exe_path)
                results.append(f"❌ Unity Ver: Path NOT end with '{expected_suffix}'.\n   Found: '...{os.path.sep}{os.path.basename(parent_dir)}{os.path.sep}{os.path.basename(normalized_exe_path)}'")
        except Exception as path_err: results.append(f"⚠️ Unity Ver: Path check error: {path_err}")

    # --- Verify Unity Projects Path ---
    if not UNITY_PROJECTS_PATH: results.append("❌ Projects Path: Missing in .env file.")
    elif not os.path.isdir(UNITY_PROJECTS_PATH): results.append(f"❌ Projects Path: Invalid or not a directory:\n   '{UNITY_PROJECTS_PATH}'")
    else:
        unity_projects_path_ok = True; results.append(f"✅ Projects Path: Directory OK.")
        SIMULATION_PROJECT_PATH = os.path.join(UNITY_PROJECTS_PATH, SIMULATION_PROJECT_NAME)
        ASSETS_FOLDER = os.path.join(SIMULATION_PROJECT_PATH, "Assets")
        STREAMING_ASSETS_FOLDER = os.path.join(ASSETS_FOLDER, "StreamingAssets")
        SIMULATION_LOADED_FILE = os.path.join(STREAMING_ASSETS_FOLDER, "simulation_loaded.txt")
        last_simulation_loaded = read_last_loaded_simulation_name()

    # --- Verify OpenAI API Key and Models (v0.x / v1.x compatible) ---
    apis_key_ok = False; apis_models_ok = False # Reset
    if not OPENAI_API_KEY: results.append("❌ API Key: Missing in .env file.")
    else:
        try:
            # --- Determine OpenAI version and call appropriate methods ---
            if OPENAI_V1_CLIENT_EXISTS:
                # --- Logic for openai >= 1.0 ---
                print("DEBUG: Verifying API using OpenAI v1.x+ client")
                client = openai.OpenAI(api_key=OPENAI_API_KEY)
                client.models.list(limit=1) # Test connection/auth
                apis_key_ok = True
                results.append("✅ API Key: Connection successful (v1.x+).")
                list_models_func = lambda: client.models.list() # Use client method
                retrieve_model_func = lambda model_id: client.models.retrieve(model_id)
                # Define v1 exception types (already imported)
                AuthErrType = AuthenticationError
                InvalidReqErrType = InvalidRequestError
                ConnErrType = APIConnectionError
            else:
                # --- Logic for openai < 1.0 ---
                print("DEBUG: Verifying API using OpenAI v0.x client")
                openai.api_key = OPENAI_API_KEY
                openai.Model.list(limit=1) # Test connection/auth
                apis_key_ok = True
                results.append("✅ API Key: Connection successful (v0.x).")
                list_models_func = lambda: openai.Model.list() # Use class method
                retrieve_model_func = lambda model_id: openai.Model.retrieve(model_id)
                 # Define v0 exception types (using imported or placeholder)
                AuthErrType = AuthenticationError_v0
                InvalidReqErrType = InvalidRequestError_v0
                ConnErrType = APIConnectionError_v0
            # --- End Version Specific Setup ---

            # --- Common Model Verification Logic ---
            if apis_key_ok:
                models_ok_list = []
                primary_model_checked = False
                for model_name_label, model_id in [("Primary Model", FINE_TUNED_MODEL_NAME), ("Secondary Model", SECONDARY_FINE_TUNED_MODEL_NAME)]:
                    is_primary = (model_name_label == "Primary Model")
                    if is_primary: primary_model_checked = True

                    if not model_id:
                        msg = f"⚠️ {model_name_label}: Not set in .env file."
                        if is_primary: msg += " (Required for API creation)"
                        results.append(msg)
                        if is_primary: models_ok_list.append(False)
                        continue

                    try:
                        retrieve_model_func(model_id) # Use the correct function
                        results.append(f"✅ {model_name_label}: ID '{model_id}' verified.")
                        if is_primary: models_ok_list.append(True)
                    except InvalidReqErrType as e: # Catch version-specific InvalidRequest
                        results.append(f"❌ {model_name_label}: ID '{model_id}' NOT FOUND or invalid. Error: {e}")
                        if is_primary: models_ok_list.append(False)
                    # Catch potential InvalidRequest from the *other* version if the detection wasn't perfect
                    except (InvalidRequestError if OPENAI_V1_CLIENT_EXISTS and not OPENAI_V0_ERROR_IMPORTED else InvalidRequestError_v0) as e_alt:
                         results.append(f"❌ {model_name_label}: ID '{model_id}' NOT FOUND/invalid (Alt). Error: {e_alt}")
                         if is_primary: models_ok_list.append(False)
                    except Exception as model_error: # Other errors
                        results.append(f"❌ {model_name_label}: Error verifying ID '{model_id}'. Error: {type(model_error).__name__}: {model_error}")
                        if is_primary: models_ok_list.append(False)

                apis_models_ok = primary_model_checked and models_ok_list and models_ok_list[0]
                if not apis_models_ok and FINE_TUNED_MODEL_NAME: results.append("❌ Primary Model: Verification failed (Invalid/Not Found ID or API error).")
                elif not FINE_TUNED_MODEL_NAME: results.append("❌ Primary Model: ID not specified in .env (Required for API creation).")

        except AuthErrType as auth_err:
             results.append(f"❌ API Key: Invalid or expired. Error: {auth_err}")
             apis_key_ok = False; apis_models_ok = False
        except ConnErrType as conn_err:
             results.append(f"❌ API Connection: Failed to connect. Error: {conn_err}")
             apis_key_ok = False; apis_models_ok = False
        # Catch potential errors from the *other* version's types
        except (AuthenticationError if not OPENAI_V1_CLIENT_EXISTS and OPENAI_V0_ERROR_IMPORTED else AuthenticationError_v0) as auth_err_alt:
            results.append(f"❌ API Key: Invalid or expired (Alt). Error: {auth_err_alt}")
            apis_key_ok = False; apis_models_ok = False
        except (APIConnectionError if not OPENAI_V1_CLIENT_EXISTS and OPENAI_V0_ERROR_IMPORTED else APIConnectionError_v0) as conn_err_alt:
            results.append(f"❌ API Connection: Failed to connect (Alt). Error: {conn_err_alt}")
            apis_key_ok = False; apis_models_ok = False
        except Exception as api_err: # Catchall
             results.append(f"❌ API Error: Unexpected error during verification. Error: {type(api_err).__name__}: {api_err}")
             apis_key_ok = False; apis_models_ok = False
             print(f"Unexpected API verification error: {api_err}"); import traceback; traceback.print_exc()


    if not initial_verification_complete: initial_verification_complete = True
    unity_status = "Unity OK" if unity_path_ok and unity_version_ok and unity_projects_path_ok else "Unity ERR"
    api_status = "API OK" if apis_key_ok and apis_models_ok else "API ERR"
    final_status = f"{unity_status} | {api_status}"

    # --- Update GUI ---
    if 'main_window' in globals() and main_window.winfo_exists():
        main_window.after(0, lambda: update_status(final_status))
        main_window.after(50, update_button_states)
        all_simulations_data = get_simulations()
        main_window.after(100, filter_simulations)

        if on_startup:
            errors = []
            if not unity_path_ok or not unity_projects_path_ok: errors.append("- Invalid Unity Executable or Projects path.")
            elif not unity_version_ok: errors.append(f"- Unity version/path mismatch (Requires ending '...{os.path.join(req_ver, 'Editor', 'Unity.exe')}').")
            if not unity_path_ok or not unity_version_ok or not unity_projects_path_ok: errors.append("  (Unity features might fail)")
            api_errors = False
            if not os.getenv("OPENAI_API_KEY"): errors.append("- OpenAI API Key missing in .env."); api_errors=True
            elif not apis_key_ok: errors.append("- OpenAI API Key invalid or connection failed."); api_errors=True
            else:
                if not FINE_TUNED_MODEL_NAME: errors.append("- Primary fine-tuned model ID missing in .env."); api_errors=True
                elif not apis_models_ok: errors.append("- Primary fine-tuned model ID invalid/not found."); api_errors=True
            if api_errors: errors.append("  (API creation disabled)")
            if errors:
                msg = "Config Issues:\n\n" + "\n".join(errors) + "\n\nUse 'Settings' to fix .env file."
                main_window.after(300, lambda m=msg: messagebox.showwarning("Initial Configuration Issues", m))
    else: print(f"Verification Status (No GUI): {final_status}")

    if show_results_box:
        text = "Verification Results:\n\n" + "\n".join(results)
        all_ok = unity_path_ok and unity_version_ok and unity_projects_path_ok and apis_key_ok and apis_models_ok
        if 'main_window' in globals() and main_window.winfo_exists():
             mtype = messagebox.showinfo if all_ok else messagebox.showwarning
             title = "Verification Complete" if all_ok else "Verification Issues Found"
             main_window.after(0, lambda t=title, msg=text: mtype(t, msg))


# ======================================================
# Configuration Window
# ======================================================
def open_config_window():
    cfg_win = ctk.CTkToplevel(main_window)
    cfg_win.title("Settings (.env Configuration)")
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    apply_icon(cfg_win) # Aplicar icono a la ventana de configuración
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    center_window(cfg_win, 700, 200); cfg_win.resizable(False, False); cfg_win.transient(main_window); cfg_win.grab_set()
    frame = ctk.CTkFrame(cfg_win); frame.pack(fill="both", expand=True, padx=20, pady=20); frame.grid_columnconfigure(1, weight=1)
    entries = {}
    def create_row(parent, r_idx, lbl_txt, env_var, key, is_file=True):
        ctk.CTkLabel(parent, text=lbl_txt, anchor="w", font=APP_FONT).grid(row=r_idx, column=0, padx=(0, 10), pady=5, sticky="w")
        val = os.environ.get(env_var, ""); entry_var = ctk.StringVar(value=val); entries[key] = entry_var
        ctk.CTkEntry(parent, textvariable=entry_var, font=APP_FONT).grid(row=r_idx, column=1, padx=5, pady=5, sticky="ew")
        def browse():
            init_dir="/"; cur = entry_var.get()
            if cur: pdir = os.path.dirname(cur);
            if os.path.isdir(pdir): init_dir=pdir
            elif os.path.isdir(cur): init_dir=cur
            path = filedialog.askopenfilename(title=f"Select {lbl_txt}", initialdir=init_dir) if is_file else filedialog.askdirectory(title=f"Select {lbl_txt}", initialdir=init_dir)
            if path: entry_var.set(path)
        ctk.CTkButton(parent, text="...", width=30, command=browse, font=APP_FONT).grid(row=r_idx, column=2, padx=(5, 0), pady=5)
    create_row(frame, 0, "Unity Executable:", "UNITY_EXECUTABLE", "unity_exe", is_file=True)
    create_row(frame, 1, "Unity Projects Folder:", "UNITY_PROJECTS_PATH", "projects_path", is_file=False)
    btn_frame = ctk.CTkFrame(cfg_win, fg_color="transparent"); btn_frame.pack(fill="x", padx=20, pady=(0, 20)); btn_frame.columnconfigure((0, 3), weight=1); btn_frame.columnconfigure((1, 2), weight=0)
    def save_config():
        key=os.getenv("OPENAI_API_KEY",""); m1=os.getenv("FINE_TUNED_MODEL_NAME",""); m2=os.getenv("2ND_FINE_TUNED_MODEL_NAME","")
        exe=entries['unity_exe'].get().strip(); proj=entries['projects_path'].get().strip()
        if not exe or not proj: messagebox.showerror("Input Error", "Both Unity paths required.", parent=cfg_win); return
        try:
            with open(".env", "w", encoding='utf-8') as f:
                f.write(f"UNITY_EXECUTABLE={exe}\n"); f.write(f"UNITY_PROJECTS_PATH={proj}\n")
                f.write(f"OPENAI_API_KEY={key}\n"); f.write(f"FINE_TUNED_MODEL_NAME={m1}\n"); f.write(f"2ND_FINE_TUNED_MODEL_NAME={m2}\n")
            messagebox.showinfo("Success", "Settings saved. Re-verifying...", parent=cfg_win); cfg_win.destroy()
            main_window.after(100, lambda: perform_verification(show_results_box=True))
        except Exception as e: messagebox.showerror("Save Error", f"Could not write .env file:\n{e}", parent=cfg_win)
    # Usar colores generales para diálogos
    mode_idx = get_color_mode_index()
    save_btn = ctk.CTkButton(btn_frame, text="Save and Verify", command=save_config, font=APP_FONT, fg_color=COLOR_SUCCESS_GENERAL[mode_idx], hover_color=COLOR_INFO_GENERAL[mode_idx]); save_btn.grid(row=0, column=1, padx=10, pady=10)
    cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=cfg_win.destroy, font=APP_FONT, fg_color=COLOR_WARNING_GENERAL[mode_idx], hover_color=COLOR_DANGER_GENERAL[mode_idx]); cancel_btn.grid(row=0, column=2, padx=10, pady=10)


# ======================================================
# GUI Definitions Callbacks
# ======================================================
def populate_simulations():
    if not initial_verification_complete: return
    update_status("Reloading simulation list...")
    global all_simulations_data, last_simulation_loaded
    all_simulations_data = get_simulations()
    last_simulation_loaded = read_last_loaded_simulation_name()
    all_simulations_data.sort(key=lambda x: x['name'].lower())
    filter_simulations()
    update_status(f"List refreshed ({len(all_simulations_data)} total simulations found).")
    update_button_states()

def filter_simulations(event=None):
    if 'sim_tree' not in globals() or 'search_entry' not in globals(): return
    search_term = search_entry.get().lower().strip()
    for item in sim_tree.get_children():
        try: sim_tree.delete(item)
        except tk.TclError: pass

    displayed_count = 0
    for i, sim_data in enumerate(all_simulations_data):
        if search_term and search_term not in sim_data['name'].lower(): continue
        is_loaded = (sim_data["name"] == last_simulation_loaded)
        row_tag = "evenrow" if displayed_count % 2 == 0 else "oddrow"
        item_tags = [row_tag];
        if is_loaded: item_tags.append("loaded")
        loaded_sym = loaded_indicator_text if is_loaded else ""
        play_sym = play_icon_text; delete_sym = delete_icon_text
        try:
            sim_tree.insert("", "end", iid=sim_data["name"],
                            values=(sim_data["name"], sim_data["creation"], sim_data["last_opened"], loaded_sym, play_sym, delete_sym),
                            tags=tuple(item_tags))
            displayed_count += 1
        except tk.TclError as e: print(f"Error inserting '{sim_data['name']}': {e}")

    status_msg = status_label.cget("text") # Keep current if not initial load
    if initial_verification_complete:
        if search_term: status_msg = f"Displaying {displayed_count} of {len(all_simulations_data)} matching '{search_term}'."
        else: status_msg = f"Displaying {len(all_simulations_data)} simulations."
    update_status(status_msg)
    if 'last_sort_column' in globals() and last_sort_column: sort_column(sim_tree, last_sort_column, sort_order[last_sort_column])
    update_button_states()

def clear_search():
    if 'search_entry' in globals(): search_entry.delete(0, 'end'); filter_simulations()

def update_button_states():
    if 'main_window' not in globals() or not main_window.winfo_exists() or is_build_running : return
    has_selection = bool(sim_tree.selection())
    can_create = apis_key_ok and apis_models_ok
    def get_state(enabled): return "normal" if enabled else "disabled"
    states = {
        'reload': get_state(not is_build_running),
        'graph': get_state(has_selection and not is_build_running),
        'create': get_state(can_create and not is_build_running),
        'verify': get_state(not is_build_running),
        'settings': get_state(not is_build_running),
        'about': get_state(not is_build_running),
        'unity_down': get_state(not is_build_running),
        'theme_switch': get_state(not is_build_running),
        'exit': get_state(not is_build_running),
        'search': get_state(not is_build_running)
    }
    try:
        reload_btn.configure(state=states['reload']); graph_btn.configure(state=states['graph']); create_btn.configure(state=states['create'])
        if 'settings_btn' in globals(): settings_btn.configure(state=states['settings'])
        if 'verify_btn' in globals(): verify_btn.configure(state=states['verify'])
        if 'unity_down_btn' in globals(): unity_down_btn.configure(state=states['unity_down'])
        if 'about_btn' in globals(): about_btn.configure(state=states['about'])
        if 'theme_switch' in globals(): theme_switch.configure(state=states['theme_switch'])
        if 'exit_btn' in globals(): exit_btn.configure(state=states['exit'])
        if 'search_entry' in globals(): search_entry.configure(state=states['search'])
        if 'clear_search_btn' in globals(): clear_search_btn.configure(state=states['search'])
    except (NameError, tk.TclError) as e: print(f"Warning: Could not update button states: {e}")

def on_load_simulation_request(simulation_name):
    global is_build_running;
    if is_build_running: return
    print(f"Load request: {simulation_name}")
    if not all([unity_path_ok, unity_version_ok, unity_projects_path_ok]): messagebox.showerror("Unity Config Error", "Cannot load: Invalid Unity config."); return
    if simulation_name == last_simulation_loaded:
        update_status(f"'{simulation_name}' already loaded. Showing options..."); update_last_opened(simulation_name)
        _, cur_exe = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
        main_window.after(0, lambda s=simulation_name, p=cur_exe: show_options_window(s, p)); return
    disable_all_interactions(); update_status(f"Starting load for '{simulation_name}'...")
    threading.Thread(target=load_simulation_logic, args=(simulation_name,), daemon=True).start()

def load_simulation_logic(simulation_name):
    load_ok = False
    try:
        update_status(f"Load '{simulation_name}': Closing Unity..."); ensure_unity_closed()
        update_status(f"Load '{simulation_name}': Copying files..."); load_ok = load_simulation(simulation_name)
        if load_ok:
            update_status(f"Load '{simulation_name}': Running prefab tool..."); prefab_ok = run_prefab_material_tool()
            if prefab_ok:
                update_status(f"Load '{simulation_name}': Starting build..."); build_simulation_threaded(callback=lambda ok, p: build_callback(ok, simulation_name, p))
            else:
                update_status(f"Error in post-load (prefabs) for '{simulation_name}'. Build cancelled.")
                messagebox.showerror("Post-Load Error", f"Prefab tool failed for '{simulation_name}'. Build cancelled.")
                main_window.after(10, enable_all_interactions)
        else:
            update_status(f"Error loading files for '{simulation_name}'. Stopped."); main_window.after(10, enable_all_interactions)
    except Exception as e:
        print(f"CRITICAL ERROR load_simulation_logic: {e}"); import traceback; traceback.print_exc()
        update_status(f"Critical error during load for '{simulation_name}'."); main_window.after(10, enable_all_interactions)

def build_callback(success, simulation_name, executable_path):
    if success and executable_path and os.path.exists(executable_path):
        update_status(f"Build for '{simulation_name}' successful.")
        show_options_window(simulation_name, executable_path)
    elif success and not executable_path:
         update_status(f"Build '{simulation_name}' finished, but exe path unknown.")
         messagebox.showerror("Build Error", f"Build for '{simulation_name}' completed, but exe path missing.")
    elif success and not os.path.exists(executable_path):
        update_status(f"Build '{simulation_name}' finished, but exe not found: {executable_path}")
        messagebox.showerror("Build Error", f"Build for '{simulation_name}' completed, but exe not found:\n{executable_path}\nCheck logs.")
    else: update_status(f"Build process for '{simulation_name}' failed.")
    # enable_all_interactions called by build_simulation_task after this

def on_delete_simulation_request(simulation_name):
    global is_build_running;
    if is_build_running: return
    print(f"Delete request: {simulation_name}")
    delete_simulation(simulation_name)

def on_show_graphs_thread():
    global is_build_running;
    if is_build_running: return
    sel = sim_tree.selection()
    if not sel: messagebox.showwarning("No Selection", "Select simulation to view graphs."); return
    sim_name = sim_tree.item(sel[0], "values")[0]
    disable_all_interactions(); update_status(f"Generating graphs for '{sim_name}'...")
    threading.Thread(target=show_graphs_logic, args=(sim_name,), daemon=True).start()

def show_graphs_logic(sim_name):
    try:
        data_dir = Path.home() / "Documents" / "SimulationLoggerData" / sim_name
        csv_path = data_dir / "SimulationStats.csv"; graphs_dir = data_dir / "Graficos"
        if not csv_path.exists(): messagebox.showerror("Data Not Found", f"CSV 'SimulationStats.csv' for '{sim_name}' not found:\n{data_dir}"); update_status(f"Error: CSV data missing for '{sim_name}'."); return
        graphs_dir.mkdir(parents=True, exist_ok=True)
        sim_script = Path(SIMULATIONS_DIR)/sim_name/"Assets"/"Scripts"/"SimulationData"/"SimulationGraphics.py"
        gen_script = Path("./Scripts/SimulationGraphics.py").resolve()
        script = str(sim_script) if sim_script.exists() else (str(gen_script) if gen_script.exists() else None)
        if not script: messagebox.showerror("Script Not Found", "Could not find 'SimulationGraphics.py'"); update_status("Error: Graph script missing."); return
        update_status(f"Running graph script for '{sim_name}': {os.path.basename(script)}")
        proc = subprocess.Popen([sys.executable, script, sim_name]); proc.wait(timeout=120);
        if proc.returncode != 0: messagebox.showwarning("Graph Warning", f"Graph script for '{sim_name}' exit code {proc.returncode}."); update_status(f"Warn: Graph script '{sim_name}' code {proc.returncode}.")
        else: update_status(f"Graph script for '{sim_name}' completed.")
        print(f"Opening graphs folder: {graphs_dir}"); open_graphs_folder(sim_name)
    except FileNotFoundError as e: messagebox.showerror("File Not Found Error", f"File not found:\n{e}"); update_status("Error: File not found for graphs.")
    except subprocess.TimeoutExpired: messagebox.showerror("Timeout Error", f"Graph script for '{sim_name}' timed out."); update_status(f"Error: Graph script '{sim_name}' timeout.")
    except Exception as e: messagebox.showerror("Graph Error", f"Error generating graphs for '{sim_name}':\n{e}"); update_status(f"Error graphs for '{sim_name}'."); print(f"Graph exception: {e}"); import traceback; traceback.print_exc()
    finally: main_window.after(0, enable_all_interactions)

def on_create_simulation():
    global is_build_running;
    if is_build_running: return
    if not apis_key_ok or not apis_models_ok: messagebox.showerror("API Config Error", "Cannot create: Invalid API Key or primary model."); return
    sim_name = custom_askstring("Create New Simulation", "Enter simulation name:");
    if not sim_name: update_status("Creation cancelled."); return
    sim_name = sim_name.strip(); invalid = r'<>:"/\|?*' + "".join(map(chr, range(32)))
    if not sim_name or any(c in sim_name for c in invalid): messagebox.showerror("Invalid Name", f"Name '{sim_name}' has invalid chars."); update_status("Invalid sim name."); return
    if os.path.exists(os.path.join(SIMULATIONS_DIR, sim_name)): messagebox.showerror("Exists", f"Sim '{sim_name}' already exists."); update_status(f"Sim '{sim_name}' exists."); return
    sim_desc = custom_askstring("Simulation Description", "Briefly describe:");
    if sim_desc is None: update_status("Creation cancelled."); return
    else: sim_desc = sim_desc.strip()
    disable_all_interactions(); update_status(f"Initiating creation of '{sim_name}'...")
    threading.Thread(target=create_simulation_thread, args=(sim_name, sim_desc, {}), daemon=True).start()

def show_options_window(simulation_name, executable_path):
    opt_win = ctk.CTkToplevel(main_window)
    opt_win.title(f"Options for '{simulation_name}'")
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    apply_icon(opt_win) # Aplicar icono a la ventana de opciones
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    center_window(opt_win, 380, 200); opt_win.resizable(False, False); opt_win.transient(main_window); opt_win.grab_set()
    frame = ctk.CTkFrame(opt_win); frame.pack(expand=True, fill="both", padx=20, pady=20)
    ctk.CTkLabel(frame, text=f"Simulation '{simulation_name}' is loaded.", font=APP_FONT_BOLD).pack(pady=(0, 15))
    exec_ok = executable_path and os.path.exists(executable_path); run_state = "normal" if exec_ok else "disabled"
    def run_close(): open_simulation_executable(); opt_win.destroy()
    def open_unity_close(): open_in_unity(); opt_win.destroy()
    # Usar colores generales para diálogos
    mode_idx = get_color_mode_index()
    run_btn = ctk.CTkButton(frame, text="Run Simulation", command=run_close, state=run_state, font=APP_FONT, height=40, fg_color=COLOR_SUCCESS_GENERAL[mode_idx], hover_color=COLOR_INFO_GENERAL[mode_idx]); run_btn.pack(pady=8, fill="x", padx=10)
    if not exec_ok: ctk.CTkLabel(frame, text="Executable not found.", text_color="gray", font=("Segoe UI", 9)).pack(pady=(0, 5))
    open_btn = ctk.CTkButton(frame, text="Open Project in Unity Editor", command=open_unity_close, font=APP_FONT, height=40, fg_color=COLOR_INFO_GENERAL[mode_idx], hover_color=COLOR_SUCCESS_GENERAL[mode_idx]); open_btn.pack(pady=8, fill="x", padx=10)
    update_status(f"Options available for loaded sim '{simulation_name}'."); opt_win.wait_window()

def handle_tree_click(event):
    global is_build_running;
    if is_build_running: return
    region = sim_tree.identify_region(event.x, event.y)
    if region == "cell":
        item_id = sim_tree.identify_row(event.y); col_id = sim_tree.identify_column(event.x)
        if not item_id or not col_id: cancel_tooltip(sim_tree); return
        try:
            col_idx = int(col_id.replace('#','')) - 1; col_ids = sim_tree['columns']
            if 0 <= col_idx < len(col_ids):
                col_name_id = col_ids[col_idx]; sim_name = sim_tree.item(item_id, "values")[0]
                sim_tree.selection_set(item_id); sim_tree.focus(item_id); update_button_states()
                hide_tooltip()
                if col_name_id == "col_load": print(f"Action click: Load/Run '{sim_name}'"); on_load_simulation_request(sim_name)
                elif col_name_id == "col_delete": print(f"Action click: Delete '{sim_name}'"); on_delete_simulation_request(sim_name)
            else: cancel_tooltip(sim_tree)
        except Exception as e: print(f"Error Treeview click: {e}"); cancel_tooltip(sim_tree)
    elif region == "heading": pass
    else: cancel_tooltip(sim_tree)

def handle_tree_motion(event):
    global is_build_running;
    if is_build_running: return
    region = sim_tree.identify_region(event.x, event.y)
    if region != "cell": cancel_tooltip(sim_tree); return
    col_id = sim_tree.identify_column(event.x); item_id = sim_tree.identify_row(event.y)
    if not col_id or not item_id: cancel_tooltip(sim_tree); return
    try:
        col_idx = int(col_id.replace('#','')) - 1; col_ids = sim_tree['columns']
        if 0 <= col_idx < len(col_ids):
            col_name_id = col_ids[col_idx]; tooltip = None; sim_name = sim_tree.item(item_id, 'values')[0]
            if col_name_id == "col_load": tooltip = f"Load / Run Sim '{sim_name}'"
            elif col_name_id == "col_delete": tooltip = f"Delete Sim '{sim_name}'"
            elif col_name_id == "col_loaded":
                 cell_val = sim_tree.set(item_id, column=col_name_id)
                 if cell_val == loaded_indicator_text: tooltip = f"'{sim_name}' is currently loaded."
            if tooltip: schedule_tooltip(sim_tree, tooltip)
            else: cancel_tooltip(sim_tree)
        else: cancel_tooltip(sim_tree)
    except Exception as e: print(f"Error handle_tree_motion: {e}"); cancel_tooltip(sim_tree)

def handle_tree_leave(event): cancel_tooltip(sim_tree)

def load_logo(path, target_width):
    global logo_photo_ref
    try:
        img = Image.open(path); w_p = (target_width / float(img.size[0])); h = int((float(img.size[1]) * float(w_p))); img = img.resize((target_width, h), Image.Resampling.LANCZOS); logo_photo_ref = ImageTk.PhotoImage(img); return logo_photo_ref
    except FileNotFoundError: print(f"Warn: Logo not found '{path}'"); return None
    except Exception as e: print(f"Error loading logo: {e}"); return None

# --- Funciones para el Tema ---
def update_treeview_style():
    if 'sim_tree' not in globals() or 'main_window' not in globals() or not main_window.winfo_exists(): return
    mode_idx = get_color_mode_index(); mode_str = "Dark" if mode_idx == 1 else "Light"
    print(f"Updating Treeview style for {mode_str} mode...")
    try:
        bg = main_window._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        fg = main_window._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
        sel_bg = main_window._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        head_bg = main_window._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"]) # Similar a botón
        head_fg = main_window._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["text_color"])
        odd = "#FDFDFD" if mode_str == "Light" else "#3A3A3A"
        even = "#F7F7F7" if mode_str == "Light" else "#343434"
        loaded_bg = "#D5F5D5" if mode_str == "Light" else "#284B28"
        loaded_fg = fg # Usar color texto normal
    except Exception as e:
        print(f"Error getting theme colors: {e}. Using fallback."); bg="#2B2B2B" if mode_str=="Dark" else "#DBDBDB"; fg="white" if mode_str=="Dark" else "black"; sel_bg="#565B5E" if mode_str=="Dark" else "#3470E7"; head_bg="#4A4D50" if mode_str=="Dark" else "#A5A9AC"; head_fg="white" if mode_str=="Dark" else "black"; odd="#3A3A3A" if mode_str=="Dark" else "#EFEFEF"; even="#343434" if mode_str=="Dark" else "#F7F7F7"; loaded_bg="#284B28" if mode_str=="Dark" else "#D5F5D5"; loaded_fg=fg

    style = ttk.Style();
    try: style.theme_use("clam")
    except tk.TclError: print("Warn: 'clam' theme not available.")
    style.configure("Treeview", background=bg, foreground=fg, fieldbackground=bg, rowheight=28, font=TREEVIEW_FONT)
    style.configure("Treeview.Heading", font=TREEVIEW_HEADER_FONT, background=head_bg, foreground="#c0c3c0", relief="flat", padding=(10, 5)) # Head foreground negro forzoso
    style.map("Treeview.Heading", relief=[('active','groove'), ('!active', 'flat')])
    style.map('Treeview', background=[('selected', sel_bg)], foreground=[('selected', head_fg)])
    sim_tree.tag_configure('oddrow', background=odd, foreground=fg)
    sim_tree.tag_configure('evenrow', background=even, foreground=fg)
    sim_tree.tag_configure('loaded', background=loaded_bg, foreground=loaded_fg, font=TREEVIEW_FONT)
    print("Treeview style updated.")

def toggle_appearance_mode():
    """Cambia tema y actualiza estilos y colores de botones."""
    current_mode = ctk.get_appearance_mode(); new_mode = "Dark" if current_mode == "Light" else "Light"
    print(f"Switching appearance mode to: {new_mode}")
    ctk.set_appearance_mode(new_mode)
    if 'theme_switch' in globals(): theme_switch.configure(text=f"{new_mode} Mode")

    # Actualizar estilo Treeview (esencial)
    main_window.after(50, update_treeview_style)

    # --- Actualizar Colores de Botones Personalizados ---
    mode_idx = get_color_mode_index()
    try:
        # Logo
        logo_photo = load_logo(LOGO_PATHS[mode_idx], LOGO_WIDTH)
        # Unpack logo y luego pack logo
        if logo_photo and 'sidebar_frame' in globals() and sidebar_frame.winfo_exists():
             logo_label = sidebar_frame.winfo_children()[0] # Asume que el logo es el primer widget
             if isinstance(logo_label, ctk.CTkLabel):
                 logo_label.configure(image=logo_photo)
                 logo_label.image = logo_photo # Guardar referencia

        # Sidebar Buttons
        settings_btn.configure(fg_color=BTN_SETTINGS_FG_COLOR[mode_idx], hover_color=BTN_SETTINGS_HOVER_COLOR[mode_idx], text_color=BTN_SETTINGS_TEXT_COLOR[mode_idx])
        verify_btn.configure(fg_color=BTN_VERIFY_FG_COLOR[mode_idx], hover_color=BTN_VERIFY_HOVER_COLOR[mode_idx], text_color=BTN_VERIFY_TEXT_COLOR[mode_idx])
        unity_down_btn.configure(fg_color=BTN_UNITY_DOWN_FG_COLOR[mode_idx], hover_color=BTN_UNITY_DOWN_HOVER_COLOR[mode_idx], text_color=BTN_UNITY_DOWN_TEXT_COLOR[mode_idx])
        about_btn.configure(fg_color=BTN_ABOUT_FG_COLOR[mode_idx], hover_color=BTN_ABOUT_HOVER_COLOR[mode_idx], text_color=BTN_ABOUT_TEXT_COLOR[mode_idx])
        exit_btn.configure(fg_color=BTN_EXIT_FG_COLOR[mode_idx], hover_color=BTN_EXIT_HOVER_COLOR[mode_idx], text_color=BTN_EXIT_TEXT_COLOR[mode_idx])

        # Bottom Buttons
        reload_btn.configure(fg_color=BTN_RELOAD_FG_COLOR[mode_idx], hover_color=BTN_RELOAD_HOVER_COLOR[mode_idx], text_color=BTN_RELOAD_TEXT_COLOR[mode_idx])
        graph_btn.configure(fg_color=BTN_GRAPH_FG_COLOR[mode_idx], hover_color=BTN_GRAPH_HOVER_COLOR[mode_idx], text_color=BTN_GRAPH_TEXT_COLOR[mode_idx])
        create_btn.configure(fg_color=BTN_CREATE_FG_COLOR[mode_idx], hover_color=BTN_CREATE_HOVER_COLOR[mode_idx], text_color=BTN_CREATE_TEXT_COLOR[mode_idx])

        # Search Button
        clear_search_btn.configure(fg_color=BTN_CLEARSEARCH_FG_COLOR[mode_idx], hover_color=BTN_CLEARSEARCH_HOVER_COLOR[mode_idx], text_color=BTN_CLEARSEARCH_TEXT_COLOR[mode_idx])

        print("Button colors updated for theme.")
    except NameError as e: print(f"Warn: Button color update failed (widget N/A?): {e}")
    except Exception as e: print(f"Error updating button colors: {e}")


# ======================================================
# GUI Setup
# ======================================================
main_window = ctk.CTk()
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
apply_icon(main_window) # Aplicar icono a la ventana principal
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
main_window.title("Unity Simulation Manager v1.0")
initial_width=1050; initial_height=700; center_window(main_window, initial_width, initial_height)
main_window.resizable(True, True); main_window.minsize(850, 550)

# --- Layout ---
main_window.columnconfigure(0, weight=0); main_window.columnconfigure(1, weight=1)
main_window.rowconfigure(0, weight=1); main_window.rowconfigure(1, weight=0)

# --- Sidebar ---
sidebar_width=200; sidebar_frame = ctk.CTkFrame(main_window, width=sidebar_width, corner_radius=5, fg_color=COLOR_SIDEBAR_BG)
sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10); sidebar_frame.grid_propagate(False); sidebar_frame.columnconfigure(0, weight=1)

# Determinar modo inicial para cargar logo y colores iniciales
mode_idx = get_color_mode_index() # Get initial mode index
initial_mode = ctk.get_appearance_mode()

logo_photo = load_logo(LOGO_PATHS[mode_idx], LOGO_WIDTH)
if logo_photo: ctk.CTkLabel(sidebar_frame, image=logo_photo, text="").pack(pady=(20, 10), padx=10)
else: ctk.CTkLabel(sidebar_frame, text="[Logo]", font=(APP_FONT[0], 14, "italic")).pack(pady=(20, 10), padx=10)
ctk.CTkLabel(sidebar_frame, text="Menu", font=(APP_FONT[0], 16, "bold")).pack(pady=(5, 15), padx=10)

# Sidebar Buttons (CON COLORES INDIVIDUALES)
settings_btn = ctk.CTkButton(sidebar_frame, text="Settings (.env)", command=open_config_window, font=APP_FONT,
                             fg_color=BTN_SETTINGS_FG_COLOR[mode_idx],
                             hover_color=BTN_SETTINGS_HOVER_COLOR[mode_idx],
                             text_color=BTN_SETTINGS_TEXT_COLOR[mode_idx])
settings_btn.pack(fill="x", padx=15, pady=5)

verify_btn = ctk.CTkButton(sidebar_frame, text="Verify Config", command=lambda: perform_verification(show_results_box=True), font=APP_FONT,
                           fg_color=BTN_VERIFY_FG_COLOR[mode_idx],
                           hover_color=BTN_VERIFY_HOVER_COLOR[mode_idx],
                           text_color=BTN_VERIFY_TEXT_COLOR[mode_idx])
verify_btn.pack(fill="x", padx=15, pady=5)

separator = ctk.CTkFrame(sidebar_frame, height=2, fg_color="gray"); separator.pack(fill="x", padx=15, pady=15)

unity_down_btn = ctk.CTkButton(sidebar_frame, text="Download Unity Hub", command=lambda: webbrowser.open(f"unityhub://{UNITY_REQUIRED_VERSION_STRING}/b2e806cf271c"), font=APP_FONT,
                              fg_color=BTN_UNITY_DOWN_FG_COLOR[mode_idx],
                              hover_color=BTN_UNITY_DOWN_HOVER_COLOR[mode_idx],
                              text_color=BTN_UNITY_DOWN_TEXT_COLOR[mode_idx])
unity_down_btn.pack(fill="x", padx=15, pady=5)

about_btn = ctk.CTkButton(sidebar_frame, text="About", command=lambda: messagebox.showinfo("About", "Unity Simulation Manager v1.0.\nBy:\nIván Cáceres S. \nTobías Guerrero Ch."), font=APP_FONT,
                          fg_color=BTN_ABOUT_FG_COLOR[mode_idx],
                          hover_color=BTN_ABOUT_HOVER_COLOR[mode_idx],
                          text_color=BTN_ABOUT_TEXT_COLOR[mode_idx])
about_btn.pack(fill="x", padx=15, pady=5)

theme_switch = ctk.CTkSwitch(sidebar_frame, text=f"{initial_mode} Mode", command=toggle_appearance_mode, font=APP_FONT); theme_switch.pack(fill="x", side='bottom', padx=15, pady=(10, 5))
if initial_mode == "Dark": theme_switch.select()
else: theme_switch.deselect()

exit_btn = ctk.CTkButton(sidebar_frame, text="Exit Application", command=main_window.quit, font=APP_FONT,
                         fg_color=BTN_EXIT_FG_COLOR[mode_idx],
                         hover_color=BTN_EXIT_HOVER_COLOR[mode_idx],
                         text_color=BTN_EXIT_TEXT_COLOR[mode_idx])
exit_btn.pack(fill="x", side='bottom', padx=15, pady=(5, 20))

# --- Main Content ---
main_content_frame = ctk.CTkFrame(main_window, corner_radius=5); main_content_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
main_content_frame.columnconfigure(0, weight=1); main_content_frame.rowconfigure((0, 1, 3), weight=0); main_content_frame.rowconfigure(2, weight=1) # Treeview expands
header_frame = ctk.CTkFrame(main_content_frame, fg_color="transparent"); header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5)); header_frame.columnconfigure(0, weight=1)
ctk.CTkLabel(header_frame, text="Unity Simulation Manager", font=TITLE_FONT, anchor="center").grid(row=0, column=0, pady=(0, 10))
search_frame = ctk.CTkFrame(main_content_frame, fg_color="transparent"); search_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 5)); search_frame.columnconfigure(1, weight=1)
ctk.CTkLabel(search_frame, text="Search:", font=APP_FONT).grid(row=0, column=0, padx=(5, 5), pady=5)
search_entry = ctk.CTkEntry(search_frame, placeholder_text="Type simulation name to filter...", font=APP_FONT); search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew"); search_entry.bind("<KeyRelease>", filter_simulations)
clear_search_btn = ctk.CTkButton(search_frame, text="Clear", width=60, font=APP_FONT, command=clear_search,
                                fg_color=BTN_CLEARSEARCH_FG_COLOR[mode_idx],
                                hover_color=BTN_CLEARSEARCH_HOVER_COLOR[mode_idx],
                                text_color=BTN_CLEARSEARCH_TEXT_COLOR[mode_idx])
clear_search_btn.grid(row=0, column=2, padx=(5, 5), pady=5)

# --- Treeview ---
tree_frame = ctk.CTkFrame(main_content_frame, corner_radius=5); tree_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5); tree_frame.columnconfigure(0, weight=1); tree_frame.rowconfigure(0, weight=1)
columns = ("nombre", "creacion", "ultima", "col_loaded", "col_load", "col_delete")
sim_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
sim_tree.heading("nombre", text="Simulation Name", anchor='w'); sim_tree.column("nombre", width=200, anchor="w", stretch=tk.YES)
sim_tree.heading("creacion", text="Created", anchor='center'); sim_tree.column("creacion", width=120, anchor="center", stretch=tk.NO)
sim_tree.heading("ultima", text="Last Used", anchor='center'); sim_tree.column("ultima", width=120, anchor="center", stretch=tk.NO)
sim_tree.heading("col_loaded", text="Loaded", anchor='center'); sim_tree.column("col_loaded", width=90, stretch=tk.NO, anchor="center")
sim_tree.heading("col_load", text="Load/Run", anchor='center'); sim_tree.column("col_load", width=90, stretch=tk.NO, anchor="center")
sim_tree.heading("col_delete", text="Delete", anchor='center'); sim_tree.column("col_delete", width=90, stretch=tk.NO, anchor="center")

last_sort_column = None; sort_order = {c: False for c in columns if c not in ["col_load", "col_delete", "col_loaded"]}
def sort_column(tree, col, reverse):
    if col in ["col_load", "col_delete", "col_loaded"]: return
    global last_sort_column, sort_order
    try:
        data = [(tree.set(item, col), item) for item in tree.get_children('')]
        def conv_key(val):
            if col in ("creacion", "ultima"):
                if val in ("???", "Never") or not val: return 0
                try: return time.mktime(time.strptime(val, "%y-%m-%d %H:%M"))
                except ValueError: return 0
            else: return str(val).lower()
        data.sort(key=lambda t: conv_key(t[0]), reverse=reverse)
        for i, (_, item) in enumerate(data): tree.move(item, '', i)
        sort_order[col] = reverse; last_sort_column = col
        for c in sort_order:
             txt = tree.heading(c)['text'].replace(' ▲', '').replace(' ▼', '')
             if c == col: txt += (' ▼' if reverse else ' ▲')
             tree.heading(c, text=txt, command=lambda c_=c: sort_column(tree, c_, not sort_order.get(c_, False)))
    except Exception as e: print(f"Error sorting '{col}': {e}")

for col in columns:
    if col not in ["col_load", "col_delete", "col_loaded"]:
        txt = sim_tree.heading(col)['text'].replace(' ▲','').replace(' ▼','')
        sim_tree.heading(col, text=txt, command=lambda c=col: sort_column(sim_tree, c, False), anchor='w' if col=='nombre' else 'center')

sim_tree.grid(row=0, column=0, sticky="nsew"); scrollbar = ctk.CTkScrollbar(tree_frame, command=sim_tree.yview); scrollbar.grid(row=0, column=1, sticky="ns"); sim_tree.configure(yscrollcommand=scrollbar.set)
sim_tree.bind('<<TreeviewSelect>>', lambda e: update_button_states()); sim_tree.bind("<Button-1>", handle_tree_click); sim_tree.bind("<Motion>", handle_tree_motion); sim_tree.bind("<Leave>", handle_tree_leave)

# --- Bottom Buttons ---
button_frame_bottom = ctk.CTkFrame(main_content_frame, fg_color="transparent"); button_frame_bottom.grid(row=3, column=0, pady=(10, 10), padx=10, sticky="ew")
button_frame_bottom.columnconfigure((0, 4), weight=1); button_frame_bottom.columnconfigure((1, 2, 3), weight=0)
button_height=35

reload_btn = ctk.CTkButton(button_frame_bottom, text="Reload List", command=populate_simulations, font=APP_FONT, height=button_height,
                           fg_color=BTN_RELOAD_FG_COLOR[mode_idx],
                           hover_color=BTN_RELOAD_HOVER_COLOR[mode_idx],
                           text_color=BTN_RELOAD_TEXT_COLOR[mode_idx])
reload_btn.grid(row=0, column=1, padx=10, pady=5)

graph_btn = ctk.CTkButton(button_frame_bottom, text="Show Graphs", command=on_show_graphs_thread, font=APP_FONT, height=button_height,
                          fg_color=BTN_GRAPH_FG_COLOR[mode_idx],
                          hover_color=BTN_GRAPH_HOVER_COLOR[mode_idx],
                          text_color=BTN_GRAPH_TEXT_COLOR[mode_idx])
graph_btn.grid(row=0, column=2, padx=10, pady=5)

create_btn = ctk.CTkButton(button_frame_bottom, text="Create Sim (API)", command=on_create_simulation, font=APP_FONT, height=button_height,
                           fg_color=BTN_CREATE_FG_COLOR[mode_idx],
                           hover_color=BTN_CREATE_HOVER_COLOR[mode_idx],
                           text_color=BTN_CREATE_TEXT_COLOR[mode_idx])
create_btn.grid(row=0, column=3, padx=10, pady=5)

# --- Status Bar ---
status_frame = ctk.CTkFrame(main_window, height=25, corner_radius=0); status_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
status_label = ctk.CTkLabel(status_frame, text="Initializing...", anchor="w", font=STATUS_FONT); status_label.pack(side="left", fill="x", expand=True, padx=10, pady=3)

# ======================================================
# App Initialization
# ======================================================
if __name__ == "__main__":
    main_window.after(10, update_treeview_style) # Apply initial style
    update_button_states()
    update_status("Performing initial configuration verification...")
    threading.Thread(target=perform_verification, args=(False, True), daemon=True).start()
    def on_closing():
        """Se llama cuando el usuario intenta cerrar la ventana."""
        global is_build_running
        if is_build_running:
            messagebox.showwarning("Operación en Progreso", "Por favor, espere a que la operación actual (build/load) finalice antes de cerrar la aplicación.")
            return # Prevenir cierre

        # --- FIX: Corregir llamada a askokcancel ---
        # El primer argumento es 'title', el segundo es 'message'.
        # No se debe pasar 'title' como keyword si ya se pasó posicionalmente.
        if messagebox.askokcancel(
            title="Confirmar Salida", # Argumento posicional 1: Título
            message="¿Está seguro de que desea salir de Unity Simulation Manager?", # Argumento posicional 2: Mensaje
            icon='question' # Argumento keyword para opciones
            # , title="Confirm Exit" # <-- ESTE ERA EL ERROR, TÍTULO DUPLICADO
            ):
            update_status("Cerrando aplicación...")
            print("Intentando cerrar instancias de Unity asociadas (si existen)...")
            # Intentar cerrar Unity en segundo plano para no retrasar mucho el cierre de la GUI
            close_unity_thread = threading.Thread(target=ensure_unity_closed, daemon=True)
            close_unity_thread.start()
            # Esperar un poquito para que el mensaje de cierre se vea y el hilo empiece
            # y luego destruir la ventana principal, lo que termina el mainloop.
            print("Cerrando GUI...")
            main_window.after(200, main_window.destroy)
        # else: # Usuario hizo clic en Cancelar
        #     print("Cierre cancelado por el usuario.")

    # Asignar la función on_closing al protocolo WM_DELETE_WINDOW
    main_window.protocol("WM_DELETE_WINDOW", on_closing)

    # Iniciar el bucle principal de la aplicación
    main_window.mainloop()