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
from openai import error

# ======================================================
# Función para centrar una ventana en la pantalla
# ======================================================
def center_window(window, width, height):
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")

# ======================================================
# Cuadro de diálogo de entrada personalizado
# ======================================================
class CustomInputDialog(tk.Toplevel):
    def __init__(self, parent, title, prompt, width=400, height=150, font=("Segoe UI", 12)):
        super().__init__(parent)
        self.title(title)
        # Centrar la ventana en la pantalla
        center_window(self, width, height)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = None

        # Estilo y layout
        self.configure(bg="white")
        prompt_label = ttk.Label(self, text=prompt, font=font)
        prompt_label.pack(pady=(20, 10), padx=20)

        self.entry = ttk.Entry(self, font=font)
        self.entry.pack(pady=5, padx=20, fill="x")
        
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)
        ok_button = ttk.Button(button_frame, text="Aceptar", command=self.ok)
        ok_button.pack(side="left", padx=5)
        cancel_button = ttk.Button(button_frame, text="Cancelar", command=self.cancel)
        cancel_button.pack(side="left", padx=5)

        self.bind("<Return>", lambda event: self.ok())
        self.bind("<Escape>", lambda event: self.cancel())
        self.entry.focus()
        self.wait_window(self)

    def ok(self):
        self.result = self.entry.get()
        self.destroy()

    def cancel(self):
        self.destroy()

def custom_askstring(title, prompt):
    dialog = CustomInputDialog(main_window, title, prompt)
    return dialog.result

# ======================================================
# Cargar configuración desde .env y verificar versión
# ======================================================
load_dotenv('.env')

UNITY_EXECUTABLE = os.environ.get("UNITY_EXECUTABLE")
UNITY_PROJECTS_PATH = os.environ.get("UNITY_PROJECTS_PATH")

if not UNITY_EXECUTABLE or not UNITY_PROJECTS_PATH:
    messagebox.showerror("Error de Configuración", 
                         "No se encontraron las variables UNITY_EXECUTABLE o UNITY_PROJECTS_PATH en el archivo .env")
    exit(1)

required_version = "6000.0.32f1"
if required_version not in UNITY_EXECUTABLE:
    respuesta = messagebox.askyesno("Versión de Unity incorrecta",
                                    f"La versión del editor especificada en UNITY_EXECUTABLE no es {required_version}.\n¿Desea modificar el PATH del editor?")
    if respuesta:
        nuevo_path = filedialog.askopenfilename(title=f"Seleccione Unity.exe versión {required_version}",
                                                  filetypes=[("Unity Executable", "*.exe")])
        if nuevo_path and required_version in nuevo_path:
            UNITY_EXECUTABLE = nuevo_path
        else:
            messagebox.showerror("Error", 
                f"El ejecutable seleccionado no es la versión requerida ({required_version}). Se abortará la ejecución.")
            exit(1)
    else:
        messagebox.showerror("Error", 
            f"Modifique la variable UNITY_EXECUTABLE a la versión {required_version}.")
        exit(1)

# ======================================================
# Definición de rutas y variables globales
# ======================================================
SIMULATIONS_DIR = "./Simulations"
SIMULATION_PROJECT_NAME = "Simulacion"
SIMULATION_PROJECT_PATH = os.path.join(UNITY_PROJECTS_PATH, SIMULATION_PROJECT_NAME)
ASSETS_FOLDER = os.path.join(SIMULATION_PROJECT_PATH, "Assets")
STREAMING_ASSETS_FOLDER = os.path.join(ASSETS_FOLDER, "StreamingAssets")
SIMULATION_LOADED_FILE = os.path.join(STREAMING_ASSETS_FOLDER, "simulation_loaded.txt")
last_simulation_loaded = None

# ======================================================
# Función para cerrar Unity si está abierto
# ======================================================
def ensure_unity_closed():
    unity_processes = []
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            exe = proc.info.get('exe', '')
            if exe and os.path.normcase(exe) == os.path.normcase(UNITY_EXECUTABLE):
                unity_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    if unity_processes:
        update_status("Unity se detectó abierto. Cerrándolo, por favor espere...")
        for proc in unity_processes:
            try:
                proc.terminate()
            except Exception as e:
                print(f"Error al terminar el proceso: {e}")
        psutil.wait_procs(unity_processes, timeout=5)
        update_status("Unity ha sido cerrado.")

# ======================================================
# Función para abrir la carpeta de gráficos
# ======================================================
def open_graphs_folder(simulation_name):
    folder_path = Path.home() / "Documents" / "SimulationLoggerData" / simulation_name / "Graficos"
    if not folder_path.exists():
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear la carpeta de gráficos:\n{e}")
            return
    try:
        if platform.system() == "Windows":
            subprocess.Popen(["explorer", str(folder_path)])
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", str(folder_path)])
        else:
            subprocess.Popen(["xdg-open", str(folder_path)])
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo abrir la carpeta de gráficos:\n{e}")

# ======================================================
# Funciones para deshabilitar y habilitar botones
# ======================================================
def disable_all_buttons():
    reload_btn.config(state="disabled")
    cargar_btn.config(state="disabled")
    graph_btn.config(state="disabled")
    delete_btn.config(state="disabled")
    create_btn.config(state="disabled")

def enable_all_buttons():
    reload_btn.config(state="normal")
    cargar_btn.config(state="normal")
    graph_btn.config(state="normal")
    delete_btn.config(state="normal")
    create_btn.config(state="normal")

# ======================================================
# Función para crear simulación (llama a api_manager.py)
# ======================================================
def on_create_simulation():
    simulation_name = custom_askstring("Crear Simulación", "Ingrese el nombre de la simulación:")
    if not simulation_name:
        update_status("Creación de simulación cancelada.")
        return
    simulation_name = simulation_name.strip()
    simulation_path = os.path.join(SIMULATIONS_DIR, simulation_name)
    if os.path.exists(simulation_path):
        messagebox.showerror("Error", f"Ya existe una simulación con el nombre '{simulation_name}'. Por favor, elija otro nombre.")
        update_status("Simulación no creada. Nombre duplicado.")
        return
    simulation_description = custom_askstring("Descripción de la Simulación", "Describe la simulación:")
    if not simulation_description:
        update_status("Creación de simulación cancelada. Se requiere una descripción.")
        return
    threading.Thread(target=create_simulation, args=(simulation_name, simulation_description), daemon=True).start()

def create_simulation(simulation_name, simulation_description):
    update_status("Creando simulación, por favor espere...")
    disable_all_buttons()
    try:
        result = subprocess.run(
            [sys.executable, "./Scripts/api_manager.py", simulation_name, simulation_description],
            check=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        update_status("Simulación creada exitosamente.")
        messagebox.showinfo("Éxito", "Simulación creada exitosamente.")
        populate_simulations()
        
    except subprocess.CalledProcessError as e:
        error_msg = ""
        error_details = ""
        
        # Capturar salida de errores
        error_output = e.stderr if e.stderr else e.stdout
        
        # Mapear códigos de error
        if e.returncode == 7:
            error_msg = "ERROR DE CONTENIDO"
            error_details = "La simulación debe ser referente exclusivamente a:\n- E.Coli (Bacteria)\n- S.Cerevisiae (Levadura)"
        elif e.returncode == 1:
            if "ya existe" in error_output:
                error_msg = "SIMULACIÓN DUPLICADA"
                error_details = f"Ya existe una simulación con el nombre: '{simulation_name}'"
            elif "formato de pregunta" in error_output.lower():
                error_msg = "ERROR DE FORMATEO"
                error_details = "La pregunta no sigue el formato requerido\n\nEjemplo válido:\n'Simular 2 bacterias E.Coli rojas que se duplican cada 5 minutos'"
            else:
                error_msg = "ERROR EN EL PROCESO"
                error_details = f"Error durante la creación:\n{error_output}"
        else:
            error_msg = "ERROR DESCONOCIDO"
            error_details = f"Código de error: {e.returncode}\n{error_output}"
        
        # Mostrar mensaje completo
        full_error = f"{error_msg}\n\n{error_details}"
        messagebox.showerror("Error en la Simulación", full_error)
        update_status(error_msg)
        
    except Exception as e:
        error_msg = f"ERROR CRÍTICO: {str(e)}"
        messagebox.showerror("Error Inesperado", error_msg)
        update_status("Error crítico")
        
    finally:
        enable_all_buttons()

# ======================================================
# Función para monitorear el tamaño de carpeta para el tool de prefabs
# ======================================================
def monitor_progress_prefab_tool(stop_event):
    while not stop_event.is_set():
        size_bytes = get_folder_size(SIMULATION_PROJECT_PATH)
        size_mb = size_bytes / (1024 * 1024)
        update_status(f"[Prefabs] Tamaño actual del directorio: {size_mb:.2f} MB")
        time.sleep(2)

def run_prefab_material_tool():
    log_file = os.path.join(SIMULATION_PROJECT_PATH, "prefab_tool_log.txt")
    command = [
        UNITY_EXECUTABLE,
        "-batchmode",
        "-quit",
        "-projectPath", os.path.normpath(SIMULATION_PROJECT_PATH),
        "-executeMethod", "PrefabMaterialCreator.CreatePrefabsAndMaterials",
        "-logFile", log_file
    ]
    progress_stop_event = threading.Event()
    monitor_thread = threading.Thread(target=monitor_progress_prefab_tool, args=(progress_stop_event,), daemon=True)
    monitor_thread.start()
    try:
        update_status("Ejecutando la herramienta de prefabs y materiales...")
        subprocess.run(command, check=True)
        update_status("La herramienta de prefabs y materiales se ejecutó correctamente.")
    except subprocess.CalledProcessError as e:
        update_status(f"[Error] Ocurrió un error al ejecutar la herramienta de prefabs: {e}")
    progress_stop_event.set()
    monitor_thread.join()

# ======================================================
# Funciones auxiliares para metadatos de simulaciones
# ======================================================
def get_simulations():
    simulations = []
    if not os.path.exists(SIMULATIONS_DIR):
        messagebox.showerror("Error", f"No se encontró la carpeta {SIMULATIONS_DIR}")
        return simulations
    for item in os.listdir(SIMULATIONS_DIR):
        sim_path = os.path.join(SIMULATIONS_DIR, item)
        if os.path.isdir(sim_path):
            required = ["Assets", "Packages", "ProjectSettings"]
            if all(os.path.exists(os.path.join(sim_path, req)) for req in required):
                try:
                    creation_ts = os.path.getctime(sim_path)
                    creation_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(creation_ts))
                except Exception:
                    creation_ts = 0
                    creation_str = "Desconocido"
                last_opened_file = os.path.join(sim_path, "last_opened.txt")
                if os.path.exists(last_opened_file):
                    try:
                        with open(last_opened_file, "r") as f:
                            last_ts = float(f.read().strip())
                        last_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_ts))
                    except Exception:
                        last_ts = 0
                        last_str = "Desconocido"
                else:
                    last_ts = 0
                    last_str = "Nunca"
                simulations.append({
                    "name": item,
                    "creation_ts": creation_ts,
                    "creation": creation_str,
                    "last_opened_ts": last_ts,
                    "last_opened": last_str
                })
    return simulations

def update_last_opened(simulation_name):
    sim_folder = os.path.join(SIMULATIONS_DIR, simulation_name)
    timestamp = time.time()
    try:
        with open(os.path.join(sim_folder, "last_opened.txt"), "w") as f:
            f.write(str(timestamp))
    except Exception as e:
        print(f"[Error] No se pudo actualizar el last_opened: {e}")

def copy_directory(src, dst):
    try:
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print(f"Copiado {src} a {dst}")
    except Exception as e:
        messagebox.showerror("Error", f"Error al copiar {src} a {dst}:\n{e}")

def load_simulation(simulation_name, first_time=True):
    global last_simulation_loaded
    sim_source_path = os.path.join(SIMULATIONS_DIR, simulation_name)
    if not os.path.exists(sim_source_path):
        messagebox.showerror("Error", f"La simulación '{simulation_name}' no existe.")
        return False
    if not os.path.exists(SIMULATION_PROJECT_PATH):
        os.makedirs(SIMULATION_PROJECT_PATH)
    if first_time:
        for carpeta in ["Assets", "Packages", "ProjectSettings"]:
            src = os.path.join(sim_source_path, carpeta)
            dst = os.path.join(SIMULATION_PROJECT_PATH, carpeta)
            copy_directory(src, dst)
    else:
        for carpeta in ["Build", "Assets"]:
            path = os.path.join(SIMULATION_PROJECT_PATH, carpeta)
            if os.path.exists(path):
                shutil.rmtree(path)
        src_assets = os.path.join(sim_source_path, "Assets")
        dst_assets = os.path.join(SIMULATION_PROJECT_PATH, "Assets")
        copy_directory(src_assets, dst_assets)
    update_last_opened(simulation_name)
    if not os.path.exists(STREAMING_ASSETS_FOLDER):
        try:
            os.makedirs(STREAMING_ASSETS_FOLDER, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear la carpeta StreamingAssets:\n{e}")
            return False
    try:
        with open(SIMULATION_LOADED_FILE, "w") as f:
            f.write(simulation_name)
    except Exception as e:
        print(f"[Error] No se pudo escribir en simulation_loaded.txt: {e}")
    last_simulation_loaded = simulation_name
    return True

def get_build_target_and_executable(project_path):
    sistema = platform.system()
    if sistema == "Windows":
        build_target = "Win64"
        ejecutable = os.path.join(project_path, "Build", "Windows", "Simulation.exe")
    elif sistema == "Linux":
        build_target = "Linux64"
        ejecutable = os.path.join(project_path, "Build", "Linux", "Simulation")
    elif sistema == "Darwin":
        build_target = "OSXUniversal"
        ejecutable = os.path.join(project_path, "Build", "Mac", "Simulation.app")
    else:
        build_target = "Win64"
        ejecutable = os.path.join(project_path, "Build", "Windows", "Simulation.exe")
    return build_target, ejecutable

def update_status(message):
    main_window.after(0, lambda: status_label.config(text=message))

def get_folder_size(path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            fp = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(fp)
            except Exception:
                pass
    return total_size

def monitor_progress(stop_event):
    while not stop_event.is_set():
        size_bytes = get_folder_size(SIMULATION_PROJECT_PATH)
        size_mb = size_bytes / (1024 * 1024)
        update_status(f"[Build] Tamaño actual del directorio: {size_mb:.2f} MB")
        time.sleep(2)

def build_simulation_threaded(callback=None):
    build_target, _ = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
    log_file = os.path.join(SIMULATION_PROJECT_PATH, "build_log.txt")
    command = [
        UNITY_EXECUTABLE,
        "-batchmode",
        "-quit",
        "-projectPath", os.path.normpath(SIMULATION_PROJECT_PATH),
        "-executeMethod", "BuildScript.PerformBuild",
        "-buildTarget", build_target,
        "-logFile", log_file
    ]
    max_retries = 2
    success = False

    progress_stop_event = threading.Event()
    monitor_thread = threading.Thread(target=monitor_progress, args=(progress_stop_event,), daemon=True)
    monitor_thread.start()

    for attempt in range(max_retries):
        try:
            update_status(f"[Build] Ejecutando compilación (Intento {attempt + 1} de {max_retries})...")
            subprocess.run(command, check=True)
            update_status("[Build] Compilación completada exitosamente.")
            success = True
            break
        except subprocess.CalledProcessError as e:
            update_status(f"[Error] Falló la compilación (Intento {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                update_status("[Build] Reintentando en 30 segundos...")
                time.sleep(30)
    progress_stop_event.set()
    monitor_thread.join()

    if not success:
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                log_contents = f.read()
        except Exception:
            log_contents = ""
        if "executeMethod class 'BuildScript' could not be found" in log_contents:
            messagebox.showerror("Error en el Build",
                "La compilación falló: no se encontró el método BuildScript.PerformBuild.\n"
                "Verifique que exista un script (por ejemplo, en Assets/Editor) con un método estático 'PerformBuild'.\n\n"
                f"Revise el log: {log_file}")
        else:
            messagebox.showerror("Error en el Build", f"La compilación falló. Revise el log: {log_file}")
        update_status("[Build] Compilación fallida.")
    if callback:
        main_window.after(0, lambda: callback(success))

def open_simulation_executable():
    _, ejecutable = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
    if os.path.exists(ejecutable):
        try:
            if platform.system() == "Darwin":
                subprocess.Popen(["open", ejecutable])
            else:
                subprocess.Popen([ejecutable])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo ejecutar el build:\n{e}")
    else:
        messagebox.showerror("Error", f"No se encontró el ejecutable en:\n{ejecutable}")

def open_in_unity():
    try:
        subprocess.Popen([UNITY_EXECUTABLE, "-projectPath", os.path.normpath(SIMULATION_PROJECT_PATH)])
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo abrir el proyecto en Unity:\n{e}")

def delete_simulation(simulation_name):
    confirm = messagebox.askyesno("Confirmación",
        f"¿Está seguro que desea eliminar la simulación '{simulation_name}'?\n"
        "Esta acción eliminará permanentemente los archivos de la carpeta de simulación y sus datos de estadísticas.")
    if not confirm:
        update_status("Eliminación cancelada.")
        return

    # Verificar si la simulación a eliminar es la que está cargada
    if os.path.exists(SIMULATION_LOADED_FILE):
        try:
            with open(SIMULATION_LOADED_FILE, 'r') as f:
                loaded_sim = f.read().strip()
            if loaded_sim == simulation_name:
                os.remove(SIMULATION_LOADED_FILE)
                update_status(f"Archivo de simulación cargada eliminado: {SIMULATION_LOADED_FILE}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al verificar/eliminar simulation_loaded.txt: {str(e)}")
            return

    sim_path = os.path.join(SIMULATIONS_DIR, simulation_name)
    if os.path.exists(sim_path):
        try:
            shutil.rmtree(sim_path)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar la carpeta de la simulación en {sim_path}:\n{e}")
            return
    documents_path = Path.home() / "Documents"
    data_path = documents_path / "SimulationLoggerData" / simulation_name
    if data_path.exists():
        try:
            shutil.rmtree(data_path)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar la carpeta de datos en {data_path}:\n{e}")
            return

    update_status(f"La simulación '{simulation_name}' fue eliminada correctamente.")
    populate_simulations()

# ======================================================
# Ventana de Configuración
# ======================================================
def open_config_window():
    config_win = tk.Toplevel(main_window)
    config_win.title("Configuración")
    center_window(config_win, 600, 300)
    config_win.resizable(False, False)
    
    main_config_frame = ttk.Frame(config_win, padding=20)
    main_config_frame.pack(fill="both", expand=True)
    
    # Sección de rutas
    paths_frame = ttk.LabelFrame(main_config_frame, text="Configuración de Rutas", padding=10)
    paths_frame.pack(fill="x", pady=5)
    
    def create_path_row(parent, label, env_var, is_file=True):
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill="x", pady=5)
        
        ttk.Label(row_frame, text=label, width=20).pack(side="left")
        entry = ttk.Entry(row_frame, width=50)
        
        # Insertar valor y bloquear edición manual
        entry.insert(0, os.environ.get(env_var, ""))
        entry.config(state="readonly")
        entry.pack(side="left", padx=5)
        
        def browse():
            if is_file:
                path = filedialog.askopenfilename(title=f"Seleccionar {label}")
            else:
                path = filedialog.askdirectory(title=f"Seleccionar {label}")
            if path:
                # Habilitar temporalmente para actualizar
                entry.config(state="normal")
                entry.delete(0, tk.END)
                entry.insert(0, path)
                entry.config(state="readonly")
        
        ttk.Button(row_frame, text="Examinar", command=browse).pack(side="left")
        return entry
    
    unity_exe_entry = create_path_row(paths_frame, "Unity Executable", "UNITY_EXECUTABLE", is_file=True)
    projects_path_entry = create_path_row(paths_frame, "Proyectos Unity", "UNITY_PROJECTS_PATH", is_file=False)
    
    # Función de verificación completa
    def verify_all():
        results = []
        
        # Verificar Unity
        unity_path = unity_exe_entry.get()
        if not os.path.exists(unity_path):
            results.append("❌ Ruta de Unity no existe")
        else:
            if "6000.0.32f1" in unity_path:
                results.append("✅ Versión de Unity correcta")
            else:
                results.append("❌ Versión de Unity incorrecta (requerida 6000.0.32f1)")
        
        # Verificar APIs
        try:
            openai.api_key = os.getenv("OPENAI_API_KEY")
            
            # Verificar conexión API
            try:
                openai.Model.list()
                results.append("✅ OpenAI API funciona")
            except openai.error.AuthenticationError:
                results.append("❌ OpenAI API: API Key inválida")
            except Exception as e:
                results.append(f"❌ Error OpenAI API: {str(e)}")
            
            # Verificar modelos
            models_to_check = [
                ("Principal", os.getenv("FINE_TUNED_MODEL_NAME")),
                ("Secundario", os.getenv("2ND_FINE_TUNED_MODEL_NAME"))
            ]
            
            for name, model in models_to_check:
                try:
                    openai.Model.retrieve(model)
                    results.append(f"✅ Modelo {name} válido")
                except openai.error.InvalidRequestError:
                    results.append(f"❌ Modelo {name} no encontrado")
                except Exception as e:
                    results.append(f"❌ Error modelo {name}: {str(e)}")
                    
        except Exception as e:
            results.append(f"❌ Error general: {str(e)}")
        
        # Mostrar resultados
        result_text = "\n".join(results)
        messagebox.showinfo("Resultado de Verificaciones", result_text)
        config_win.destroy()
    
    # Botones
    button_frame = ttk.Frame(main_config_frame)
    button_frame.pack(pady=10)
    
    ttk.Button(button_frame, text="Verificar Todo", command=verify_all).pack(side="left", padx=5)
    
    def save_config():
        new_config = {
            "UNITY_EXECUTABLE": unity_exe_entry.get(),
            "UNITY_PROJECTS_PATH": projects_path_entry.get()
        }
        
        # Validar rutas
        errors = []
        if not os.path.exists(new_config["UNITY_EXECUTABLE"]):
            errors.append("La ruta de Unity no es válida")
        if not os.path.isdir(new_config["UNITY_PROJECTS_PATH"]):
            errors.append("La ruta de proyectos no es válida")
        
        if errors:
            messagebox.showerror("Errores", "\n".join(errors))
            return
        
        # Mantener las variables existentes de API
        env_vars = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "FINE_TUNED_MODEL_NAME": os.getenv("FINE_TUNED_MODEL_NAME", ""),
            "2ND_FINE_TUNED_MODEL_NAME": os.getenv("2ND_FINE_TUNED_MODEL_NAME", "")
        }
        
        try:
            with open(".env", "w") as f:
                f.write(f"UNITY_EXECUTABLE = {new_config['UNITY_EXECUTABLE']}\n")
                f.write(f"UNITY_PROJECTS_PATH = {new_config['UNITY_PROJECTS_PATH']}\n")
                for key, value in env_vars.items():
                    f.write(f"{key} = {value}\n")
            
            load_dotenv('.env', override=True)
            messagebox.showinfo("Éxito", "Configuración guardada correctamente")
            config_win.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar: {str(e)}")
    
    ttk.Button(button_frame, text="Guardar", command=save_config).pack(side="left", padx=5)
# ======================================================
# INTERFAZ GRÁFICA (GUI)
# ======================================================
main_window = tk.Tk()
main_window.iconbitmap("icono.ico")
main_window.title("Gestor de Simulaciones de Unity")
center_window(main_window, 700, 500)
main_window.resizable(False, False)

style = ttk.Style(main_window)
style.theme_use("clam")
style.configure("TButton", font=("Segoe UI", 10))
style.configure("Info.TButton", foreground="white", background="#5B6EE1")
style.map("Info.TButton", background=[("active", "#4759c7")])
style.configure("Success.TButton", foreground="white", background="#4CAF50")
style.map("Success.TButton", background=[("active", "#43A047")])
style.configure("Danger.TButton", foreground="white", background="#F44336")
style.map("Danger.TButton", background=[("active", "#E53935")])
style.configure("Graph.TButton", foreground="white", background="#009688")
style.map("Graph.TButton", background=[("active", "#00796B")])
style.configure("Reload.TButton", foreground="white", background="#9C27B0")
style.map("Reload.TButton", background=[("active", "#7B1FA2")])

menubar = tk.Menu(main_window)
archivo_menu = tk.Menu(menubar, tearoff=0)
archivo_menu.add_command(label="Salir", command=main_window.destroy)
menubar.add_cascade(label="Archivo", menu=archivo_menu)
ayuda_menu = tk.Menu(menubar, tearoff=0)
ayuda_menu.add_command(label="Descargar versión de Unity Editor",command=lambda: subprocess.Popen(["start", "unityhub://6000.0.32f1/b2e806cf271c"], shell=True))
ayuda_menu.add_command(label="Acerca de", command=lambda: messagebox.showinfo("Acerca de", "Gestor de Simulaciones de Unity\nVersión 1.0"))
menubar.add_cascade(label="Ayuda", menu=ayuda_menu)
main_window.config(menu=menubar)

header_frame = ttk.Frame(main_window, padding=(10, 10))
header_frame.pack(fill="x")
header_label = ttk.Label(header_frame, text="Gestor de Simulaciones de Unity", font=("Segoe UI", 20, "bold"), foreground="#2C3E50")
header_label.pack(side="top")

main_frame = ttk.Frame(main_window, padding=10)
main_frame.pack(expand=True, fill="both")

select_label = ttk.Label(main_frame, text="Seleccione una simulación:", font=("Segoe UI", 14))
select_label.pack(pady=(10, 5))

tree_frame = ttk.Frame(main_frame)
tree_frame.pack(fill="both", expand=True, padx=20, pady=10)

columns = ("nombre", "creacion", "ultima")
sim_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse", height=10)
sim_tree.heading("nombre", text="Simulación")
sim_tree.heading("creacion", text="Fecha de Creación")
sim_tree.heading("ultima", text="Última Apertura")
sim_tree.column("nombre", width=200, anchor="w")
sim_tree.column("creacion", width=180, anchor="center")
sim_tree.column("ultima", width=180, anchor="center")

def sort_column(tree, col, reverse):
    l = [(tree.set(k, col), k) for k in tree.get_children('')]
    if col in ("creacion", "ultima"):
        def conv(val):
            try:
                return time.mktime(time.strptime(val, "%Y-%m-%d %H:%M:%S"))
            except Exception:
                return 0
        l.sort(key=lambda t: conv(t[0]), reverse=reverse)
    else:
        l.sort(reverse=reverse)
    for index, (val, k) in enumerate(l):
        tree.move(k, '', index)
    tree.heading(col, command=lambda: sort_column(tree, col, not reverse))

for col in columns:
    sim_tree.heading(col, command=lambda c=col: sort_column(sim_tree, c, False))

sim_tree.pack(side="left", fill="both", expand=True)

scrollbar_tree = ttk.Scrollbar(tree_frame, orient="vertical", command=sim_tree.yview)
scrollbar_tree.pack(side="right", fill="y")
sim_tree.config(yscrollcommand=scrollbar_tree.set)

button_frame = ttk.Frame(main_frame)
button_frame.pack(pady=10)

reload_btn = ttk.Button(button_frame, text="Recargar Lista", style="Reload.TButton", command=lambda: populate_simulations())
reload_btn.pack(side="left", padx=5)

cargar_btn = ttk.Button(button_frame, text="Cargar Simulación", style="Info.TButton",
                          command=lambda: threading.Thread(target=on_load_simulation, daemon=True).start())
cargar_btn.pack(side="left", padx=5)

graph_btn = ttk.Button(button_frame, text="Mostrar Gráficos", style="Graph.TButton",
                         command=lambda: threading.Thread(target=on_show_graphs, daemon=True).start())
graph_btn.pack(side="left", padx=5)

delete_btn = ttk.Button(button_frame, text="Eliminar Simulación", style="Danger.TButton",
                          command=lambda: on_delete_simulation())
delete_btn.pack(side="left", padx=5)

create_btn = ttk.Button(button_frame, text="Crear Simulación", style="Success.TButton",
                          command=on_create_simulation)
create_btn.pack(side="left", padx=5)

config_btn = ttk.Button(button_frame, text="Configuración", style="Info.TButton",
                        command=open_config_window)
config_btn.pack(side="left", padx=5)

status_frame = ttk.Frame(main_window)
status_frame.pack(fill="x", side="bottom")
status_label = ttk.Label(status_frame, text="Seleccione una simulación para comenzar.", relief="sunken", anchor="w", font=("Segoe UI", 10))
status_label.pack(fill="x")

def populate_simulations():
    sim_tree.delete(*sim_tree.get_children())
    simulations = get_simulations()
    if not simulations:
        messagebox.showerror("Error", "No se encontraron simulaciones en la carpeta './Simulations'.")
    else:
        for sim in simulations:
            sim_tree.insert("", "end", values=(sim["name"], sim["creation"], sim["last_opened"]))
    update_status("Lista de simulaciones actualizada.")

def on_load_simulation():
    selected = sim_tree.selection()
    if not selected:
        messagebox.showwarning("Advertencia", "Por favor, seleccione una simulación de la lista.")
        return
    simulation_name = sim_tree.item(selected[0], "values")[0]
    global last_simulation_loaded

    if os.path.exists(SIMULATION_LOADED_FILE):
        try:
            with open(SIMULATION_LOADED_FILE, "r") as f:
                loaded_sim = f.read().strip()
        except Exception:
            loaded_sim = ""
        if loaded_sim == simulation_name:
            update_last_opened(simulation_name)
            update_status("La simulación seleccionada ya está cargada. Mostrando opciones disponibles...")
            main_window.after(500, show_options_window)
            return

    ensure_unity_closed()

    update_status("Cargando la simulación, por favor espere...")
    if not os.path.exists(SIMULATION_PROJECT_PATH):
        messagebox.showinfo("Aviso",
            "Esta es la primera vez que se carga la simulación.\n"
            "Se creará el ambiente de la simulación, lo que puede tardar unos minutos.")
    reload_btn.config(state="disabled")
    cargar_btn.config(state="disabled")
    sim_tree.config(selectmode="none")

    first_time = (last_simulation_loaded is None)
    if load_simulation(simulation_name, first_time):
        run_prefab_material_tool()
        build_simulation_threaded(callback=build_callback)
    else:
        update_status("Error al cargar la simulación.")
        reload_btn.config(state="normal")
        cargar_btn.config(state="normal")
        sim_tree.config(selectmode="browse")

def build_callback(success):
    if success:
        show_options_window()
    reload_btn.config(state="normal")
    cargar_btn.config(state="normal")
    sim_tree.config(selectmode="browse")

def on_show_graphs():
    selected = sim_tree.selection()
    if not selected:
        messagebox.showwarning("Advertencia", "Seleccione una simulación para visualizar sus gráficos.")
        return
    simulation_name = sim_tree.item(selected[0], "values")[0]
    update_status("Generando gráficos, por favor espere...")
    
    documents_path = Path.home() / "Documents"
    csv_path = documents_path / "SimulationLoggerData" / simulation_name / "SimulationStats.csv"
    if not csv_path.exists():
        messagebox.showerror("Error", f"[Error] No se encontró el archivo CSV en:\n{csv_path}")
        update_status(f"[Error] No se encontró el archivo CSV en: {csv_path}")
        return
    
    simulation_graphics_path = os.path.join(SIMULATIONS_DIR, simulation_name, "Assets", "Scripts", "SimulationData", "SimulationGraphics.py")
    if not os.path.exists(simulation_graphics_path):
        messagebox.showerror("Error", f"No se encontró el script de gráficos en:\n{simulation_graphics_path}")
        update_status("Error: Script de gráficos no encontrado.")
        return
    try:
        subprocess.Popen([sys.executable, simulation_graphics_path, simulation_name])
        update_status("Los gráficos se están generando. Revise la carpeta correspondiente en Documents.")
        open_graphs_folder(simulation_name)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudieron generar los gráficos:\n{e}")
        update_status("Error al generar los gráficos.")

def on_delete_simulation():
    selected = sim_tree.selection()
    if not selected:
        messagebox.showwarning("Advertencia", "Seleccione una simulación para eliminarla.")
        return
    simulation_name = sim_tree.item(selected[0], "values")[0]
    delete_simulation(simulation_name)

def show_options_window():
    options_win = tk.Toplevel(main_window)
    options_win.title("Opciones Post-Build")
    center_window(options_win, 400, 300)
    options_win.resizable(False, False)
    
    options_frame = ttk.Frame(options_win, padding=20)
    options_frame.pack(expand=True, fill="both")
    
    info_label = ttk.Label(options_frame, text="¿Qué desea hacer a continuación?", font=("Segoe UI", 14))
    info_label.pack(pady=10)
    
    btn_ejecutar = ttk.Button(options_frame, text="Ejecutar Build", command=open_simulation_executable)
    btn_ejecutar.pack(pady=5, fill="x")
    
    btn_abrir = ttk.Button(options_frame, text="Abrir en Unity", command=open_in_unity)
    btn_abrir.pack(pady=5, fill="x")
    
    btn_nueva = ttk.Button(options_frame, text="Cargar Otra Simulación",
                            command=lambda: (options_win.destroy(), update_status("Seleccione otra simulación.")))
    btn_nueva.pack(pady=5, fill="x")
    
    btn_salir = ttk.Button(options_frame, text="Salir", command=main_window.destroy)
    btn_salir.pack(pady=5, fill="x")
    
    update_status("Opciones disponibles.")

populate_simulations()
main_window.mainloop()
