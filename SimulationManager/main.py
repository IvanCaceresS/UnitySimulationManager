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
# El archivo simulation_loaded.txt se guardará en:
# SIMULATION_PROJECT_PATH/Assets/StreamingAssets/simulation_loaded.txt
ASSETS_FOLDER = os.path.join(SIMULATION_PROJECT_PATH, "Assets")
STREAMING_ASSETS_FOLDER = os.path.join(ASSETS_FOLDER, "StreamingAssets")
SIMULATION_LOADED_FILE = os.path.join(STREAMING_ASSETS_FOLDER, "simulation_loaded.txt")
last_simulation_loaded = None

# ======================================================
# Función para abrir la carpeta de gráficos
# ======================================================
def open_graphs_folder(simulation_name):
    folder_path = Path.home() / "Documents" / "SimulationLoggerData" / simulation_name / "Graficos"
    if folder_path.exists():
        try:
            if platform.system() == "Windows":
                subprocess.Popen(["explorer", str(folder_path)])
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(folder_path)])
            else:
                subprocess.Popen(["xdg-open", str(folder_path)])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta de gráficos:\n{e}")
    else:
        messagebox.showerror("Error", f"La carpeta de gráficos no existe: {folder_path}")

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
# Función para crear simulación (llama a CreateSimulation.py)
# ======================================================
def on_create_simulation():
    update_status("Creando simulación, por favor espere...")
    disable_all_buttons()
    try:
        subprocess.run(["python", "./Scripts/CreateSimulation.py"], check=True)
        update_status("Simulación creada exitosamente.")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Error al crear simulación:\n{e}")
        update_status("Error al crear simulación.")
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
    # Asegurarse de que la carpeta StreamingAssets exista (después de copiar Assets)
    if not os.path.exists(STREAMING_ASSETS_FOLDER):
        try:
            os.makedirs(STREAMING_ASSETS_FOLDER, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear la carpeta StreamingAssets:\n{e}")
            return False
    # Escribir simulation_loaded.txt en StreamingAssets
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

    # Eliminar carpeta en SIMULATIONS_DIR
    sim_path = os.path.join(SIMULATIONS_DIR, simulation_name)
    if os.path.exists(sim_path):
        try:
            shutil.rmtree(sim_path)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar la carpeta de la simulación en {sim_path}:\n{e}")
            return
    # Eliminar carpeta de datos en Documents/SimulationLoggerData
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
# INTERFAZ GRÁFICA (GUI)
# ======================================================
main_window = tk.Tk()
main_window.title("Gestor de Simulaciones de Unity")
main_window.geometry("700x500")
main_window.resizable(False, False)

# Configuración de estilos personalizados para botones
style = ttk.Style(main_window)
style.theme_use("clam")
style.configure("TButton", font=("Segoe UI", 10))
style.configure("Info.TButton", foreground="white", background="#5B6EE1")      # Azul (Cargar simulación)
style.map("Info.TButton", background=[("active", "#4759c7")])
style.configure("Success.TButton", foreground="white", background="#4CAF50")   # Verde (Crear simulación)
style.map("Success.TButton", background=[("active", "#43A047")])
style.configure("Danger.TButton", foreground="white", background="#F44336")    # Rojo (Eliminar simulación)
style.map("Danger.TButton", background=[("active", "#E53935")])
style.configure("Graph.TButton", foreground="white", background="#009688")     # Teal (Mostrar gráficos)
style.map("Graph.TButton", background=[("active", "#00796B")])
style.configure("Reload.TButton", foreground="white", background="#9C27B0")    # Morado (Recargar lista)
style.map("Reload.TButton", background=[("active", "#7B1FA2")])

menubar = tk.Menu(main_window)
archivo_menu = tk.Menu(menubar, tearoff=0)
archivo_menu.add_command(label="Salir", command=main_window.destroy)
menubar.add_cascade(label="Archivo", menu=archivo_menu)
ayuda_menu = tk.Menu(menubar, tearoff=0)
ayuda_menu.add_command(label="Acerca de", command=lambda: messagebox.showinfo("Acerca de", "Gestor de Simulaciones de Unity\nVersión 1.0"))
menubar.add_cascade(label="Ayuda", menu=ayuda_menu)
main_window.config(menu=menubar)

header_frame = ttk.Frame(main_window, padding=(10, 10))
header_frame.pack(fill="x")
header_label = ttk.Label(header_frame, text="Gestor de Simulaciones de Unity", font=("Segoe UI", 20, "bold"), foreground="#2C3E50")
header_label.pack(side="left")

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
                          command=lambda: threading.Thread(target=on_create_simulation, daemon=True).start())
create_btn.pack(side="left", padx=5)

status_frame = ttk.Frame(main_window)
status_frame.pack(fill="x", side="bottom")
status_label = ttk.Label(status_frame, text="Seleccione una simulación para comenzar.", relief="sunken", anchor="w", font=("Segoe UI", 10))
status_label.pack(fill="x")

def populate_simulations():
    sim_tree.delete(*sim_tree.get_children())
    simulations = get_simulations()
    if not simulations:
        messagebox.showerror("Error", "No se encontraron simulaciones en la carpeta './Simulations'.")
        main_window.destroy()
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
    
    # Verificar que exista el CSV en My Documents\SimulationLoggerData\<simulationName>\SimulationStats.csv
    documents_path = Path.home() / "Documents"
    csv_path = documents_path / "SimulationLoggerData" / simulation_name / "SimulationStats.csv"
    if not csv_path.exists():
        messagebox.showerror("Error", f"[Error] No se encontró el archivo CSV en:\n{csv_path}")
        update_status(f"[Error] No se encontró el archivo CSV en: {csv_path}")
        return
    
    # Ruta al script de gráficos:
    # ./Simulations/<simulationName>/Assets/Scripts/SimulationData/SimulationGraphics.py
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
    options_win.geometry("400x300")
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
    
    main_x = main_window.winfo_x()
    main_y = main_window.winfo_y()
    options_win.geometry(f"+{main_x + 150}+{main_y + 150}")
    update_status("Opciones disponibles.")

populate_simulations()

main_window.mainloop()
