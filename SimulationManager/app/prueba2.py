# -*- coding: utf-8 -*-
import sys
import os
import shutil
import subprocess
import platform
import threading
import time

# --- CustomTkinter ---
import customtkinter as ctk
from tkinter import messagebox, filedialog # Mantener de tkinter
from tkinter import ttk # SOLO para Treeview y su estilo

# --- Otras dependencias ---
from dotenv import load_dotenv
from pathlib import Path
import psutil
import openai
import math
try:
    from PIL import Image, ImageTk # Necesario para el logo
except ImportError:
    messagebox.showerror("Error de Dependencia",
                         "La biblioteca Pillow no está instalada.\n"
                         "Por favor, instálala ejecutando: pip install Pillow")
    sys.exit(1) # Salir si Pillow no está instalado

try:
    from openai import error as openai_error # OpenAI < 1.0
except ImportError:
    class OpenAIError(Exception): pass # Placeholder if openai >= 1.0
    class AuthenticationError(OpenAIError): pass
    class InvalidRequestError(OpenAIError): pass
    class APIConnectionError(OpenAIError): pass
    openai_error = sys.modules[__name__]
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

SIMULATIONS_DIR = "./Simulations"
SIMULATION_PROJECT_NAME = "Simulation"
SIMULATION_PROJECT_PATH = None
ASSETS_FOLDER = None
STREAMING_ASSETS_FOLDER = None
SIMULATION_LOADED_FILE = None
last_simulation_loaded = None
all_simulations_data = [] # Para almacenar la lista completa de simulaciones para búsqueda

# Icons (text fallback) - Ahora usados también en cabeceras
play_icon_text = "▶"
delete_icon_text = "🗑️"
loaded_indicator_text = "✓"

# Tooltip handling (Usando tk.Toplevel simple para esto)
import tkinter as tk # Importar tk específicamente para el tooltip
tooltip_window = None
tooltip_delay = 700
tooltip_job_id = None

# Referencia global para la imagen del logo (evita garbage collection)
logo_photo_ref = None
LOGO_PATH = "img/logo.png"
LOGO_WIDTH = 150 # Ancho deseado para el logo en pixels

# --- CustomTkinter Theme & Font ---
ctk.set_appearance_mode("System") # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue") # Themes: "blue" (default), "green", "dark-blue"

APP_FONT = ("Segoe UI", 11) # Fuente estándar
APP_FONT_BOLD = ("Segoe UI", 11, "bold")
TITLE_FONT = ("Times New Roman", 22, "bold")
STATUS_FONT = ("Segoe UI", 10)
TREEVIEW_FONT = ("Segoe UI", 10)
TREEVIEW_HEADER_FONT = ("Segoe UI", 10, "bold")

# --- Colores para Botones (puedes ajustarlos) ---
COLOR_SUCCESS = ("#2ECC71", "#27AE60") # Light, Dark
COLOR_DANGER = ("#E74C3C", "#C0392B")
COLOR_INFO = ("#3498DB", "#2980B9")
COLOR_WARNING = ("#F39C12", "#D35400")
COLOR_GRAPH = ("#1ABC9C", "#16A085")
COLOR_RELOAD = ("#9B59B6", "#8E44AD")
COLOR_DISABLED = ("#BDC3C7", "#95A5A6") # Color para botones deshabilitados
COLOR_SIDEBAR_BG = None # Usará el color del tema por defecto
COLOR_SEARCH_CLEAR = ("#E67E22", "#D35400") # Naranja para el botón Clear

# ======================================================
# GUI Utilities & Interaction Control (Adaptado a CTk)
# ======================================================
def center_window(window, width, height):
    # (Sin cambios)
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")

class CustomInputDialog(ctk.CTkToplevel):
    # (Sin cambios)
    def __init__(self, parent, title, prompt, width=400, height=170):
        super().__init__(parent)
        self.title(title)
        center_window(self, width, height)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        ctk.CTkLabel(self, text=prompt, font=APP_FONT).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.entry = ctk.CTkEntry(self, font=APP_FONT, width=width-40)
        self.entry.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="e")

        ok_button = ctk.CTkButton(button_frame, text="OK", command=self.ok, width=80, font=APP_FONT)
        ok_button.pack(side="left", padx=(0, 10))

        cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=self.cancel, width=80, font=APP_FONT,
                                     fg_color=COLOR_WARNING[ctk.get_appearance_mode() == "Dark"],
                                     hover_color=COLOR_DANGER[ctk.get_appearance_mode() == "Dark"])
        cancel_button.pack(side="left")

        self.bind("<Return>", lambda e: self.ok())
        self.bind("<Escape>", lambda e: self.cancel())
        self.entry.focus()
        self.wait_window()

    def ok(self):
        self.result = self.entry.get()
        self.destroy()

    def cancel(self):
        self.destroy()

def custom_askstring(title, prompt):
    # (Sin cambios)
    if 'main_window' in globals() and main_window.winfo_exists():
        dialog = CustomInputDialog(main_window, title, prompt)
        return dialog.result
    print(f"Warn: Main window N/A for dialog '{title}'.")
    return None

# --- Tooltip Functions (Usando tk.Toplevel simple) ---
def show_tooltip(widget, text):
    # (Sin cambios)
    global tooltip_window
    hide_tooltip()
    # Mejorar obtención de coordenadas para Treeview
    if isinstance(widget, ttk.Treeview):
        x_root, y_root = widget.winfo_pointerxy()
        x = x_root + 20
        y = y_root + 10
    else:
        try:
            x_root = widget.winfo_rootx()
            y_root = widget.winfo_rooty()
            height = widget.winfo_height()
            x = x_root + 20
            y = y_root + height + 5 # Posicionar debajo del widget
        except Exception: # Fallback si todo falla
             x, y = widget.winfo_pointerxy()
             x += 20
             y += 20

    tooltip_window = tk.Toplevel(widget)
    tooltip_window.wm_overrideredirect(True)
    tooltip_window.wm_geometry(f"+{x}+{y}")
    label = tk.Label(tooltip_window, text=text, justify='left',
                     background="#ffffe0", relief='solid', borderwidth=1,
                     font=("Segoe UI", 9)) # Fuente fija para tooltip
    label.pack(ipadx=1)

def hide_tooltip():
    # (Sin cambios)
    global tooltip_window
    if tooltip_window:
        try: tooltip_window.destroy()
        except tk.TclError: pass
        tooltip_window = None

def schedule_tooltip(widget, text):
    # (Sin cambios)
    global tooltip_job_id
    cancel_tooltip(widget)
    tooltip_job_id = widget.after(tooltip_delay, lambda: show_tooltip(widget, text))

def cancel_tooltip(widget):
    # (Sin cambios)
    global tooltip_job_id
    if tooltip_job_id:
        widget.after_cancel(tooltip_job_id)
        tooltip_job_id = None
    hide_tooltip()

# --- Interaction Control ---
def disable_all_interactions():
    # (Sin cambios)
    global is_build_running
    is_build_running = True
    try:
        # Disable bottom buttons
        reload_btn.configure(state="disabled")
        graph_btn.configure(state="disabled")
        create_btn.configure(state="disabled")

        # Disable sidebar buttons
        if 'sidebar_frame' in globals():
            for widget in sidebar_frame.winfo_children():
                if isinstance(widget, ctk.CTkButton):
                    widget.configure(state="disabled")

        # Disable search
        if 'search_entry' in globals(): search_entry.configure(state="disabled")
        if 'clear_search_btn' in globals(): clear_search_btn.configure(state="disabled")

        # Unbind treeview click
        sim_tree.unbind("<Button-1>")
        sim_tree.unbind("<Motion>") # Also disable tooltips during build
        sim_tree.configure(cursor="watch") # Indicate busy state
        update_status("Build in progress... Please wait.")
    except (NameError, tk.TclError) as e:
        print(f"Warning: Could not disable all interactions (GUI not fully ready?): {e}")

def enable_all_interactions():
    # (Sin cambios en lógica, solo añadir widgets de búsqueda)
    global is_build_running
    is_build_running = False
    try:
         # Enable sidebar buttons
        if 'sidebar_frame' in globals():
            for widget in sidebar_frame.winfo_children():
                 if isinstance(widget, ctk.CTkButton):
                      widget.configure(state="normal")

         # Enable search
        if 'search_entry' in globals(): search_entry.configure(state="normal")
        if 'clear_search_btn' in globals(): clear_search_btn.configure(state="normal")

        # Re-bind treeview click and motion
        sim_tree.bind("<Button-1>", handle_tree_click)
        sim_tree.bind("<Motion>", handle_tree_motion)
        sim_tree.configure(cursor="") # Restore default cursor
        update_button_states() # Update buttons based on current state (incluye los de abajo)
    except (NameError, tk.TclError) as e:
         print(f"Warning: Could not re-enable all interactions: {e}")


# ======================================================
# Core Utilities & Error Handling (Sin cambios funcionales)
# ======================================================
def update_status(message):
    # (Sin cambios)
    if 'main_window' in globals() and main_window.winfo_exists():
        main_window.after(0, lambda: status_label.configure(text=str(message)))
    else: print(f"Status (GUI !ready): {message}")

def handle_unity_execution_error(e, operation_name="operation"):
    # (Sin cambios)
    err_msg = (f"Error during Unity {operation_name}.\n\nDetails: {type(e).__name__}: {str(e)}\n\n"
               "Check Unity installation/version (6000.0.32f1) and path.\n"
               "Consider reinstalling Unity Editor.")
    print(f"Unity Error ({operation_name}): {e}")
    if 'main_window' in globals() and main_window.winfo_exists(): main_window.after(0, lambda: messagebox.showerror("Unity Execution Error", err_msg))
    else: print("Critical error: " + err_msg)

def ensure_unity_closed():
    # (Sin cambios)
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
        t_start = time.time()
        for p in procs:
            try: p.terminate()
            except psutil.Error: pass
        _, alive = psutil.wait_procs(procs, timeout=5)
        if alive:
            for p in alive:
                try: p.kill()
                except psutil.Error: pass
            psutil.wait_procs(alive, timeout=3)
        print(f"Unity close check took {time.time()-t_start:.2f}s")

def open_graphs_folder(simulation_name):
    # (Sin cambios)
    try:
        fldr = Path.home()/"Documents"/"SimulationLoggerData"/simulation_name/"Graficos"
        fldr.mkdir(parents=True, exist_ok=True)
        if platform.system() == "Windows": os.startfile(str(fldr))
        elif platform.system() == "Darwin": subprocess.Popen(["open", str(fldr)])
        else: subprocess.Popen(["xdg-open", str(fldr)])
    except Exception as e: messagebox.showerror("Error", f"Could not open graphs folder '{fldr}':\n{e}")

def get_folder_size(path):
    # (Sin cambios)
    total = 0;
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False): total += entry.stat(follow_symlinks=False).st_size
            elif entry.is_dir(follow_symlinks=False): total += get_folder_size(entry.path)
    except Exception: pass
    return total

def copy_directory(src, dst):
    # (Sin cambios)
    try:
        if os.path.exists(dst): shutil.rmtree(dst, ignore_errors=True); time.sleep(0.1)
        shutil.copytree(src, dst, symlinks=False, ignore_dangling_symlinks=True); return True
    except Exception as e:
        msg = f"Error copying {src} to {dst}:\n{e}"; print(msg)
        if 'main_window' in globals() and main_window.winfo_exists(): main_window.after(0, lambda: messagebox.showerror("Copy Error", msg))
        return False

def get_build_target_and_executable(project_path):
    # (Sin cambios)
    if not project_path: return "Unknown", None
    sistema = platform.system(); exe_name = SIMULATION_PROJECT_NAME
    if sistema == "Windows": target, pfolder, suff = "Win64", "Windows", ".exe"
    elif sistema == "Linux": target, pfolder, suff = "Linux64", "Linux", ""
    elif sistema == "Darwin": target, pfolder, suff = "OSXUniversal", "Mac", ".app"
    else: target, pfolder, suff = "Win64", "Windows", ".exe" # Default a Windows
    build_base = os.path.join(project_path, "Build", pfolder)
    ejecutable = os.path.join(build_base, exe_name + suff)
    return target, ejecutable

# ======================================================
# Simulation Logic (adaptado para búsqueda)
# ======================================================
def get_simulations():
    # (Ahora devuelve la lista directamente, sin ordenar aquí)
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
                # Guardar el timestamp de creación para posible ordenamiento futuro
                sims.append({"name": item, "creation": c_str, "last_opened": l_str, "creation_ts": c_ts})
    except Exception as e: print(f"Err reading sims: {e}"); return []
    # El ordenamiento se hará en populate_simulations o filter_simulations si es necesario
    return sims

def update_last_opened(sim_name):
    # (Sin cambios)
    folder = os.path.join(SIMULATIONS_DIR, sim_name)
    try: os.makedirs(folder, exist_ok=True);
    except: pass
    try:
        with open(os.path.join(folder, "last_opened.txt"), "w") as f: f.write(str(time.time()))
    except Exception as e: print(f"[Err] update_last_opened({sim_name}): {e}")

def read_last_loaded_simulation_name():
    # (Sin cambios)
    if SIMULATION_LOADED_FILE and os.path.exists(SIMULATION_LOADED_FILE):
        try:
            with open(SIMULATION_LOADED_FILE, "r") as f: return f.read().strip()
        except Exception as e: print(f"Error reading {SIMULATION_LOADED_FILE}: {e}")
    return None

def load_simulation(sim_name):
    # (Sin cambios funcionales)
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
    # populate_simulations refrescará la vista y re-aplicará el filtro actual
    if 'main_window' in globals() and main_window.winfo_exists(): main_window.after(50, populate_simulations)
    return True

def delete_simulation(sim_name):
    # (Sin cambios funcionales, populate_simulations actualizará la vista)
    confirm = messagebox.askyesno("Confirm Delete", f"Permanently delete '{sim_name}' and all its associated data (logs, graphs)?\n\nThis action cannot be undone.", icon='warning', title="Confirm Deletion")
    if not confirm: update_status("Deletion cancelled."); return
    update_status(f"Deleting '{sim_name}'..."); errs = False; global last_simulation_loaded, all_simulations_data
    if SIMULATION_LOADED_FILE and os.path.exists(SIMULATION_LOADED_FILE):
        try:
            loaded = read_last_loaded_simulation_name()
            if loaded == sim_name: os.remove(SIMULATION_LOADED_FILE); print("State file removed.")
            if last_simulation_loaded == sim_name: last_simulation_loaded = None
        except Exception as e: print(f"Warn: Could not clean state file: {e}")
    sim_p = os.path.join(SIMULATIONS_DIR, sim_name)
    if os.path.exists(sim_p):
        try: shutil.rmtree(sim_p, ignore_errors=True); time.sleep(0.1); shutil.rmtree(sim_p)
        except Exception as e: messagebox.showerror("Error", f"Could not delete simulation folder:\n{sim_p}\n{e}"); errs = True
    try: data_p = Path.home()/"Documents"/"SimulationLoggerData"/sim_name;
    except: data_p = None
    if data_p and data_p.is_dir():
        try: shutil.rmtree(data_p)
        except Exception as e: messagebox.showerror("Error", f"Could not delete data folder:\n{data_p}\n{e}"); errs = True

    # Actualizar la lista global de datos ANTES de repoblar la tabla
    all_simulations_data = [s for s in all_simulations_data if s['name'] != sim_name]

    update_status(f"Deletion of '{sim_name}' " + ("completed with errors." if errs else "successful."))
    populate_simulations() # Refresca la tabla con la lista actualizada y filtro actual


# ======================================================
# Unity Batch Execution & Progress Monitoring (Sin cambios funcionales)
# ======================================================
def format_time(seconds):
    # (Sin cambios)
    if seconds is None or seconds < 0 or math.isinf(seconds) or math.isnan(seconds): return "--:--:--"
    if seconds == 0: return "0s"
    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600); minutes, secs = divmod(rem, 60)
    if hours > 0: return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    elif minutes > 0: return f"{minutes:02d}:{secs:02d}"
    else: return f"{secs}s"

def monitor_unity_progress(stop_event, operation_tag):
    # (Sin cambios)
    if not SIMULATION_PROJECT_PATH or not os.path.exists(SIMULATION_PROJECT_PATH):
        print(f"\nAdvertencia: La ruta '{SIMULATION_PROJECT_PATH}' no existe al iniciar el monitoreo.")
        return
    TARGET_SIZE_MB = 3000.0; BYTES_PER_MB = 1024*1024; TARGET_SIZE_BYTES = TARGET_SIZE_MB * BYTES_PER_MB
    last_update_time = 0; start_time = time.time(); initial_size_bytes = 0; eta_str = "Calculating..."
    try: initial_size_bytes = get_folder_size(SIMULATION_PROJECT_PATH)
    except Exception as e: print(f"\nError al obtener tamaño inicial para '{SIMULATION_PROJECT_PATH}': {e}"); initial_size_bytes = 0
    initial_size_mb = initial_size_bytes / BYTES_PER_MB
    print(f"[{operation_tag}] Iniciando monitoreo. Tamaño inicial: {initial_size_mb:.1f}MB. Objetivo: {TARGET_SIZE_MB:.0f}MB")
    while not stop_event.is_set():
        now = time.time()
        if now - last_update_time > 1.5:
            current_size_bytes = 0
            try:
                current_size_bytes = get_folder_size(SIMULATION_PROJECT_PATH)
                current_size_mb = current_size_bytes / BYTES_PER_MB
                elapsed_time = now - start_time
                size_increase_bytes = current_size_bytes - initial_size_bytes
                if elapsed_time > 5 and size_increase_bytes > 1024:
                    rate_bytes_per_sec = size_increase_bytes / elapsed_time
                    remaining_bytes = TARGET_SIZE_BYTES - current_size_bytes
                    if rate_bytes_per_sec > 0 and remaining_bytes > 0: eta_seconds = remaining_bytes / rate_bytes_per_sec; eta_str = f"ETA: {format_time(eta_seconds)}"
                    elif remaining_bytes <= 0: eta_str = "ETA: Completed"
                    else: eta_str = "ETA: --"
                elif elapsed_time <= 5: eta_str = "ETA: Calculating..."
                else: eta_str = "ETA: --"
                progress_percent = (current_size_mb / TARGET_SIZE_MB) * 100 if TARGET_SIZE_MB > 0 else 0
                display_percent = min(progress_percent, 100.0)
                status_msg = (f"[{operation_tag}] {current_size_mb:.1f}/{TARGET_SIZE_MB:.0f}MB ({display_percent:.1f}%) - {eta_str}      ")
                update_status(status_msg)
            except Exception as e: error_msg = f"Error reading size: {e}"[:30]; update_status(f"[{operation_tag}] {error_msg}... - {eta_str}      ")
            last_update_time = now
        time.sleep(0.5)
    final_size_mb = get_folder_size(SIMULATION_PROJECT_PATH) / BYTES_PER_MB
    print(f"\n[{operation_tag}] Monitoreo finalizado. Tamaño final: {final_size_mb:.1f}MB")

def run_unity_batchmode(exec_method, op_name, log_file, timeout=600, extra_args=None):
    # (Sin cambios)
    if not all([unity_path_ok, unity_version_ok, unity_projects_path_ok, SIMULATION_PROJECT_PATH]):
        update_status(f"Error: Cannot {op_name}. Check Unity config."); return False, None
    log_path = os.path.join(SIMULATION_PROJECT_PATH, log_file)
    cmd = [UNITY_EXECUTABLE, "-batchmode", "-quit", "-projectPath", os.path.normpath(SIMULATION_PROJECT_PATH),
           "-executeMethod", exec_method, "-logFile", log_path]
    if extra_args: cmd.extend(extra_args)
    success = False; stop = threading.Event(); exe_path_after_build = None
    monitor = threading.Thread(target=monitor_unity_progress, args=(stop, op_name.capitalize()), daemon=True)
    try:
        update_status(f"[{op_name.capitalize()}] Starting Unity..."); monitor.start()
        flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        process = subprocess.run(cmd, check=True, timeout=timeout, creationflags=flags, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        print(f"--- Unity Stdout Snippet ({op_name}) ---\n{process.stdout[-1000:]}\n---")
        if process.stderr: print(f"--- Unity Stderr Snippet ({op_name}) ---\n{process.stderr[-1000:]}\n---")
        update_status(f"[{op_name.capitalize()}] Unity process finished.")
        success = True
        if "BuildScript.PerformBuild" in exec_method:
            update_status(f"[{op_name.capitalize()}] Verifying build output...")
            _, exe_path_after_build = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
            found = False
            for attempt in range(6): # Check for a few seconds
                if exe_path_after_build and os.path.exists(exe_path_after_build): found = True; print(f"DEBUG build_task: Executable CONFIRMED (attempt {attempt+1}): {exe_path_after_build}"); break
                print(f"DEBUG build_task: Executable check attempt {attempt+1} failed for {exe_path_after_build}"); time.sleep(0.5)
            if found: update_status(f"[{op_name.capitalize()}] Executable verified.")
            else: print(f"WARN build_task: Executable NOT FOUND post-build: {exe_path_after_build}"); success = False; handle_unity_execution_error(FileNotFoundError(f"Build finished but output not found: {exe_path_after_build}"), op_name); update_status(f"[Error] {op_name.capitalize()} failed: Output missing.")
    except subprocess.CalledProcessError as e: handle_unity_execution_error(e, op_name); update_status(f"[Error] {op_name.capitalize()} failed (code {e.returncode}). Check log: {log_path}"); print(f"--- Unity Output on Error ({op_name}) ---"); # Incluir ruta log en status
    except subprocess.TimeoutExpired as e: handle_unity_execution_error(e, op_name); update_status(f"[Error] {op_name.capitalize()} timed out. Check log: {log_path}")
    except (FileNotFoundError, PermissionError) as e: handle_unity_execution_error(e, op_name); update_status(f"[Error] {op_name.capitalize()} failed (File/Permission).")
    except Exception as e: handle_unity_execution_error(e, f"{op_name} (unexpected)"); update_status(f"[Error] Unexpected error during {op_name}.")
    finally: stop.set(); monitor.join(timeout=1.0) # Asegurarse que el monitor termine
    return success, exe_path_after_build

def run_prefab_material_tool():
    # (Sin cambios)
    success, _ = run_unity_batchmode("PrefabMaterialCreator.CreatePrefabsAndMaterials", "prefabs tool", "prefab_tool_log.txt", timeout=600)
    return success

def build_simulation_task(extra_args, callback):
    # (Sin cambios)
    """Task run in thread to perform build and call callback."""
    disable_all_interactions() # Disable UI before starting
    success, final_exe_path = run_unity_batchmode("BuildScript.PerformBuild", "build", "build_log.txt", timeout=1800, extra_args=extra_args)
    if callback:
        main_window.after(0, lambda s=success, p=final_exe_path: callback(s, p))
    main_window.after(10, enable_all_interactions) # Ensure UI is enabled after callback

def build_simulation_threaded(callback=None):
    # (Sin cambios)
    """Starts the build process in a separate thread."""
    build_target, _ = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
    if not build_target:
        print("Error: Could not determine build target");
        update_status("Error: Build target unknown.")
        return
    extra = ["-buildTarget", build_target]
    threading.Thread(target=lambda: build_simulation_task(extra, callback), daemon=True).start()

def open_simulation_executable():
    # (Sin cambios)
    if not SIMULATION_PROJECT_PATH: update_status("Error: Project path not set."); return
    _, exe_path = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
    if not exe_path: messagebox.showerror("Error", "Could not determine executable path."); return
    if os.path.exists(exe_path):
        try:
            update_status(f"Launching: {os.path.basename(exe_path)}...")
            if platform.system() == "Darwin": subprocess.Popen(["open", exe_path])
            elif platform.system() == "Windows": os.startfile(exe_path)
            else: # Linux/Other
                if not os.access(exe_path, os.X_OK): os.chmod(exe_path, 0o755) # Asegurar permisos de ejecución
                subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path)) # Ejecutar desde su directorio
        except Exception as e: handle_unity_execution_error(e, f"run built sim ({os.path.basename(exe_path)})"); update_status(f"Error launching: {e}")
    else: messagebox.showerror("Error", f"Executable not found:\n{exe_path}\nPlease build the simulation first."); update_status("Error: Executable not found.")

def open_in_unity():
    # (Sin cambios)
    if not all([unity_path_ok, unity_projects_path_ok, UNITY_EXECUTABLE, SIMULATION_PROJECT_PATH]): messagebox.showerror("Error", "Cannot open in Unity. Check configuration."); return
    if not os.path.isdir(SIMULATION_PROJECT_PATH): messagebox.showerror("Error", f"Project path does not exist:\n{SIMULATION_PROJECT_PATH}"); return
    try:
        update_status(f"Opening project in Unity Editor..."); cmd = [UNITY_EXECUTABLE, "-projectPath", os.path.normpath(SIMULATION_PROJECT_PATH)]
        subprocess.Popen(cmd); update_status("Launching Unity Editor...")
    except Exception as e: handle_unity_execution_error(e, "open in Unity")

# ======================================================
# API Simulation Creation (Sin cambios funcionales)
# ======================================================
def create_simulation_thread(sim_name, sim_desc, original_states):
    # (populate_simulations actualizará la vista)
    update_status(f"Creating '{sim_name}' via API...");
    try: os.makedirs(SIMULATIONS_DIR, exist_ok=True)
    except Exception as e: messagebox.showerror("Critical Error", f"Could not create simulations directory: {e}"); update_status("Critical directory error."); main_window.after(0, enable_all_interactions); return
    success = False
    try:
        api_script = Path("./Scripts/api_manager.py").resolve()
        if not api_script.exists(): raise FileNotFoundError(f"API script not found: {api_script}")
        cmd = [sys.executable, str(api_script), sim_name, sim_desc]
        flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300, creationflags=flags, encoding='utf-8', errors='ignore')
        update_status(f"'{sim_name}' created successfully."); main_window.after(0, lambda: messagebox.showinfo("Success", f"Simulation '{sim_name}' created successfully via API."))
        # Actualizar datos y repoblar tabla
        global all_simulations_data
        all_simulations_data = get_simulations() # Recargar toda la lista
        main_window.after(50, populate_simulations); success = True
    except FileNotFoundError as e: messagebox.showerror("Critical Error", f"Required API script not found:\n{e}"); update_status("Error: Missing API script.")
    except subprocess.CalledProcessError as e:
        err_out = e.stderr if e.stderr else e.stdout; code=e.returncode; msg = f"API Script Error (Code: {code})"; details = f"Error creating simulation '{sim_name}' using the API script.\n\nOutput:\n{err_out}"; messagebox.showerror(msg, details); update_status(f"Error: API script failed (Code {code})."); print(f"API Script Error Output:\n{err_out}")
    except subprocess.TimeoutExpired: messagebox.showerror("Error", "Simulation creation via API timed out."); update_status("Error: API creation timeout.")
    except Exception as e: messagebox.showerror("Unexpected Error", f"CRITICAL ERROR during API creation:\n{e}"); update_status("Critical API creation error."); print(f"Err create_sim_thread: {e}"); import traceback; traceback.print_exc()
    finally:
        main_window.after(100, enable_all_interactions) # Habilitar UI después de todo

# ======================================================
# Verification Logic (Sin cambios funcionales)
# ======================================================
def perform_verification(show_results_box=False, on_startup=False):
    # (populate_simulations actualizará la vista)
    global unity_path_ok, unity_version_ok, unity_projects_path_ok, apis_key_ok, apis_models_ok, initial_verification_complete
    global UNITY_EXECUTABLE, UNITY_PROJECTS_PATH, OPENAI_API_KEY, FINE_TUNED_MODEL_NAME, SECONDARY_FINE_TUNED_MODEL_NAME
    global SIMULATION_PROJECT_PATH, ASSETS_FOLDER, STREAMING_ASSETS_FOLDER, SIMULATION_LOADED_FILE, last_simulation_loaded, all_simulations_data

    if not on_startup: update_status("Verifying configuration...")
    load_dotenv('.env', override=True)
    UNITY_EXECUTABLE = os.environ.get("UNITY_EXECUTABLE"); UNITY_PROJECTS_PATH = os.environ.get("UNITY_PROJECTS_PATH")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY"); FINE_TUNED_MODEL_NAME = os.getenv("FINE_TUNED_MODEL_NAME")
    SECONDARY_FINE_TUNED_MODEL_NAME = os.getenv("2ND_FINE_TUNED_MODEL_NAME")
    results = []; unity_path_ok=unity_version_ok=unity_projects_path_ok=apis_key_ok=apis_models_ok=False
    req_ver = "6000.0.32f1"

    # Verify Unity Executable
    if not UNITY_EXECUTABLE: results.append("❌ Unity Exe: Path missing in .env file.")
    elif not os.path.isfile(UNITY_EXECUTABLE): results.append(f"❌ Unity Exe: Path invalid or file not found:\n   '{UNITY_EXECUTABLE}'")
    else:
        unity_path_ok = True; results.append(f"✅ Unity Exe: Path OK.")
        if req_ver in UNITY_EXECUTABLE: unity_version_ok = True; results.append(f"✅ Unity Ver: String '{req_ver}' found in path.")
        else: results.append(f"❌ Unity Ver: Required version string '{req_ver}' NOT found in executable path.")

    # Verify Unity Projects Path
    if not UNITY_PROJECTS_PATH: results.append("❌ Projects Path: Missing in .env file.")
    elif not os.path.isdir(UNITY_PROJECTS_PATH): results.append(f"❌ Projects Path: Invalid or not a directory:\n   '{UNITY_PROJECTS_PATH}'")
    else:
        unity_projects_path_ok = True; results.append(f"✅ Projects Path: Directory OK.")
        SIMULATION_PROJECT_PATH = os.path.join(UNITY_PROJECTS_PATH, SIMULATION_PROJECT_NAME)
        ASSETS_FOLDER = os.path.join(SIMULATION_PROJECT_PATH, "Assets")
        STREAMING_ASSETS_FOLDER = os.path.join(ASSETS_FOLDER, "StreamingAssets")
        SIMULATION_LOADED_FILE = os.path.join(STREAMING_ASSETS_FOLDER, "simulation_loaded.txt")
        last_simulation_loaded = read_last_loaded_simulation_name()

    # Verify OpenAI API Key and Models
    if not OPENAI_API_KEY: results.append("❌ API Key: Missing in .env file.")
    else:
        openai.api_key = OPENAI_API_KEY
        try:
            if hasattr(openai, "models") and hasattr(openai.models, "list"): client = openai.OpenAI(); client.models.list(limit=1)
            else: openai.Model.list(limit=1)
            apis_key_ok = True; results.append("✅ API Key: Connection successful.")
            models_ok_list = []
            client = None;
            if hasattr(openai, "models") and hasattr(openai.models, "retrieve"): client = openai.OpenAI()
            for model_name_label, model_id in [("Primary Model", FINE_TUNED_MODEL_NAME), ("Secondary Model", SECONDARY_FINE_TUNED_MODEL_NAME)]:
                if not model_id:
                    results.append(f"⚠️ {model_name_label}: Not set in .env file.")
                    if model_name_label == "Primary Model": models_ok_list.append(False)
                    continue
                try:
                    if client: client.models.retrieve(model_id)
                    else: openai.Model.retrieve(model_id)
                    results.append(f"✅ {model_name_label}: ID '{model_id}' verified.")
                    if model_name_label == "Primary Model": models_ok_list.append(True)
                except (openai_error.InvalidRequestError, InvalidRequestError) as e:
                    results.append(f"❌ {model_name_label}: ID '{model_id}' NOT FOUND or invalid. Error: {e}")
                    if model_name_label == "Primary Model": models_ok_list.append(False)
                except Exception as model_error:
                    results.append(f"❌ {model_name_label}: Error verifying ID '{model_id}'. Error: {model_error}")
                    if model_name_label == "Primary Model": models_ok_list.append(False)
            apis_models_ok = models_ok_list and models_ok_list[0]
            if not apis_models_ok and FINE_TUNED_MODEL_NAME: results.append("❌ Primary Model: Verification failed (Invalid ID or API error).")
            elif not FINE_TUNED_MODEL_NAME: results.append("❌ Primary Model: ID not specified in .env.")
        except (openai_error.AuthenticationError, AuthenticationError) as auth_err: results.append(f"❌ API Key: Invalid or expired. Error: {auth_err}")
        except (openai_error.APIConnectionError, APIConnectionError) as conn_err: results.append(f"❌ API Connection: Failed to connect. Check network. Error: {conn_err}")
        except Exception as api_err: results.append(f"❌ API Error: Unexpected error during verification. Error: {api_err}")

    if not initial_verification_complete: initial_verification_complete = True
    unity_status = "Unity OK" if unity_path_ok and unity_version_ok and unity_projects_path_ok else "Unity ERR"
    api_status = "API OK" if apis_key_ok and apis_models_ok else "API ERR"
    final_status = f"{unity_status} | {api_status}"

    # Actualizar GUI
    if 'main_window' in globals() and main_window.winfo_exists():
        main_window.after(0, lambda: update_status(final_status))
        main_window.after(50, update_button_states)
        # Recargar datos de simulación y aplicar filtro actual
        all_simulations_data = get_simulations() # Actualizar la lista global
        main_window.after(100, filter_simulations) # Filtrar y mostrar

        if on_startup:
            error_messages = []
            if not unity_path_ok or not unity_projects_path_ok: error_messages.append("- Invalid Unity Executable or Projects path.")
            elif not unity_version_ok: error_messages.append(f"- Unity version mismatch (Required: '{req_ver}').")
            if not unity_path_ok or not unity_version_ok or not unity_projects_path_ok: error_messages.append("  (Loading, Building, and Opening might fail)")
            if not apis_key_ok: error_messages.append("- Invalid or missing OpenAI API Key.")
            elif not apis_models_ok: error_messages.append("- Primary fine-tuned model ID is invalid, not found, or missing.")
            if not apis_key_ok or not apis_models_ok: error_messages.append("  (Simulation creation via API will be disabled)")
            if error_messages:
                full_error_message = "Configuration Issues Found:\n\n" + "\n".join(error_messages) + "\n\nPlease use the 'Settings' button to correct the paths in the .env file."
                main_window.after(300, lambda msg=full_error_message: messagebox.showwarning("Initial Configuration Issues", msg))
    else: print(f"Verification Status (No GUI): {final_status}")

    if show_results_box:
        results_text = "Verification Results:\n\n" + "\n".join(results)
        all_ok = unity_path_ok and unity_version_ok and unity_projects_path_ok and apis_key_ok and apis_models_ok
        if 'main_window' in globals() and main_window.winfo_exists():
            main_window.after(0, lambda: messagebox.showinfo("Verification Complete", results_text) if all_ok else messagebox.showwarning("Verification Issues Found", results_text))


# ======================================================
# Configuration Window (Adaptado a CTk)
# ======================================================
def open_config_window():
    # (Sin cambios)
    cfg_win = ctk.CTkToplevel(main_window)
    cfg_win.title("Settings (.env Configuration)")
    center_window(cfg_win, 700, 200); cfg_win.resizable(False, False); cfg_win.transient(main_window); cfg_win.grab_set()
    frame = ctk.CTkFrame(cfg_win); frame.pack(fill="both", expand=True, padx=20, pady=20); frame.grid_columnconfigure(1, weight=1)
    entries = {}
    def create_row(parent, row_index, label_text, env_var, key, is_file=True):
        label = ctk.CTkLabel(parent, text=label_text, anchor="w", font=APP_FONT); label.grid(row=row_index, column=0, padx=(0, 10), pady=5, sticky="w")
        current_value = os.environ.get(env_var, ""); entry_var = ctk.StringVar(value=current_value); entries[key] = entry_var
        entry = ctk.CTkEntry(parent, textvariable=entry_var, font=APP_FONT); entry.grid(row=row_index, column=1, padx=5, pady=5, sticky="ew")
        def browse():
            initial_dir = "/"; current_path = entry_var.get()
            if current_path: potential_dir = os.path.dirname(current_path);
            if os.path.isdir(potential_dir): initial_dir = potential_dir
            elif os.path.isdir(current_path): initial_dir = current_path
            path = filedialog.askopenfilename(title=f"Select {label_text}", initialdir=initial_dir) if is_file else filedialog.askdirectory(title=f"Select {label_text}", initialdir=initial_dir)
            if path: entry_var.set(path)
        browse_button = ctk.CTkButton(parent, text="...", width=30, command=browse, font=APP_FONT); browse_button.grid(row=row_index, column=2, padx=(5, 0), pady=5)
    create_row(frame, 0, "Unity Executable:", "UNITY_EXECUTABLE", "unity_exe", is_file=True)
    create_row(frame, 1, "Unity Projects Folder:", "UNITY_PROJECTS_PATH", "projects_path", is_file=False)
    button_frame = ctk.CTkFrame(cfg_win, fg_color="transparent"); button_frame.pack(fill="x", padx=20, pady=(0, 20)); button_frame.columnconfigure(0, weight=1); button_frame.columnconfigure(1, weight=0); button_frame.columnconfigure(2, weight=0); button_frame.columnconfigure(3, weight=1)
    def save_config():
        current_api_key = os.getenv("OPENAI_API_KEY", ""); current_model1 = os.getenv("FINE_TUNED_MODEL_NAME", ""); current_model2 = os.getenv("2ND_FINE_TUNED_MODEL_NAME", "")
        new_unity_exe = entries['unity_exe'].get().strip(); new_projects_path = entries['projects_path'].get().strip()
        if not new_unity_exe or not new_projects_path: messagebox.showerror("Input Error", "Both Unity Executable and Projects Folder paths are required.", parent=cfg_win); return
        try:
            with open(".env", "w", encoding='utf-8') as f:
                f.write(f"UNITY_EXECUTABLE={new_unity_exe}\n"); f.write(f"UNITY_PROJECTS_PATH={new_projects_path}\n")
                f.write(f"OPENAI_API_KEY={current_api_key}\n"); f.write(f"FINE_TUNED_MODEL_NAME={current_model1}\n"); f.write(f"2ND_FINE_TUNED_MODEL_NAME={current_model2}\n")
            messagebox.showinfo("Success", "Settings saved to .env file.\nRe-verifying configuration...", parent=cfg_win); cfg_win.destroy()
            main_window.after(100, lambda: perform_verification(show_results_box=True))
        except Exception as e: messagebox.showerror("Save Error", f"Could not write to .env file:\n{e}", parent=cfg_win)
    save_button = ctk.CTkButton(button_frame, text="Save and Verify", command=save_config, font=APP_FONT, fg_color=COLOR_SUCCESS[ctk.get_appearance_mode() == "Dark"], hover_color=COLOR_INFO[ctk.get_appearance_mode() == "Dark"]); save_button.grid(row=0, column=1, padx=10, pady=10)
    cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=cfg_win.destroy, font=APP_FONT, fg_color=COLOR_WARNING[ctk.get_appearance_mode() == "Dark"], hover_color=COLOR_DANGER[ctk.get_appearance_mode() == "Dark"]); cancel_button.grid(row=0, column=2, padx=10, pady=10)

# ======================================================
# GUI Definitions (Callbacks - Adaptados a CTk y búsqueda)
# ======================================================
def populate_simulations():
    """Recarga la lista completa de simulaciones y actualiza la vista (aplicando filtro)."""
    if not initial_verification_complete: return

    update_status("Reloading simulation list...")
    global all_simulations_data, last_simulation_loaded
    all_simulations_data = get_simulations() # Obtener la lista fresca
    last_simulation_loaded = read_last_loaded_simulation_name() # Actualizar por si cambió

    # Ordenar la lista completa por nombre por defecto (ignorar mayúsculas/minúsculas)
    all_simulations_data.sort(key=lambda x: x['name'].lower())

    # Llamar a filter_simulations para mostrar la lista (con el filtro actual si existe)
    filter_simulations() # Usa el texto actual en search_entry

    update_status(f"List refreshed ({len(all_simulations_data)} total simulations found).")
    update_button_states()

def filter_simulations(event=None):
    """Filtra y muestra las simulaciones en el Treeview basado en el texto de búsqueda."""
    if 'sim_tree' not in globals() or 'search_entry' not in globals(): return # Evitar errores tempranos

    search_term = search_entry.get().lower().strip()

    # Limpiar Treeview actual
    for item in sim_tree.get_children():
        try: sim_tree.delete(item)
        except tk.TclError: pass

    displayed_count = 0
    # Iterar sobre la lista completa almacenada
    for i, sim_data in enumerate(all_simulations_data):
        # Aplicar filtro (si hay término de búsqueda)
        if search_term and search_term not in sim_data['name'].lower():
            continue # Saltar si no coincide

        # Si coincide (o no hay filtro), mostrarlo
        is_loaded = (sim_data["name"] == last_simulation_loaded)
        row_tag = "evenrow" if displayed_count % 2 == 0 else "oddrow"
        item_tags = [row_tag]
        if is_loaded:
            item_tags.append("loaded")

        try:
            sim_tree.insert("", "end", iid=sim_data["name"],
                            values=(sim_data["name"],
                                    sim_data["creation"],
                                    sim_data["last_opened"],
                                    "", # Columna 'Loaded' vacía (icono en header)
                                    "", # Columna 'Load/Run' vacía (icono en header)
                                    ""), # Columna 'Delete' vacía (icono en header)
                            tags=tuple(item_tags))
            displayed_count += 1
        except tk.TclError as e:
            print(f"Error inserting filtered item '{sim_data['name']}': {e}")

    # Actualizar estado después de filtrar
    if search_term:
        status_msg = f"Displaying {displayed_count} of {len(all_simulations_data)} simulations matching '{search_term}'."
    elif initial_verification_complete : # Solo mostrar si la verificación inicial ya pasó
         status_msg = f"Displaying {len(all_simulations_data)} simulations."
    else:
         status_msg = status_label.cget("text") # Mantener estado actual si aún inicializando
    update_status(status_msg)

    # Reaplicar ordenamiento si existe uno activo
    if 'last_sort_column' in globals() and last_sort_column:
         sort_column(sim_tree, last_sort_column, sort_order[last_sort_column])

    update_button_states() # Actualizar botones (ej. 'Show Graphs' puede cambiar)

def clear_search():
    """Borra el campo de búsqueda y refresca la lista."""
    if 'search_entry' in globals():
        search_entry.delete(0, 'end')
        filter_simulations() # Vuelve a mostrar todo

def update_button_states():
    # (Sin cambios funcionales, solo depende de la selección y estado global)
    if 'main_window' not in globals() or not main_window.winfo_exists() or is_build_running : return

    has_selection = bool(sim_tree.selection())
    can_create = apis_key_ok and apis_models_ok
    # can_load_run = unity_path_ok and unity_version_ok and unity_projects_path_ok # Ya no se usa directamente aquí

    # Determinar estado habilitado/deshabilitado ('normal' o 'disabled')
    def get_state(enabled): return "normal" if enabled else "disabled"

    reload_state = get_state(not is_build_running)
    graph_state = get_state(has_selection and not is_build_running)
    create_state = get_state(can_create and not is_build_running)
    verify_state = get_state(not is_build_running)
    settings_state = get_state(not is_build_running)
    about_state = get_state(not is_build_running)
    unity_down_state = get_state(not is_build_running)
    exit_state = get_state(not is_build_running)
    search_state = get_state(not is_build_running) # Habilitar/deshabilitar búsqueda

    # Aplicar estados
    try:
        reload_btn.configure(state=reload_state)
        graph_btn.configure(state=graph_state)
        create_btn.configure(state=create_state)
        if 'settings_btn' in globals(): settings_btn.configure(state=settings_state)
        if 'verify_btn' in globals(): verify_btn.configure(state=verify_state)
        if 'unity_down_btn' in globals(): unity_down_btn.configure(state=unity_down_state)
        if 'about_btn' in globals(): about_btn.configure(state=about_state)
        if 'exit_btn' in globals(): exit_btn.configure(state=exit_state)
        if 'search_entry' in globals(): search_entry.configure(state=search_state)
        if 'clear_search_btn' in globals(): clear_search_btn.configure(state=search_state)
    except (NameError, tk.TclError) as e:
         print(f"Warning: Could not update all button states: {e}")

def on_load_simulation_request(simulation_name):
    # (Sin cambios funcionales)
    global is_build_running
    if is_build_running: return
    print(f"Load request received for: {simulation_name}")
    if not all([unity_path_ok, unity_version_ok, unity_projects_path_ok]):
        messagebox.showerror("Unity Configuration Error", "Cannot load simulation: Invalid Unity configuration detected.\nPlease check Unity Executable path, version, and Projects Folder path in Settings.")
        return
    if simulation_name == last_simulation_loaded:
        update_status(f"'{simulation_name}' is already loaded. Showing options...")
        update_last_opened(simulation_name)
        _, current_exe_path = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
        main_window.after(0, lambda s=simulation_name, p=current_exe_path: show_options_window(s, p))
        return
    disable_all_interactions()
    update_status(f"Starting load process for '{simulation_name}'...")
    threading.Thread(target=load_simulation_logic, args=(simulation_name,), daemon=True).start()

def load_simulation_logic(simulation_name):
    # (Sin cambios funcionales)
    """Función ejecutada en un hilo para cargar y construir."""
    load_success = False
    try:
        update_status(f"Loading '{simulation_name}': Closing existing Unity instances...")
        ensure_unity_closed()
        update_status(f"Loading '{simulation_name}': Copying files...")
        load_success = load_simulation(simulation_name)
        if load_success:
            update_status(f"Loading '{simulation_name}': Running prefab/material tool...")
            prefab_success = run_prefab_material_tool()
            if prefab_success:
                update_status(f"Loading '{simulation_name}': Starting build process...")
                build_simulation_threaded(callback=lambda success, path: build_callback(success, simulation_name, path))
            else:
                update_status(f"Error during post-load step (prefabs/materials) for '{simulation_name}'. Build cancelled.")
                messagebox.showerror("Post-Load Error", f"The prefab and material creation tool failed for '{simulation_name}'. The build process has been cancelled.")
                main_window.after(10, enable_all_interactions)
        else:
            update_status(f"Error loading files for '{simulation_name}'. Load process stopped.")
            main_window.after(10, enable_all_interactions)
    except Exception as e:
        print(f"CRITICAL ERROR in load_simulation_logic thread: {e}"); import traceback; traceback.print_exc()
        update_status(f"Critical error during load process for '{simulation_name}'.")
        main_window.after(10, enable_all_interactions)

def build_callback(success, simulation_name, executable_path):
    # (Sin cambios funcionales)
    """Callback ejecutado tras finalizar el build (en hilo principal)."""
    if success and executable_path and os.path.exists(executable_path):
        update_status(f"Build for '{simulation_name}' completed successfully.")
        show_options_window(simulation_name, executable_path)
    elif success and not executable_path:
         update_status(f"Build for '{simulation_name}' finished, but executable path could not be determined.")
         messagebox.showerror("Build Error", f"The build process for '{simulation_name}' completed, but the final executable path is missing.")
    elif success and not os.path.exists(executable_path):
        update_status(f"Build for '{simulation_name}' finished, but executable not found at: {executable_path}")
        messagebox.showerror("Build Error", f"The build process for '{simulation_name}' completed, but the executable file was not found at the expected location:\n{executable_path}\nCheck build logs.")
    else:
        update_status(f"Build process for '{simulation_name}' failed.")
    # enable_all_interactions() es llamado por build_simulation_task *después* de este callback.

def on_delete_simulation_request(simulation_name):
    # (Sin cambios funcionales)
    global is_build_running
    if is_build_running: return
    print(f"Delete request received for: {simulation_name}")
    delete_simulation(simulation_name) # Ya pide confirmación y actualiza

def on_show_graphs_thread():
    # (Sin cambios funcionales)
    global is_build_running
    if is_build_running: return
    selected_items = sim_tree.selection()
    if not selected_items:
        messagebox.showwarning("No Simulation Selected", "Please select a simulation from the list to view its graphs.")
        return
    sim_name = sim_tree.item(selected_items[0], "values")[0]
    disable_all_interactions()
    update_status(f"Preparing to generate graphs for '{sim_name}'...")
    threading.Thread(target=show_graphs_logic, args=(sim_name,), daemon=True).start()

def show_graphs_logic(sim_name):
    # (Sin cambios funcionales)
    """Ejecutado en hilo para generar y mostrar gráficos."""
    script_ran = False
    try:
        data_dir = Path.home() / "Documents" / "SimulationLoggerData" / sim_name
        csv_path = data_dir / "SimulationStats.csv"; graphs_output_dir = data_dir / "Graficos"
        if not csv_path.exists():
            messagebox.showerror("Data File Not Found", f"The data file 'SimulationStats.csv' for '{sim_name}' was not found in:\n{data_dir}"); update_status(f"Error: CSV data file not found for '{sim_name}'."); return
        graphs_output_dir.mkdir(parents=True, exist_ok=True)
        sim_specific_script = Path(SIMULATIONS_DIR) / sim_name / "Assets" / "Scripts" / "SimulationData" / "SimulationGraphics.py"
        generic_script = Path("./Scripts/SimulationGraphics.py").resolve()
        script_to_run = str(sim_specific_script) if sim_specific_script.exists() else (str(generic_script) if generic_script.exists() else None)
        if not script_to_run:
            messagebox.showerror("Graph Script Not Found", "Could not find 'SimulationGraphics.py' in simulation Assets or './Scripts'."); update_status("Error: Graph script not found."); return
        update_status(f"Running graph script for '{sim_name}': {os.path.basename(script_to_run)}")
        process = subprocess.Popen([sys.executable, script_to_run, sim_name]); process.wait(timeout=120); script_ran = True
        if process.returncode != 0:
             messagebox.showwarning("Graph Script Warning", f"Graph script for '{sim_name}' finished with exit code {process.returncode}. Graphs might be incomplete."); update_status(f"Warning: Graph script '{sim_name}' exited code {process.returncode}.")
        else: update_status(f"Graph script for '{sim_name}' completed.")
        print(f"Opening graphs folder: {graphs_output_dir}")
        open_graphs_folder(sim_name)
    except FileNotFoundError as fnf_err: messagebox.showerror("File Not Found Error", f"Could not find file/executable:\n{fnf_err}"); update_status("Error: File not found during graph generation.")
    except subprocess.TimeoutExpired: messagebox.showerror("Timeout Error", f"Graph script for '{sim_name}' timed out."); update_status(f"Error: Graph script for '{sim_name}' timed out.")
    except Exception as e: messagebox.showerror("Graph Generation Error", f"Error generating graphs for '{sim_name}':\n{e}"); update_status(f"Error generating graphs for '{sim_name}'."); print(f"Graph exception: {e}"); import traceback; traceback.print_exc()
    finally: main_window.after(0, enable_all_interactions)

def on_create_simulation():
    # (Sin cambios funcionales)
    global is_build_running
    if is_build_running: return
    if not apis_key_ok or not apis_models_ok:
        messagebox.showerror("API Configuration Error", "Cannot create simulation via API: Invalid OpenAI API Key or primary fine-tuned model.\nPlease check your .env file and verify configuration."); return
    sim_name = custom_askstring("Create New Simulation", "Enter a name for the new simulation:")
    if not sim_name: update_status("Simulation creation cancelled."); return
    sim_name = sim_name.strip()
    invalid_chars = r'<>:"/\|?*' + "".join(map(chr, range(32)))
    if not sim_name or any(c in sim_name for c in invalid_chars):
        messagebox.showerror("Invalid Simulation Name", f"Name '{sim_name}' contains invalid characters."); update_status("Invalid simulation name."); return
    if os.path.exists(os.path.join(SIMULATIONS_DIR, sim_name)):
        messagebox.showerror("Simulation Exists", f"Simulation '{sim_name}' already exists."); update_status(f"Simulation '{sim_name}' exists."); return
    sim_desc = custom_askstring("Simulation Description", "Briefly describe the simulation:")
    if sim_desc is None: update_status("Simulation creation cancelled."); return
    else: sim_desc = sim_desc.strip() # Permitir vacío
    disable_all_interactions()
    update_status(f"Initiating creation of simulation '{sim_name}'...")
    threading.Thread(target=create_simulation_thread, args=(sim_name, sim_desc, {}), daemon=True).start()

def show_options_window(simulation_name, executable_path):
    # (Sin cambios funcionales)
    opt_win = ctk.CTkToplevel(main_window); opt_win.title(f"Options for '{simulation_name}'"); center_window(opt_win, 380, 200); opt_win.resizable(False, False); opt_win.transient(main_window); opt_win.grab_set()
    frame = ctk.CTkFrame(opt_win); frame.pack(expand=True, fill="both", padx=20, pady=20)
    title_label = ctk.CTkLabel(frame, text=f"Simulation '{simulation_name}' is loaded.", font=APP_FONT_BOLD); title_label.pack(pady=(0, 15))
    exec_exists = executable_path and os.path.exists(executable_path); run_button_state = "normal" if exec_exists else "disabled"
    def run_and_close(): open_simulation_executable(); opt_win.destroy()
    def open_unity_and_close(): open_in_unity(); opt_win.destroy()
    run_button = ctk.CTkButton(frame, text="Run Simulation", command=run_and_close, state=run_button_state, font=APP_FONT, height=40, fg_color=COLOR_SUCCESS[ctk.get_appearance_mode() == "Dark"], hover_color=COLOR_INFO[ctk.get_appearance_mode() == "Dark"]); run_button.pack(pady=8, fill="x", padx=10)
    if not exec_exists: warning_label = ctk.CTkLabel(frame, text="Executable not found.", text_color="gray", font=("Segoe UI", 9)); warning_label.pack(pady=(0, 5))
    open_button = ctk.CTkButton(frame, text="Open Project in Unity Editor", command=open_unity_and_close, font=APP_FONT, height=40, fg_color=COLOR_INFO[ctk.get_appearance_mode() == "Dark"], hover_color=COLOR_SUCCESS[ctk.get_appearance_mode() == "Dark"]); open_button.pack(pady=8, fill="x", padx=10)
    update_status(f"Options available for loaded simulation '{simulation_name}'."); opt_win.wait_window()

def handle_tree_click(event):
    # (Sin cambios funcionales, ya maneja clicks en celdas)
    global is_build_running
    if is_build_running: return
    region = sim_tree.identify_region(event.x, event.y)
    if region == "cell":
        item_id = sim_tree.identify_row(event.y); col_id = sim_tree.identify_column(event.x)
        if not item_id or not col_id: cancel_tooltip(sim_tree); return
        try:
            col_index = int(col_id.replace('#','')) - 1; column_names = sim_tree['columns']
            if 0 <= col_index < len(column_names):
                col_name = column_names[col_index]; simulation_name = sim_tree.item(item_id, "values")[0]
                sim_tree.selection_set(item_id); sim_tree.focus(item_id); update_button_states()
                hide_tooltip()
                if col_name == "col_load": on_load_simulation_request(simulation_name)
                elif col_name == "col_delete": on_delete_simulation_request(simulation_name)
            else: cancel_tooltip(sim_tree)
        except Exception as e: print(f"Error handling Treeview click: {e}"); cancel_tooltip(sim_tree)
    elif region == "heading": pass # Ordenamiento manejado por comando
    else: cancel_tooltip(sim_tree)

def handle_tree_motion(event):
    # (Actualizado para tooltip de columnas de acción)
    global is_build_running
    if is_build_running: return
    region = sim_tree.identify_region(event.x, event.y)
    if region != "cell": cancel_tooltip(sim_tree); return
    col_id = sim_tree.identify_column(event.x); item_id = sim_tree.identify_row(event.y)
    if not col_id or not item_id: cancel_tooltip(sim_tree); return
    try:
        col_index = int(col_id.replace('#','')) - 1; motion_columns = sim_tree['columns']
        if 0 <= col_index < len(motion_columns):
            col_name = motion_columns[col_index]; tooltip_text = None
            # Mostrar tooltip solo para las columnas de acción
            if col_name == "col_load": tooltip_text = f"Load / Run Simulation '{sim_tree.item(item_id, 'values')[0]}'"
            elif col_name == "col_delete": tooltip_text = f"Delete Simulation '{sim_tree.item(item_id, 'values')[0]}'"
            elif col_name == "col_loaded": # Tooltip para la columna 'Loaded'
                 if sim_tree.item(item_id, "tags") and "loaded" in sim_tree.item(item_id, "tags"):
                     tooltip_text = f"'{sim_tree.item(item_id, 'values')[0]}' is currently loaded in the project folder."

            if tooltip_text: schedule_tooltip(sim_tree, tooltip_text)
            else: cancel_tooltip(sim_tree)
        else: cancel_tooltip(sim_tree)
    except Exception: cancel_tooltip(sim_tree)

def handle_tree_leave(event):
    # (Sin cambios)
    cancel_tooltip(sim_tree)

def load_logo(path, target_width):
    # (Sin cambios)
    global logo_photo_ref
    try:
        img = Image.open(path); width_percent = (target_width / float(img.size[0])); target_height = int((float(img.size[1]) * float(width_percent))); img = img.resize((target_width, target_height), Image.Resampling.LANCZOS); logo_photo_ref = ImageTk.PhotoImage(img); return logo_photo_ref
    except FileNotFoundError: print(f"Warning: Logo image not found at '{path}'"); return None
    except Exception as e: print(f"Error loading logo image: {e}"); return None

# ======================================================
# GUI Setup (Usando CustomTkinter, con búsqueda y cabeceras icono)
# ======================================================
main_window = ctk.CTk()
try:
    if platform.system() == "Windows": main_window.iconbitmap("icono.ico")
except tk.TclError: print("Warning: Could not load or set 'icono.ico'.")

main_window.title("Unity Simulation Manager v2.0 (CTk + Search)")
initial_width = 1050 # Un poco más ancho para búsqueda
initial_height = 700
center_window(main_window, initial_width, initial_height)
main_window.resizable(True, True)
main_window.minsize(850, 550) # Ajustar mínimo

# --- Layout Principal (Grid) ---
main_window.columnconfigure(0, weight=0) # Sidebar
main_window.columnconfigure(1, weight=1) # Contenido
main_window.rowconfigure(0, weight=1)    # Contenido + Sidebar
main_window.rowconfigure(1, weight=0)    # Status bar

# --- Sidebar Frame ---
sidebar_width = 200
sidebar_frame = ctk.CTkFrame(main_window, width=sidebar_width, corner_radius=5, fg_color=COLOR_SIDEBAR_BG)
sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
sidebar_frame.grid_propagate(False); sidebar_frame.columnconfigure(0, weight=1)

# --- Logo en Sidebar ---
logo_photo = load_logo(LOGO_PATH, LOGO_WIDTH)
if logo_photo: logo_label = ctk.CTkLabel(sidebar_frame, image=logo_photo, text=""); logo_label.pack(pady=(20, 10), padx=10)
else: ctk.CTkLabel(sidebar_frame, text="[Logo]", font=(APP_FONT[0], 14, "italic")).pack(pady=(20, 10), padx=10)
ctk.CTkLabel(sidebar_frame, text="Menu", font=(APP_FONT[0], 16, "bold")).pack(pady=(5, 15), padx=10)

# --- Botones Sidebar ---
settings_btn = ctk.CTkButton(sidebar_frame, text="Settings (.env)", command=open_config_window, font=APP_FONT); settings_btn.pack(fill="x", padx=15, pady=5)
verify_btn = ctk.CTkButton(sidebar_frame, text="Verify Config", command=lambda: perform_verification(show_results_box=True), font=APP_FONT); verify_btn.pack(fill="x", padx=15, pady=5)
separator = ctk.CTkFrame(sidebar_frame, height=2, fg_color="gray"); separator.pack(fill="x", padx=15, pady=15)
unity_down_btn = ctk.CTkButton(sidebar_frame, text="Download Unity Hub", command=lambda: webbrowser.open("unityhub://6000.0.32f1/b2e806cf271c"), font=APP_FONT); unity_down_btn.pack(fill="x", padx=15, pady=5)
about_btn = ctk.CTkButton(sidebar_frame, text="About", command=lambda: messagebox.showinfo("About", "Unity Simulation Manager v2.0\n(CustomTkinter + Search)\n\nManage Unity simulation projects."), font=APP_FONT); about_btn.pack(fill="x", padx=15, pady=5)
exit_btn = ctk.CTkButton(sidebar_frame, text="Exit Application", command=main_window.quit, font=APP_FONT, fg_color=COLOR_DANGER[ctk.get_appearance_mode() == "Dark"], hover_color=COLOR_WARNING[ctk.get_appearance_mode() == "Dark"]); exit_btn.pack(fill="x", side='bottom', padx=15, pady=(10, 20))

# --- Main Content Frame ---
main_content_frame = ctk.CTkFrame(main_window, corner_radius=5)
main_content_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
main_content_frame.columnconfigure(0, weight=1)
main_content_frame.rowconfigure(0, weight=0) # Header
main_content_frame.rowconfigure(1, weight=0) # Search Bar
main_content_frame.rowconfigure(2, weight=1) # Treeview se expande
main_content_frame.rowconfigure(3, weight=0) # Botones inferiores

# --- Header ---
header_frame = ctk.CTkFrame(main_content_frame, fg_color="transparent"); header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5)); header_frame.columnconfigure(0, weight=1)
header_label = ctk.CTkLabel(header_frame, text="Unity Simulation Manager", font=TITLE_FONT, anchor="center"); header_label.grid(row=0, column=0, pady=(0, 10))

# --- Search Bar Frame ---
search_frame = ctk.CTkFrame(main_content_frame, fg_color="transparent")
search_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 5))
search_frame.columnconfigure(1, weight=1) # Entry se expande

search_label = ctk.CTkLabel(search_frame, text="Search:", font=APP_FONT)
search_label.grid(row=0, column=0, padx=(5, 5), pady=5)

search_entry = ctk.CTkEntry(search_frame, placeholder_text="Type simulation name to filter...", font=APP_FONT)
search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
# Asociar el evento de liberación de tecla a la función de filtrado
search_entry.bind("<KeyRelease>", filter_simulations)

clear_search_btn = ctk.CTkButton(search_frame, text="Clear", width=60, font=APP_FONT, command=clear_search,
                                 fg_color=COLOR_SEARCH_CLEAR[ctk.get_appearance_mode() == "Dark"],
                                 hover_color=COLOR_WARNING[ctk.get_appearance_mode() == "Dark"])
clear_search_btn.grid(row=0, column=2, padx=(5, 5), pady=5)

# --- Treeview Frame ---
tree_frame = ctk.CTkFrame(main_content_frame, corner_radius=5)
# Ahora en la fila 2
tree_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
tree_frame.columnconfigure(0, weight=1); tree_frame.rowconfigure(0, weight=1)

# --- Treeview (ttk) y Scrollbar (CTk) ---
columns = ("nombre", "creacion", "ultima", "col_loaded", "col_load", "col_delete")
style = ttk.Style()
bg_color = main_window._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
text_color = main_window._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
selected_color = main_window._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"])
header_bg = main_window._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"])
header_fg = main_window._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["text_color"])
style.theme_use("clam")
style.configure("Treeview", background=bg_color, foreground=text_color, fieldbackground=bg_color, rowheight=28, font=TREEVIEW_FONT)
style.configure("Treeview.Heading", font=TREEVIEW_HEADER_FONT, background=header_bg, foreground=header_fg, relief="flat", padding=(10, 5))
style.map("Treeview.Heading", relief=[('active','groove')])
style.map('Treeview', background=[('selected', selected_color)], foreground=[('selected', header_fg)])
sim_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse", style="Treeview")

# --- Configuración Columnas Treeview (Iconos en Cabeceras) ---
sim_tree.heading("nombre", text="Simulation Name", anchor='w')
sim_tree.column("nombre", width=300, anchor="w", stretch=tk.YES)
sim_tree.heading("creacion", text="Created", anchor='center')
sim_tree.column("creacion", width=120, anchor="center", stretch=tk.NO)
sim_tree.heading("ultima", text="Last Used", anchor='center')
sim_tree.column("ultima", width=120, anchor="center", stretch=tk.NO)
# Usar iconos como texto de cabecera
sim_tree.heading("col_loaded", text=loaded_indicator_text, anchor='center')
sim_tree.column("col_loaded", width=35, stretch=tk.NO, anchor="center") # Ancho ajustado
sim_tree.heading("col_load", text=play_icon_text, anchor='center')
sim_tree.column("col_load", width=45, stretch=tk.NO, anchor="center")
sim_tree.heading("col_delete", text=delete_icon_text, anchor='center')
sim_tree.column("col_delete", width=45, stretch=tk.NO, anchor="center")

# --- Configuración Ordenamiento Treeview ---
global last_sort_column
last_sort_column = None
sort_order = {col: False for col in columns if col not in ["col_load", "col_delete", "col_loaded"]}
# (Función sort_column sin cambios, se pega abajo por completitud)
def sort_column(tree, col, reverse):
    if col in ["col_load", "col_delete", "col_loaded"]: return
    global sort_order, last_sort_column
    try:
        data = [(tree.set(item, col), item) for item in tree.get_children('')]
        def convert_sort_key(value):
            if col in ("creacion", "ultima"):
                if value in ("???", "Never") or not value: return 0
                try: return time.mktime(time.strptime(value, "%y-%m-%d %H:%M"))
                except ValueError: return 0
            else: return str(value).lower()
        data.sort(key=lambda t: convert_sort_key(t[0]), reverse=reverse)
        for i, (_, item) in enumerate(data): tree.move(item, '', i)
        sort_order[col] = reverse; last_sort_column = col
        # Actualizar texto cabecera con flecha (opcional pero útil)
        for c in sort_order:
             current_text = tree.heading(c)['text'].replace(' ▲', '').replace(' ▼', '')
             if c == col: new_text = current_text + (' ▼' if reverse else ' ▲')
             else: new_text = current_text
             tree.heading(c, text=new_text, command=lambda c_=c: sort_column(tree, c_, not sort_order[c_]))

    except Exception as e: print(f"Error sorting column '{col}': {e}")

for col in columns:
    if col not in ["col_load", "col_delete", "col_loaded"]:
        current_heading_text = sim_tree.heading(col)['text'].replace(' ▲', '').replace(' ▼', '')
        sim_tree.heading(col, text=current_heading_text, command=lambda c=col: sort_column(sim_tree, c, False), anchor='w' if col=='nombre' else 'center')

# --- Configuración de Tags ---
mode = ctk.get_appearance_mode(); odd_color = "#FDFDFD" if mode == "Light" else "#393939"; even_color = "#F7F7F7" if mode == "Light" else "#343434"; loaded_color_bg = "#E0F2E0" if mode == "Light" else "#304D30"; loaded_color_fg = "#000000" if mode == "Light" else "#FFFFFF"
sim_tree.tag_configure('oddrow', background=odd_color, foreground=text_color)
sim_tree.tag_configure('evenrow', background=even_color, foreground=text_color)
sim_tree.tag_configure('loaded', background=loaded_color_bg, foreground=loaded_color_fg, font=TREEVIEW_FONT)

# --- Posicionar Treeview y Scrollbar ---
sim_tree.grid(row=0, column=0, sticky="nsew")
scrollbar = ctk.CTkScrollbar(tree_frame, command=sim_tree.yview); scrollbar.grid(row=0, column=1, sticky="ns"); sim_tree.configure(yscrollcommand=scrollbar.set)

# --- Event Bindings Treeview ---
sim_tree.bind('<<TreeviewSelect>>', lambda e: update_button_states()); sim_tree.bind("<Button-1>", handle_tree_click); sim_tree.bind("<Motion>", handle_tree_motion); sim_tree.bind("<Leave>", handle_tree_leave)

# --- Button Frame (Bottom) ---
# Ahora en la fila 3
button_frame_bottom = ctk.CTkFrame(main_content_frame, fg_color="transparent")
button_frame_bottom.grid(row=3, column=0, pady=(10, 10), padx=10, sticky="ew")
button_frame_bottom.columnconfigure(0, weight=1); button_frame_bottom.columnconfigure(1, weight=0); button_frame_bottom.columnconfigure(2, weight=0); button_frame_bottom.columnconfigure(3, weight=0); button_frame_bottom.columnconfigure(4, weight=1)
button_height = 35
reload_btn = ctk.CTkButton(button_frame_bottom, text="Reload List", command=populate_simulations, font=APP_FONT, height=button_height, fg_color=COLOR_RELOAD[ctk.get_appearance_mode() == "Dark"], hover_color=COLOR_INFO[ctk.get_appearance_mode() == "Dark"]); reload_btn.grid(row=0, column=1, padx=10, pady=5)
graph_btn = ctk.CTkButton(button_frame_bottom, text="Show Graphs", command=on_show_graphs_thread, font=APP_FONT, height=button_height, fg_color=COLOR_GRAPH[ctk.get_appearance_mode() == "Dark"], hover_color=COLOR_INFO[ctk.get_appearance_mode() == "Dark"]); graph_btn.grid(row=0, column=2, padx=10, pady=5)
create_btn = ctk.CTkButton(button_frame_bottom, text="Create Simulation (API)", command=on_create_simulation, font=APP_FONT, height=button_height, fg_color=COLOR_SUCCESS[ctk.get_appearance_mode() == "Dark"], hover_color=COLOR_INFO[ctk.get_appearance_mode() == "Dark"]); create_btn.grid(row=0, column=3, padx=10, pady=5)

# --- Status Bar ---
status_frame = ctk.CTkFrame(main_window, height=25, corner_radius=0); status_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
status_label = ctk.CTkLabel(status_frame, text="Initializing...", anchor="w", font=STATUS_FONT); status_label.pack(side="left", fill="x", expand=True, padx=10, pady=3)

# ======================================================
# App Initialization
# ======================================================
if __name__ == "__main__":
    update_button_states()
    update_status("Performing initial configuration verification...")
    threading.Thread(target=perform_verification, args=(False, True), daemon=True).start()
    def on_closing():
        global is_build_running
        if is_build_running: messagebox.showwarning("Build in Progress", "A build is running. Please wait before closing."); return
        if messagebox.askokcancel("Exit Confirmation", "Exit Unity Simulation Manager?", icon='question'):
            update_status("Closing application..."); print("Attempting to close Unity Editor instances..."); ensure_unity_closed(); print("Exiting."); main_window.destroy()
    main_window.protocol("WM_DELETE_WINDOW", on_closing)
    main_window.mainloop()