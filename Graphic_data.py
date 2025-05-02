import pandas as pd
import numpy as np
import argparse
import os
import sys

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
        # *** Aplicar a la columna especificada ***
        df[count_column_name] = pd.to_numeric(df[count_column_name], errors='coerce', downcast='integer')

        # Eliminar filas donde las conversiones numéricas fallaron
        rows_before = len(df)
        # *** Usar la columna especificada en dropna ***
        df.dropna(subset=['SimulatedTime', count_column_name], inplace=True)
        rows_after = len(df)
        if rows_before > rows_after:
             print(f"Advertencia: Se eliminaron {rows_before - rows_after} filas debido a valores no numéricos en 'SimulatedTime' o '{count_column_name}'.")

        if df.empty:
            print(f"Error: No quedan datos válidos para '{count_column_name}' después de la limpieza numérica.")
            return None, None

        # Filtrar filas pausadas
        df['Pausado'] = df['Pausado'].astype(str)
        rows_before = len(df)
        df_active = df[df['Pausado'].str.strip().str.upper() == 'NO'].copy()
        rows_after = len(df_active)
        if rows_before > rows_after:
             print(f"Filtrando datos pausados: {rows_before - rows_after} filas eliminadas.")

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

    except Exception as e:
        print(f"Error durante la limpieza o conversión de datos para '{count_column_name}': {e}")
        return None, None

    if df_active.empty:
        print(f"Error: No quedan datos válidos para '{count_column_name}' después de la limpieza y filtrado.")
        return None, None

    # --- Cálculo del Tiempo de Duplicación para la columna especificada ---
    doubling_times = []
    current_index = -1

    # *** Usar la columna especificada para encontrar el inicio ***
    first_valid_indices = df_active[df_active[count_column_name] >= min_initial_count].index
    if not first_valid_indices.empty:
        current_index = first_valid_indices[0]
        # *** Usar la columna especificada en el print ***
        print(f"Iniciando búsqueda de duplicaciones para '{count_column_name}' desde T={df_active.loc[current_index, 'SimulatedTime']:.2f} con Count={df_active.loc[current_index, count_column_name]}")
    else:
        print(f"No se encontraron datos para '{count_column_name}' con conteo >= {min_initial_count}. No se puede calcular.")
        return None, None

    while current_index is not None and current_index in df_active.index:
        current_time = df_active.loc[current_index, 'SimulatedTime']
        # *** Usar la columna especificada ***
        current_count = df_active.loc[current_index, count_column_name]

        if current_count <= 0:
             print(f"Advertencia: Conteo no positivo ({current_count}) encontrado para '{count_column_name}' en T {current_time:.2f}. Deteniendo búsqueda.")
             break

        target_count = current_count * 2

        # *** Usar la columna especificada para buscar duplicación ***
        future_data = df_active.loc[df_active.index > current_index]
        doubled_indices = future_data[future_data[count_column_name] >= target_count].index

        if not doubled_indices.empty:
            next_index = doubled_indices[0]
            next_time = df_active.loc[next_index, 'SimulatedTime']
            # *** Usar la columna especificada ***
            next_count = df_active.loc[next_index, count_column_name]
            time_elapsed = next_time - current_time

            if time_elapsed > 1e-9:
                doubling_times.append(time_elapsed)
                # *** Usar la columna especificada en el print ***
                print(f"  Duplicación ('{count_column_name}') encontrada: De {current_count} (T={current_time:.2f}) a {next_count} (T={next_time:.2f}). Tiempo: {time_elapsed:.2f}")
                current_index = next_index
            else:
                 print(f"  Advertencia: Tiempo de duplicación no positivo ({time_elapsed:.4f}) para '{count_column_name}' de T={current_time:.2f} a T={next_time:.2f}. Saltando intervalo.")
                 indices_after_current = df_active.index[df_active.index > current_index]
                 current_index = indices_after_current[0] if not indices_after_current.empty else None
        else:
            # *** Usar la columna especificada en el print ***
            print(f"No se encontró duplicación futura para '{count_column_name}' con conteo {current_count} (T={current_time:.2f}).")
            current_index = None
            break

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

# --- Ejecución del Script desde Línea de Comandos ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Calcula tiempos de duplicación promedio desde SimulationStats.csv para columnas específicas.')
    parser.add_argument('filepath', type=str, help='Ruta al archivo SimulationStats.csv')
    parser.add_argument('--min_count', type=int, default=2, help='Conteo mínimo inicial para empezar a calcular (default: 2)')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    # --- Columnas a Analizar (Asegúrate que coincidan EXACTAMENTE con tu CSV) ---
    columns_to_analyze = ['EColi', 'SCerevisiae', 'Organism count']
    results = {}

    print(f"\n=== Iniciando Análisis de Tiempos de Duplicación ===")
    print(f"Archivo: {args.filepath}")
    print(f"Conteo mínimo inicial para análisis: {args.min_count}")

    for col_name in columns_to_analyze:
        avg_dt, std_dt = calculate_doubling_time_for_column(args.filepath, col_name, args.min_count)
        results[col_name] = {'average': avg_dt, 'std_dev': std_dt}
        print("\n") # Añadir espacio entre análisis de columnas

    print("=== Resumen de Resultados ===")
    for col_name, data in results.items():
        print(f"--- {col_name} ---")
        if data['average'] is not None:
            print(f"  Tiempo de duplicación promedio: {data['average']:.3f}")
            print(f"  Desviación estándar: {data['std_dev']:.3f}")
        else:
            print("  No se pudo calcular el tiempo de duplicación.")
        print("-" * (len(col_name) + 6))

    print("============================")