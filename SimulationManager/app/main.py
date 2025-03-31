# -*- coding: utf-8 -*-
import sys
import os
import shutil
import subprocess
import platform
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dotenv import load_dotenv
from pathlib import Path
import psutil
import openai
import math
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

# Icons (text fallback)
play_icon_text = "▶"
delete_icon_text = "🗑️"
loaded_indicator_text = "✓"

# Tooltip handling
tooltip_window = None
tooltip_delay = 700
tooltip_job_id = None

# ======================================================
# GUI Utilities & Interaction Control
# ======================================================
def center_window(window, width, height):
    window.update_idletasks(); sw, sh = window.winfo_screenwidth(), window.winfo_screenheight()
    x, y = (sw - width) // 2, (sh - height) // 2; window.geometry(f"{width}x{height}+{x}+{y}")

class CustomInputDialog(tk.Toplevel):
    # (No changes)
    def __init__(self, parent, title, prompt, width=400, height=150, font=("Segoe UI", 12)):
        super().__init__(parent); self.title(title); center_window(self, width, height)
        self.resizable(False, False); self.transient(parent); self.grab_set(); self.result = None
        self.configure(bg="white"); ttk.Label(self, text=prompt, font=font).pack(pady=(20, 10), padx=20)
        self.entry = ttk.Entry(self, font=font); self.entry.pack(pady=5, padx=20, fill="x")
        bf = ttk.Frame(self); bf.pack(pady=10)
        ttk.Button(bf, text="OK", command=self.ok).pack(side="left", padx=5)
        ttk.Button(bf, text="Cancel", command=self.cancel).pack(side="left", padx=5)
        self.bind("<Return>", lambda e: self.ok()); self.bind("<Escape>", lambda e: self.cancel())
        self.entry.focus(); self.wait_window(self)
    def ok(self): self.result = self.entry.get(); self.destroy()
    def cancel(self): self.destroy()

def custom_askstring(title, prompt):
    if 'main_window' in globals() and main_window.winfo_exists():
        dialog = CustomInputDialog(main_window, title, prompt); return dialog.result
    print(f"Warn: Main window N/A for dialog '{title}'."); return None

# --- Tooltip Functions ---
def show_tooltip(widget, text):
    global tooltip_window; hide_tooltip()
    x, y, _, _ = widget.bbox("insert")
    x += widget.winfo_rootx() + 20; y += widget.winfo_rooty() + 20
    tooltip_window = tk.Toplevel(widget); tooltip_window.wm_overrideredirect(True); tooltip_window.wm_geometry(f"+{x}+{y}")
    tk.Label(tooltip_window, text=text, justify='left', background="#ffffe0", relief='solid', borderwidth=1, font=("Segoe UI", 9)).pack(ipadx=1)
def hide_tooltip():
    global tooltip_window
    if tooltip_window: tooltip_window.destroy(); tooltip_window = None

def schedule_tooltip(widget, text): global tooltip_job_id; cancel_tooltip(widget); tooltip_job_id = widget.after(tooltip_delay, lambda: show_tooltip(widget, text))
def cancel_tooltip(widget): 
    global tooltip_job_id
    if 'tooltip_job_id' in globals() and tooltip_job_id: widget.after_cancel(tooltip_job_id); tooltip_job_id = None; hide_tooltip()

# --- Interaction Control ---
def disable_all_interactions():
    """Disables buttons, menu items, and treeview clicks."""
    global is_build_running
    is_build_running = True
    try:
        reload_btn.config(state="disabled")
        graph_btn.config(state="disabled")
        create_btn.config(state="disabled")
        # Disable menu items
        fmenu.entryconfig("Settings...", state="disabled")
        fmenu.entryconfig("Verify Config", state="disabled")
        # Unbind treeview click (safer than disabling the whole widget)
        sim_tree.unbind("<Button-1>")
        sim_tree.unbind("<Motion>") # Also disable tooltips during build
        sim_tree.config(cursor="watch") # Indicate busy state
        update_status("Build in progress... Please wait.")
    except (NameError, tk.TclError):
        print("Warning: Could not disable all interactions (GUI not fully ready?).")

def enable_all_interactions():
    """Re-enables interactions and updates button states."""
    global is_build_running
    is_build_running = False
    try:
        # Re-enable menu items
        fmenu.entryconfig("Settings...", state="normal")
        fmenu.entryconfig("Verify Config", state="normal")
        # Re-bind treeview click and motion
        sim_tree.bind("<Button-1>", handle_tree_click)
        sim_tree.bind("<Motion>", handle_tree_motion)
        sim_tree.config(cursor="") # Restore default cursor
        update_button_states() # Update buttons based on current state
    except (NameError, tk.TclError):
         print("Warning: Could not re-enable all interactions.")

# ======================================================
# Core Utilities & Error Handling
# ======================================================
def update_status(message):
    if 'main_window' in globals() and main_window.winfo_exists():
        main_window.after(0, lambda: status_label.config(text=str(message)))
    else: print(f"Status (GUI !ready): {message}")

def handle_unity_execution_error(e, operation_name="operation"):
    err_msg = (f"Error during Unity {operation_name}.\n\nDetails: {type(e).__name__}: {str(e)}\n\n"
               "Check Unity installation/version (6000.0.32f1) and path.\n"
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
        #update_status("Closing detected Unity instances..."); # Less verbose
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
        #update_status("Unity close check completed.")

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
                sims.append({"name": item, "creation": c_str,"last_opened": l_str}) # Removed ts for simplicity
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
    confirm = messagebox.askyesno("Confirm Delete", f"Permanently delete '{sim_name}' and data?", icon='warning')
    if not confirm: update_status("Deletion cancelled."); return
    update_status(f"Deleting '{sim_name}'..."); errs = False; global last_simulation_loaded
    if SIMULATION_LOADED_FILE and os.path.exists(SIMULATION_LOADED_FILE):
        try:
            loaded = read_last_loaded_simulation_name()
            if loaded == sim_name: os.remove(SIMULATION_LOADED_FILE); print("State file removed.")
            if last_simulation_loaded == sim_name: last_simulation_loaded = None
        except Exception as e: print(f"Warn: Could not clean state file: {e}")
    sim_p = os.path.join(SIMULATIONS_DIR, sim_name)
    if os.path.exists(sim_p):
        try: shutil.rmtree(sim_p, ignore_errors=True); time.sleep(0.1); shutil.rmtree(sim_p)
        except Exception as e: messagebox.showerror("Error", f"Could not delete sim folder:\n{sim_p}\n{e}"); errs = True
    try: data_p = Path.home()/"Documents"/"SimulationLoggerData"/sim_name;
    except: data_p = None
    if data_p and data_p.is_dir():
        try: shutil.rmtree(data_p)
        except Exception as e: messagebox.showerror("Error", f"Could not delete data folder:\n{data_p}\n{e}"); errs = True
    update_status(f"Deletion '{sim_name}' OK." + (" With errors." if errs else ""))
    populate_simulations()

# ======================================================
# Unity Batch Execution & Progress Monitoring
# ======================================================
# --- Función para formatear segundos (útil para ETA) ---
def format_time(seconds):
    if seconds is None or seconds < 0 or math.isinf(seconds) or math.isnan(seconds):
        return "--:--:--"
    if seconds == 0:
        return "0s"

    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    elif minutes > 0:
        return f"{minutes:02d}:{secs:02d}"
    else:
        return f"{secs}s"
    
def monitor_unity_progress(stop_event, operation_tag):
    if not SIMULATION_PROJECT_PATH or not os.path.exists(SIMULATION_PROJECT_PATH):
        print(f"\nAdvertencia: La ruta '{SIMULATION_PROJECT_PATH}' no existe al iniciar el monitoreo.")
        return

    TARGET_SIZE_MB = 3000.0
    BYTES_PER_MB = 1024 * 1024
    TARGET_SIZE_BYTES = TARGET_SIZE_MB * BYTES_PER_MB

    last_update_time = 0
    start_time = time.time()
    initial_size_bytes = 0
    eta_str = "Calculating..." # Valor inicial para ETA

    try:
        # Obtenemos tamaño inicial para cálculos de tasa
        initial_size_bytes = get_folder_size(SIMULATION_PROJECT_PATH)
    except Exception as e:
        print(f"\nError al obtener tamaño inicial para '{SIMULATION_PROJECT_PATH}': {e}")
        # Decide si continuar con tamaño 0 o retornar
        initial_size_bytes = 0 # Continuar asumiendo 0 si falla

    initial_size_mb = initial_size_bytes / BYTES_PER_MB
    print(f"[{operation_tag}] Iniciando monitoreo. Tamaño inicial: {initial_size_mb:.1f}MB. Objetivo: {TARGET_SIZE_MB:.0f}MB")

    while not stop_event.is_set():
        now = time.time()
        # Comprobar tamaño cada 1.5 segundos
        if now - last_update_time > 1.5:
            current_size_bytes = 0
            try:
                current_size_bytes = get_folder_size(SIMULATION_PROJECT_PATH)
                current_size_mb = current_size_bytes / BYTES_PER_MB
                elapsed_time = now - start_time
                size_increase_bytes = current_size_bytes - initial_size_bytes

                # --- Cálculo del ETA ---
                if elapsed_time > 5 and size_increase_bytes > 1024: # Esperar > 5s y crecimiento > 1KB para calcular
                    # Tasa de crecimiento en Bytes por segundo
                    rate_bytes_per_sec = size_increase_bytes / elapsed_time
                    remaining_bytes = TARGET_SIZE_BYTES - current_size_bytes

                    if rate_bytes_per_sec > 0 and remaining_bytes > 0:
                        eta_seconds = remaining_bytes / rate_bytes_per_sec
                        eta_str = f"ETA: {format_time(eta_seconds)}"
                    elif remaining_bytes <= 0:
                        eta_str = "ETA: Completed"
                        # Opcional: podrías querer detener el monitoreo aquí
                        # stop_event.set() # Descomenta si quieres que pare al llegar
                    else:
                        # No hay crecimiento positivo o ya pasó el objetivo (pero rate=0?)
                        eta_str = "ETA: --" # O "Stalled"
                elif elapsed_time <= 5:
                     eta_str = "ETA: Calculating..." # Aún muy pronto
                else: # Hubo tiempo pero sin crecimiento significativo
                     eta_str = "ETA: --"


                # --- Actualización del Estado ---
                progress_percent = (current_size_mb / TARGET_SIZE_MB) * 100 if TARGET_SIZE_MB > 0 else 0
                # Limitar el porcentaje a 100% para la visualización
                display_percent = min(progress_percent, 100.0)

                status_msg = (f"[{operation_tag}] {current_size_mb:.1f}/{TARGET_SIZE_MB:.0f}MB "
                              f"({display_percent:.1f}%) - {eta_str}      ") # Espacios para limpiar línea
                update_status(status_msg)

            except Exception as e:
                # Captura errores durante la obtención de tamaño o cálculo de ETA
                # Mantén el último ETA conocido o muestra un error
                error_msg = f"Error reading size: {e}"[:30] # Limitar longitud del error
                update_status(f"[{operation_tag}] {error_msg}... - {eta_str}      ")
                # 'pass' ya no está, el error se muestra pero el bucle continúa

            last_update_time = now # Actualizar el tiempo de la última comprobación válida o intento

        # Espera corta para no saturar la CPU y permitir que stop_event funcione
        # time.sleep(0.5) es suficiente si no usas threading.Event.wait()
        time.sleep(0.5)

    # Mensaje final al salir del bucle
    final_size_mb = get_folder_size(SIMULATION_PROJECT_PATH) / BYTES_PER_MB
    print(f"\n[{operation_tag}] Monitoreo finalizado. Tamaño final: {final_size_mb:.1f}MB")

def run_unity_batchmode(exec_method, op_name, log_file, timeout=600, extra_args=None):
    if not all([unity_path_ok, unity_version_ok, unity_projects_path_ok, SIMULATION_PROJECT_PATH]):
        update_status(f"Error: Cannot {op_name}."); return False, None
    log_path = os.path.join(SIMULATION_PROJECT_PATH, log_file)
    cmd = [UNITY_EXECUTABLE, "-batchmode", "-quit", "-projectPath", os.path.normpath(SIMULATION_PROJECT_PATH),
           "-executeMethod", exec_method, "-logFile", log_path]
    if extra_args: cmd.extend(extra_args)
    success = False; stop = threading.Event(); exe_path_after_build = None
    monitor = threading.Thread(target=monitor_unity_progress, args=(stop, op_name.capitalize()), daemon=True)
    try:
        update_status(f"[{op_name.capitalize()}] Starting..."); monitor.start()
        flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        process = subprocess.run(cmd, check=True, timeout=timeout, creationflags=flags, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        print(f"--- Unity Stdout Snippet ({op_name}) ---\n{process.stdout[-1000:]}\n---")
        if process.stderr: print(f"--- Unity Stderr Snippet ({op_name}) ---\n{process.stderr[-1000:]}\n---")
        update_status(f"[{op_name.capitalize()}] Unity process finished.")
        success = True
        if "BuildScript.PerformBuild" in exec_method:
            update_status(f"[{op_name.capitalize()}] Verifying output...")
            _, exe_path_after_build = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
            found = False
            for attempt in range(6):
                if exe_path_after_build and os.path.exists(exe_path_after_build):
                    found = True; print(f"DEBUG build_task: Executable CONFIRMED (attempt {attempt+1}): {exe_path_after_build}"); break
                print(f"DEBUG build_task: Executable check attempt {attempt+1} failed for {exe_path_after_build}"); time.sleep(0.5)
            if found: update_status(f"[{op_name.capitalize()}] Executable verified.")
            else:
                print(f"WARN build_task: Executable NOT FOUND post-build: {exe_path_after_build}"); success = False
                handle_unity_execution_error(FileNotFoundError(f"Build finished but output not found: {exe_path_after_build}"), op_name)
                update_status(f"[Error] {op_name.capitalize()} failed: Output missing.")
    except subprocess.CalledProcessError as e:
        handle_unity_execution_error(e, op_name); update_status(f"[Error] {op_name.capitalize()} failed (code {e.returncode}). Check {log_path}")
        print(f"--- Unity Output on Error ({op_name}) ---")
        if e.stdout: print(e.stdout[-1000:])
        if e.stderr: print("--- Unity Errors ---\n" + e.stderr[-1000:])
        print("--- End Unity Output ---")
    except subprocess.TimeoutExpired as e: handle_unity_execution_error(e, op_name); update_status(f"[Error] {op_name.capitalize()} timed out. Check {log_path}")
    except (FileNotFoundError, PermissionError) as e: handle_unity_execution_error(e, op_name); update_status(f"[Error] {op_name.capitalize()} failed (File/Permission).")
    except Exception as e: handle_unity_execution_error(e, f"{op_name} (unexpected)"); update_status(f"[Error] Unexpected error during {op_name}.")
    finally: stop.set(); monitor.join(timeout=1.0)
    return success, exe_path_after_build

def run_prefab_material_tool():
    success, _ = run_unity_batchmode("PrefabMaterialCreator.CreatePrefabsAndMaterials", "prefabs tool", "prefab_tool_log.txt", timeout=600)
    return success

def build_simulation_task(extra_args, callback):
    """Task run in thread to perform build and call callback."""
    disable_all_interactions() # Disable UI before starting
    success, final_exe_path = run_unity_batchmode("BuildScript.PerformBuild", "build", "build_log.txt", timeout=1800, extra_args=extra_args)
    # Re-enable UI via callback in main thread
    if callback: main_window.after(0, lambda s=success, p=final_exe_path: callback(s, p))
    main_window.after(10, enable_all_interactions) # Ensure UI is enabled after callback

def build_simulation_threaded(callback=None):
    """Starts the build process in a separate thread."""
    build_target, _ = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
    if not build_target: print("Error: Could not determine build target"); return
    extra = ["-buildTarget", build_target]
    # Disable UI immediately before starting thread
    # disable_all_interactions() # Moved inside the task to ensure it runs before Unity starts
    threading.Thread(target=lambda: build_simulation_task(extra, callback), daemon=True).start()

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
    else: messagebox.showerror("Error", f"Executable not found:\n{exe_path}\nPlease build first."); update_status("Error: Executable not found.")

def open_in_unity():
    if not all([unity_path_ok, unity_projects_path_ok, UNITY_EXECUTABLE, SIMULATION_PROJECT_PATH]): messagebox.showerror("Error", "Cannot open in Unity. Check config."); return
    if not os.path.isdir(SIMULATION_PROJECT_PATH): messagebox.showerror("Error", f"Project path does not exist: {SIMULATION_PROJECT_PATH}"); return
    try:
        update_status(f"Opening project in Unity..."); cmd = [UNITY_EXECUTABLE, "-projectPath", os.path.normpath(SIMULATION_PROJECT_PATH)]
        subprocess.Popen(cmd); update_status("Launching Unity Editor...")
    except Exception as e: handle_unity_execution_error(e, "open in Unity")

# ======================================================
# API Simulation Creation
# ======================================================
def create_simulation_thread(sim_name, sim_desc, original_states):
    # (No significant changes needed here, just status messages)
    update_status(f"Creating '{sim_name}'...");
    try: os.makedirs(SIMULATIONS_DIR, exist_ok=True)
    except Exception as e: messagebox.showerror("Critical Error", f"Could not create simulations dir: {e}"); update_status("Critical dir error."); main_window.after(0, update_button_states); return
    success = False
    try:
        api_script = Path("./Scripts/api_manager.py").resolve()
        if not api_script.exists(): raise FileNotFoundError(f"Script not found: {api_script}")
        cmd = [sys.executable, str(api_script), sim_name, sim_desc]
        flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300, creationflags=flags)
        update_status(f"'{sim_name}' created successfully."); main_window.after(0, lambda: messagebox.showinfo("Success", f"'{sim_name}' created."))
        main_window.after(0, populate_simulations); success = True
    except FileNotFoundError as e: messagebox.showerror("Critical Error", f"Required script not found:\n{e}"); update_status("Error: Missing script.")
    except subprocess.CalledProcessError as e:
        err_out = e.stderr if e.stderr else e.stdout; code=e.returncode; msg, det = "API ERROR", f"Code {code}. Output:\n{err_out}"
        if code == 7 or "CONTENT ERROR" in err_out: msg, det = "CONTENT ERROR", "Simulation must be E.Coli or S.Cerevisiae."
        elif "already exists" in err_out or "DUPLICATE" in err_out: msg, det = "DUPLICATE SIMULATION", f"'{sim_name}' already exists."
        elif "format" in err_out.lower() or "FORMATTING ERROR" in err_out: msg, det = "FORMATTING ERROR", "Invalid question format."
        main_window.after(0, lambda m=msg, d=det: messagebox.showerror(f"Creation Error ({m})", d)); update_status(f"Creation error: {msg}")
    except subprocess.TimeoutExpired: messagebox.showerror("Error", "Simulation creation timed out."); update_status("Error: Creation timeout.")
    except Exception as e: messagebox.showerror("Unexpected Error", f"CRITICAL ERROR:\n{e}"); update_status("Critical creation error."); print(f"Err create_sim_thread: {e}"); import traceback; traceback.print_exc()
    finally: main_window.after(0, update_button_states)

# ======================================================
# Verification Logic
# ======================================================
def perform_verification(show_results_box=False, on_startup=False):
    # (No changes from previous version regarding checks)
    global unity_path_ok, unity_version_ok, unity_projects_path_ok, apis_key_ok, apis_models_ok, initial_verification_complete
    global UNITY_EXECUTABLE, UNITY_PROJECTS_PATH, OPENAI_API_KEY, FINE_TUNED_MODEL_NAME, SECONDARY_FINE_TUNED_MODEL_NAME
    global SIMULATION_PROJECT_PATH, ASSETS_FOLDER, STREAMING_ASSETS_FOLDER, SIMULATION_LOADED_FILE, last_simulation_loaded
    if not on_startup: update_status("Verifying configuration...")
    load_dotenv('.env', override=True)
    UNITY_EXECUTABLE = os.environ.get("UNITY_EXECUTABLE"); UNITY_PROJECTS_PATH = os.environ.get("UNITY_PROJECTS_PATH")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY"); FINE_TUNED_MODEL_NAME = os.getenv("FINE_TUNED_MODEL_NAME")
    SECONDARY_FINE_TUNED_MODEL_NAME = os.getenv("2ND_FINE_TUNED_MODEL_NAME")
    results = []; unity_path_ok=unity_version_ok=unity_projects_path_ok=apis_key_ok=apis_models_ok=False
    req_ver = "6000.0.32f1"
    if not UNITY_EXECUTABLE: results.append("❌ Unity Exe: Missing in .env")
    elif not os.path.isfile(UNITY_EXECUTABLE): results.append(f"❌ Unity Exe: Invalid path")
    else:
        unity_path_ok = True; results.append(f"✅ Unity Exe: Path OK")
        if req_ver in UNITY_EXECUTABLE: unity_version_ok = True; results.append(f"✅ Unity Ver: OK ({req_ver})")
        else: results.append(f"❌ Unity Ver: Incorrect (Requires {req_ver})")
    if not UNITY_PROJECTS_PATH: results.append("❌ Projects Path: Missing in .env")
    elif not os.path.isdir(UNITY_PROJECTS_PATH): results.append(f"❌ Projects Path: Invalid")
    else:
        unity_projects_path_ok = True; results.append(f"✅ Projects Path: OK")
        SIMULATION_PROJECT_PATH = os.path.join(UNITY_PROJECTS_PATH, SIMULATION_PROJECT_NAME)
        ASSETS_FOLDER = os.path.join(SIMULATION_PROJECT_PATH, "Assets")
        STREAMING_ASSETS_FOLDER = os.path.join(ASSETS_FOLDER, "StreamingAssets")
        SIMULATION_LOADED_FILE = os.path.join(STREAMING_ASSETS_FOLDER, "simulation_loaded.txt")
        last_simulation_loaded = read_last_loaded_simulation_name()
    if not OPENAI_API_KEY: results.append("❌ API Key: Missing in .env")
    else:
        openai.api_key = OPENAI_API_KEY
        try:
            openai.Model.list(limit=1); apis_key_ok = True; results.append("✅ API Key: Connection OK.")
            models_ok_list = []
            for name, mid in [("Primary", FINE_TUNED_MODEL_NAME), ("Secondary", SECONDARY_FINE_TUNED_MODEL_NAME)]:
                if not mid: results.append(f"⚠️ {name} Model: Not set"); continue
                try: openai.Model.retrieve(mid); results.append(f"✅ {name} Model: OK"); models_ok_list.append(name=="Primary")
                except openai_error.InvalidRequestError: results.append(f"❌ {name} Model: Not found"); models_ok_list.append(False)
                except Exception as me: results.append(f"❌ {name} Model: Error ({me})"); models_ok_list.append(False)
            apis_models_ok = models_ok_list and models_ok_list[0]
            if not apis_models_ok and len(models_ok_list)>0 : results.append("❌ Primary Model: Invalid or not found.")
        except openai_error.AuthenticationError: results.append("❌ API Key: Invalid.")
        except Exception as ae: results.append(f"❌ API Error: {ae}")
    if not initial_verification_complete: initial_verification_complete = True
    status_parts = ["Unity OK" if unity_path_ok and unity_version_ok and unity_projects_path_ok else "Unity ERR",
                    "API OK" if apis_key_ok and apis_models_ok else "API ERR"]
    final_status = " | ".join(status_parts)
    if 'main_window' in globals() and main_window.winfo_exists():
        main_window.after(0, lambda: update_status(final_status))
        main_window.after(50, update_button_states)
        main_window.after(100, populate_simulations)
        if on_startup:
            err_msg = ""
            if not unity_path_ok or not unity_projects_path_ok: err_msg += "- Invalid Unity/Projects path.\n"
            elif not unity_version_ok: err_msg += f"- Incorrect Unity version (requires {req_ver}).\n"
            if not unity_path_ok or not unity_version_ok or not unity_projects_path_ok: err_msg += "  (Loading disabled)\n"
            if not apis_key_ok or not apis_models_ok: err_msg += "- Invalid API Key/Models.\n  (Creation disabled)\n"
            if err_msg: main_window.after(200, lambda m=err_msg: messagebox.showwarning("Initial Config Issues", "Problems found:\n" + m + "\nUse File -> Settings to fix."))
    else: print(f"Verification Status: {final_status}")
    if show_results_box:
        res_text = "Verification Results:\n\n" + "\n".join(results)
        all_ok = unity_path_ok and unity_version_ok and unity_projects_path_ok and apis_key_ok and apis_models_ok
        if 'main_window' in globals() and main_window.winfo_exists():
             main_window.after(0, lambda: messagebox.showinfo("Verification", res_text) if all_ok else messagebox.showwarning("Verification", res_text))

# ======================================================
# Configuration Window (API Note Removed)
# ======================================================
def open_config_window():
    cfg_win = tk.Toplevel(main_window); cfg_win.title("Settings"); center_window(cfg_win, 650, 230) # Adjusted height
    cfg_win.resizable(False, False); cfg_win.transient(main_window); cfg_win.grab_set()
    frame = ttk.Frame(cfg_win, padding=20); frame.pack(fill="both", expand=True)
    paths_f = ttk.LabelFrame(frame, text="Paths", padding=10); paths_f.pack(fill="x", pady=5)
    # api_note_f removed
    entries = {}
    def create_row(p, lbl, env, key, is_path=True, is_file=True):
        f = ttk.Frame(p); f.pack(fill="x", pady=4)
        ttk.Label(f, text=lbl, width=20).pack(side="left", padx=(0, 5))
        v = tk.StringVar(value=os.environ.get(env, "")); entries[key] = v
        e = ttk.Entry(f, textvariable=v); e.pack(side="left", expand=True, fill="x", padx=5)
        if is_path:
            def browse():
                init = os.path.dirname(v.get()) if v.get() and os.path.exists(os.path.dirname(v.get())) else "/"
                p = filedialog.askopenfilename(title=f"Select {lbl}", initialdir=init) if is_file else filedialog.askdirectory(title=f"Select {lbl}", initialdir=init if os.path.isdir(init) else "/")
                if p: v.set(p)
            ttk.Button(f, text="...", width=3, command=browse).pack(side="left")

    create_row(paths_f, "Unity Executable:", "UNITY_EXECUTABLE", "unity_exe");
    create_row(paths_f, "Projects Folder:", "UNITY_PROJECTS_PATH", "projects_path", is_file=False)
    # API fields are not shown
    btn_f = ttk.Frame(frame); btn_f.pack(pady=15, side="bottom", fill="x")
    def save():
        data = {k: v.get().strip() for k, v in entries.items()}
        errs = [f"- {k.replace('_',' ').capitalize()} empty." for k, v in data.items() if not v]
        if errs: messagebox.showerror("Input Error", "Required fields:\n"+"\n".join(errs), parent=cfg_win); return
        current_api_key = os.getenv("OPENAI_API_KEY", "") # Read existing API vars
        current_model1 = os.getenv("FINE_TUNED_MODEL_NAME", "")
        current_model2 = os.getenv("2ND_FINE_TUNED_MODEL_NAME", "")
        try:
            with open(".env", "w", encoding='utf-8') as f:
                f.write(f"UNITY_EXECUTABLE={data['unity_exe']}\n")
                f.write(f"UNITY_PROJECTS_PATH={data['projects_path']}\n")
                f.write(f"OPENAI_API_KEY={current_api_key}\n") # Preserve API vars
                f.write(f"FINE_TUNED_MODEL_NAME={current_model1}\n")
                f.write(f"2ND_FINE_TUNED_MODEL_NAME={current_model2}\n")
            messagebox.showinfo("Success", "Settings saved.\nRe-verifying...", parent=cfg_win); cfg_win.destroy(); main_window.after(100, lambda: perform_verification(show_results_box=True))
        except Exception as e: messagebox.showerror("Save Error", f"Could not write .env:\n{e}", parent=cfg_win)
    ttk.Button(btn_f, text="Save and Verify", command=save).pack(side="left", padx=20, expand=True); ttk.Button(btn_f, text="Cancel", command=cfg_win.destroy).pack(side="left", padx=20, expand=True)


# ======================================================
# GUI Definitions (Callbacks first)
# ======================================================
def populate_simulations():
    if not initial_verification_complete: return
    for item in sim_tree.get_children():
        try: sim_tree.delete(item)
        except tk.TclError: pass # Ignorar si ya no existe

    update_status("Searching for simulations...")
    simulations = get_simulations()
    global last_simulation_loaded
    last_simulation_loaded = read_last_loaded_simulation_name()

    if simulations:
        for i, sim in enumerate(simulations):
            is_loaded = (sim["name"] == last_simulation_loaded)
            row_tag = "evenrow" if i % 2 == 0 else "oddrow"
            # APLICAR LOS TAGS CORRECTOS
            item_tags = [row_tag] # Tag base par/impar
            if is_loaded:
                item_tags.append("loaded") # Añadir tag 'loaded' si corresponde

            try:
                sim_tree.insert("", "end", iid=sim["name"],
                                values=(sim["name"], sim["creation"], sim["last_opened"],
                                        loaded_indicator_text if is_loaded else "",
                                        play_icon_text, delete_icon_text),
                                tags=tuple(item_tags)) # Usar los tags calculados
            except tk.TclError as e:
                print(f"Error inserting {sim['name']}: {e}")


        # Ordenar después de poblar
        # Encuentra la columna por la que ordenar inicialmente (ej. 'nombre')
        default_sort_col = "nombre"
        if default_sort_col in sort_order:
            sort_column(sim_tree, default_sort_col, sort_order[default_sort_col])

        update_status(f"List updated ({len(simulations)} found).")
    else:
        update_status("No simulations found.")
    update_button_states()
    
def update_button_states():
    if 'main_window' not in globals() or not main_window.winfo_exists() or is_build_running : return # Check build flag
    if not initial_verification_complete: state = "disabled"; reload_state = "normal"
    else:
        reload_state = "normal"
        create_state = "normal" if apis_key_ok and apis_models_ok else "disabled"
        graph_state = "normal" if sim_tree.selection() else "disabled"
    try:
        reload_btn.config(state=reload_state)
        graph_btn.config(state=graph_state if initial_verification_complete else "disabled")
        create_btn.config(state=create_state if initial_verification_complete else "disabled")
    except NameError: pass
    except tk.TclError: pass

def on_load_simulation_request(simulation_name):
    global is_build_running
    if is_build_running: return # Prevent action if build is running
    print(f"Load request for: {simulation_name}")
    if not all([unity_path_ok, unity_version_ok, unity_projects_path_ok]):
        messagebox.showerror("Unity Error", "Cannot load: Invalid Unity config."); return
    if simulation_name == last_simulation_loaded:
        update_status(f"'{simulation_name}' is already loaded. Showing options..."); update_last_opened(simulation_name)
        _, current_exe_path = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
        main_window.after(0, lambda s=simulation_name, p=current_exe_path: show_options_window(s, p))
        return
    # Disable UI elements *before* starting the thread for loading/building
    # disable_all_interactions() # Moved to build_simulation_task start
    reload_btn.config(state="disabled"); graph_btn.config(state="disabled"); create_btn.config(state="disabled")
    sim_tree.unbind("<Button-1>") # Disable tree clicks specifically during load as well
    sim_tree.config(selectmode="none", cursor="watch")
    threading.Thread(target=load_simulation_logic, args=(simulation_name,), daemon=True).start()

def load_simulation_logic(simulation_name):
    """Performs loading and building in a thread."""
    update_status(f"Loading '{simulation_name}'...");
    update_status("Closing Unity..."); ensure_unity_closed()
    update_status(f"Loading files '{simulation_name}'..."); load_success = load_simulation(simulation_name)
    if load_success:
        update_status("Files OK. Post-load..."); prefab_success = run_prefab_material_tool()
        if prefab_success:
            update_status("Prefabs OK. Build...");
            # Build is started here, it will disable interactions internally
            build_simulation_threaded(callback=lambda success, path: build_callback(success, simulation_name, path))
        else:
            update_status(f"Prefabs fail '{simulation_name}'. Build cancelled."); messagebox.showerror("Post-Load Error", "Prefabs tool failed. Build cancelled.")
            # Re-enable UI if build doesn't start
            main_window.after(0, enable_all_interactions)
    else:
        update_status(f"Error loading '{simulation_name}'.");
        # Re-enable UI on load failure
        main_window.after(0, enable_all_interactions)

def build_callback(success, simulation_name, executable_path):
    """Called after build finishes (in main thread)."""
    if success and executable_path:
        update_status(f"Build '{simulation_name}' OK."); show_options_window(simulation_name, executable_path)
    else: update_status(f"Build '{simulation_name}' failed" + (" (Executable missing)." if success else "."))
    # enable_all_interactions() is called in the build_simulation_task finally block

def on_delete_simulation_request(simulation_name):
    global is_build_running
    if is_build_running: return # Prevent action
    print(f"Delete request for: {simulation_name}")
    delete_simulation(simulation_name)

def on_show_graphs_thread():
    global is_build_running
    if is_build_running: return # Prevent action
    selected = sim_tree.selection()
    if not selected: messagebox.showwarning("Selection", "Select simulation to view graphs."); return
    sim_name = sim_tree.item(selected[0], "values")[0] # Name is back to index 0
    update_status(f"Generating graphs for '{sim_name}'...")
    reload_btn.config(state="disabled"); graph_btn.config(state="disabled"); create_btn.config(state="disabled")
    threading.Thread(target=show_graphs_logic, args=(sim_name,), daemon=True).start()

def show_graphs_logic(sim_name):
    try:
        csv_p = Path.home()/"Documents"/"SimulationLoggerData"/sim_name/"SimulationStats.csv"
        if not csv_p.exists(): messagebox.showerror("Error", f"Data file not found: {csv_p}"); update_status("Error: CSV not found."); return
        spec_s = Path(SIMULATIONS_DIR)/sim_name/"Assets"/"Scripts"/"SimulationData"/"SimulationGraphics.py"
        gen_s = Path("./Scripts/SimulationGraphics.py").resolve()
        script = str(spec_s) if spec_s.exists() else (str(gen_s) if gen_s.exists() else None)
        if not script: messagebox.showerror("Error", "Graph script not found."); update_status("Error: Graph script missing."); return
        update_status(f"Running script: {os.path.basename(script)}"); subprocess.Popen([sys.executable, script, sim_name])
        update_status(f"Graphs for '{sim_name}' generating..."); open_graphs_folder(sim_name)
    except Exception as e: messagebox.showerror("Graph Error", f"Error:\n{e}"); update_status("Graph error.")
    finally: main_window.after(0, update_button_states)

def on_create_simulation():
    global is_build_running
    if is_build_running: return # Prevent action
    if not apis_key_ok or not apis_models_ok: messagebox.showerror("API Error", "Cannot create: Invalid API config."); return
    sim_name = custom_askstring("Create Simulation", "Simulation Name:")
    if not sim_name: update_status("Creation cancelled."); return
    sim_name = sim_name.strip(); invalid_chars = r'\/:*?"<>|'
    if not sim_name or any(c in sim_name for c in invalid_chars): messagebox.showerror("Error", "Invalid name."); update_status("Invalid name."); return
    if os.path.exists(os.path.join(SIMULATIONS_DIR, sim_name)): messagebox.showerror("Error", f"'{sim_name}' already exists."); update_status("Duplicate."); return
    sim_desc = custom_askstring("Simulation Description", "Describe the simulation:")
    if not sim_desc: update_status("Creation cancelled."); return
    states = { 'reload': reload_btn['state'], 'graph': graph_btn['state'], 'create': create_btn['state'] }
    reload_btn.config(state="disabled"); graph_btn.config(state="disabled"); create_btn.config(state="disabled")
    threading.Thread(target=create_simulation_thread, args=(sim_name, sim_desc, states), daemon=True).start()

def show_options_window(simulation_name, executable_path):
    # (No changes needed from previous version)
    opt_win = tk.Toplevel(main_window); opt_win.title(f"Options for '{simulation_name}'")
    center_window(opt_win, 350, 180); opt_win.resizable(False, False); opt_win.transient(main_window); opt_win.grab_set()
    frame = ttk.Frame(opt_win, padding=20); frame.pack(expand=True, fill="both")
    ttk.Label(frame, text=f"Simulation '{simulation_name}' is ready.", font=("Segoe UI", 12)).pack(pady=(0,15))
    close = opt_win.destroy
    exec_state = "normal" if (executable_path and os.path.exists(executable_path)) else "disabled"
    print(f"DEBUG show_options_window: Path='{executable_path}', Exists={os.path.exists(executable_path) if executable_path else False}, State={exec_state}")
    ttk.Button(frame, text="Run Simulation", style="Success.TButton", command=lambda: [open_simulation_executable(), close()], state=exec_state).pack(pady=8, fill="x", ipady=5)
    ttk.Button(frame, text="Open in Unity", style="Info.TButton", command=lambda: [open_in_unity(), close()]).pack(pady=8, fill="x", ipady=5)
    update_status(f"Options available for '{simulation_name}'."); opt_win.wait_window()

def handle_tree_click(event):
    # (No changes needed from previous version)
    global is_build_running
    if is_build_running: return # Prevent action
    region = sim_tree.identify_region(event.x, event.y)
    if region != "cell": cancel_tooltip(sim_tree); return
    item_id = sim_tree.identify_row(event.y); col_id = sim_tree.identify_column(event.x)
    if not item_id or not col_id: cancel_tooltip(sim_tree); return
    try:
        col_index = int(col_id.replace('#','')) - 1
        # Updated column order
        click_columns = ("nombre", "creacion", "ultima", "col_loaded", "col_load", "col_delete")
        if col_index < 0 or col_index >= len(click_columns): cancel_tooltip(sim_tree); return
        col_name = click_columns[col_index]
        simulation_name = sim_tree.item(item_id, "values")[0] # Name is now at index 0
        sim_tree.selection_set(item_id); sim_tree.focus(item_id)
        hide_tooltip()
        if col_name == "col_load": on_load_simulation_request(simulation_name)
        elif col_name == "col_delete": on_delete_simulation_request(simulation_name)
    except Exception as e: print(f"Error handle_tree_click: {e}"); cancel_tooltip(sim_tree)

def handle_tree_motion(event):
    # (Tooltip logic adapted for new column order)
    global is_build_running
    if is_build_running: return # Prevent action
    global tooltip_job_id
    region = sim_tree.identify_region(event.x, event.y)
    if region != "cell": cancel_tooltip(sim_tree); return
    col_id = sim_tree.identify_column(event.x); item_id = sim_tree.identify_row(event.y)
    if not col_id or not item_id: cancel_tooltip(sim_tree); return
    try:
        col_index = int(col_id.replace('#','')) - 1
        motion_columns = ("nombre", "creacion", "ultima", "col_loaded", "col_load", "col_delete") # New order
        if col_index < 0 or col_index >= len(motion_columns): cancel_tooltip(sim_tree); return
        col_name = motion_columns[col_index]
        tooltip_text = None
        # Check new indices for load/delete columns
        if col_name == "col_load": tooltip_text = "Load/Run Simulation"
        elif col_name == "col_delete": tooltip_text = "Delete Simulation"
        if tooltip_text: schedule_tooltip(sim_tree, tooltip_text)
        else: cancel_tooltip(sim_tree)
    except Exception: cancel_tooltip(sim_tree)

def handle_tree_leave(event):
    # (No changes needed from previous version)
    cancel_tooltip(sim_tree)

# ======================================================
# GUI Setup
# ======================================================
main_window = tk.Tk()
try: main_window.iconbitmap("icono.ico")
except tk.TclError: print("Warn: icono.ico not found.")
main_window.title("Unity Simulation Manager")
center_window(main_window, 800, 550)
main_window.resizable(True, True)

# --- Styles ---
style = ttk.Style(main_window)
style.theme_use("clam")

# Configurar estilos para Widgets Generales (Botones, Labels, etc.)
style.configure("TButton", font=("Segoe UI", 10), padding=5)
style.configure("Treeview", font=("Segoe UI", 10), rowheight=25) # Estilo base del Treeview
style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold")) # Estilo cabeceras
style.configure("Info.TButton", foreground="white", background="#5B6EE1")
style.map("Info.TButton", background=[("active", "#4759c7"), ("disabled", "#B0B9E8")])
style.configure("Success.TButton", foreground="white", background="#4CAF50")
style.map("Success.TButton", background=[("active", "#43A047"), ("disabled", "#A5D6A7")])
style.configure("Danger.TButton", foreground="white", background="#F44336")
style.map("Danger.TButton", background=[("active", "#E53935"), ("disabled", "#EF9A9A")])
style.configure("Graph.TButton", foreground="white", background="#009688")
style.map("Graph.TButton", background=[("active", "#00796B"), ("disabled", "#80CBC4")])
style.configure("Reload.TButton", foreground="white", background="#9C27B0")
style.map("Reload.TButton", background=[("active", "#7B1FA2"), ("disabled", "#CE93D8")])
style.configure("TLabel", font=("Segoe UI", 10))
style.configure("Status.TLabel", font=("Segoe UI", 9))

# --- Menu ---
menubar = tk.Menu(main_window)
fmenu = tk.Menu(menubar,tearoff=0); fmenu.add_command(label="Settings...", command=open_config_window); 
fmenu.add_command(label="Verify Config", command=lambda: perform_verification(show_results_box=True)); 
fmenu.add_separator(); fmenu.add_command(label="Exit", command=main_window.quit); 
menubar.add_cascade(label="File", menu=fmenu)
hmenu = tk.Menu(menubar,tearoff=0); hmenu.add_command(label="Download Unity (6000.0.32f1)", command=lambda: webbrowser.open("unityhub://6000.0.32f1/b2e806cf271c")); 
hmenu.add_separator(); hmenu.add_command(label="About...", command=lambda: messagebox.showinfo("About", "Unity Simulation Manager\nVersion 1.6")); 
menubar.add_cascade(label="Help", menu=hmenu)
main_window.config(menu=menubar)


# --- Header ---
hdr_f = ttk.Frame(main_window, padding=(10, 10)); hdr_f.pack(fill="x")
hdr_l = ttk.Label(hdr_f, text="Unity Simulation Manager", font=("Times New Roman", 20, "bold"), anchor="center"); hdr_l.pack(fill="x")

# --- Main Frame ---
main_f = ttk.Frame(main_window, padding=10); main_f.pack(expand=True, fill="both")
main_f.columnconfigure(0, weight=1); main_f.rowconfigure(0, weight=1)

# --- Treeview Setup ---
tree_f = ttk.Frame(main_f); tree_f.grid(row=0, column=0, sticky="nsew", padx=5, pady=(0,5))
tree_f.columnconfigure(0, weight=1); tree_f.rowconfigure(0, weight=1)
columns = ("nombre", "creacion", "ultima", "col_loaded", "col_load", "col_delete")
sim_tree = ttk.Treeview(tree_f, columns=columns, show="headings", selectmode="browse")

# Column setup (Usar texto en cabeceras de iconos si se desea)
sim_tree.heading("nombre", text="Simulation Name"); sim_tree.column("nombre", width=250, anchor="w", stretch=tk.YES)
sim_tree.heading("creacion", text="Created"); sim_tree.column("creacion", width=110, anchor="center", stretch=tk.NO)
sim_tree.heading("ultima", text="Last Used"); sim_tree.column("ultima", width=110, anchor="center", stretch=tk.NO)
sim_tree.heading("col_loaded", text="✓", anchor="center"); sim_tree.column("col_loaded", width=25, stretch=tk.NO, anchor="center")
sim_tree.heading("col_load", text=" Load", anchor="center"); sim_tree.column("col_load", width=40, stretch=tk.NO, anchor="center")
sim_tree.heading("col_delete", text="Del", anchor="center"); sim_tree.column("col_delete", width=40, stretch=tk.NO, anchor="center")

# Sorting config (sin cambios necesarios aquí)
sort_order = {col: False for col in columns if col not in ["col_load", "col_delete", "col_loaded"]}
def sort_column(tree, col, reverse):
    # ... (tu función sort_column completa) ...
    if col in ["col_load", "col_delete", "col_loaded"]: return
    global sort_order; data = [(tree.set(item, col), item) for item in tree.get_children('')]
    def conv_date(v): return 0 if v in ("???", "Never") else time.mktime(time.strptime(v, "%y-%m-%d %H:%M")) if v else 0
    try: data.sort(key=lambda t: conv_date(t[0]) if col in ("creacion", "ultima") else t[0].lower(), reverse=reverse)
    except: data.sort(key=lambda t: t[0].lower(), reverse=reverse) # Fallback sort
    for i, (_, item) in enumerate(data): tree.move(item, '', i)
    sort_order[col] = reverse
    # Actualizar el comando para la cabecera para invertir la próxima vez
    tree.heading(col, command=lambda c=col: sort_column(tree, c, not reverse)) # <--- Asegúrate que el comando se actualiza

for col in columns:
    if col not in ["col_load", "col_delete", "col_loaded"]:
        current_heading_text = sim_tree.heading(col)['text'] # Leer texto actual
        sim_tree.heading(col, text=current_heading_text, command=lambda c=col: sort_column(sim_tree, c, False)) # Comando inicial para ordenar Asc

# Tag configuration (applied in populate_simulations)
sim_tree.tag_configure('oddrow', background='#F0F0F0')
sim_tree.tag_configure('evenrow', background='#FFFFFF')
sim_tree.tag_configure('loaded', background='#E0F2E0', font=('Segoe UI', 10))

sim_tree.grid(row=0, column=0, sticky="nsew")
scroll = ttk.Scrollbar(tree_f, orient="vertical", command=sim_tree.yview); scroll.grid(row=0, column=1, sticky="ns"); sim_tree.config(yscrollcommand=scroll.set)

# Event Bindings
sim_tree.bind('<<TreeviewSelect>>', lambda e: update_button_states())
sim_tree.bind("<Button-1>", handle_tree_click)
sim_tree.bind("<Motion>", handle_tree_motion)
sim_tree.bind("<Leave>", handle_tree_leave)

# --- Button Frame (Bottom) ---
btn_f_bottom = ttk.Frame(main_f); btn_f_bottom.grid(row=1, column=0, pady=(10,0), sticky="ew") # Changed row index
num_bottom_buttons = 3; btn_f_bottom.columnconfigure(0, weight=1); btn_f_bottom.columnconfigure(num_bottom_buttons + 1, weight=1)
reload_btn = ttk.Button(btn_f_bottom, text="Reload List", style="Reload.TButton", command=populate_simulations); reload_btn.grid(row=0, column=1, padx=10, pady=5)
graph_btn = ttk.Button(btn_f_bottom, text="Show Graphs", style="Graph.TButton", command=on_show_graphs_thread); graph_btn.grid(row=0, column=2, padx=10, pady=5)
create_btn = ttk.Button(btn_f_bottom, text="Create Simulation", style="Success.TButton", command=on_create_simulation); create_btn.grid(row=0, column=3, padx=10, pady=5)

# --- Status Bar ---
status_f = ttk.Frame(main_window, relief="sunken", borderwidth=1); status_f.pack(fill="x", side="bottom", padx=1, pady=1)
status_label = ttk.Label(status_f, text="Initializing...", anchor="w", style="Status.TLabel", padding=(5,2)); status_label.pack(fill="x")

# ======================================================
# App Initialization
# ====================================================== 
if __name__ == "__main__":
    update_button_states() # Actualiza estado inicial botones
    update_status("Performing initial verification...")
    # Iniciar verificación en hilo (que eventualmente llamará a populate_simulations)
    threading.Thread(target=perform_verification, args=(False, True), daemon=True).start()

    def on_closing():
        # ... (tu código on_closing) ...
        if is_build_running: # Prevent closing during build
            messagebox.showwarning("Build in Progress", "Please wait for the current build to finish before closing.")
            return
        if messagebox.askokcancel("Exit", "Exit Simulation Manager?", icon='question'):
            update_status("Closing..."); ensure_unity_closed(); main_window.destroy()

    main_window.protocol("WM_DELETE_WINDOW", on_closing)
    main_window.mainloop()