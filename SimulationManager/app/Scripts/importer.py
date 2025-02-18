import os
import sys
import json
import shutil

def import_codes(codes: dict, simulation_name: str):
    """
    Crea una copia de la estructura de la carpeta Template y coloca los archivos modificados
    en las rutas correspondientes dentro de la simulación.

    Reglas:
      - Se copia la carpeta Template (con "Assets", "Packages" y "ProjectSettings") a:
            ./Simulations/<simulation_name>
      - En Assets/Editor se crea "PrefabMaterialCreator.cs" con:
            #if UNITY_EDITOR 
            using UnityEngine;
            using UnityEditor;
            using System.IO;
            <código recibido>
            #endif
      - En Assets/Scripts/Components se colocan los archivos cuyo nombre contenga "Component.cs".
      - En Assets/Scripts/Systems se colocan los archivos cuyo nombre contenga "System.cs". Para cada
        uno se carga el template ubicado en:
            Template/Assets/Scripts/Systems/GeneralSystem.cs
        se reemplaza la declaración de clase "GeneralSystem" por el nombre correspondiente (ej. "EColiSystem")
        y se inserta el código recibido (proporcionado por la API) inmediatamente después de la línea que contiene:
            var ecb = ecbSystem.CreateCommandBuffer().AsParallelWriter();
      - En Assets/Scripts/General se coloca "CreatePrefabsOnClick.cs". Para este archivo se toma el template ubicado en
            Template/Assets/Scripts/General/CreatePrefabsOnClick.cs
        y se inserta el código recibido luego de la línea que contenga "private void CargarPrefabs()" y "Resources.LoadAll<GameObject>".
      - El resto de archivos se colocan en la raíz de la simulación.
      
    Se garantiza que, aun cuando las carpetas "Systems" y "Components" (o cualquier otra ruta de destino)
    no existan en el Template copiado, se crearán en la carpeta de la simulación.

    :param codes: Diccionario {nombre_archivo: contenido}
    :param simulation_name: Nombre de la simulación
    """
    # Ruta de la simulación
    simulation_folder = os.path.join(".", "Simulations", simulation_name)
    if os.path.exists(simulation_folder):
        print(f"La simulación '{simulation_name}' ya existe. Elija otro nombre.")
        return

    # Ruta del template
    template_folder = os.path.join(".", "Template")
    try:
        shutil.copytree(template_folder, simulation_folder)
        print(f"Estructura de Template copiada a: {simulation_folder}")
    except Exception as e:
        print(f"Error al copiar el Template: {e}")
        return

    # Asegurarse de que existan las carpetas necesarias, aun si no estaban en el Template
    assets_editor_folder = os.path.join(simulation_folder, "Assets", "Editor")
    os.makedirs(assets_editor_folder, exist_ok=True)

    assets_scripts_components = os.path.join(simulation_folder, "Assets", "Scripts", "Components")
    os.makedirs(assets_scripts_components, exist_ok=True)

    assets_scripts_systems = os.path.join(simulation_folder, "Assets", "Scripts", "Systems")
    os.makedirs(assets_scripts_systems, exist_ok=True)

    assets_scripts_general = os.path.join(simulation_folder, "Assets", "Scripts", "General")
    os.makedirs(assets_scripts_general, exist_ok=True)

    # Ruta al template para sistemas
    template_system_path = os.path.join(template_folder, "Assets", "Scripts", "Systems", "GeneralSystem.cs")

    # Procesar cada archivo recibido en el diccionario
    for file_name, content in codes.items():
        # Determinar ruta destino y contenido final según el tipo de archivo
        if file_name == "PrefabMaterialCreator.cs":
            # Se creará en Assets/Editor
            dest_path = os.path.join(assets_editor_folder, "PrefabMaterialCreator.cs")
            new_content = (
                "#if UNITY_EDITOR\n"
                "using UnityEngine;\n"
                "using UnityEditor;\n"
                "using System.IO;\n"
                f"{content}\n"
                "#endif\n"
            )
        elif "Component.cs" in file_name:
            # Se colocan en Assets/Scripts/Components
            dest_path = os.path.join(assets_scripts_components, file_name)
            new_content = content
        elif "System.cs" in file_name:
            # Para los archivos de sistema, basarse en el template GeneralSystem.cs
            dest_path = os.path.join(assets_scripts_systems, file_name)
            try:
                with open(template_system_path, "r", encoding="utf-8") as f:
                    template_lines = f.readlines()
            except Exception as e:
                print(f"Error al leer el template de sistemas: {e}")
                continue

            # Reemplazar la declaración de clase
            class_declaration = "public partial class GeneralSystem : SystemBase"
            new_class_declaration = f"public partial class {file_name.replace('.cs','')} : SystemBase"
            template_lines = [line.replace(class_declaration, new_class_declaration) for line in template_lines]

            # Buscar la línea donde se crea el ParallelWriter (placeholder para insertar el código)
            insertion_index = None
            for i, line in enumerate(template_lines):
                if "var ecb = ecbSystem.CreateCommandBuffer().AsParallelWriter();" in line:
                    insertion_index = i
                    break

            if insertion_index is not None:
                # Insertar el código recibido justo después de la línea encontrada
                template_lines.insert(insertion_index + 1, content + "\n")
                new_content = "".join(template_lines)
            else:
                print(f"No se encontró la línea de inserción en el template de sistemas para {file_name}. Se usará el contenido recibido directamente.")
                new_content = content
        elif file_name == "CreatePrefabsOnClick.cs":
            # Se coloca en Assets/Scripts/General
            dest_path = os.path.join(assets_scripts_general, "CreatePrefabsOnClick.cs")
            # Leer el template original para CreatePrefabsOnClick.cs
            template_create_path = os.path.join(template_folder, "Assets", "Scripts", "General", "CreatePrefabsOnClick.cs")
            try:
                with open(template_create_path, "r", encoding="utf-8") as f:
                    template_lines = f.readlines()
            except Exception as e:
                print(f"Error al leer el template de CreatePrefabsOnClick.cs: {e}")
                continue

            insertion_index = None
            for i, line in enumerate(template_lines):
                if "private void CargarPrefabs()" in line and "Resources.LoadAll<GameObject>" in line:
                    insertion_index = i
                    break

            if insertion_index is not None:
                template_lines.insert(insertion_index + 1, content + "\n")
                new_content = "".join(template_lines)
            else:
                print("No se encontró la línea de inserción en el template de CreatePrefabsOnClick.cs. Se usará el contenido recibido directamente.")
                new_content = content
        else:
            # Para cualquier otro archivo, se coloca en la raíz de la simulación
            dest_path = os.path.join(simulation_folder, file_name)
            new_content = content

        # Asegurarse de que el directorio destino exista
        dest_dir = os.path.dirname(dest_path)
        os.makedirs(dest_dir, exist_ok=True)
        
        try:
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Archivo '{file_name}' creado en {dest_dir}")
        except Exception as e:
            print(f"Error al escribir el archivo {file_name}: {e}")

    # Finalmente, eliminar el template de sistemas (GeneralSystem.cs) de la copia, si existe
    template_system_dest = os.path.join(assets_scripts_systems, "GeneralSystem.cs")
    if os.path.exists(template_system_dest):
        try:
            os.remove(template_system_dest)
            print("Archivo 'GeneralSystem.cs' eliminado de la simulación.")
        except Exception as e:
            print(f"Error al eliminar 'GeneralSystem.cs': {e}")

def main():
    """
    Uso desde línea de comandos:
        importer.py <nombre_simulación> <ruta_json_con_codes>
    
    Se espera que el segundo argumento sea un archivo JSON que contenga el diccionario de códigos.
    """
    if len(sys.argv) < 3:
        print("Uso: importer.py <nombre_simulación> <ruta_json_con_codes>")
        sys.exit(1)

    simulation_name = sys.argv[1]
    codes_json_file = sys.argv[2]

    try:
        with open(codes_json_file, "r", encoding="utf-8") as f:
            codes = json.load(f)
    except Exception as e:
        print(f"Error al leer el archivo JSON: {e}")
        sys.exit(1)

    import_codes(codes, simulation_name)

if __name__ == "__main__":
    main()
