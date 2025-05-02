import pandas as pd
import numpy as np
# import argparse # Ya no se necesita para la ruta del archivo
import os
import sys # Mantenido por si se quiere reintroducir argparse o para print_help

def calculate_doubling_time_for_column(filepath, count_column_name, min_initial_count=2):
    """
    Calcula el tiempo de duplicación promedio para una columna de conteo específica
    a partir de un archivo SimulationStats.csv.

    Args:
        filepath (str): Ruta al archivo SimulationStats.csv.
        count_column_name (str): Nombre exacto de la columna que contiene
                                 el conteo a analizar (ej: 'EColi').
        min_initial_count (int): El conteo mínimo en la columna especificada
                                 para empezar a buscar el primer evento de
                                 duplicación.

    Returns:
        tuple: (promedio, desviacion_estandar) del tiempo de duplicación en
               las unidades de 'SimulatedTime', o (None, None) si no se
               pueden calcular.
    """
    print("-" * 40)
    print(f"Analizando columna: '{count_column_name}' en archivo: {os.path.basename(filepath)}")
    print("-" * 40)

    if not os.path.exists(filepath):
        print(f"Error: El archivo no se encontró en la ruta: {filepath}")
        return None, None

    try:
        # Asegúrate de que el separador y el decimal sean correctos para tu archivo CSV
        df = pd.read_csv(filepath, sep=';', decimal='.') 
        print(f"Archivo leído. {len(df)} filas encontradas.")
    except pd.errors.EmptyDataError:
        print("Error: El archivo CSV está vacío.")
        return None, None
    except Exception as e:
        print(f"Error al leer o parsear el archivo CSV: {e}")
        return None, None

    # --- Validación de Columnas Esenciales ---
    required_columns = ['SimulatedTime', 'Pausado', count_column_name]
    if not all(col in df.columns for col in required_columns):
        print(f"Error: Faltan columnas requeridas en el CSV para analizar '{count_column_name}'.")
        print(f"Se necesitan: {required_columns}")
        print(f"Columnas encontradas: {list(df.columns)}")
        return None, None

    # --- Limpieza y Preparación de Datos ---
    try:
        # Convertir columnas a tipos numéricos
        df['SimulatedTime'] = pd.to_numeric(df['SimulatedTime'], errors='coerce', downcast='float')
        df[count_column_name] = pd.to_numeric(df[count_column_name], errors='coerce', downcast='integer')

        # Eliminar filas donde las conversiones numéricas fallaron
        rows_before = len(df)
        df.dropna(subset=['SimulatedTime', count_column_name], inplace=True)
        rows_after = len(df)
        if rows_before > rows_after:
             print(f"Advertencia: Se eliminaron {rows_before - rows_after} filas debido a valores no numéricos en 'SimulatedTime' o '{count_column_name}'.")

        if df.empty:
            print(f"Error: No quedan datos válidos para '{count_column_name}' después de la limpieza numérica.")
            return None, None

        # Filtrar filas pausadas (asegurarse que 'Pausado' existe y es interpretable)
        if 'Pausado' in df.columns:
             df['Pausado'] = df['Pausado'].astype(str)
             rows_before = len(df)
             df_active = df[df['Pausado'].str.strip().str.upper() == 'NO'].copy()
             rows_after = len(df_active)
             if rows_before > rows_after:
                 print(f"Filtrando datos pausados: {rows_before - rows_after} filas eliminadas.")
        else:
             print("Advertencia: No se encontró la columna 'Pausado'. Se asumirá que todos los datos son activos.")
             df_active = df.copy() # Usar todos los datos si 'Pausado' no existe


        if df_active.empty:
            print(f"Error: No hay datos activos registrados para '{count_column_name}'.")
            return None, None

        # Ordenar y eliminar duplicados de tiempo
        df_active = df_active.sort_values(by='SimulatedTime')
        rows_before = len(df_active)
        df_active = df_active.drop_duplicates(subset=['SimulatedTime'], keep='last')
        rows_after = len(df_active)
        if rows_before > rows_after:
            print(f"Advertencia: Se eliminaron {rows_before - rows_after} filas con 'SimulatedTime' duplicado.")

    except KeyError as e:
        print(f"Error: Falta la columna '{e}' necesaria para la limpieza o filtrado.")
        return None, None
    except Exception as e:
        print(f"Error durante la limpieza o conversión de datos para '{count_column_name}': {e}")
        return None, None

    if df_active.empty:
        print(f"Error: No quedan datos válidos para '{count_column_name}' después de la limpieza y filtrado.")
        return None, None

    # --- Cálculo del Tiempo de Duplicación para la columna especificada ---
    doubling_times = []
    current_index = -1

    first_valid_indices = df_active[df_active[count_column_name] >= min_initial_count].index
    if not first_valid_indices.empty:
        current_index = first_valid_indices[0]
        print(f"Iniciando búsqueda de duplicaciones para '{count_column_name}' desde T={df_active.loc[current_index, 'SimulatedTime']:.2f} con Count={df_active.loc[current_index, count_column_name]}")
    else:
        print(f"No se encontraron datos para '{count_column_name}' con conteo >= {min_initial_count}. No se puede calcular.")
        return None, None

    while current_index is not None and current_index in df_active.index:
        current_time = df_active.loc[current_index, 'SimulatedTime']
        current_count = df_active.loc[current_index, count_column_name]

        if current_count <= 0:
             print(f"Advertencia: Conteo no positivo ({current_count}) encontrado para '{count_column_name}' en T {current_time:.2f}. Deteniendo búsqueda.")
             break # Salir del bucle si el conteo es cero o negativo

        target_count = current_count * 2

        future_data = df_active.loc[df_active.index > current_index]
        doubled_indices = future_data[future_data[count_column_name] >= target_count].index

        if not doubled_indices.empty:
            next_index = doubled_indices[0]
            next_time = df_active.loc[next_index, 'SimulatedTime']
            next_count = df_active.loc[next_index, count_column_name]
            time_elapsed = next_time - current_time

            # Evitar división por cero o tiempos de duplicación insignificantes
            if time_elapsed > 1e-9: # Un umbral pequeño para considerar un tiempo válido
                doubling_times.append(time_elapsed)
                print(f"  Duplicación ('{count_column_name}') encontrada: De {current_count} (T={current_time:.2f}) a {next_count} (T={next_time:.2f}). Tiempo: {time_elapsed:.2f}")
                current_index = next_index # Avanzar al índice donde se duplicó
            else:
                # Si el tiempo es cero o negativo, buscar el *siguiente* punto de datos para continuar
                print(f"  Advertencia: Tiempo de duplicación no positivo o muy pequeño ({time_elapsed:.4f}) para '{count_column_name}' de T={current_time:.2f} a T={next_time:.2f}. Buscando siguiente punto.")
                # Encontrar el índice inmediatamente posterior al actual para evitar bucles infinitos
                indices_after_current = df_active.index[df_active.index > current_index]
                if not indices_after_current.empty:
                    current_index = indices_after_current[0] 
                else:
                    print("No hay más puntos de datos después del evento de tiempo no positivo.")
                    current_index = None # Terminar si no hay más datos
        else:
            print(f"No se encontró duplicación futura para '{count_column_name}' con conteo {current_count} (T={current_time:.2f}). Fin del análisis para esta columna.")
            current_index = None # Terminar la búsqueda para esta columna
            # No se usa 'break' aquí explícitamente, current_index = None detiene el while

    # --- Calcular y Devolver el Promedio ---
    if doubling_times:
        average_dt = np.mean(doubling_times)
        std_dt = np.std(doubling_times)
        print(f"\nSe encontraron {len(doubling_times)} eventos de duplicación para '{count_column_name}'.")
        print(f"Tiempos individuales: {[round(t, 2) for t in doubling_times]}")
        return average_dt, std_dt
    else:
        print(f"\nNo se pudo calcular ningún tiempo de duplicación para '{count_column_name}'.")
        return None, None

# --- Ejecución del Script ---
if __name__ == "__main__":

    # --- PARÁMETROS DE CONFIGURACIÓN ---
    # 1. Ruta al archivo CSV (Modifica esta línea con tu ruta real)
    #    Asegúrate de usar dobles barras invertidas '\\' o una barra normal '/'
    csv_filepath = r"C:\Users\icace\Documents\SimulationLoggerData\Escenario 1\SimulationStats.csv"
    # Ejemplo alternativo con barras normales:
    # csv_filepath = "C:/Users/icace/Documents/SimulationLoggerData/Escenario 1/SimulationStats.csv"

    # 2. Tiempos de duplicación esperados/solicitados para cada organismo (en las mismas unidades que 'SimulatedTime')
    #    El nombre (clave) debe coincidir EXACTAMENTE con el encabezado de la columna en el CSV.
    #    Si el valor es 0, el organismo NO será analizado.
    target_doubling_times = {
        'EColi': 20.0,         # Ejemplo: Se espera que EColi se duplique cada 20 unidades de tiempo
        'SCerevisiae': 90.0,   # Ejemplo: Se espera que SCerevisiae se duplique cada 90 unidades de tiempo
        'Organism count': 0,   # Ejemplo: No analizar la columna 'Organism count' (quizás es un total)
        'OtroOrganismo': 45.5, # Ejemplo: Analizar 'OtroOrganismo' si existe en el CSV
        'NoAnalizar': 0        # Ejemplo: No analizar 'NoAnalizar'
    }

    # 3. Conteo mínimo inicial para empezar el análisis de duplicación
    min_count_for_analysis = 2
    # --- FIN DE PARÁMETROS DE CONFIGURACIÓN ---


    results = {} # Diccionario para almacenar los resultados detallados

    print(f"\n=== Iniciando Análisis de Tiempos de Duplicación ===")
    print(f"Archivo: {csv_filepath}")
    print(f"Conteo mínimo inicial para análisis: {min_count_for_analysis}")
    print("Tiempos de duplicación esperados (0 = no analizar):")
    for org, time in target_doubling_times.items():
        print(f"  - {org}: {time}")

    # Iterar sobre los organismos definidos en target_doubling_times
    for organism_name, target_dt in target_doubling_times.items():
        if target_dt > 0: # Solo analizar si el tiempo esperado es mayor que 0
            avg_dt, std_dt = calculate_doubling_time_for_column(csv_filepath, organism_name, min_count_for_analysis)
            
            error_percent = None
            if avg_dt is not None and target_dt is not None and target_dt > 0:
                # Calcular error relativo porcentual
                error_percent = abs(avg_dt - target_dt) / target_dt * 100

            results[organism_name] = {
                'target': target_dt,
                'average': avg_dt,
                'std_dev': std_dt,
                'error_percent': error_percent
            }
            print("\n") # Añadir espacio entre análisis de organismos
        else:
            print(f"\n--- Omitiendo análisis para '{organism_name}' (tiempo esperado = 0) ---\n")


    # --- Generar la Tabla de Precisión Paramétrica ---
    print("=" * 80)
    print("=== Tabla de Precisión Paramétrica ===")
    print("=" * 80)
    # Encabezado de la tabla
    header = f"{'Organismo':<20} | {'DT Esperado':<15} | {'DT Calculado (Avg)':<20} | {'Std Dev':<10} | {'Error (%)':<10}"
    print(header)
    print("-" * len(header))

    # Filas de la tabla
    for organism_name, data in results.items():
        target_str = f"{data['target']:.2f}" if data['target'] is not None else "N/A"
        avg_str = f"{data['average']:.3f}" if data['average'] is not None else "No calculado"
        std_str = f"{data['std_dev']:.3f}" if data['std_dev'] is not None else "N/A"
        err_str = f"{data['error_percent']:.2f}%" if data['error_percent'] is not None else "N/A"
        
        print(f"{organism_name:<20} | {target_str:<15} | {avg_str:<20} | {std_str:<10} | {err_str:<10}")

    # Imprimir organismos omitidos (opcional, para confirmación)
    omitted = [org for org, time in target_doubling_times.items() if time <= 0]
    if omitted:
        print("-" * len(header))
        print(f"Organismos omitidos (DT Esperado = 0): {', '.join(omitted)}")

    print("=" * 80)