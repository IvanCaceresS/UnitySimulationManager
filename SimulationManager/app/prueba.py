# -*- coding: utf-8 -*-
import sys
import os
import shutil
import subprocess
import platform
import threading
import time
# GUI Libraries
import customtkinter as ctk
from tkinter import messagebox, filedialog # Keep standard dialogs
from tkinter import ttk # Keep ttk specifically for Treeview & its Scrollbar
import tkinter as tk
# Other Libraries
from dotenv import load_dotenv
from pathlib import Path
import psutil
import openai
import math
try:
    from PIL import Image # No longer needs ImageTk directly with CTkImage
except ImportError:
    # Use CTk messagebox before main window exists
    root_err = ctk.CTk()
    root_err.withdraw() # Hide the empty root window
    messagebox.showerror("Error de Dependencia",
                         "La biblioteca Pillow no está instalada.\n"
                         "Por favor, instálala ejecutando: pip install Pillow")
    root_err.destroy()
    sys.exit(1)

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
# CustomTkinter Appearance Settings
# ======================================================
ctk.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue") # Themes: "blue" (default), "green", "dark-blue"

# ======================================================
# Global State & Config Variables (Unchanged)
# ======================================================
unity_path_ok = False
unity_version_ok = False
unity_projects_path_ok = False
apis_key_ok = False
apis_models_ok = False
initial_verification_complete = False
is_build_running = False

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

# Icons (text fallback) - Keep as they are used in Treeview values
play_icon_text = "▶"
delete_icon_text = "🗑️"
loaded_indicator_text = "✓"

# Tooltip handling (Keep using tk.Toplevel for simplicity)
tooltip_window = None
tooltip_delay = 700
tooltip_job_id = None

# Logo Handling
logo_image_ref = None # Keep reference for CTkImage
LOGO_PATH = "img/logo.png"
LOGO_WIDTH = 140 # Adjusted width

# Define some colors semantically (optional, CTk handles themes well)
COLOR_SUCCESS = "#28A745"
COLOR_DANGER = "#DC3545"
COLOR_INFO = "#17A2B8" # Teal/Info blue
COLOR_WARNING = "#FFC107" # Yellowish warning
COLOR_DISABLED = "#ADB5BD" # Grey for disabled state

# ======================================================
# GUI Utilities & Interaction Control
# ======================================================
def center_window(window, width, height):
    # Works the same for CTk windows
    window.update_idletasks()
    sw, sh = window.winfo_screenwidth(), window.winfo_screenheight()
    x, y = (sw - width) // 2, (sh - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")

# --- Custom Input Dialog using CustomTkinter ---
class CustomInputDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, prompt, width=400, height=180): # Adjusted height
        super().__init__(parent)
        self.title(title)
        center_window(self, width, height)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)

        prompt_label = ctk.CTkLabel(main_frame, text=prompt, font=font_base)
        prompt_label.grid(row=0, column=0, padx=0, pady=(0, 10), sticky="w")

        self.entry = ctk.CTkEntry(main_frame, font=font_base, width=300) # Specify width
        self.entry.grid(row=1, column=0, padx=0, pady=(0, 15), sticky="ew")
        self.entry.focus()

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="e")

        ok_button = ctk.CTkButton(button_frame, text="OK", command=self.ok, width=80, font=font_base)
        ok_button.grid(row=0, column=0, padx=(0, 10))

        cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=self.cancel, width=80, font=font_base,
                                     fg_color="grey50", hover_color="grey30") # Secondary color
        cancel_button.grid(row=0, column=1, padx=0)

        self.bind("<Return>", lambda e: self.ok())
        self.bind("<Escape>", lambda e: self.cancel())

        self.wait_window() # Wait for the dialog to close

    def ok(self, event=None): # Add event=None for binding
        self.result = self.entry.get()
        self.destroy()

    def cancel(self, event=None): # Add event=None for binding
        self.destroy()

def custom_askstring(title, prompt):
    if 'app' in globals() and app.winfo_exists(): # Check for CTk app instance
        dialog = CustomInputDialog(app, title, prompt)
        return dialog.result
    print(f"Warn: Main window not available for dialog '{title}'.")
    return None

# --- Tooltip Functions ---
# Keep using tk.Toplevel as CTk doesn't have a direct tooltip replacement yet
# Styling is basic, might not perfectly match CTk theme.
def show_tooltip(widget, text):
    global tooltip_window; hide_tooltip()
    try:
        x, y, _, _ = widget.bbox("insert") # Might fail for some CTk widgets
    except: # Fallback position
         x = y = 0
    # Adjust position relative to widget's root coordinates
    x += widget.winfo_rootx() + 25
    y += widget.winfo_rooty() + 20

    tooltip_window = tk.Toplevel(widget) # Standard Toplevel
    tooltip_window.wm_overrideredirect(True) # No window decorations
    tooltip_window.wm_geometry(f"+{x}+{y}")

    # Basic label styling for the tooltip
    label = tk.Label(tooltip_window, text=text, justify='left',
                     background="#FFFFE0", relief='solid', borderwidth=1,
                     font=(FONT_FAMILY, FONT_SIZE_SMALL - 1)) # Slightly smaller font
    label.pack(ipadx=2)

def hide_tooltip():
    global tooltip_window
    if tooltip_window:
        tooltip_window.destroy()
        tooltip_window = None

def schedule_tooltip(widget, text):
    global tooltip_job_id; cancel_tooltip(widget)
    tooltip_job_id = widget.after(tooltip_delay, lambda: show_tooltip(widget, text))

def cancel_tooltip(widget):
    global tooltip_job_id
    if 'tooltip_job_id' in globals() and tooltip_job_id:
        try:
            widget.after_cancel(tooltip_job_id)
        except: pass # Ignore if widget destroyed
        tooltip_job_id = None
        hide_tooltip()


# --- Interaction Control ---
def set_widget_state(widget, state):
    """Helper to set state for CTk or ttk widgets."""
    if hasattr(widget, 'configure'):
        try:
            widget.configure(state=state)
        except Exception as e:
             # Treeview might raise TclError if column is clicked, handle gracefully
             if isinstance(widget, ttk.Treeview) and state == "disabled":
                 # For Treeview, unbinding clicks is safer than disabling
                 widget.unbind("<Button-1>")
                 widget.unbind("<Motion>")
                 widget.configure(cursor="watch")
             elif isinstance(widget, ttk.Treeview) and state == "normal":
                 widget.bind("<Button-1>", handle_tree_click)
                 widget.bind("<Motion>", handle_tree_motion)
                 widget.configure(cursor="")
             else:
                 print(f"Warning: Could not set state '{state}' for {widget}: {e}")


def disable_all_interactions():
    global is_build_running
    is_build_running = True
    try:
        # Disable bottom buttons (now CTkButton)
        if 'reload_btn' in globals(): set_widget_state(reload_btn, "disabled")
        if 'graph_btn' in globals(): set_widget_state(graph_btn, "disabled")
        if 'create_btn' in globals(): set_widget_state(create_btn, "disabled")

        # Disable sidebar buttons (now CTkButton)
        if 'sidebar_frame' in globals():
            for widget in sidebar_frame.winfo_children():
                if isinstance(widget, ctk.CTkButton):
                    set_widget_state(widget, "disabled")

        # Disable Treeview (keep using ttk specific handling)
        if 'sim_tree' in globals():
             sim_tree.unbind("<Button-1>")
             sim_tree.unbind("<Motion>")
             sim_tree.configure(cursor="watch")

        if 'status_label' in globals(): update_status("Build in progress... Please wait.")

    except Exception as e: # Broader exception catch during GUI manipulation
        print(f"Warning: Error during disable_all_interactions: {e}")

def enable_all_interactions():
    global is_build_running
    is_build_running = False
    try:
         # Enable sidebar buttons
        if 'sidebar_frame' in globals():
            for widget in sidebar_frame.winfo_children():
                 if isinstance(widget, ctk.CTkButton):
                      set_widget_state(widget, "normal")

        # Re-bind treeview events
        if 'sim_tree' in globals():
             sim_tree.bind("<Button-1>", handle_tree_click)
             sim_tree.bind("<Motion>", handle_tree_motion)
             sim_tree.configure(cursor="")

        update_button_states() # Update states based on current context

    except Exception as e: # Broader exception catch
         print(f"Warning: Error during enable_all_interactions: {e}")


# ======================================================
# Core Utilities & Error Handling (Unchanged Functionally)
# ======================================================
def update_status(message):
    # Assumes status_label is a CTkLabel now
    if 'status_label' in globals() and status_label.winfo_exists():
        # Use CTk configure method
        status_label.configure(text=str(message))
    else: print(f"Status (GUI !ready): {message}")

def handle_unity_execution_error(e, operation_name="operation"):
    # Keep using standard messagebox
    err_msg = (f"Error during Unity {operation_name}.\n\nDetails: {type(e).__name__}: {str(e)}\n\n"
               "Check Unity installation/version (6000.0.32f1) and path.\n"
               "Consider reinstalling Unity Editor.")
    print(f"Unity Error ({operation_name}): {e}")
    # No need for main_window.after for messagebox
    messagebox.showerror("Unity Execution Error", err_msg)

# ensure_unity_closed, open_graphs_folder, get_folder_size, copy_directory, get_build_target_and_executable
# remain unchanged as they don't involve GUI elements directly.
def ensure_unity_closed(): # (Code unchanged)
    if not unity_path_ok or not UNITY_EXECUTABLE: return
    procs = []; norm_exe = ""
    try: norm_exe = os.path.normcase(UNITY_EXECUTABLE)
    except TypeError: return # If None
    try:
        for p in psutil.process_iter(['exe', 'pid']):
            try:
                if p.info['exe'] and os.path.normcase(p.info['exe']) == norm_exe: procs.append(p)
            except (psutil.Error, TypeError, AttributeError, OSError): continue
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
        if procs: print(f"Unity close check took {time.time()-t_start:.2f}s (terminated {len(procs)} processes)")
def open_graphs_folder(simulation_name): # (Code unchanged)
    try:
        fldr = Path.home()/"Documents"/"SimulationLoggerData"/simulation_name/"Graficos"
        fldr.mkdir(parents=True, exist_ok=True)
        if platform.system() == "Windows": os.startfile(str(fldr))
        elif platform.system() == "Darwin": subprocess.Popen(["open", str(fldr)])
        else: subprocess.Popen(["xdg-open", str(fldr)])
    except Exception as e: messagebox.showerror("Error", f"Could not open graphs folder '{fldr}':\n{e}")
def get_folder_size(path): # (Code unchanged)
    total = 0;
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False): total += entry.stat(follow_symlinks=False).st_size
            elif entry.is_dir(follow_symlinks=False): total += get_folder_size(entry.path)
    except Exception: pass
    return total
def copy_directory(src, dst): # (Code unchanged)
    try:
        if os.path.exists(dst): shutil.rmtree(dst, ignore_errors=True); time.sleep(0.1)
        shutil.copytree(src, dst, symlinks=False, ignore_dangling_symlinks=True); return True
    except Exception as e:
        msg = f"Error copying {src} to {dst}:\n{e}"; print(msg)
        messagebox.showerror("Copy Error", msg) # Use standard messagebox
        return False
def get_build_target_and_executable(project_path): # (Code unchanged)
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
# Simulation Logic (Unchanged)
# ======================================================
# get_simulations, update_last_opened, read_last_loaded_simulation_name,
# load_simulation, delete_simulation remain unchanged.
def get_simulations(): # (Code unchanged)
    sims = []
    if not os.path.isdir(SIMULATIONS_DIR): return sims
    try:
        for item in os.listdir(SIMULATIONS_DIR):
            p = os.path.join(SIMULATIONS_DIR, item)
            if os.path.isdir(p) and all(os.path.exists(os.path.join(p, r)) for r in ["Assets", "ProjectSettings"]):
                c_str, l_str = "???", "Never";
                try: c_ts = os.path.getctime(p); c_str = time.strftime("%y-%m-%d %H:%M", time.localtime(c_ts))
                except: pass
                l_file = os.path.join(p, "last_opened.txt")
                if os.path.exists(l_file):
                    try:
                        with open(l_file, "r", encoding='utf-8') as f: l_ts = float(f.read().strip())
                        l_str = time.strftime("%y-%m-%d %H:%M", time.localtime(l_ts))
                    except: pass
                sims.append({"name": item, "creation": c_str,"last_opened": l_str})
    except Exception as e: print(f"Err reading sims: {e}"); return []
    sims.sort(key=lambda s: s['name'].lower()) # Sort here
    return sims
def update_last_opened(sim_name): # (Code unchanged)
    folder = os.path.join(SIMULATIONS_DIR, sim_name); os.makedirs(folder, exist_ok=True)
    try:
        with open(os.path.join(folder, "last_opened.txt"), "w", encoding='utf-8') as f: f.write(str(time.time()))
    except Exception as e: print(f"[Err] update_last_opened({sim_name}): {e}")
def read_last_loaded_simulation_name(): # (Code unchanged)
    global SIMULATION_LOADED_FILE
    if SIMULATION_LOADED_FILE and os.path.exists(SIMULATION_LOADED_FILE):
        try:
            with open(SIMULATION_LOADED_FILE, "r", encoding='utf-8') as f: return f.read().strip()
        except Exception as e: print(f"Error reading {SIMULATION_LOADED_FILE}: {e}")
    return None
def load_simulation(sim_name): # (Code unchanged functionally, uses standard messagebox)
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
        for fldr in ["Assets", "Packages", "ProjectSettings"]:
            src = os.path.join(src_path, fldr); dst = os.path.join(SIMULATION_PROJECT_PATH, fldr)
            if os.path.exists(src):
                if not copy_directory(src, dst): copy_ok = False; break
            elif fldr in ["Assets", "ProjectSettings"]: messagebox.showwarning("Warning", f"Missing '{fldr}' folder in source simulation '{sim_name}'.")
    else:
        update_status("Updating Assets folder..."); src_assets = os.path.join(src_path, "Assets"); dst_assets = ASSETS_FOLDER
        if os.path.exists(src_assets): copy_ok = copy_directory(src_assets, dst_assets)
        else: messagebox.showerror("Error", f"Required 'Assets' folder missing in source simulation '{sim_name}'."); copy_ok = False
    if not copy_ok: update_status("Copy error. Load cancelled."); return False
    try: os.makedirs(STREAMING_ASSETS_FOLDER, exist_ok=True)
    except Exception as e: print(f"Warning: Could not create StreamingAssets folder: {e}")
    try:
        with open(SIMULATION_LOADED_FILE, "w", encoding='utf-8') as f: f.write(sim_name)
        print(f"State file updated with: {sim_name}")
    except Exception as e: messagebox.showwarning("File Error", f"Could not write simulation state file:\n{e}")
    update_last_opened(sim_name); last_simulation_loaded = sim_name
    if 'app' in globals() and app.winfo_exists(): app.after(50, populate_simulations)
    return True
def delete_simulation(sim_name): # (Code unchanged functionally, uses standard messagebox)
    confirm = messagebox.askyesno("Confirm Delete", f"Permanently delete simulation '{sim_name}' and all its associated data (including generated graphs/stats)?\n\nThis action cannot be undone.", icon='warning', default=messagebox.NO)
    if not confirm: update_status("Deletion cancelled."); return
    update_status(f"Deleting '{sim_name}'..."); errs = False; global last_simulation_loaded
    if SIMULATION_LOADED_FILE and os.path.exists(SIMULATION_LOADED_FILE):
        try:
            loaded = read_last_loaded_simulation_name()
            if loaded == sim_name: os.remove(SIMULATION_LOADED_FILE); print("Loaded state file removed.")
            if last_simulation_loaded == sim_name: last_simulation_loaded = None
        except Exception as e: print(f"Warn: Could not clean state file: {e}")
    sim_p = os.path.join(SIMULATIONS_DIR, sim_name)
    if os.path.exists(sim_p):
        try: shutil.rmtree(sim_p); print(f"Deleted simulation folder: {sim_p}")
        except Exception as e: messagebox.showerror("Delete Error", f"Could not delete simulation folder:\n{sim_p}\n{e}"); errs = True
    data_p = Path.home() / "Documents" / "SimulationLoggerData" / sim_name
    if data_p.is_dir():
        try: shutil.rmtree(data_p); print(f"Deleted data folder: {data_p}")
        except Exception as e: messagebox.showerror("Delete Error", f"Could not delete data folder:\n{data_p}\n{e}"); errs = True
    update_status(f"Deletion of '{sim_name}' " + ("completed with errors." if errs else "completed successfully."))
    populate_simulations()


# ======================================================
# Unity Batch Execution & Progress Monitoring (Unchanged)
# ======================================================
# format_time, monitor_unity_progress, run_unity_batchmode, run_prefab_material_tool,
# build_simulation_task, build_simulation_threaded, open_simulation_executable, open_in_unity
# remain unchanged as they are backend logic.
def format_time(seconds): # (Code unchanged)
    if seconds is None or seconds < 0 or math.isinf(seconds) or math.isnan(seconds): return "--:--:--"
    if seconds == 0: return "0s"
    seconds = int(seconds); hours, rem = divmod(seconds, 3600); minutes, secs = divmod(rem, 60)
    if hours > 0: return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    elif minutes > 0: return f"{minutes:02d}:{secs:02d}"
    else: return f"{secs}s"
def monitor_unity_progress(stop_event, operation_tag): # (Code unchanged)
    if not SIMULATION_PROJECT_PATH or not os.path.exists(SIMULATION_PROJECT_PATH): print(f"\nWarning: Path '{SIMULATION_PROJECT_PATH}' not found for monitoring."); return
    TARGET_SIZE_MB = 3000.0; BYTES_PER_MB = 1024*1024; TARGET_SIZE_BYTES = TARGET_SIZE_MB * BYTES_PER_MB
    last_update_time = 0; start_time = time.time(); initial_size_bytes = 0; eta_str = "Calculating..."
    try: initial_size_bytes = get_folder_size(SIMULATION_PROJECT_PATH)
    except Exception as e: print(f"\nError getting initial size for '{SIMULATION_PROJECT_PATH}': {e}"); initial_size_bytes = 0
    initial_size_mb = initial_size_bytes / BYTES_PER_MB
    print(f"[{operation_tag}] Monitoring start. Initial: {initial_size_mb:.1f}MB. Target: {TARGET_SIZE_MB:.0f}MB")
    while not stop_event.is_set():
        now = time.time()
        if now - last_update_time > 1.5:
            current_size_bytes = 0
            try:
                current_size_bytes = get_folder_size(SIMULATION_PROJECT_PATH); current_size_mb = current_size_bytes / BYTES_PER_MB
                elapsed_time = now - start_time; size_increase_bytes = current_size_bytes - initial_size_bytes
                if elapsed_time > 5 and size_increase_bytes > 1024:
                    rate = size_increase_bytes / elapsed_time; remaining = TARGET_SIZE_BYTES - current_size_bytes
                    if rate > 0 and remaining > 0: eta_str = f"ETA: {format_time(remaining / rate)}"
                    elif remaining <= 0: eta_str = "ETA: Completed"
                    else: eta_str = "ETA: --"
                elif elapsed_time <= 5: eta_str = "ETA: Calculating..."
                else: eta_str = "ETA: --"
                progress = min((current_size_mb / TARGET_SIZE_MB) * 100 if TARGET_SIZE_MB > 0 else 0, 100.0)
                status_msg = f"[{operation_tag}] {current_size_mb:.1f}/{TARGET_SIZE_MB:.0f}MB ({progress:.1f}%) - {eta_str}      "
                update_status(status_msg)
            except Exception as e: error_msg = f"Size error: {e}"[:30]; update_status(f"[{operation_tag}] {error_msg}... - {eta_str}      ")
            last_update_time = now
        time.sleep(0.5)
    final_size_mb = get_folder_size(SIMULATION_PROJECT_PATH) / BYTES_PER_MB if SIMULATION_PROJECT_PATH else 0
    print(f"\n[{operation_tag}] Monitoring end. Final size: {final_size_mb:.1f}MB")
def run_unity_batchmode(exec_method, op_name, log_file, timeout=600, extra_args=None): # (Code unchanged)
    if not all([unity_path_ok, unity_version_ok, unity_projects_path_ok, SIMULATION_PROJECT_PATH]): update_status(f"Error: Cannot {op_name}. Config missing."); return False, None
    log_path = os.path.join(SIMULATION_PROJECT_PATH, log_file)
    cmd = [UNITY_EXECUTABLE, "-batchmode", "-quit", "-projectPath", os.path.normpath(SIMULATION_PROJECT_PATH), "-executeMethod", exec_method, "-logFile", log_path]
    if extra_args: cmd.extend(extra_args)
    success = False; stop = threading.Event(); exe_path_after_build = None
    monitor = threading.Thread(target=monitor_unity_progress, args=(stop, op_name.capitalize()), daemon=True)
    try:
        update_status(f"[{op_name.capitalize()}] Starting Unity process..."); monitor.start()
        flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        process = subprocess.run(cmd, check=True, timeout=timeout, creationflags=flags, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        print(f"--- Unity Stdout ({op_name}) ---\n{process.stdout[-1000:]}\n--- End Stdout ---")
        if process.stderr: print(f"--- Unity Stderr ({op_name}) ---\n{process.stderr[-1000:]}\n--- End Stderr ---")
        update_status(f"[{op_name.capitalize()}] Unity process finished."); success = True
        if "BuildScript.PerformBuild" in exec_method:
            update_status(f"[{op_name.capitalize()}] Verifying build output...")
            _, exe_path_after_build = get_build_target_and_executable(SIMULATION_PROJECT_PATH); found = False
            for attempt in range(6):
                if exe_path_after_build and os.path.exists(exe_path_after_build): found = True; print(f"Build output CONFIRMED (attempt {attempt+1}): {exe_path_after_build}"); break
                print(f"Build output check attempt {attempt+1} failed for {exe_path_after_build}"); time.sleep(0.5)
            if found: update_status(f"[{op_name.capitalize()}] Build executable verified.")
            else: print(f"WARN: Executable NOT FOUND post-build: {exe_path_after_build}"); success = False; handle_unity_execution_error(FileNotFoundError(f"Build finished but output executable is missing: {exe_path_after_build}"), op_name); update_status(f"[Error] {op_name.capitalize()} failed: Output missing.")
    except subprocess.CalledProcessError as e: handle_unity_execution_error(e, op_name); update_status(f"[Error] {op_name.capitalize()} failed (code {e.returncode}). See {log_path}"); print(f"--- Unity Output on Error ({op_name}) ---\nStdout:\n{e.stdout[-1000:] if e.stdout else 'N/A'}\nStderr:\n{e.stderr[-1000:] if e.stderr else 'N/A'}\n---")
    except subprocess.TimeoutExpired as e: handle_unity_execution_error(e, op_name); update_status(f"[Error] {op_name.capitalize()} timed out ({timeout}s). See {log_path}")
    except (FileNotFoundError, PermissionError) as e: handle_unity_execution_error(e, op_name); update_status(f"[Error] {op_name.capitalize()} failed (File/Permission). Check Unity path.")
    except Exception as e: handle_unity_execution_error(e, f"{op_name} (unexpected)"); update_status(f"[Error] Unexpected error during {op_name}.")
    finally: stop.set(); monitor.join(timeout=1.0)
    return success, exe_path_after_build
def run_prefab_material_tool(): # (Code unchanged)
    success, _ = run_unity_batchmode("PrefabMaterialCreator.CreatePrefabsAndMaterials", "prefabs tool", "prefab_tool_log.txt", timeout=600)
    return success
def build_simulation_task(extra_args, callback): # (Code unchanged)
    disable_all_interactions()
    success, final_exe_path = run_unity_batchmode("BuildScript.PerformBuild", "build", "build_log.txt", timeout=1800, extra_args=extra_args)
    if 'app' in globals() and app.winfo_exists(): # Check app exists
        if callback: app.after(0, lambda s=success, p=final_exe_path: callback(s, p))
        app.after(10, enable_all_interactions)
def build_simulation_threaded(callback=None): # (Code unchanged)
    build_target, _ = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
    if not build_target: print("Error: Could not determine build target"); messagebox.showerror("Build Error", "Could not determine the build target for your operating system."); return
    extra = ["-buildTarget", build_target]
    threading.Thread(target=lambda: build_simulation_task(extra, callback), daemon=True).start()
def open_simulation_executable(): # (Code unchanged functionally)
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
            time.sleep(1); update_status("Executable launched.")
        except Exception as e: handle_unity_execution_error(e, f"run simulation ({os.path.basename(exe_path)})"); update_status(f"Error launching: {e}")
    else: messagebox.showerror("Error", f"Executable not found:\n{exe_path}\nPlease build the simulation first."); update_status("Error: Executable not found.")
def open_in_unity(): # (Code unchanged functionally)
    if not all([unity_path_ok, unity_projects_path_ok, UNITY_EXECUTABLE, SIMULATION_PROJECT_PATH]): messagebox.showerror("Error", "Cannot open in Unity. Check configuration."); return
    if not os.path.isdir(SIMULATION_PROJECT_PATH): messagebox.showerror("Error", f"Project path does not exist: {SIMULATION_PROJECT_PATH}"); return
    try:
        update_status(f"Opening project in Unity Editor..."); cmd = [UNITY_EXECUTABLE, "-projectPath", os.path.normpath(SIMULATION_PROJECT_PATH)]
        subprocess.Popen(cmd); update_status("Unity Editor launch initiated...")
    except Exception as e: handle_unity_execution_error(e, "open in Unity")

# ======================================================
# API Simulation Creation (Unchanged Functionally)
# ======================================================
def create_simulation_thread(sim_name, sim_desc, original_states): # (Code unchanged functionally)
    update_status(f"Creating '{sim_name}' via API..."); disable_all_interactions()
    os.makedirs(SIMULATIONS_DIR, exist_ok=True)
    success = False
    try:
        api_script = Path("./Scripts/api_manager.py").resolve()
        if not api_script.exists(): raise FileNotFoundError(f"API script not found: {api_script}")
        cmd = [sys.executable, str(api_script), sim_name, sim_desc]
        flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300, creationflags=flags, encoding='utf-8', errors='ignore')
        print("API Script Output:", result.stdout[-500:])
        update_status(f"'{sim_name}' created successfully.")
        if 'app' in globals() and app.winfo_exists(): # Check app exists
            app.after(10, lambda: messagebox.showinfo("Success", f"Simulation '{sim_name}' created."))
            app.after(50, populate_simulations)
        success = True
    except FileNotFoundError as e: messagebox.showerror("Critical Error", f"Required API script not found:\n{e}"); update_status("Error: Missing API script.")
    except subprocess.CalledProcessError as e:
        err_out = (e.stderr if e.stderr else e.stdout); code=e.returncode; print(f"API Script Error (Code {code}):\n{err_out}")
        msg, det = f"API Error (Code {code})", f"See console/logs for details."
        if "CONTENT ERROR" in err_out: msg, det = "Content Error", "Simulation type might be invalid (e.g., E.Coli, S.Cerevisiae)."
        elif "already exists" in err_out or "DUPLICATE" in err_out: msg, det = "Duplicate Simulation", f"A simulation named '{sim_name}' already exists."
        elif "format" in err_out.lower() or "FORMATTING ERROR" in err_out: msg, det = "Formatting Error", "Invalid question or description format."
        elif "AuthenticationError" in err_out: msg, det = "API Authentication Error", "Invalid OpenAI API Key."
        if 'app' in globals() and app.winfo_exists(): app.after(0, lambda m=msg, d=det: messagebox.showerror(f"Creation Error: {m}", d))
        update_status(f"Creation error: {msg}")
    except subprocess.TimeoutExpired: messagebox.showerror("Error", "Simulation creation timed out (300s)."); update_status("Error: Creation timeout.")
    except Exception as e: messagebox.showerror("Unexpected Error", f"An unexpected critical error occurred during creation:\n{type(e).__name__}: {e}"); update_status("Critical creation error."); print(f"Critical Error (create_sim_thread): {e}"); import traceback; traceback.print_exc()
    finally:
        if 'app' in globals() and app.winfo_exists(): app.after(100, enable_all_interactions)

# ======================================================
# Verification Logic (Unchanged Functionally)
# ======================================================
def perform_verification(show_results_box=False, on_startup=False): # (Code unchanged functionally)
    global unity_path_ok, unity_version_ok, unity_projects_path_ok, apis_key_ok, apis_models_ok, initial_verification_complete
    global UNITY_EXECUTABLE, UNITY_PROJECTS_PATH, OPENAI_API_KEY, FINE_TUNED_MODEL_NAME, SECONDARY_FINE_TUNED_MODEL_NAME
    global SIMULATION_PROJECT_PATH, ASSETS_FOLDER, STREAMING_ASSETS_FOLDER, SIMULATION_LOADED_FILE, last_simulation_loaded
    if not on_startup: update_status("Verifying configuration...")
    load_dotenv('.env', override=True)
    UNITY_EXECUTABLE = os.environ.get("UNITY_EXECUTABLE"); UNITY_PROJECTS_PATH = os.environ.get("UNITY_PROJECTS_PATH")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY"); FINE_TUNED_MODEL_NAME = os.getenv("FINE_TUNED_MODEL_NAME"); SECONDARY_FINE_TUNED_MODEL_NAME = os.getenv("2ND_FINE_TUNED_MODEL_NAME")
    results = []; unity_path_ok=unity_version_ok=unity_projects_path_ok=apis_key_ok=apis_models_ok=False
    req_ver = "6000.0.32f1"
    if not UNITY_EXECUTABLE: results.append("❌ Unity Exe: Path missing in .env")
    elif not os.path.isfile(UNITY_EXECUTABLE): results.append(f"❌ Unity Exe: Path not found or not a file:\n   '{UNITY_EXECUTABLE}'")
    else:
        unity_path_ok = True; results.append(f"✅ Unity Exe: Path OK")
        if req_ver in UNITY_EXECUTABLE: unity_version_ok = True; results.append(f"✅ Unity Ver: OK (found '{req_ver}')")
        else: results.append(f"⚠️ Unity Ver: Path doesn't contain expected version '{req_ver}'. Ensure it's correct.")
    if not UNITY_PROJECTS_PATH: results.append("❌ Projects Path: Missing in .env")
    elif not os.path.isdir(UNITY_PROJECTS_PATH): results.append(f"❌ Projects Path: Not found or not a directory:\n   '{UNITY_PROJECTS_PATH}'")
    else:
        unity_projects_path_ok = True; results.append(f"✅ Projects Path: OK")
        SIMULATION_PROJECT_PATH = os.path.join(UNITY_PROJECTS_PATH, SIMULATION_PROJECT_NAME)
        ASSETS_FOLDER = os.path.join(SIMULATION_PROJECT_PATH, "Assets")
        STREAMING_ASSETS_FOLDER = os.path.join(ASSETS_FOLDER, "StreamingAssets")
        SIMULATION_LOADED_FILE = os.path.join(STREAMING_ASSETS_FOLDER, "simulation_loaded.txt")
        last_simulation_loaded = read_last_loaded_simulation_name()
    if not OPENAI_API_KEY: results.append("❌ API Key: Missing in .env")
    else:
        openai.api_key = OPENAI_API_KEY; client = None
        if hasattr(openai, "OpenAI"): client = openai.OpenAI()
        try:
            if client: client.models.list(limit=1)
            else: openai.Model.list(limit=1)
            apis_key_ok = True; results.append("✅ API Key: Connection OK.")
            models_ok_list = []
            for name, mid in [("Primary", FINE_TUNED_MODEL_NAME), ("Secondary", SECONDARY_FINE_TUNED_MODEL_NAME)]:
                if not mid: results.append(f"ℹ️ {name} Model: Not set in .env (optional)."); continue
                try:
                    if client: client.models.retrieve(mid)
                    else: openai.Model.retrieve(mid)
                    results.append(f"✅ {name} Model ('{mid}'): Found."); models_ok_list.append(name=="Primary")
                except (openai_error.InvalidRequestError, InvalidRequestError): results.append(f"❌ {name} Model ('{mid}'): Not found on OpenAI."); models_ok_list.append(False)
                except Exception as me: results.append(f"❌ {name} Model ('{mid}'): API Error ({type(me).__name__})"); models_ok_list.append(False); print(f"Model check error: {me}")
            apis_models_ok = bool(models_ok_list) and models_ok_list[0]
            if not apis_models_ok and FINE_TUNED_MODEL_NAME: results.append("❌ Primary Model: Invalid or not found. Creation disabled.")
            elif not FINE_TUNED_MODEL_NAME: results.append("⚠️ Primary Model: Not set. Creation disabled."); apis_models_ok = False
        except (openai_error.AuthenticationError, AuthenticationError): results.append("❌ API Key: Invalid (Authentication failed).")
        except (openai_error.APIConnectionError, APIConnectionError) as ace: results.append(f"❌ API Connection Error: {ace}"); print(f"API Connection Error: {ace}")
        except Exception as ae: results.append(f"❌ API Error: {type(ae).__name__} - {ae}"); print(f"Unhandled API verification error: {ae}")
    if not initial_verification_complete: initial_verification_complete = True
    unity_ok = unity_path_ok and unity_version_ok and unity_projects_path_ok
    api_ok = apis_key_ok and apis_models_ok
    status_parts = [f"{'✅' if unity_ok else '❌'} Unity", f"{'✅' if api_ok else '❌'} API"]
    final_status = " | ".join(status_parts)
    if 'app' in globals() and app.winfo_exists():
        app.after(0, lambda: update_status(final_status))
        app.after(50, update_button_states)
        app.after(100, populate_simulations)
        if on_startup:
            err_msg = ""
            if not unity_path_ok or not unity_projects_path_ok: err_msg += f"- Invalid Unity/Projects path in .env.\n"
            elif not unity_version_ok: err_msg += f"- Unity version mismatch (requires '{req_ver}' in path).\n"
            if not unity_ok: err_msg += "  (Simulation loading/building might fail)\n"
            if not apis_key_ok: err_msg += "- Invalid or missing OpenAI API Key in .env.\n"
            elif not apis_models_ok: err_msg += "- Primary Fine-Tuned Model invalid or missing in .env.\n"
            if not api_ok: err_msg += "  (Simulation creation disabled)\n"
            if err_msg:
                 full_msg = "Configuration Problems Found:\n\n" + err_msg + "\nPlease check your .env file and use 'Settings' or 'Verify Config'."
                 app.after(200, lambda m=full_msg: messagebox.showwarning("Initial Configuration Issues", m))
    else: print(f"Verification Status: {final_status}")
    if show_results_box:
        res_text = "Verification Results:\n\n" + "\n".join(results)
        all_ok = unity_ok and api_ok
        if 'app' in globals() and app.winfo_exists():
             app.after(0, lambda: messagebox.showinfo("Verification Complete", res_text) if all_ok else messagebox.showwarning("Verification Issues Found", res_text))

# ======================================================
# Configuration Window (Rewritten for CTk)
# ======================================================
def open_config_window():
    cfg_win = ctk.CTkToplevel(app)
    cfg_win.title("Settings")
    cfg_win.geometry("650x260") # Slightly more height for CTk widgets
    center_window(cfg_win, 650, 260)
    cfg_win.resizable(False, False)
    cfg_win.transient(app)
    cfg_win.grab_set()

    cfg_win.grid_columnconfigure(0, weight=1)
    cfg_win.grid_rowconfigure(0, weight=1) # Frame container expands
    cfg_win.grid_rowconfigure(1, weight=0) # Button frame fixed

    main_frame = ctk.CTkFrame(cfg_win, fg_color="transparent")
    main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
    main_frame.grid_columnconfigure(0, weight=1)

    # --- Path Selection ---
    # Use CTkFrame directly instead of LabelFrame
    paths_frame = ctk.CTkFrame(main_frame)
    paths_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
    paths_frame.grid_columnconfigure(1, weight=1) # Make entry expand

    ctk.CTkLabel(paths_frame, text="Paths Configuration", font=font_base_bold).grid(
        row=0, column=0, columnspan=3, padx=10, pady=(10, 15), sticky="w")

    entries = {} # To store CTkEntry widgets or StringVars if needed

    def create_row(parent, row_index, label_text, env_var, key, is_file=True):
        ctk.CTkLabel(parent, text=label_text, font=font_base).grid(
            row=row_index, column=0, padx=(10, 5), pady=5, sticky="w")

        entry_var = ctk.StringVar(value=os.environ.get(env_var, ""))
        entry = ctk.CTkEntry(parent, textvariable=entry_var, font=font_base)
        entry.grid(row=row_index, column=1, padx=5, pady=5, sticky="ew")
        entries[key] = entry_var # Store the variable

        def browse():
            initial_dir = "/"
            current_path = entry_var.get()
            if current_path:
                 if is_file and os.path.exists(os.path.dirname(current_path)):
                     initial_dir = os.path.dirname(current_path)
                 elif not is_file and os.path.isdir(current_path):
                     initial_dir = current_path
                 elif not is_file and os.path.exists(os.path.dirname(current_path)):
                      initial_dir = os.path.dirname(current_path)


            if is_file:
                path = filedialog.askopenfilename(title=f"Select {label_text}", initialdir=initial_dir)
            else:
                path = filedialog.askdirectory(title=f"Select {label_text}", initialdir=initial_dir)

            if path:
                entry_var.set(path)

        browse_button = ctk.CTkButton(parent, text="...", width=30, font=font_base, command=browse)
        browse_button.grid(row=row_index, column=2, padx=(5, 10), pady=5)

    create_row(paths_frame, 1, "Unity Executable:", "UNITY_EXECUTABLE", "unity_exe", is_file=True)
    create_row(paths_frame, 2, "Projects Folder:", "UNITY_PROJECTS_PATH", "projects_path", is_file=False)


    # --- Buttons ---
    button_frame = ctk.CTkFrame(cfg_win, fg_color="transparent")
    button_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="e")

    def save():
        data = {k: v.get().strip() for k, v in entries.items()}
        errs = [f"- {k.replace('_',' ').capitalize()} cannot be empty." for k, v in data.items() if not v]
        if errs: messagebox.showerror("Input Error", "Please fill all required fields:\n"+"\n".join(errs), parent=cfg_win); return

        current_api_key = os.getenv("OPENAI_API_KEY", "")
        current_model1 = os.getenv("FINE_TUNED_MODEL_NAME", "")
        current_model2 = os.getenv("2ND_FINE_TUNED_MODEL_NAME", "")

        try:
            env_path = Path(".env")
            env_vars = {}
            if env_path.exists():
                with open(env_path, "r", encoding='utf-8') as f:
                    for line in f:
                        if '=' in line and not line.strip().startswith('#'):
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip().strip('"') # Remove quotes when reading

            env_vars["UNITY_EXECUTABLE"] = data['unity_exe']
            env_vars["UNITY_PROJECTS_PATH"] = data['projects_path']
            env_vars["OPENAI_API_KEY"] = current_api_key # Preserve
            env_vars["FINE_TUNED_MODEL_NAME"] = current_model1 # Preserve
            env_vars["2ND_FINE_TUNED_MODEL_NAME"] = current_model2 # Preserve

            with open(env_path, "w", encoding='utf-8') as f:
                for key, value in env_vars.items():
                    # Add quotes if value contains spaces
                    if ' ' in value:
                        f.write(f'{key}="{value}"\n')
                    else:
                        f.write(f'{key}={value}\n')

            messagebox.showinfo("Success", "Settings saved to .env file.\nRe-verifying configuration...", parent=cfg_win)
            cfg_win.destroy()
            app.after(100, lambda: perform_verification(show_results_box=True))
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not write to .env file:\n{e}", parent=cfg_win)

    save_button = ctk.CTkButton(button_frame, text="Save and Verify", command=save, font=font_base)
    save_button.grid(row=0, column=0, padx=(0, 10))

    cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=cfg_win.destroy, font=font_base,
                                  fg_color="grey50", hover_color="grey30")
    cancel_button.grid(row=0, column=1, padx=0)

# ======================================================
# GUI Definitions (Callbacks - Unchanged Functionally)
# ======================================================
# populate_simulations, update_button_states, on_load_simulation_request, load_simulation_logic,
# build_callback, on_delete_simulation_request, on_show_graphs_thread, show_graphs_logic,
# on_create_simulation, show_options_window, handle_tree_click, handle_tree_motion, handle_tree_leave
# remain functionally the same, but GUI interactions inside them (like disabling buttons)
# now target CTk widgets where applicable. Messageboxes remain standard.

def populate_simulations(): # (Unchanged Functionally)
    if not initial_verification_complete: return
    if 'sim_tree' not in globals(): return # Check if tree exists

    # Clear Treeview
    for item in sim_tree.get_children():
        try: sim_tree.delete(item)
        except tk.TclError: pass

    update_status("Searching for simulations...")
    simulations = get_simulations() # Already sorted
    global last_simulation_loaded
    last_simulation_loaded = read_last_loaded_simulation_name()

    if simulations:
        for i, sim in enumerate(simulations):
            is_loaded = (sim["name"] == last_simulation_loaded)
            item_tags = []
            if is_loaded: item_tags.append("loaded") # Tag for loaded style

            try:
                sim_tree.insert("", "end", iid=sim["name"],
                                values=(sim["name"], sim["creation"], sim["last_opened"],
                                        loaded_indicator_text if is_loaded else "",
                                        play_icon_text, delete_icon_text),
                                tags=tuple(item_tags))
            except tk.TclError as e: print(f"Error inserting '{sim['name']}': {e}")

        update_status(f"Found {len(simulations)} simulations.")
    else:
        update_status("No simulations found in ./Simulations")
    update_button_states()

def update_button_states(): # (Updated for CTk where applicable)
    if 'app' not in globals() or not app.winfo_exists() or not initial_verification_complete : return

    can_load_build = unity_path_ok and unity_version_ok and unity_projects_path_ok
    can_create = apis_key_ok and apis_models_ok
    is_selection = False
    if 'sim_tree' in globals(): # Check if tree exists
        try: is_selection = bool(sim_tree.selection())
        except tk.TclError: pass # Handle if tree destroyed

    # Determine states based on verification and selection
    reload_state = "normal"
    graph_state = "normal" if is_selection and can_load_build else "disabled" # Need valid Unity for graphs too? Assume yes.
    create_state = "normal" if can_create else "disabled"
    verify_state = "normal"
    settings_state = "normal"
    about_state = "normal"
    unity_down_state = "normal"
    exit_state = "normal"

    # Override if build is running
    if is_build_running:
        reload_state = graph_state = create_state = verify_state = settings_state = about_state = unity_down_state = exit_state = "disabled"

    # Apply states to CTk widgets using helper
    if 'reload_btn' in globals(): set_widget_state(reload_btn, reload_state)
    if 'graph_btn' in globals(): set_widget_state(graph_btn, graph_state)
    if 'create_btn' in globals(): set_widget_state(create_btn, create_state)
    if 'settings_btn' in globals(): set_widget_state(settings_btn, settings_state)
    if 'verify_btn' in globals(): set_widget_state(verify_btn, verify_state)
    if 'unity_down_btn' in globals(): set_widget_state(unity_down_btn, unity_down_state)
    if 'about_btn' in globals(): set_widget_state(about_btn, about_state)
    if 'exit_btn' in globals(): set_widget_state(exit_btn, exit_state)

def on_load_simulation_request(simulation_name): # (Unchanged functionally)
    global is_build_running
    if is_build_running: return
    print(f"Load request for: {simulation_name}")
    if not all([unity_path_ok, unity_version_ok, unity_projects_path_ok]):
        messagebox.showerror("Unity Configuration Error", "Cannot load simulation: Invalid Unity path or version.\nPlease check Settings."); return
    if simulation_name == last_simulation_loaded:
        update_status(f"'{simulation_name}' is already loaded. Showing options..."); update_last_opened(simulation_name)
        _, current_exe_path = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
        app.after(0, lambda s=simulation_name, p=current_exe_path: show_options_window(s, p))
        return
    disable_all_interactions()
    threading.Thread(target=load_simulation_logic, args=(simulation_name,), daemon=True).start()

def load_simulation_logic(simulation_name): # (Unchanged functionally)
    update_status(f"Loading '{simulation_name}'..."); update_status("Ensuring Unity is closed..."); ensure_unity_closed()
    update_status(f"Copying simulation files for '{simulation_name}'..."); load_success = load_simulation(simulation_name)
    if load_success:
        update_status("Files loaded. Running post-load tools (Prefabs/Materials)..."); prefab_success = run_prefab_material_tool()
        if prefab_success:
            update_status("Post-load tools OK. Starting build..."); build_simulation_threaded(callback=lambda success, path: build_callback(success, simulation_name, path))
        else:
            update_status(f"Post-load tools failed for '{simulation_name}'. Build cancelled."); messagebox.showerror("Post-Load Error", "The Prefab/Material creation tool failed. The build process was cancelled.\nCheck prefab_tool_log.txt for details.")
            if 'app' in globals() and app.winfo_exists(): app.after(0, enable_all_interactions)
    else:
        update_status(f"Error loading files for '{simulation_name}'.");
        if 'app' in globals() and app.winfo_exists(): app.after(0, enable_all_interactions)

def build_callback(success, simulation_name, executable_path): # (Unchanged functionally)
    if 'app' in globals() and app.winfo_exists(): app.after(0, enable_all_interactions) # Enable UI first
    else: return # App closed

    if success and executable_path:
        update_status(f"Build successful for '{simulation_name}'.");
        if messagebox.askyesno("Build Complete", f"Simulation '{simulation_name}' built successfully.\n\nDo you want to run it now?", icon='question'):
            open_simulation_executable()
        # else: show_options_window(simulation_name, executable_path) # Option: show options even if they don't run
    else:
        update_status(f"Build failed for '{simulation_name}'" + (" (Executable missing)." if success else ". Check build_log.txt."))
        messagebox.showerror("Build Failed", f"The build for '{simulation_name}' failed.\nPlease check the build_log.txt file inside the '{SIMULATION_PROJECT_NAME}' project folder for errors.")

def on_delete_simulation_request(simulation_name): # (Unchanged functionally)
    global is_build_running
    if is_build_running: return
    print(f"Delete request for: {simulation_name}")
    delete_simulation(simulation_name)

def on_show_graphs_thread(): # (Unchanged functionally)
    global is_build_running
    if is_build_running: return
    selected_items = sim_tree.selection()
    if not selected_items: messagebox.showwarning("No Selection", "Please select a simulation from the list to view its graphs."); return
    sim_name = sim_tree.item(selected_items[0], "values")[0]
    update_status(f"Checking data and scripts for '{sim_name}' graphs...")
    disable_all_interactions()
    threading.Thread(target=show_graphs_logic, args=(sim_name,), daemon=True).start()

def show_graphs_logic(sim_name): # (Unchanged functionally)
    try:
        data_dir = Path.home() / "Documents" / "SimulationLoggerData" / sim_name
        csv_p = data_dir / "SimulationStats.csv"
        if not csv_p.exists():
            if 'app' in globals() and app.winfo_exists(): app.after(0, lambda: messagebox.showerror("Data Not Found", f"Statistics file not found:\n{csv_p}\n\nRun the simulation at least once to generate data."))
            update_status("Error: Simulation statistics CSV not found."); return
        spec_s_path = Path(SIMULATIONS_DIR) / sim_name / "Assets" / "Scripts" / "SimulationData" / "SimulationGraphics.py"
        gen_s_path = Path("./Scripts/SimulationGraphics.py").resolve()
        script_to_run = None
        if spec_s_path.exists(): script_to_run = str(spec_s_path); print(f"Using specific graph script: {script_to_run}")
        elif gen_s_path.exists(): script_to_run = str(gen_s_path); print(f"Using generic graph script: {script_to_run}")
        else:
            if 'app' in globals() and app.winfo_exists(): app.after(0, lambda: messagebox.showerror("Script Error", f"Graph generation script not found.\nChecked:\n- {spec_s_path}\n- {gen_s_path}"))
            update_status("Error: Graph generation script missing."); return
        update_status(f"Running graph script: {os.path.basename(script_to_run)}...")
        process = subprocess.Popen([sys.executable, script_to_run, sim_name])
        process.wait(timeout=60)
        update_status(f"Graph generation process for '{sim_name}' finished. Opening folder...")
        if 'app' in globals() and app.winfo_exists(): app.after(100, lambda s=sim_name: open_graphs_folder(s))
    except subprocess.TimeoutExpired:
        if 'app' in globals() and app.winfo_exists(): app.after(0, lambda: messagebox.showwarning("Timeout", "Graph generation script took too long and might still be running."))
        update_status("Graph script timed out.")
    except Exception as e:
        if 'app' in globals() and app.winfo_exists(): app.after(0, lambda: messagebox.showerror("Graph Generation Error", f"An error occurred while generating graphs:\n{type(e).__name__}: {e}"))
        update_status("Error during graph generation."); print(f"Graph logic error: {e}"); import traceback; traceback.print_exc()
    finally:
        if 'app' in globals() and app.winfo_exists(): app.after(0, enable_all_interactions)

def on_create_simulation(): # (Unchanged functionally)
    global is_build_running
    if is_build_running: return
    if not apis_key_ok or not apis_models_ok:
        messagebox.showerror("API Configuration Error", "Cannot create simulation: Invalid API Key or Primary Model.\nPlease check your .env file and Verify Config."); return
    sim_name = custom_askstring("Create New Simulation", "Enter Simulation Name:")
    if not sim_name: update_status("Creation cancelled."); return
    sim_name = sim_name.strip().replace(" ", "_")
    invalid_chars = r'\/:*?"<>|'
    if not sim_name or any(c in sim_name for c in invalid_chars):
        messagebox.showerror("Invalid Name", f"Simulation name cannot be empty and cannot contain: {invalid_chars}"); update_status("Invalid simulation name."); return
    if os.path.exists(os.path.join(SIMULATIONS_DIR, sim_name)):
        messagebox.showerror("Duplicate Name", f"A simulation named '{sim_name}' already exists."); update_status("Duplicate simulation name."); return
    sim_desc = custom_askstring("Simulation Description", "Describe the simulation objective or question:")
    if not sim_desc: update_status("Creation cancelled."); return
    update_status(f"Starting creation process for '{sim_name}'...")
    disable_all_interactions()
    states = { 'reload': 'disabled', 'graph': 'disabled', 'create': 'disabled' }
    threading.Thread(target=create_simulation_thread, args=(sim_name, sim_desc, states), daemon=True).start()

def show_options_window(simulation_name, executable_path): # (Rewritten for CTk)
    opt_win = ctk.CTkToplevel(app)
    opt_win.title(f"Options: {simulation_name}")
    opt_win.geometry("350x200") # Adjusted height
    center_window(opt_win, 350, 200)
    opt_win.resizable(False, False)
    opt_win.transient(app)
    opt_win.grab_set()

    opt_win.grid_columnconfigure(0, weight=1)
    opt_win.grid_rowconfigure(0, weight=0)
    opt_win.grid_rowconfigure(1, weight=1) # Frame expands

    title_label = ctk.CTkLabel(opt_win, text=f"Simulation '{simulation_name}' is ready.",
                               font=font_medium_bold)
    title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

    button_frame = ctk.CTkFrame(opt_win, fg_color="transparent")
    button_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
    button_frame.grid_columnconfigure(0, weight=1)

    close_func = opt_win.destroy # Capture destroy method

    exec_state = "normal" if (executable_path and os.path.exists(executable_path)) else "disabled"
    print(f"DEBUG show_options_window: Path='{executable_path}', Exists={os.path.exists(executable_path) if executable_path else False}, State={exec_state}")

    run_button = ctk.CTkButton(button_frame, text="Run Simulation", font=font_base_bold,
                                command=lambda: [open_simulation_executable(), close_func()],
                                state=exec_state, fg_color=COLOR_SUCCESS, hover_color="#1E7E34") # Darker green hover
    run_button.grid(row=0, column=0, padx=0, pady=8, sticky="ew", ipady=5) # Internal padding for height

    open_unity_button = ctk.CTkButton(button_frame, text="Open Project in Unity", font=font_base,
                                       command=lambda: [open_in_unity(), close_func()],
                                       fg_color=COLOR_INFO, hover_color="#117A8B") # Darker teal hover
    open_unity_button.grid(row=1, column=0, padx=0, pady=8, sticky="ew", ipady=5)

    update_status(f"Options available for '{simulation_name}'.")
    opt_win.wait_window()

def handle_tree_click(event): # (Unchanged functionally, interacts with ttk.Treeview)
    global is_build_running
    if is_build_running: return
    if 'sim_tree' not in globals(): return # Treeview check

    region = sim_tree.identify_region(event.x, event.y)
    if region != "cell": cancel_tooltip(sim_tree); return

    item_id = sim_tree.identify_row(event.y)
    col_id = sim_tree.identify_column(event.x)
    if not item_id or not col_id: cancel_tooltip(sim_tree); return

    try:
        col_index = int(col_id.replace('#','')) - 1
        values = sim_tree.item(item_id, "values")
        if not values: return
        simulation_name = values[0]

        if item_id not in sim_tree.selection():
            sim_tree.selection_set(item_id)
            sim_tree.focus(item_id)
            update_button_states()

        hide_tooltip()

        if col_index == 4: # Index of "col_load"
             on_load_simulation_request(simulation_name)
        elif col_index == 5: # Index of "col_delete"
             on_delete_simulation_request(simulation_name)

    except Exception as e: print(f"Error handle_tree_click: {e}"); cancel_tooltip(sim_tree)

def handle_tree_motion(event): # (Unchanged functionally)
    global is_build_running
    if is_build_running: return
    if 'sim_tree' not in globals(): return # Treeview check

    global tooltip_job_id
    region = sim_tree.identify_region(event.x, event.y)
    if region != "cell": cancel_tooltip(sim_tree); return
    col_id = sim_tree.identify_column(event.x); item_id = sim_tree.identify_row(event.y)
    if not col_id or not item_id: cancel_tooltip(sim_tree); return
    try:
        col_index = int(col_id.replace('#','')) - 1
        tooltip_text = None
        if col_index == 4: tooltip_text = "Load/Build/Run Simulation"
        elif col_index == 5: tooltip_text = "Delete Simulation"
        if tooltip_text: schedule_tooltip(sim_tree, tooltip_text)
        else: cancel_tooltip(sim_tree)
    except Exception: cancel_tooltip(sim_tree)

def handle_tree_leave(event): # (Unchanged functionally)
    if 'sim_tree' in globals(): cancel_tooltip(sim_tree)

# --- Logo Loading using CTkImage ---
def load_logo(path, target_width):
    global logo_image_ref
    try:
        if not os.path.exists(path):
             print(f"Warning: Logo image not found at '{path}'. Using placeholder.")
             # Create a placeholder transparent image using PIL
             pil_image = Image.new('RGBA', (target_width, int(target_width * 0.4)), (0,0,0,0))
        else:
            pil_image = Image.open(path)
            # Calculate new height maintaining aspect ratio
            width_percent = (target_width / float(pil_image.size[0]))
            target_height = int((float(pil_image.size[1]) * float(width_percent)))
            # Resize with high quality resampling
            pil_image = pil_image.resize((target_width, target_height), Image.Resampling.LANCZOS)

        # Create CTkImage (can specify dark_image=... if needed)
        logo_image_ref = ctk.CTkImage(light_image=pil_image, size=(pil_image.width, pil_image.height))
        return logo_image_ref
    except Exception as e:
        print(f"Error loading or creating logo: {e}")
        return None # Return None if loading fails

# ======================================================
# GUI Setup (Rewritten with CustomTkinter)
# ======================================================
app = ctk.CTk() # Main application window

# --- Define Fonts AFTER creating the main app window ---
FONT_FAMILY = "Segoe UI" # Or another preferred font
FONT_SIZE_BASE = 13
FONT_SIZE_LARGE = 22
FONT_SIZE_MEDIUM = 16
FONT_SIZE_SMALL = 11

try:
    font_base = ctk.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_BASE)
    font_base_bold = ctk.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_BASE, weight="bold")
    font_large_bold = ctk.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_LARGE, weight="bold")
    font_medium_bold = ctk.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_MEDIUM, weight="bold")
    font_small = ctk.CTkFont(family=FONT_FAMILY, size=FONT_SIZE_SMALL)
    print("Fonts loaded successfully.")
except Exception as e:
    print(f"Error loading font '{FONT_FAMILY}': {e}. Falling back to default.")
    # Fallback to default fonts if specific one fails
    font_base = ctk.CTkFont(size=FONT_SIZE_BASE)
    font_base_bold = ctk.CTkFont(size=FONT_SIZE_BASE, weight="bold")
    font_large_bold = ctk.CTkFont(size=FONT_SIZE_LARGE, weight="bold")
    font_medium_bold = ctk.CTkFont(size=FONT_SIZE_MEDIUM, weight="bold")
    font_small = ctk.CTkFont(size=FONT_SIZE_SMALL)
# --- End Font Definition ---


try: app.iconbitmap("icono.ico")
except tk.TclError: print("Warn: icono.ico not found or not supported.") # CTk might handle icons differently
app.title("Unity Simulation Manager")
initial_width = 1050 # Slightly wider for CTk padding
initial_height = 700
center_window(app, initial_width, initial_height)
app.resizable(True, True)
app.minsize(850, 550)

# --- Main Layout ---
app.grid_columnconfigure(1, weight=1) # Content area expands
app.grid_columnconfigure(0, weight=0) # Sidebar fixed width
app.grid_rowconfigure(0, weight=1)    # Main content row expands
app.grid_rowconfigure(1, weight=0)    # Status bar fixed height

# --- Sidebar ---
sidebar_frame = ctk.CTkFrame(app, width=180, corner_radius=0) # No corner radius for sidebar edge
sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew") # Span both rows? Maybe just row 0. Let's try row 0 first.
# Corrected sidebar grid:
sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=(0,0), pady=0)
sidebar_frame.grid_rowconfigure(5, weight=1) # Spacer row to push exit button down

# --- Logo ---
logo_image = load_logo(LOGO_PATH, LOGO_WIDTH)
logo_label = ctk.CTkLabel(sidebar_frame, text="", image=logo_image) # Empty text, show image
logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

# --- Sidebar Title ---
title_label = ctk.CTkLabel(sidebar_frame, text="Menu", font=font_medium_bold)
title_label.grid(row=1, column=0, padx=20, pady=(10, 15), sticky="w")

# --- Sidebar Buttons ---
settings_btn = ctk.CTkButton(sidebar_frame, text="Settings", command=open_config_window, font=font_base)
settings_btn.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

verify_btn = ctk.CTkButton(sidebar_frame, text="Verify Config", command=lambda: perform_verification(show_results_box=True), font=font_base)
verify_btn.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

# --- Separator --- (Using a thin frame)
separator = ctk.CTkFrame(sidebar_frame, height=1, fg_color="grey50") # Use a theme color or specific hex
separator.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

# --- Spacer Row (takes up weight) ---
# Row 5 is configured with weight=1

unity_down_btn = ctk.CTkButton(sidebar_frame, text="Download Unity", command=lambda: webbrowser.open("unityhub://6000.0.32f1/b2e806cf271c"), font=font_base)
unity_down_btn.grid(row=6, column=0, padx=20, pady=5, sticky="ew")

about_btn = ctk.CTkButton(sidebar_frame, text="About", command=lambda: messagebox.showinfo("About", "Unity Simulation Manager\nVersion 2.0 (CustomTkinter UI)"), font=font_base)
about_btn.grid(row=7, column=0, padx=20, pady=5, sticky="ew")

# --- Exit Button (Pushed down by row 5 weight) ---
exit_btn = ctk.CTkButton(sidebar_frame, text="Exit", command=app.quit, font=font_base,
                         fg_color=COLOR_DANGER, hover_color="#B02A37") # Darker red hover
exit_btn.grid(row=8, column=0, padx=20, pady=(10, 20), sticky="sew") # Stick bottom


# --- Main Content Area ---
main_content_frame = ctk.CTkFrame(app, corner_radius=0, fg_color="transparent") # Transparent BG to show app BG
main_content_frame.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
main_content_frame.grid_columnconfigure(0, weight=1)
main_content_frame.grid_rowconfigure(1, weight=1) # Treeview frame expands

# --- Header ---
header_label = ctk.CTkLabel(main_content_frame, text="Unity Simulation Manager", font=font_large_bold)
header_label.grid(row=0, column=0, padx=10, pady=(0, 15), sticky="w")

# --- Treeview Frame (Container for ttk.Treeview) ---
# Use CTkFrame to contain the ttk Treeview and Scrollbar
tree_container_frame = ctk.CTkFrame(main_content_frame) # Default fg_color from theme
tree_container_frame.grid(row=1, column=0, sticky="nsew")
tree_container_frame.grid_columnconfigure(0, weight=1)
tree_container_frame.grid_rowconfigure(0, weight=1)

# --- Styling the ttk.Treeview to Match CTk ---
# This requires careful color selection based on the CTk theme.
# Let's try to get colors dynamically or use reasonable defaults.
# Get theme colors (this might vary slightly depending on CTk version/theme details)
try:
    ctk_fg_color = app._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
    ctk_text_color = app._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
    ctk_entry_bg_color = app._apply_appearance_mode(ctk.ThemeManager.theme["CTkEntry"]["fg_color"])
    ctk_select_color = app._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"]) # Use button color as selection?
except Exception: # Fallback colors if dynamic fetching fails
    print("Warning: Could not dynamically get CTk theme colors. Using fallback for Treeview.")
    if ctk.get_appearance_mode() == "Dark":
        ctk_fg_color = "#2a2d2e"
        ctk_text_color = "#dce4ee"
        ctk_entry_bg_color = "#343638"
        ctk_select_color = "#1f6aa5"
    else: # Light mode
        ctk_fg_color = "#ebebeb"
        ctk_text_color = "#1f1f1f"
        ctk_entry_bg_color = "#f9f9fa"
        ctk_select_color = "#3b8ed0"

TREE_BG = ctk_entry_bg_color
TREE_FG = ctk_text_color
TREE_FIELD_BG = ctk_entry_bg_color # Background behind text
TREE_SELECT_BG = ctk_select_color
TREE_SELECT_FG = ctk_text_color # Or white/black depending on select_bg contrast
TREE_HEADING_BG = ctk_fg_color
TREE_HEADING_FG = ctk_text_color
TREE_LOADED_BG = "#DFF0D8" if ctk.get_appearance_mode() == "Light" else "#3A5F3A" # Keep light/dark distinct green
TREE_LOADED_FG = "#155724" if ctk.get_appearance_mode() == "Light" else "#D4EDDA"

style = ttk.Style()
# Configure Treeview style (essential for matching look)
style.theme_use("clam") # 'clam' is often best for custom styling ttk
style.configure("Treeview",
                background=TREE_BG,
                foreground=TREE_FG,
                fieldbackground=TREE_FIELD_BG,
                rowheight=28, # Keep row height
                font=(FONT_FAMILY, FONT_SIZE_BASE)) # Match font
style.map("Treeview",
          background=[('selected', TREE_SELECT_BG)],
          foreground=[('selected', TREE_SELECT_FG)])

style.configure("Treeview.Heading",
                font=(FONT_FAMILY, FONT_SIZE_BASE, 'bold'), # Bold heading
                background=TREE_HEADING_BG,
                foreground=TREE_HEADING_FG,
                relief="flat", # Flat look
                padding=(8, 5))
style.map("Treeview.Heading", relief=[('active','groove')]) # Subtle hover/click

# Configure row tags
style.configure('loaded', background=TREE_LOADED_BG, foreground=TREE_LOADED_FG)
# Removed odd/even row styling for cleaner look

# --- Create ttk.Treeview and Scrollbar ---
columns = ("nombre", "creacion", "ultima", "col_loaded", "col_load", "col_delete")
sim_tree = ttk.Treeview(tree_container_frame, columns=columns, show="headings",
                        selectmode="browse", style="Treeview") # Apply the configured style

sim_tree.heading("nombre", text="Simulation Name"); sim_tree.column("nombre", width=300, anchor="w", stretch=tk.YES)
sim_tree.heading("creacion", text="Created"); sim_tree.column("creacion", width=120, anchor="center", stretch=tk.NO)
sim_tree.heading("ultima", text="Last Used"); sim_tree.column("ultima", width=120, anchor="center", stretch=tk.NO)
sim_tree.heading("col_loaded", text=loaded_indicator_text, anchor="center"); sim_tree.column("col_loaded", width=30, stretch=tk.NO, anchor="center")
sim_tree.heading("col_load", text=play_icon_text, anchor="center"); sim_tree.column("col_load", width=45, stretch=tk.NO, anchor="center")
sim_tree.heading("col_delete", text=delete_icon_text, anchor="center"); sim_tree.column("col_delete", width=45, stretch=tk.NO, anchor="center")

# Sorting config (Function is unchanged, just apply commands)
sort_order = {col: False for col in columns if col not in ["col_load", "col_delete", "col_loaded"]}
def sort_column(tree, col, reverse):
    if col in ["col_load", "col_delete", "col_loaded"]: return
    global sort_order; data = [(tree.set(item, col), item) for item in tree.get_children('')]
    def conv_date(v): return 0 if v in ("???", "Never") else time.mktime(time.strptime(v, "%y-%m-%d %H:%M")) if v else 0
    try: data.sort(key=lambda t: conv_date(t[0]) if col in ("creacion", "ultima") else t[0].lower(), reverse=reverse)
    except ValueError: # Handle potential parsing errors
         print(f"Warning: Date conversion error during sort on column '{col}'. Falling back to text sort.")
         data.sort(key=lambda t: t[0].lower(), reverse=reverse)
    except Exception as e:
        print(f"Error during sort: {e}")
        data.sort(key=lambda t: t[0].lower(), reverse=reverse) # Fallback sort
    for i, (_, item) in enumerate(data): tree.move(item, '', i)
    sort_order[col] = reverse
    tree.heading(col, command=lambda c=col: sort_column(tree, c, not reverse))

for col in columns:
    if col not in ["col_load", "col_delete", "col_loaded"]:
        current_heading_text = sim_tree.heading(col)['text']
        sim_tree.heading(col, text=current_heading_text, command=lambda c=col: sort_column(sim_tree, c, False))

sim_tree.grid(row=0, column=0, sticky="nsew")

# Use ttk Scrollbar, as CTkScrollbar doesn't work with ttk.Treeview
tree_scroll = ttk.Scrollbar(tree_container_frame, orient="vertical", command=sim_tree.yview)
tree_scroll.grid(row=0, column=1, sticky="ns")
sim_tree.config(yscrollcommand=tree_scroll.set)

# Event Bindings (Unchanged)
sim_tree.bind('<<TreeviewSelect>>', lambda e: update_button_states())
sim_tree.bind("<Button-1>", handle_tree_click)
sim_tree.bind("<Motion>", handle_tree_motion)
sim_tree.bind("<Leave>", handle_tree_leave)


# --- Bottom Button Frame ---
btn_f_bottom = ctk.CTkFrame(main_content_frame, fg_color="transparent")
btn_f_bottom.grid(row=2, column=0, pady=(15, 5), sticky="ew")
# Center buttons using grid weights
btn_f_bottom.columnconfigure(0, weight=1) # Left spacer
btn_f_bottom.columnconfigure(1, weight=0) # Reload
btn_f_bottom.columnconfigure(2, weight=0) # Graph
btn_f_bottom.columnconfigure(3, weight=0) # Create
btn_f_bottom.columnconfigure(4, weight=1) # Right spacer

reload_btn = ctk.CTkButton(btn_f_bottom, text="Reload List", command=populate_simulations, font=font_base)
reload_btn.grid(row=0, column=1, padx=5, pady=5)

graph_btn = ctk.CTkButton(btn_f_bottom, text="Show Graphs", command=on_show_graphs_thread, font=font_base)
graph_btn.grid(row=0, column=2, padx=5, pady=5)

create_btn = ctk.CTkButton(btn_f_bottom, text="Create Simulation", command=on_create_simulation, font=font_base_bold,
                           fg_color=COLOR_SUCCESS, hover_color="#1E7E34") # Green
create_btn.grid(row=0, column=3, padx=5, pady=5)


# --- Status Bar ---
status_frame = ctk.CTkFrame(app, height=25, corner_radius=0) # Define height
status_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
status_frame.grid_columnconfigure(0, weight=1)

status_label = ctk.CTkLabel(status_frame, text="Initializing...", font=font_small, anchor="w")
status_label.grid(row=0, column=0, padx=10, pady=1, sticky="ew")


# ======================================================
# App Initialization
# ======================================================
if __name__ == "__main__":
    update_status("Initializing and verifying configuration...")
    threading.Thread(target=perform_verification, args=(False, True), daemon=True).start()
    # Initial button states will be set after verification finishes

    def on_closing():
        if is_build_running:
            messagebox.showwarning("Build in Progress", "A build process is running. Please wait for it to finish.")
            return
        if messagebox.askokcancel("Exit Confirmation", "Are you sure you want to exit?", icon='question', default=messagebox.CANCEL):
            update_status("Closing application..."); ensure_unity_closed()
            app.quit() # Use quit for CTk main loop
            app.destroy() # Ensure window is destroyed

    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.mainloop()