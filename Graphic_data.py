import pandas as pd
import numpy as np
# import argparse # Ya no se necesita para la ruta del archivo
import os
import sys # Mantenido por si se quiere reintroducir argparse o para print_help

def calculate_doubling_time_for_column(filepath, count_column_name, min_initial_count=2):
    """
    Calcula el tiempo de duplicación promedio para una columna de conteo específica
    a partir de un archivo SimulationStats.csv.
    (El código de esta función no cambia respecto a la versión anterior)
    """
    # --- Inicio del código de la función (sin cambios) ---
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

    required_base_columns = ['SimulatedTime', count_column_name]
    if not all(col in df.columns for col in required_base_columns):
        missing = [col for col in required_base_columns if col not in df.columns]
        print(f"Error: Faltan columnas requeridas en el CSV para analizar '{count_column_name}'.")
        print(f"Se necesitan al menos: {required_base_columns}")
        print(f"Faltan: {missing}")
        print(f"Columnas encontradas: {list(df.columns)}")
        return None, None
    if 'Pausado' not in df.columns:
         print("Advertencia: Columna 'Pausado' no encontrada. Se procederá asumiendo todos los datos como no pausados.")

    try:
        df['SimulatedTime'] = pd.to_numeric(df['SimulatedTime'], errors='coerce', downcast='float')
        df[count_column_name] = pd.to_numeric(df[count_column_name], errors='coerce', downcast='integer')

        rows_before = len(df)
        df.dropna(subset=['SimulatedTime', count_column_name], inplace=True)
        rows_after = len(df)
        if rows_before > rows_after:
             print(f"Advertencia: Se eliminaron {rows_before - rows_after} filas debido a valores no numéricos en 'SimulatedTime' o '{count_column_name}'.")

        if df.empty:
            print(f"Error: No quedan datos válidos para '{count_column_name}' después de la limpieza numérica.")
            return None, None

        if 'Pausado' in df.columns:
            df['Pausado'] = df['Pausado'].astype(str)
            rows_before_pause_filter = len(df)
            df_active = df[df['Pausado'].str.strip().str.upper() == 'NO'].copy()
            rows_after_pause_filter = len(df_active)
            if rows_before_pause_filter > rows_after_pause_filter:
                print(f"Filtrando datos pausados: {rows_before_pause_filter - rows_after_pause_filter} filas eliminadas.")
        else:
            df_active = df.copy()

        if df_active.empty:
            print(f"Error: No hay datos activos registrados para '{count_column_name}' (después de filtrar por 'Pausado' si existe).")
            return None, None

        df_active = df_active.sort_values(by='SimulatedTime')
        rows_before_dedup = len(df_active)
        df_active = df_active.drop_duplicates(subset=['SimulatedTime'], keep='last')
        rows_after_dedup = len(df_active)
        if rows_before_dedup > rows_after_dedup:
            print(f"Advertencia: Se eliminaron {rows_before_dedup - rows_after_dedup} filas con 'SimulatedTime' duplicado.")

    except KeyError as e:
        print(f"Error inesperado de KeyError: Falta la columna '{e}' durante la limpieza.")
        return None, None
    except Exception as e:
        print(f"Error durante la limpieza o conversión de datos para '{count_column_name}': {e}")
        return None, None

    if df_active.empty:
        print(f"Error: No quedan datos válidos para '{count_column_name}' después de la limpieza y filtrado.")
        return None, None

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
             break

        target_count = current_count * 2
        future_data = df_active.loc[df_active.index > current_index]
        doubled_indices = future_data[future_data[count_column_name] >= target_count].index

        if not doubled_indices.empty:
            next_index = doubled_indices[0]
            next_time = df_active.loc[next_index, 'SimulatedTime']
            next_count = df_active.loc[next_index, count_column_name]
            time_elapsed = next_time - current_time

            if time_elapsed > 1e-9:
                doubling_times.append(time_elapsed)
                print(f"  Duplicación ('{count_column_name}') encontrada: De {current_count} (T={current_time:.2f}) a {next_count} (T={next_time:.2f}). Tiempo: {time_elapsed:.2f}")
                current_index = next_index
            else:
                print(f"  Advertencia: Tiempo de duplicación no positivo o muy pequeño ({time_elapsed:.4f}) para '{count_column_name}' de T={current_time:.2f} a T={next_time:.2f}. Buscando siguiente punto.")
                indices_after_current = df_active.index[df_active.index > current_index]
                if not indices_after_current.empty:
                    current_index = indices_after_current[0]
                else:
                    print("No hay más puntos de datos después del evento de tiempo no positivo.")
                    current_index = None
        else:
            print(f"No se encontró duplicación futura para '{count_column_name}' con conteo {current_count} (T={current_time:.2f}). Fin del análisis para esta columna.")
            current_index = None

    if doubling_times:
        average_dt = np.mean(doubling_times)
        std_dt = np.std(doubling_times)
        print(f"\nSe encontraron {len(doubling_times)} eventos de duplicación para '{count_column_name}'.")
        print(f"Tiempos individuales: {[round(t, 2) for t in doubling_times]}")
        return average_dt, std_dt
    else:
        print(f"\nNo se pudo calcular ningún tiempo de duplicación para '{count_column_name}'.")
        return None, None
    # --- Fin del código de la función ---


# --- Ejecución del Script ---
if __name__ == "__main__":

    # --- PARÁMETROS DE CONFIGURACIÓN ---
    csv_filepath = r"C:\Users\icace\AppData\LocalLow\DefaultCompany\InitialSetup\SimulationLoggerData\Test\SimulationStats.csv"

    target_doubling_times = {
        'EColi': 1080.0,
        'SCerevisiae': 5400.0,
        'Organism count': 0,
        'NoAnalizar': 0
    }

    min_count_for_analysis = 2
    tolerance_percent = 10.0
    # --- FIN DE PARÁMETROS DE CONFIGURACIÓN ---

    tolerance_fraction = tolerance_percent / 100.0
    results = {}

    print(f"\n=== Iniciando Análisis de Tiempos de Duplicación ===")
    print(f"Archivo: {csv_filepath}")
    print(f"Conteo mínimo inicial para análisis: {min_count_for_analysis}")
    print(f"Tolerancia aceptable: ±{tolerance_percent}%")
    print("Tiempos de duplicación esperados (0 = no analizar):")
    for org, time in target_doubling_times.items():
        print(f"  - {org}: {time}")

    # Iterar sobre los organismos definidos en target_doubling_times
    for organism_name, target_dt in target_doubling_times.items():
        if target_dt > 0:
            avg_dt, std_dt = calculate_doubling_time_for_column(csv_filepath, organism_name, min_count_for_analysis)

            error_percent = None
            within_tolerance_status = "N/A"
            lower_bound = target_dt * (1 - tolerance_fraction) # Calcular siempre el rango
            upper_bound = target_dt * (1 + tolerance_fraction)

            if avg_dt is not None:
                # Calcular error relativo porcentual
                error_percent = abs(avg_dt - target_dt) / target_dt * 100

                # Comprobar si está dentro de la tolerancia
                if lower_bound <= avg_dt <= upper_bound:
                    within_tolerance_status = "Dentro"
                else:
                    within_tolerance_status = "Fuera"
            # Si avg_dt es None, error_percent y within_tolerance_status se quedan como None/N/A

            results[organism_name] = {
                'target': target_dt,
                'lower_bound': lower_bound, # Guardar límite inferior
                'upper_bound': upper_bound, # Guardar límite superior
                'average': avg_dt,
                'std_dev': std_dt,
                'error_percent': error_percent,
                'status': within_tolerance_status
            }
            print("\n")
        else:
            print(f"\n--- Omitiendo análisis para '{organism_name}' (tiempo esperado = 0) ---\n")


    # --- Generar la Tabla de Precisión Paramétrica ---
    print("=" * 120) # Ajustar ancho para nueva columna
    print(f"=== Tabla de Precisión Paramétrica (Tolerancia: ±{tolerance_percent}%) ===")
    print("=" * 120)
    print("Prompt:")
    print("Una EColi y una SCerevisiae. La EColi debe ser de color verde esmeralda, duplicarse cada 18 minutos y el hijo se separa del padre cuando alcanza el 72% del crecimiento. La SCerevisiae debe ser de color dorado, duplicarse cada 90 minutos y el hijo se separa del padre cuando alcanza el 65% del crecimiento.")
    # Encabezado de la tabla con la nueva columna para el rango
    header = (f"{'Organismo':<20} | {'DT Esperado':<15} | {'Rango Permitido (±{tolerance_percent}%)':<25} | "
              f"{'DT Calculado (Avg)':<20} | {'Std Dev':<10} | {'Error (%)':<10} | {'Status':<10}")
    print(header)
    print("-" * len(header))

    # Filas de la tabla
    for organism_name, data in results.items():
        target_str = f"{data['target']:.2f}"
        # Formatear la nueva columna del rango
        range_str = f"[{data['lower_bound']:.2f}, {data['upper_bound']:.2f}]"
        avg_str = f"{data['average']:.3f}" if data['average'] is not None else "No calculado"
        std_str = f"{data['std_dev']:.3f}" if data['std_dev'] is not None else "N/A"
        err_str = f"{data['error_percent']:.2f}%" if data['error_percent'] is not None else "N/A"
        status_str = data['status']

        print(f"{organism_name:<20} | {target_str:<15} | {range_str:<25} | "
              f"{avg_str:<20} | {std_str:<10} | {err_str:<10} | {status_str:<10}")

    # Imprimir organismos omitidos
    omitted = [org for org, time in target_doubling_times.items() if time <= 0]
    if omitted:
        print("-" * len(header))
        print(f"Organismos omitidos (DT Esperado = 0): {', '.join(omitted)}")

    print("=" * 120)