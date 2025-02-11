import os
import shutil
import subprocess
import platform
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dotenv import load_dotenv

# ======================================================
# Cargar configuración desde .env y verificar versión
# ======================================================
load_dotenv('.env')

UNITY_EXECUTABLE = os.environ.get("UNITY_EXECUTABLE")
UNITY_PROJECTS_PATH = os.environ.get("UNITY_PROJECTS_PATH")

if not UNITY_EXECUTABLE or not UNITY_PROJECTS_PATH:
    messagebox.showerror("Error de Configuración", "No se encontraron las variables UNITY_EXECUTABLE o UNITY_PROJECTS_PATH en el .env")
    exit(1)

# Verificar que el ejecutable corresponda a la versión requerida
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
            messagebox.showerror("Error", f"El ejecutable seleccionado no es la versión requerida ({required_version}). Se abortará la ejecución.")
            exit(1)
    else:
        messagebox.showerror("Error", f"Modifique la variable de entorno UNITY_EXECUTABLE a la versión {required_version}.")
        exit(1)

# ======================================================
# Definición de rutas y variables globales
# ======================================================
SIMULATIONS_DIR = "./Simulations"
SIMULATION_PROJECT_NAME = "Simulacion"
SIMULATION_PROJECT_PATH = os.path.join(UNITY_PROJECTS_PATH, SIMULATION_PROJECT_NAME)
SIMULATION_LOADED_FILE = os.path.join(SIMULATION_PROJECT_PATH, "simulation_loaded.txt")
last_simulation_loaded = None

# ======================================================
# Función para monitorear el tamaño de carpeta para el tool de prefabs
# ======================================================
def monitor_progress_prefab_tool(stop_event):
    """
    Cada 2 segundos, actualiza la etiqueta de estado con el tamaño de la carpeta
    SIMULATION_PROJECT_PATH, mostrando un mensaje específico para el tool de prefabs.
    """
    while not stop_event.is_set():
        size_bytes = get_folder_size(SIMULATION_PROJECT_PATH)
        size_mb = size_bytes / (1024 * 1024)
        update_status(f"Ejecutando tool de prefabs y materiales... Tamaño de carpeta: {size_mb:.2f} MB")
        time.sleep(2)

# ======================================================
# Función para ejecutar el tool de creación de prefabs y materiales
# ======================================================
def run_prefab_material_tool():
    """
    Ejecuta Unity en modo batch para correr el método del Editor que crea los prefabs y materiales.
    Se invoca el método 'PrefabMaterialCreator.CreatePrefabsAndMaterials' que debe existir en el proyecto de Unity.
    Mientras se ejecuta, se muestra el tamaño de la carpeta actualizado cada 2 segundos.
    """
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
        update_status("Ejecutando tool de prefabs y materiales...")
        subprocess.run(command, check=True)
        update_status("Tool de prefabs y materiales ejecutado exitosamente.")
    except subprocess.CalledProcessError as e:
        update_status(f"Error al ejecutar el tool de prefabs: {e}")
    progress_stop_event.set()
    monitor_thread.join()

# ======================================================
# Funciones auxiliares para metadatos de simulaciones
# ======================================================
def get_simulations():
    """
    Retorna una lista de diccionarios con información de cada simulación (nombre, fecha de creación y última apertura)
    de las carpetas en SIMULATIONS_DIR que contengan las carpetas Assets, Packages y ProjectSettings.
    """
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
    """
    Actualiza (o crea) el archivo 'last_opened.txt' en la carpeta de la simulación en SIMULATIONS_DIR
    con el timestamp actual.
    """
    sim_folder = os.path.join(SIMULATIONS_DIR, simulation_name)
    timestamp = time.time()
    try:
        with open(os.path.join(sim_folder, "last_opened.txt"), "w") as f:
            f.write(str(timestamp))
    except Exception as e:
        print("Error al actualizar last_opened:", e)

# ======================================================
# Funciones auxiliares para copia y build
# ======================================================
def copy_directory(src, dst):
    """
    Copia el directorio 'src' a 'dst'. Si 'dst' existe se elimina primero.
    """
    try:
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print(f"Copiado {src} a {dst}")
    except Exception as e:
        messagebox.showerror("Error", f"Error al copiar {src} a {dst}:\n{e}")

def load_simulation(simulation_name, first_time=True):
    """
    Copia las carpetas necesarias de la simulación seleccionada a SIMULATION_PROJECT_PATH.
    Si es la primera carga se copian Assets, Packages y ProjectSettings.
    Si se carga una simulación nueva, solo se actualiza la carpeta Assets (eliminando Build y Assets).
    Al finalizar, se actualiza la fecha de última apertura y se guarda el nombre de la simulación en SIMULATION_LOADED_FILE.
    """
    global last_simulation_loaded
    sim_source_path = os.path.join(SIMULATIONS_DIR, simulation_name)
    if not os.path.exists(sim_source_path):
        messagebox.showerror("Error", f"La simulación {simulation_name} no existe.")
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
    try:
        with open(SIMULATION_LOADED_FILE, "w") as f:
            f.write(simulation_name)
    except Exception as e:
        print("Error al escribir simulation_loaded.txt:", e)
    last_simulation_loaded = simulation_name
    return True

def get_build_target_and_executable(project_path):
    """
    Según el sistema operativo, retorna el parámetro build_target y la ruta al ejecutable generado.
    """
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
    """
    Actualiza la etiqueta de estado en la interfaz de forma thread-safe.
    """
    main_window.after(0, lambda: status_label.config(text=message))

def get_folder_size(path):
    """
    Calcula recursivamente el tamaño total (en bytes) de la carpeta 'path'.
    """
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
    """
    Hilo que, cada 2 segundos, calcula y muestra el tamaño total de la carpeta SIMULATION_PROJECT_PATH.
    """
    while not stop_event.is_set():
        size_bytes = get_folder_size(SIMULATION_PROJECT_PATH)
        size_mb = size_bytes / (1024 * 1024)
        update_status(f"Construyendo... Tamaño de carpeta: {size_mb:.2f} MB")
        time.sleep(2)

def build_simulation_threaded(callback=None):
    """
    Ejecuta el build de Unity en modo batch con hasta 2 intentos (espera 30 s entre intentos).
    Mientras se ejecuta, se muestra el tamaño total de la carpeta SIMULATION_PROJECT_PATH para indicar progreso.
    Si falla, se lee el log para identificar si el error es que no se encontró BuildScript.PerformBuild.
    """
    build_target, _ = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
    log_file = os.path.join(SIMULATION_PROJECT_PATH, "build_log.txt")
    command = [
        UNITY_EXECUTABLE,
        "-batchmode",
        "-quit",
        "-projectPath", os.path.normpath(SIMULATION_PROJECT_PATH),
        "-executeMethod", "BuildScript.PerformBuild",  # Debe existir en el proyecto de Unity
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
            update_status(f"Ejecutando build (Intento {attempt + 1} de {max_retries})...")
            subprocess.run(command, check=True)
            update_status("Build completado exitosamente.")
            success = True
            break
        except subprocess.CalledProcessError as e:
            update_status(f"Error durante el build (Intento {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                update_status("Esperando 30 segundos para reintentar...")
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
                "El build falló: no se encontró el método BuildScript.PerformBuild.\n"
                "Asegúrese de incluir en el proyecto (por ejemplo, en Assets/Editor) un script BuildScript.cs con un método estático 'PerformBuild'.\n\n"
                "Revisa el log: " + log_file)
        else:
            messagebox.showerror("Error en el Build", "El build falló. Revisa el log: " + log_file)
        update_status("Build fallido.")
    if callback:
        main_window.after(0, lambda: callback(success))

def open_simulation_executable():
    """
    Ejecuta el build generado (el ejecutable) según el sistema operativo.
    """
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
    """
    Abre el proyecto en el editor de Unity.
    """
    try:
        subprocess.Popen([UNITY_EXECUTABLE, "-projectPath", os.path.normpath(SIMULATION_PROJECT_PATH)])
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo abrir el proyecto en Unity:\n{e}")

# ======================================================
# Interfaz Gráfica (GUI) – Diseño Profesional
# ======================================================
main_window = tk.Tk()
main_window.title("Gestor de Simulaciones de Unity")
main_window.geometry("700x500")
main_window.resizable(False, False)

style = ttk.Style(main_window)
style.theme_use("clam")

# Menú superior
menubar = tk.Menu(main_window)
archivo_menu = tk.Menu(menubar, tearoff=0)
archivo_menu.add_command(label="Salir", command=main_window.destroy)
menubar.add_cascade(label="Archivo", menu=archivo_menu)
ayuda_menu = tk.Menu(menubar, tearoff=0)
ayuda_menu.add_command(label="Acerca de", command=lambda: messagebox.showinfo("Acerca de", "Gestor de Simulaciones de Unity\nVersión 1.0"))
menubar.add_cascade(label="Ayuda", menu=ayuda_menu)
main_window.config(menu=menubar)

# Cabecera
header_frame = ttk.Frame(main_window, padding=(10, 10))
header_frame.pack(fill="x")
header_label = ttk.Label(header_frame, text="Gestor de Simulaciones de Unity", font=("Segoe UI", 20, "bold"), foreground="#2C3E50")
header_label.pack(side="left")

# Marco principal
main_frame = ttk.Frame(main_window, padding=10)
main_frame.pack(expand=True, fill="both")

select_label = ttk.Label(main_frame, text="Seleccione una simulación:", font=("Segoe UI", 14))
select_label.pack(pady=(10, 5))

# --- Treeview para listado de simulaciones ---
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

# --- Botones para recargar y cargar ---
button_frame = ttk.Frame(main_frame)
button_frame.pack(pady=10)

reload_btn = ttk.Button(button_frame, text="Recargar Lista", command=lambda: populate_simulations())
reload_btn.pack(side="left", padx=5)

cargar_btn = ttk.Button(button_frame, text="Cargar Simulación",
                          command=lambda: threading.Thread(target=on_load_simulation, daemon=True).start())
cargar_btn.pack(side="left", padx=5)

# Barra de estado
status_frame = ttk.Frame(main_window)
status_frame.pack(fill="x", side="bottom")
status_label = ttk.Label(status_frame, text="Esperando selección...", relief="sunken", anchor="w", font=("Segoe UI", 10))
status_label.pack(fill="x")

# ======================================================
# Funciones de la interfaz
# ======================================================
def populate_simulations():
    sim_tree.delete(*sim_tree.get_children())
    simulations = get_simulations()
    if not simulations:
        messagebox.showerror("Error", "No se encontraron simulaciones en la carpeta './Simulations'.")
        main_window.destroy()
    else:
        for sim in simulations:
            sim_tree.insert("", "end", values=(sim["name"], sim["creation"], sim["last_opened"]))

def on_load_simulation():
    selected = sim_tree.selection()
    if not selected:
        messagebox.showwarning("Advertencia", "Seleccione una simulación de la lista.")
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
            update_status("La simulación ya está cargada. Mostrando opciones...")
            main_window.after(500, show_options_window)
            return

    if not os.path.exists(SIMULATION_PROJECT_PATH):
        messagebox.showinfo("Aviso",
            "Esta es la primera vez que se carga una simulación.\n"
            "Por favor, tenga paciencia, ya que se va a crear desde cero el ambiente de la simulación (alrededor de 2500 MB) y demorará más que las demás.")

    reload_btn.config(state="disabled")
    cargar_btn.config(state="disabled")
    sim_tree.config(selectmode="none")
    update_status("Cargando simulación...")

    first_time = (last_simulation_loaded is None)
    if load_simulation(simulation_name, first_time):
        # Ejecutar el tool de prefabs y materiales antes de iniciar el build
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

def show_options_window():
    options_win = tk.Toplevel(main_window)
    options_win.title("Opciones Post-Build")
    options_win.geometry("400x300")
    options_win.resizable(False, False)
    
    options_frame = ttk.Frame(options_win, padding=20)
    options_frame.pack(expand=True, fill="both")
    
    info_label = ttk.Label(options_frame, text="¿Qué desea hacer ahora?", font=("Segoe UI", 14))
    info_label.pack(pady=10)
    
    btn_ejecutar = ttk.Button(options_frame, text="Ejecutar Build", command=open_simulation_executable)
    btn_ejecutar.pack(pady=5, fill="x")
    
    btn_abrir = ttk.Button(options_frame, text="Abrir en Unity", command=open_in_unity)
    btn_abrir.pack(pady=5, fill="x")
    
    btn_nueva = ttk.Button(options_frame, text="Cargar Nueva Simulación",
                            command=lambda: (options_win.destroy(), update_status("Esperando nueva selección...")))
    btn_nueva.pack(pady=5, fill="x")
    
    btn_salir = ttk.Button(options_frame, text="Salir", command=main_window.destroy)
    btn_salir.pack(pady=5, fill="x")
    
    main_x = main_window.winfo_x()
    main_y = main_window.winfo_y()
    options_win.geometry(f"+{main_x + 150}+{main_y + 150}")

populate_simulations()

main_window.mainloop()
