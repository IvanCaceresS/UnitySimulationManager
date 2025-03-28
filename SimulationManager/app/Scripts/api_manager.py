import os
import sys
import formater
import importer
import api

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
        if cached_pregunta == pregunta:
            return cached_respuesta
    return None

def main():
    if len(sys.argv) < 3:
        print("Uso: api_manager.py <nombre-simulación> <pregunta>")
        sys.exit(1)

    simulation_name = sys.argv[1]
    original_pregunta = sys.argv[2]
    
    if os.path.exists(os.path.join("..", "Simulations", simulation_name)):
        print(f"Simulación '{simulation_name}' ya existe")
        sys.exit(1)

    print(f"\nIniciando procesamiento para: {simulation_name}")
    print(f"Consulta original: {original_pregunta}")

    # Paso 1: Validación y formateo con modelo secundario
    formatted_pregunta, second_input_tk, second_output_tk = api.call_secondary_model(original_pregunta)
    
    if not formatted_pregunta:
        print("Error crítico: Fallo al contactar modelo secundario")
        sys.exit(1)
        
    if formatted_pregunta.strip() == "ERROR DE CONTENIDO":
        print("❌ Pregunta rechazada por contenido inválido", file=sys.stderr)  # Escribir en stderr
        sys.exit(7)

    print(f"\nPregunta validada y formateada: {formatted_pregunta}")

    # Paso 2: Verificar cache
    cached_response = get_cached_response(formatted_pregunta)
    if cached_response:
        print("✅ Usando respuesta en caché")
        write_response_to_csv(formatted_pregunta, cached_response, second_input_tk, second_output_tk)
        final_response = cached_response
    else:
        # Paso 3: Procesar con modelo primario
        print("⌛ Generando código con modelo primario...")
        final_response, primary_input_tk, primary_output_tk = "", 0, 0
        for attempt in range(2):
            final_response, primary_input_tk, primary_output_tk = api.call_primary_model(formatted_pregunta)
            if final_response: break
            print(f"Intento {attempt+1} fallido")
        
        if not final_response:
            print("❌ Error: Modelo primario no respondió")
            sys.exit(1)
            
        # Registrar tokens totales
        total_input = second_input_tk + primary_input_tk
        total_output = second_output_tk + primary_output_tk
        write_response_to_csv(formatted_pregunta, final_response, total_input, total_output)

    # Procesar respuesta final
    if "ERROR FORMATO DE PREGUNTA" in final_response:
        print("❌ Error en formato de pregunta validada")
        sys.exit(1)
        
    codes = formater.separar_codigos_por_archivo(final_response)
    if not codes:
        print("❌ No se encontraron códigos válidos")
        sys.exit(1)
        
    print(f"\n✅ Generados {len(codes)} scripts:")
    for filename in codes.keys():
        print(f"- {filename}")
        
    importer.import_codes(codes, simulation_name)
    print(f"\nSimulación '{simulation_name}' creada exitosamente")

if __name__ == "__main__":
    main()