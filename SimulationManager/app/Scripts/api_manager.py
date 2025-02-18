import os
import sys
import formater
import importer
import api  # Importa el módulo que llama a la API de OpenAI

# Usamos el separador especial
DELIMITER = "%|%"
RESPONSES_CSV = os.path.join(".", "Responses", "Responses.csv")

def get_next_id(csv_path: str) -> int:
    if not os.path.exists(csv_path):
        return 1
    with open(csv_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        if len(lines) < 2:
            return 1
        for line in reversed(lines):
            if line.strip():
                try:
                    parts = line.split(DELIMITER)
                    last_id = int(parts[0])
                    return last_id + 1
                except (IndexError, ValueError):
                    continue
    return 1

def write_response_to_csv(pregunta: str, respuesta: str, input_tokens: int, output_tokens: int):
    responses_folder = os.path.join(".", "Responses")
    os.makedirs(responses_folder, exist_ok=True)
    
    write_header = not os.path.exists(RESPONSES_CSV)
    newline_needed = False

    if not write_header:
        with open(RESPONSES_CSV, "rb") as f:
            f.seek(0, os.SEEK_END)
            if f.tell() > 0:
                f.seek(f.tell() - 1)
                last_char = f.read(1)
                if last_char != b'\n':
                    newline_needed = True

    with open(RESPONSES_CSV, "a", encoding="utf-8") as f:
        if write_header:
            f.write(f"id{DELIMITER}pregunta{DELIMITER}respuesta{DELIMITER}input_tokens{DELIMITER}output_tokens\n")
        elif newline_needed:
            f.write("\n")
        next_id = get_next_id(RESPONSES_CSV)
        line = f"{next_id}{DELIMITER}{pregunta}{DELIMITER}{respuesta}{DELIMITER}{input_tokens}{DELIMITER}{output_tokens}\n"
        f.write(line)
    print(f"Respuesta guardada en: {RESPONSES_CSV} (id: {next_id})")

def get_cached_response(pregunta: str) -> str:
    if not os.path.exists(RESPONSES_CSV):
        return None
    with open(RESPONSES_CSV, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines[1:]:
        parts = line.strip().split(DELIMITER)
        if len(parts) < 5:
            continue
        cached_pregunta = parts[1]
        cached_respuesta = parts[2]
        cached_input_tokens = parts[3]
        cached_output_tokens = parts[4]
        if cached_pregunta == pregunta and cached_input_tokens != "0" and cached_output_tokens != "0":
            return cached_respuesta
    return None

def main():
    """
    Flujo:
      1. Recibe el nombre de la simulación y la descripción (pregunta) a enviar a la API.
      2. Verifica que la simulación no exista previamente.
      3. Si la pregunta ya fue consultada (cache), usa la respuesta cacheada y registra tokens 0.
      4. De lo contrario, llama a la API real mediante api.call_api() y guarda los tokens reales.
      5. Procesa la respuesta con formater.py para obtener los códigos.
      6. Llama a importer.py para crear los archivos en la carpeta de la simulación.
    """
    if len(sys.argv) < 3:
        print("Uso: api_manager.py <nombre-simulación> <pregunta>")
        sys.exit(1)

    simulation_name = sys.argv[1]
    pregunta = sys.argv[2]
    
    simulation_folder = os.path.join("..", "Simulations", simulation_name)
    if os.path.exists(simulation_folder):
        print(f"La simulación '{simulation_name}' ya existe. Elija otro nombre.")
        sys.exit(1)

    #print("ESTE ES EL ARCHIVO api_manager.py")
    print(f"Procesando simulación: {simulation_name}")
    print(f"Pregunta: {pregunta}")

    cached_response = get_cached_response(pregunta)
    if cached_response is not None:
        print("Usando respuesta cacheada para la pregunta.")
        response = cached_response
        write_response_to_csv(pregunta, response, 0, 0)
    else:
        # Llama a la API real definida en api.py
        response, input_tokens, output_tokens = api.call_api(pregunta)
        if not response:
            print("Error al obtener respuesta de la API.")
            sys.exit(1)
        write_response_to_csv(pregunta, response, input_tokens, output_tokens)

    codes = formater.separar_codigos_por_archivo(response)
    if not codes:
        print("No se procesaron códigos a partir de la respuesta.")
        sys.exit(1)
    print(f"Se encontraron {len(codes)} archivos en la respuesta formateada.")

    importer.import_codes(codes, simulation_name)

    print("Proceso completado. Simulación creada exitosamente.")

if __name__ == "__main__":
    main()
