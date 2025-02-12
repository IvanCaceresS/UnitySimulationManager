import os
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

def main():
    # Verificar que se haya proporcionado el nombre de la simulación como argumento
    if len(sys.argv) < 2:
        print("Uso: python SimulationGraphics.py <nombre_simulacion>")
        return
    simulation_name = sys.argv[1]
    
    # Construir la ruta: My Documents\SimulationLoggerData\<simulationName>
    documents_path = Path.home() / "Documents"
    simulation_folder = documents_path / "SimulationLoggerData" / simulation_name
    
    # Definir la ruta del CSV y la carpeta de salida para los gráficos
    csv_path = simulation_folder / "SimulationStats.csv"
    output_folder = simulation_folder / "Graficos"
    
    # Crear la carpeta de salida si no existe
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Verificar la existencia del CSV
    if not csv_path.exists():
        print("El archivo CSV no existe en:", csv_path)
        return

    # Cargar el CSV usando ';' como separador
    try:
        df = pd.read_csv(csv_path, sep=";", engine="python")
    except Exception as e:
        print("Error al leer el archivo CSV:", e)
        return

    # Limpiar nombres de columnas (eliminar espacios en blanco)
    df.columns = df.columns.str.strip()

    # Verificar que exista la columna "Timestamp"
    if "Timestamp" not in df.columns:
        print("[Error] La columna 'Timestamp' no se encontró en el CSV.")
        return

    # Filtrar filas donde la columna Timestamp sea "0" (o que al quitar espacios resulte "0")
    df = df[df["Timestamp"].str.strip() != "0"]

    # Reemplazar múltiples espacios por uno solo (por si hay "12-02-2025  16:23:05")
    df["Timestamp"] = df["Timestamp"].astype(str).str.replace(r'\s+', ' ', regex=True)

    # Convertir la columna Timestamp a formato datetime (día-mes-año hora:minuto:segundo)
    try:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="%d-%m-%Y %H:%M:%S", errors="coerce")
    except Exception as e:
        print("Error al convertir la columna Timestamp:", e)
        return

    # Eliminar filas que no se pudieron convertir (NaT)
    df = df.dropna(subset=["Timestamp"])

    # --- Identificar las columnas de organismos ---
    # Asumiendo que las primeras 7 columnas son fijas y la última es "Cantidad de organismos"
    # Tomamos todo lo que quede en medio como columnas de organismos.
    # Alternativamente, podrías usar un set con los nombres fijos y filtrar.
    known_columns = [
        "Timestamp", "FPS", "RealTime", "SimulatedTime",
        "DeltaTime", "FrameCount", "Pausado", "Cantidad de organismos"
    ]
    # Filtramos las que no sean parte de las conocidas:
    organism_columns = [col for col in df.columns if col not in known_columns]

    # --- Gráfico 1: FPS over Time ---
    plt.figure(figsize=(12, 6))
    plt.plot(df["Timestamp"], df["FPS"], marker="o", linestyle="-", color="blue")
    plt.title("FPS over Time")
    plt.xlabel("Timestamp")
    plt.ylabel("FPS")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(str(output_folder / "fps_over_time.png"))
    plt.close()

    # --- Gráfico 2: RealTime vs SimulatedTime ---
    plt.figure(figsize=(12, 6))
    plt.plot(df["Timestamp"], df["RealTime"], label="RealTime", marker="o", linestyle="-")
    plt.plot(df["Timestamp"], df["SimulatedTime"], label="SimulatedTime", marker="o", linestyle="-", color="orange")
    plt.title("RealTime vs SimulatedTime")
    plt.xlabel("Timestamp")
    plt.ylabel("Time (s)")
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(str(output_folder / "time_comparison.png"))
    plt.close()

    # --- Gráfico 3: Organism Counts over Time ---
    # Graficamos todas las columnas de organismos
    if organism_columns:
        plt.figure(figsize=(12, 6))
        for col in organism_columns:
            plt.plot(df["Timestamp"], df[col], label=col, marker="o", linestyle="-")
        plt.title("Organism Counts over Time")
        plt.xlabel("Timestamp")
        plt.ylabel("Count")
        plt.xticks(rotation=45)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(str(output_folder / "organism_counts.png"))
        plt.close()

    # --- Gráfico 4: Total Organisms over Time ---
    if "Cantidad de organismos" in df.columns:
        plt.figure(figsize=(12, 6))
        plt.plot(df["Timestamp"], df["Cantidad de organismos"], marker="o", linestyle="-", color="purple")
        plt.title("Total Organisms over Time")
        plt.xlabel("Timestamp")
        plt.ylabel("Total Count")
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(str(output_folder / "total_organisms.png"))
        plt.close()

    # --- Gráfico 5: Frame Count over Time ---
    if "FrameCount" in df.columns:
        plt.figure(figsize=(12, 6))
        plt.plot(df["Timestamp"], df["FrameCount"], marker="o", linestyle="-", color="orange")
        plt.title("Frame Count over Time")
        plt.xlabel("Timestamp")
        plt.ylabel("Frame Count")
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(str(output_folder / "frame_count.png"))
        plt.close()

    # --- Gráfico 6: FPS Distribution ---
    plt.figure(figsize=(12, 6))
    plt.hist(df["FPS"], bins=20, color="green", edgecolor="black")
    plt.title("FPS Distribution")
    plt.xlabel("FPS")
    plt.ylabel("Frequency")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(str(output_folder / "fps_histogram.png"))
    plt.close()

    # --- Gráfico 7: Average FPS per Total Organisms ---
    if "Cantidad de organismos" in df.columns:
        df_grouped = df.groupby("Cantidad de organismos")["FPS"].mean().reset_index()
        plt.figure(figsize=(12, 6))
        plt.plot(df_grouped["Cantidad de organismos"], df_grouped["FPS"], marker="o", linestyle="-", color="red")
        plt.title("Average FPS per Total Organisms")
        plt.xlabel("Total Organisms")
        plt.ylabel("Average FPS")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(str(output_folder / "total_organisms_vs_fps.png"))
        plt.close()

    # --- Gráfico 8: Organisms per Simulated Time ---
    if "SimulatedTime" in df.columns and organism_columns:
        plt.figure(figsize=(12, 6))
        for col in organism_columns:
            plt.plot(df["SimulatedTime"], df[col], label=col, marker="o", linestyle="-")
        plt.title("Organism Count over Simulated Time")
        plt.xlabel("Simulated Time (s)")
        plt.ylabel("Organism Count")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(str(output_folder / "organisms_vs_simulated_time.png"))
        plt.close()

    print("SimulationGraphics: Los gráficos se han generado y se han guardado en:", output_folder)

if __name__ == "__main__":
    main()
