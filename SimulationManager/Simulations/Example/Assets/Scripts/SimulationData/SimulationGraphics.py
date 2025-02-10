import os
import pandas as pd
import matplotlib.pyplot as plt

def main():
    # Ruta del CSV y carpeta de salida
    csv_path = r"C:\Users\IVAN\AppData\LocalLow\DefaultCompany\InitialSetup\SimulationStats.csv"
    output_folder = r"C:\Users\IVAN\AppData\LocalLow\DefaultCompany\InitialSetup\Graficos"

    # Crear la carpeta de salida si no existe
    os.makedirs(output_folder, exist_ok=True)

    # Cargar el CSV usando ';' como separador
    try:
        df = pd.read_csv(csv_path, sep=";", engine="python")
    except Exception as e:
        print("Error al leer el archivo CSV:", e)
        return

    # Limpiar nombres de columnas y eliminar espacios en blanco
    df.columns = df.columns.str.strip()

    # Convertir Timestamp a formato datetime (día-mes-año hora:minuto:segundo)
    try:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="%d-%m-%Y %H:%M:%S")
    except Exception as e:
        print("Error al convertir la columna Timestamp:", e)
        return

    # --- Gráfico 1: FPS over Time ---
    plt.figure(figsize=(12, 6))
    plt.plot(df["Timestamp"], df["FPS"], marker="o", linestyle="-", color="blue")
    plt.title("FPS over Time")
    plt.xlabel("Timestamp")
    plt.ylabel("FPS")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, "fps_over_time.png"))
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
    plt.savefig(os.path.join(output_folder, "time_comparison.png"))
    plt.close()

    # --- Gráfico 3: Organism Counts over Time ---
    plt.figure(figsize=(12, 6))
    for col in ["Cube", "EColi", "SCerevisiae"]:
        if col in df.columns:
            plt.plot(df["Timestamp"], df[col], label=col, marker="o", linestyle="-")
    plt.title("Organism Counts over Time")
    plt.xlabel("Timestamp")
    plt.ylabel("Count")
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, "organism_counts.png"))
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
        plt.savefig(os.path.join(output_folder, "total_organisms.png"))
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
        plt.savefig(os.path.join(output_folder, "frame_count.png"))
        plt.close()

    # --- Gráfico 6: FPS Distribution ---
    plt.figure(figsize=(12, 6))
    plt.hist(df["FPS"], bins=20, color="green", edgecolor="black")
    plt.title("FPS Distribution")
    plt.xlabel("FPS")
    plt.ylabel("Frequency")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, "fps_histogram.png"))
    plt.close()

    # --- Gráfico 7: Total Organisms vs FPS (Media de FPS por cantidad de organismos) ---
    if "Cantidad de organismos" in df.columns:
        df_grouped = df.groupby("Cantidad de organismos")["FPS"].mean().reset_index()

        plt.figure(figsize=(12, 6))
        plt.plot(df_grouped["Cantidad de organismos"], df_grouped["FPS"], marker="o", linestyle="-", color="red")
        plt.title("Average FPS per Total Organisms")
        plt.xlabel("Total Organisms")
        plt.ylabel("Average FPS")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(output_folder, "total_organisms_vs_fps.png"))
        plt.close()

    # --- Gráfico 8: Organisms per Simulated Time ---
    if "SimulatedTime" in df.columns:
        plt.figure(figsize=(12, 6))
        for col in ["Cube", "EColi", "SCerevisiae"]:
            if col in df.columns:
                plt.plot(df["SimulatedTime"], df[col], label=col, marker="o", linestyle="-")
        plt.title("Organism Count over Simulated Time")
        plt.xlabel("Simulated Time (s)")
        plt.ylabel("Organism Count")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(output_folder, "organisms_vs_simulated_time.png"))
        plt.close()

    print("Se han generado los gráficos y se han guardado en:", output_folder)

if __name__ == "__main__":
    main()
