import sys
import os
import traceback
import shutil
import subprocess
import platform
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import customtkinter as ctk
from tkinter import messagebox, filedialog
from tkinter import ttk
from dotenv import load_dotenv
import psutil
import openai
import math
from PIL import Image, ImageTk
from openai import error as openai_error_v0
#import tiktoken
import re
from typing import Union, Tuple, Dict
import numpy as np
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score

if getattr(sys, 'frozen', False):
    APP_BASE_DIR = Path(sys.executable).resolve().parent.parent.parent.parent
else:
    APP_BASE_DIR = Path(__file__).resolve().parent

AuthenticationError_v0 = openai_error_v0.AuthenticationError
InvalidRequestError_v0 = openai_error_v0.InvalidRequestError
APIConnectionError_v0 = openai_error_v0.APIConnectionError
OPENAI_V0_ERROR_IMPORTED = True
OPENAI_V1_CLIENT_EXISTS = False

unity_path_ok = False
unity_version_ok = False
unity_projects_path_ok = False
apis_key_ok = False
apis_models_ok = False
initial_verification_complete = False
is_build_running = False
UNITY_EXECUTABLE = None
UNITY_PROJECTS_PATH = None
OPENAI_API_KEY = None
FINE_TUNED_MODEL_NAME = None
SECONDARY_FINE_TUNED_MODEL_NAME = None
UNITY_REQUIRED_VERSION_STRING = "6000.0.32f1"
SIMULATIONS_DIR = APP_BASE_DIR / "Simulations"
SIMULATION_PROJECT_NAME = "Simulation"
SIMULATION_PROJECT_PATH = None
ASSETS_FOLDER = None
STREAMING_ASSETS_FOLDER = None
SIMULATION_LOADED_FILE = None
last_simulation_loaded = None
all_simulations_data = []
play_icon_text = "▶"
delete_icon_text = "🗑️"
loaded_indicator_text = "✓"
tooltip_window = None
tooltip_delay = 700
tooltip_job_id = None
logo_photo_ref = None
ICON_PATH_MAC = APP_BASE_DIR / "img" / "icono.icns"
LOGO_PATHS = [APP_BASE_DIR / "img" / "logo_light.png", APP_BASE_DIR / "img" / "logo_dark.png"]
LOGO_WIDTH = 200
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")
APP_FONT = ("Segoe UI", 11)
APP_FONT_BOLD = ("Segoe UI", 11, "bold")
TITLE_FONT = ("Times New Roman", 22, "bold")
STATUS_FONT = ("Segoe UI", 10)
TREEVIEW_FONT = ("Segoe UI", 10)
TREEVIEW_HEADER_FONT = ("Segoe UI", 10, "bold")
COLOR_SUCCESS_GENERAL = ("#28a745", "#4CAF50")
COLOR_DANGER_GENERAL = ("#C62828", "#EF5350")
COLOR_INFO_GENERAL = ("#218838", "#66BB6A")
COLOR_WARNING_GENERAL = ("#E53935", "#E53935")
COLOR_DISABLED_GENERAL = ("#BDBDBD", "#757575")
COLOR_SIDEBAR_BG = None

def get_color_mode_index():
    return 1 if ctk.get_appearance_mode() == "Dark" else 0

_NEUTRAL_FG_COLOR = ("#A0A0A0", "#616161")
_NEUTRAL_HOVER_COLOR = ("#888888", "#757575")
_NEUTRAL_TEXT_COLOR = ("#000000", "#FFFFFF")
BTN_SETTINGS_FG_COLOR = _NEUTRAL_FG_COLOR
BTN_SETTINGS_HOVER_COLOR = _NEUTRAL_HOVER_COLOR
BTN_SETTINGS_TEXT_COLOR = _NEUTRAL_TEXT_COLOR
BTN_VERIFY_FG_COLOR = _NEUTRAL_FG_COLOR
BTN_VERIFY_HOVER_COLOR = _NEUTRAL_HOVER_COLOR
BTN_VERIFY_TEXT_COLOR = _NEUTRAL_TEXT_COLOR
BTN_ABOUT_FG_COLOR = _NEUTRAL_FG_COLOR
BTN_ABOUT_HOVER_COLOR = _NEUTRAL_HOVER_COLOR
BTN_ABOUT_TEXT_COLOR = _NEUTRAL_TEXT_COLOR
BTN_UNITY_DOWN_FG_COLOR = ("#4CAF50", "#4CAF50")
BTN_UNITY_DOWN_HOVER_COLOR = ("#388E3C", "#66BB6A")
BTN_UNITY_DOWN_TEXT_COLOR = ("#FFFFFF", "#FFFFFF")
BTN_EXIT_FG_COLOR = ("#E53935", "#E53935")
BTN_EXIT_HOVER_COLOR = ("#C62828", "#EF5350")
BTN_EXIT_TEXT_COLOR = ("#FFFFFF", "#FFFFFF")
BTN_RELOAD_FG_COLOR = ("#1E88E5", "#1E88E5")
BTN_RELOAD_HOVER_COLOR = ("#1565C0", "#42A5F5")
BTN_RELOAD_TEXT_COLOR = ("#FFFFFF", "#FFFFFF")
BTN_GRAPH_FG_COLOR = ("#673AB7", "#673AB7")
BTN_GRAPH_HOVER_COLOR = ("#512DA8", "#7E57C2")
BTN_GRAPH_TEXT_COLOR = ("#FFFFFF", "#FFFFFF")
BTN_CREATE_FG_COLOR = ("#28a745", "#4CAF50")
BTN_CREATE_HOVER_COLOR = ("#218838", "#66BB6A")
BTN_CREATE_TEXT_COLOR = ("#FFFFFF", "#FFFFFF")
BTN_CLEARSEARCH_FG_COLOR = ("#E53935", "#E53935")
BTN_CLEARSEARCH_HOVER_COLOR = ("#C62828", "#EF5350")
BTN_CLEARSEARCH_TEXT_COLOR = ("#FFFFFF", "#FFFFFF")

UNITY_PRODUCT_NAME = "InitialSetup"
LOG_SUBFOLDER = "SimulationLoggerData"
CSV_FILENAME = "SimulationStats.csv"
GRAPHICS_SUBFOLDER = "Graphics"
DOTENV_PATH = APP_BASE_DIR / ".env"

def find_unity_persistent_path(product_name: str) -> Union[Path, None]:
    system = platform.system()
    home = Path.home()
    search_base: Union[Path, None] = None
    potential_paths: list[Path] = []

    try:
        if system == "Darwin":
            search_base = home / 'Library' / 'Application Support'
        else:
            print(f"  [PathFinder] Error: OS '{system}' not supported for automatic search (macOS only).")
            return None

        if not search_base or not search_base.is_dir():
            print(f"  [PathFinder] Error: Base directory '{search_base}' does not exist or is not accessible.")
            return None

        for company_dir in search_base.iterdir():
            if company_dir.is_dir():
                _potential_product_path = company_dir / product_name
                if _potential_product_path.is_dir():
                    potential_paths.append(_potential_product_path)

        if len(potential_paths) == 1:
            found_path = potential_paths[0]
            return found_path
        elif len(potential_paths) == 0:
            print(f"  [PathFinder] Error: Product folder '{product_name}' not found under '{search_base}'.")
            print(f"  Ensure the Unity application ('{product_name}') has run at least once and created its data folder.")
            return None
        else:
            print(f"  [PathFinder] Error: Ambiguity! Multiple paths found for '{product_name}':")
            for p in potential_paths: print(f"    - {p}")
            print(f"  Clean up old or duplicate installations.")
            return None

    except PermissionError:
        print(f"  [PathFinder] Permission error attempting to search in '{search_base}'.")
        return None
    except Exception as e:
        print(f"  [PathFinder] Unexpected error during product path search: {e}")
        traceback.print_exc()
        return None

def find_simulation_data_path(simulation_name: str) -> Union[Path, None]:
    if not simulation_name:
        print("[find_simulation_data_path] Error: Empty simulation name provided.")
        return None
    product_base_path = find_unity_persistent_path(UNITY_PRODUCT_NAME)
    if not product_base_path:
        print(f"[find_simulation_data_path] Could not find the base product folder '{UNITY_PRODUCT_NAME}' to locate data for '{simulation_name}'.")
        return None
    simulation_path = product_base_path / LOG_SUBFOLDER / simulation_name
    return simulation_path

def exponential_func(x, a, b):
    return a * np.exp(b * x)

def SimulationGraphics(simulation_name):
    if not simulation_name:
        print("Error: A simulation name must be provided to the SimulationGraphics function.")
        return

    print(f"\n--- Starting Graph Generation for Simulation: '{simulation_name}' ---")
    print("Step 1: Locating data folder...")
    simulation_folder = find_simulation_data_path(simulation_name)

    if not simulation_folder:
        print(f"Critical Error: Could not locate data folder for '{simulation_name}'. Aborting graph generation.")
        return

    print(f"  Data folder located: {simulation_folder}")
    csv_path = simulation_folder / CSV_FILENAME
    output_folder = simulation_folder / GRAPHICS_SUBFOLDER
    print(f"  Expected CSV path: {csv_path}")
    print(f"  Output folder for graphs: {output_folder}")

    try:
        print(f"Step 3: Ensuring graphics folder exists...")
        output_folder.mkdir(parents=True, exist_ok=True)
        print(f"  Folder '{output_folder}' ensured.")
    except OSError as e:
         print(f"  Critical Error creating/ensuring output folder '{output_folder}': {e}. Aborting.")
         return

    print(f"Step 4: Verifying and reading CSV file...")
    if not csv_path.is_file():
        print(f"  Error: CSV file not found at the expected path: {csv_path}")
        return

    try:
        df = pd.read_csv(csv_path, sep=";", engine="python")
        if df.empty:
             print(f"  Error: The CSV file '{csv_path}' is empty.")
             return
        print(f"  CSV read successful ({len(df)} rows).")
    except pd.errors.EmptyDataError:
         print(f"  Error: The CSV file '{csv_path}' is empty or contains no data.")
         return
    except Exception as e:
        print(f"  Critical Error reading or parsing CSV file '{csv_path}': {e}")
        traceback.print_exc()
        return

    print(f"Step 5: Processing data...")
    try:
        df.columns = df.columns.str.strip()
        if "Timestamp" not in df.columns:
            print("  Error: Required column 'Timestamp' not found in the CSV.")
            return
        df["Timestamp_str"] = df["Timestamp"].astype(str).str.strip()
        df = df[df["Timestamp_str"].str.lower().isin(['0', '']) == False].copy()
        df["Timestamp"] = pd.to_datetime(df["Timestamp_str"], format="%d-%m-%Y %H:%M:%S", errors='coerce')
        initial_rows = len(df)
        df.dropna(subset=["Timestamp"], inplace=True)
        rows_dropped = initial_rows - len(df)
        if rows_dropped > 0:
            print(f"  Warning: Removed {rows_dropped} rows with invalid Timestamp format.")
        if df.empty:
            print("  Error: No valid data remaining after processing Timestamps.")
            return
        df.sort_values(by="Timestamp", inplace=True)
        print("  Data processing completed.")
    except Exception as e:
        print(f"  Error during data processing: {e}")
        traceback.print_exc()
        return

    known_columns = {"Timestamp", "Timestamp_str", "FPS", "RealTime", "SimulatedTime", "DeltaTime", "FrameCount", "Pausado"}
    organism_columns = sorted([col for col in df.columns if col not in known_columns])
    print(f"  Identified organism columns: {organism_columns}")

    print(f"Step 7: Generating graphs...")
    plot_generated_count = 0

    if "FPS" in df.columns:
        plt.figure(figsize=(12, 6))
        plt.plot(df["Timestamp"], df["FPS"], marker=".", linestyle="-", color="blue")
        plt.title(f"FPS over Time ({simulation_name})")
        plt.xlabel("Timestamp")
        plt.ylabel("FPS")
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()
        try:
            plt.savefig(str(output_folder / "fps_over_time.png"))
            plot_generated_count += 1
        except Exception as e:
            print(f"Error saving fps_over_time.png: {e}")
        plt.close()
    else:
        print("Column 'FPS' not found, skipping FPS over Time graph.")

    if "RealTime" in df.columns and "SimulatedTime" in df.columns:
        plt.figure(figsize=(12, 6))
        plt.plot(df["Timestamp"], df["RealTime"], label="RealTime", marker=".", linestyle="-")
        plt.plot(df["Timestamp"], df["SimulatedTime"], label="SimulatedTime", marker=".", linestyle="-", color="orange")
        plt.title(f"RealTime vs SimulatedTime ({simulation_name})")
        plt.xlabel("Timestamp")
        plt.ylabel("Time (s)")
        plt.xticks(rotation=45, ha='right')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()
        try:
            plt.savefig(str(output_folder / "time_comparison.png"))
            plot_generated_count += 1
        except Exception as e:
            print(f"Error saving time_comparison.png: {e}")
        plt.close()
    else:
         print("Columns 'RealTime' or 'SimulatedTime' not found, skipping Time Comparison graph.")

    if organism_columns:
        plt.figure(figsize=(12, 6))
        plotted_any_organism = False
        for col in organism_columns:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                plt.plot(df["Timestamp"], df[col], label=col, marker=".", linestyle="-")
                plotted_any_organism = True
            else:
                print(f"Warning: Skipping non-numeric or missing organism column: '{col}'")

        if plotted_any_organism:
            plt.title(f"Organism Counts over Time ({simulation_name})")
            plt.xlabel("Timestamp")
            plt.ylabel("Count")
            plt.xticks(rotation=45, ha='right')
            plt.legend()
            plt.grid(True, linestyle='--', alpha=0.6)
            plt.tight_layout()
            try:
                plt.savefig(str(output_folder / "organism_counts.png"))
                plot_generated_count += 1
            except Exception as e:
                print(f"Error saving organism_counts.png: {e}")
        plt.close()
    else:
        print("No specific organism columns found, skipping Organism Counts graph.")

    if "Organism count" in df.columns:
        plt.figure(figsize=(12, 6))
        plt.plot(df["Timestamp"], df["Organism count"], marker=".", linestyle="-", color="purple")
        plt.title(f"Total Organisms over Time ({simulation_name})")
        plt.xlabel("Timestamp")
        plt.ylabel("Total Count")
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()
        try:
            plt.savefig(str(output_folder / "total_organisms.png"))
            plot_generated_count += 1
        except Exception as e:
            print(f"Error saving total_organisms.png: {e}")
        plt.close()
    else:
        print("Column 'Organism count' not found, skipping Total Organisms graph.")

    if "FrameCount" in df.columns:
        plt.figure(figsize=(12, 6))
        plt.plot(df["Timestamp"], df["FrameCount"], marker=".", linestyle="-", color="darkcyan")
        plt.title(f"Frame Count over Time ({simulation_name})")
        plt.xlabel("Timestamp")
        plt.ylabel("Frame Count")
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()
        try:
            plt.savefig(str(output_folder / "frame_count.png"))
            plot_generated_count += 1
        except Exception as e:
            print(f"Error saving frame_count.png: {e}")
        plt.close()
    else:
        print("Column 'FrameCount' not found, skipping Frame Count graph.")

    if "FPS" in df.columns and not df["FPS"].isnull().all():
        plt.figure(figsize=(12, 6))
        plt.hist(df["FPS"].dropna(), bins=20, color="green", edgecolor="black")
        plt.title(f"FPS Distribution ({simulation_name})")
        plt.xlabel("FPS")
        plt.ylabel("Frequency")
        plt.grid(True, axis='y', linestyle='--', alpha=0.6)
        plt.tight_layout()
        try:
            plt.savefig(str(output_folder / "fps_histogram.png"))
            plot_generated_count += 1
        except Exception as e:
             print(f"Error saving fps_histogram.png: {e}")
        plt.close()
    elif "FPS" in df.columns:
         print("Column 'FPS' found but contains no valid data, skipping FPS histogram.")

    if "Organism count" in df.columns and "FPS" in df.columns and not df["Organism count"].isnull().all() and not df["FPS"].isnull().all():
        if pd.api.types.is_numeric_dtype(df["Organism count"]):
            df_groupable = df.dropna(subset=["Organism count", "FPS"])
            try:
                 df_groupable["Organism count"] = df_groupable["Organism count"].astype(int)
            except ValueError:
                 print("Warning: 'Organism count' contains non-integer values, grouping by float values.")
            df_grouped = df_groupable.groupby("Organism count")["FPS"].mean().reset_index()
            if not df_grouped.empty:
                plt.figure(figsize=(12, 6))
                plt.plot(df_grouped["Organism count"], df_grouped["FPS"], marker="o", linestyle="-", color="red")
                plt.title(f"Average FPS per Total Organisms ({simulation_name})")
                plt.xlabel("Total Organisms")
                plt.ylabel("Average FPS")
                plt.grid(True, linestyle='--', alpha=0.6)
                plt.tight_layout()
                try:
                    plt.savefig(str(output_folder / "total_organisms_vs_fps.png"))
                    plot_generated_count += 1
                except Exception as e:
                    print(f"Error saving total_organisms_vs_fps.png: {e}")
                plt.close()
            else:
                print("Could not group data for Average FPS per Total Organisms graph.")
        else:
            print("Column 'Organism count' is not numeric, skipping Average FPS per Total Organisms graph.")

    if "SimulatedTime" in df.columns and organism_columns:
        if pd.api.types.is_numeric_dtype(df["SimulatedTime"]) and not df["SimulatedTime"].isnull().all():
            plt.figure(figsize=(14, 7))
            plotted_something = False
            actual_organisms_plotted = []
            time_data_full = df["SimulatedTime"]
            for col in organism_columns:
                if col == "Organism count":
                    print(f"  Skipping column '{col}' from Graph 8 as requested.")
                    continue
                if col in df.columns and pd.api.types.is_numeric_dtype(df[col]) and not df[col].isnull().all():
                    valid_indices = df[col].notna() & time_data_full.notna()
                    time_data_clean = time_data_full[valid_indices].values
                    organism_data_clean = df.loc[valid_indices, col].values
                    if len(time_data_clean) > 0:
                        plt.plot(time_data_clean, organism_data_clean, label=f"{col}", marker=".", linestyle="-", alpha=0.7)
                        plotted_something = True
                        if col not in actual_organisms_plotted:
                            actual_organisms_plotted.append(col)
                    else:
                        print(f"  Warning: No valid numeric data for '{col}' on Y-axis or corresponding 'SimulatedTime'.")
                        continue
                    if len(time_data_clean) >= 2:
                        try:
                            initial_a = organism_data_clean[0] if organism_data_clean[0] > 0 else 1.0
                            if np.all(organism_data_clean == organism_data_clean[0]):
                                initial_b = 0.0
                            elif len(time_data_clean) > 1 and organism_data_clean[-1] > initial_a and time_data_clean[-1] > time_data_clean[0]:
                                time_diff = time_data_clean[-1] - time_data_clean[0]
                                if time_diff > 1e-9:
                                    initial_b = np.log(organism_data_clean[-1] / initial_a) / time_diff
                                else:
                                    initial_b = 0.0
                            else:
                                initial_b = 0.01
                            if not np.isfinite(initial_b):
                                initial_b = 0.01
                            p0 = [initial_a, initial_b]
                            bounds = ([0, -np.inf], [np.inf, np.inf])
                            params, covariance = curve_fit(
                                exponential_func,
                                time_data_clean,
                                organism_data_clean,
                                p0=p0,
                                bounds=bounds,
                                maxfev=10000
                            )
                            a_fit, b_fit = params
                            organism_predicted = exponential_func(time_data_clean, a_fit, b_fit)
                            r_squared = r2_score(organism_data_clean, organism_predicted)
                            time_fit = np.linspace(time_data_clean.min(), time_data_clean.max(), 100)
                            organism_fit = exponential_func(time_fit, a_fit, b_fit)
                            label_fit = f"{col} (Exp: a={a_fit:.2f}, b={b_fit:.3f}, R²={r_squared:.2f})"
                            plt.plot(time_fit, organism_fit, label=label_fit, linestyle="--")
                        except RuntimeError:
                            print(f"  Warning: Could not fit exponential curve for '{col}'. Optimization did not converge.")
                        except ValueError as ve:
                            print(f"  Warning: Value error during fitting for '{col}'. Incompatible data? {ve}")
                        except Exception as e:
                            print(f"  Warning: Unexpected error during curve fitting for '{col}': {e}")
                    else:
                        print(f"  Warning: Not enough data points ({len(time_data_clean)}) to fit curve for '{col}'.")
            if plotted_something:
                plt.title(f"Specific Organism Count & Exponential Fit over Simulated Time ({simulation_name})")
                plt.xlabel("Simulated Time (s)")
                plt.ylabel("Organism Count")
                if len(actual_organisms_plotted) > 2:
                    plt.legend(bbox_to_anchor=(1.04, 1), loc="upper left")
                    plt.tight_layout(rect=[0, 0, 0.85, 1])
                else:
                    plt.legend()
                    plt.tight_layout()
                plt.grid(True, linestyle='--', alpha=0.6)
                try:
                    save_path = output_folder / "organisms_vs_simulated_time_fit.png"
                    plt.savefig(str(save_path))
                    plot_generated_count += 1
                    print(f"  Graph 'organisms_vs_simulated_time_fit.png' saved (excluding 'Organism count').")
                except Exception as e:
                    print(f"  Error saving organisms_vs_simulated_time_fit.png: {e}")
            else:
                print("  Nothing plotted for Organisms vs Simulated Time (no valid data or only 'Organism count' found).")
            plt.close()
        elif "SimulatedTime" in df.columns and df["SimulatedTime"].isnull().all():
            print("Column 'SimulatedTime' exists but all values are null, skipping Organisms vs Simulated Time graph.")
        else:
            print("Column 'SimulatedTime' is not numeric, skipping Organisms vs Simulated Time graph.")
    elif not organism_columns:
        print("No specific organism columns found, skipping Organisms vs Simulated Time graph.")
    else:
        print("Column 'SimulatedTime' not found, skipping Organisms vs Simulated Time graph.")

    print(f"\n--- Graph generation process completed for '{simulation_name}' ---")
    if plot_generated_count > 0:
        print(f"{plot_generated_count} graphs were generated in: {output_folder}")
    else:
        print("No useful graphs were generated due to missing data or issues.")

load_dotenv(dotenv_path=DOTENV_PATH)
openai.api_key = os.getenv("OPENAI_API_KEY")
FINE_TUNED_MODEL_NAME = os.getenv("FINE_TUNED_MODEL_NAME")
SECOND_FINE_TUNED_MODEL_NAME = os.getenv("2ND_FINE_TUNED_MODEL_NAME")

SYSTEM_MESSAGE_PRIMARY = (
    "Eres un modelo especializado en generar código C# para simulaciones de Unity. Considera que los tiempos son en segundos; además, los colores en Unity se expresan en valores RGB divididos en 255. Debes contestar tal cual como se te fue entrenado, sin agregar nada más de lo que se espera en C#. No puedes responder en ningún otro lenguaje de programación ni añadir comentarios o palabras innecesarias. Solo puedes responder a consultas relacionadas con simulaciones en Unity sobre EColi, SCerevisiae o ambas, donde se indiquen: - El color de la(s) célula(s). - El tiempo de duplicación en minutos. - El porcentaje de crecimiento para separarse del padre. Tu respuesta debe incluir estrictamente estos scripts en el orden especificado: - Si se piden ambas (EColi y SCerevisiae): 1.PrefabMaterialCreator.cs, 2.CreatePrefabsOnClick.cs, 3.EColiComponent.cs, 4.SCerevisiaeComponent.cs, 5.EColiSystem.cs, 6.SCerevisiaeSystem.cs. - Si se pide solo EColi: 1.PrefabMaterialCreator.cs, 2.CreatePrefabsOnClick.cs, 3.EColiComponent.cs, 4.EColiSystem.cs. - Si se pide solo SCerevisiae: 1.PrefabMaterialCreator.cs, 2.CreatePrefabsOnClick.cs, 3.SCerevisiaeComponent.cs, 4.SCerevisiaeSystem.cs - Si se pide 2 EColi: 1.PrefabMaterialCreator.cs, 2.CreatePrefabsOnClick.cs, 3.EColi_1Component.cs, 4.EColi_2Component.cs, 5.EColi_1System.cs, 6.EColi_2System.cs. - Si se pide 2 SCerevisiae: 1.PrefabMaterialCreator.cs, 2.CreatePrefabsOnClick.cs, 3.SCerevisiae_1Component.cs, 4.SCerevisiae_2Component.cs, 5.SCerevisiae_1System.cs, 6.SCerevisiae_2System.cs. El formato de cada script debe ser \"1.PrefabMaterialCreator.cs{...}2.CreatePrefabsOnClick.cs{...}\" etc. Cualquier pregunta que no cumpla con las características anteriores será respondida con: \"ERROR FORMATO DE PREGUNTA.\"."
)
SYSTEM_MESSAGE_SECONDARY = (
    "Eres un traductor especializado en simulaciones biológicas para Unity. Tu función exclusiva es convertir descripciones en lenguaje natural en especificaciones técnicas estructuradas para EColi y SCerevisiae. Requisitos obligatorios: 1. Solo procesarás 1 o 2 organismos por solicitud 2. Organismos permitidos: exclusivamente EColi (bacteria) y SCerevisiae (levadura) 3. Parámetros requeridos para cada organismo: - Color (en formato nombre o adjetivo+color) - Tiempo de duplicación (en minutos) - Porcentaje de separación padre-hijo (50-95%) Instrucciones estrictas: • Si la solicitud menciona otros organismos, fenómenos no biológicos, o está fuera del contexto de simulaciones celulares: responde exactamente 'ERROR DE CONTENIDO' • Si la solicitud menciona más de organismos distintos: responde exactamente 'ERROR CANTIDAD EXCEDIDA' • Usa el formato: '[Cantidad] [Organismo]. El [Organismo] debe ser de color [color], duplicarse cada [X] minutos y el hijo se separa del padre cuando alcanza el [Y]% del crecimiento.' • Para múltiples organismos del mismo tipo usa sufijos numéricos (Ej: EColi_1, SCerevisiae_2) • Asigna valores por defecto coherentes cuando el usuario no especifique parámetros"
)

def count_tokens(text: str) -> int:
    # try:
    #     encoding = tiktoken.encoding_for_model(FINE_TUNED_MODEL_NAME if FINE_TUNED_MODEL_NAME else "gpt-3.5-turbo")
    # except Exception:
    #     encoding = tiktoken.get_encoding("cl100k_base")
    # return len(encoding.encode(text))
    return len(text.split())

def check_api_connection() -> bool:
    if not openai.api_key:
        print("Error: OpenAI API key is not set.")
        return False
    try:
        openai.Model.list(limit=1)
        return True
    except AuthenticationError_v0:
        print("Error connecting to API: Authentication failed (Invalid API Key?).")
        return False
    except APIConnectionError_v0 as e:
        print(f"Error connecting to API: Connection issue. {e}")
        return False
    except Exception as e:
        print(f"Error connecting to API: Unexpected error ({type(e).__name__}). {e}")
        return False

def call_api_generic(prompt: str, model_name: str, system_message: str) -> tuple[str, int, int]:
    if not check_api_connection():
        return "Error: API Connection Failed", 0, 0
    if not model_name:
        print(f"Error calling API: Model name is not specified.")
        return "Error: Model Name Missing", 0, 0
    try:
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        input_tokens = count_tokens(system_message) + count_tokens(prompt)
        response = openai.ChatCompletion.create(
            model=model_name,
            messages=messages,
            temperature=0,
            timeout=30
        )
        reply = response.choices[0].message["content"].strip()
        output_tokens = count_tokens(reply)
        return reply, input_tokens, output_tokens
    except InvalidRequestError_v0 as e:
        print(f"Error calling model {model_name}: Invalid Request. {e}")
        return f"Error: Invalid Request (Model '{model_name}' not found or invalid?)", 0, 0
    except AuthenticationError_v0:
        print(f"Error calling model {model_name}: Authentication Error.")
        return "Error: Authentication Failed", 0, 0
    except Exception as e:
        print(f"Error calling model {model_name}: Unexpected error ({type(e).__name__}). {e}")
        return f"Error: API Call Failed ({type(e).__name__})", 0, 0

def call_primary_model(prompt: str) -> tuple[str, int, int]:
    if not FINE_TUNED_MODEL_NAME:
        return "Error: Primary Fine-Tuned Model Name not set in .env", 0, 0
    return call_api_generic(prompt, FINE_TUNED_MODEL_NAME, SYSTEM_MESSAGE_PRIMARY)

def call_secondary_model(prompt: str) -> tuple[str, int, int]:
    model_to_use = SECONDARY_FINE_TUNED_MODEL_NAME
    if not model_to_use:
        print("Warning: Secondary Fine-Tuned Model Name not set. Using primary model for validation.")
        model_to_use = FINE_TUNED_MODEL_NAME
        if not model_to_use:
             return "Error: Neither Secondary nor Primary Model Name is set.", 0, 0
    return call_api_generic(prompt, model_to_use, SYSTEM_MESSAGE_SECONDARY)

def split_braces_outside_strings(code: str) -> str:
    result_lines = []
    in_string = False
    for line in code.splitlines(keepends=True):
        new_line_chars = []
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '"':
                in_string = not in_string
                new_line_chars.append(ch)
            elif ch == '{' and not in_string:
                new_line_chars.append('\n{\n')
            elif ch == '}' and not in_string:
                new_line_chars.append('\n}\n')
            else:
                new_line_chars.append(ch)
            i += 1
        result_lines.append(''.join(new_line_chars))
    return ''.join(result_lines)

def separar_codigos_por_archivo(respuesta: str) -> dict:
    patrones = re.findall(r'(\d+)\.(\w+\.cs)\{(.*?)}(?=\d+\.|$)', respuesta, re.DOTALL)
    if not patrones:
        print("No se encontraron bloques de código en la respuesta.")
        return {}
    codigos = {}
    for _, archivo, contenido in patrones:
        codigos[archivo] = format_csharp(contenido.strip())
    return codigos

def format_csharp(contenido: str) -> str:
    preprocesado = split_braces_outside_strings(contenido)
    preprocesado = re.sub(r';', r';\n', preprocesado)
    preprocesado = re.sub(r'\n\s*\n', '\n', preprocesado)
    lineas = [l.strip() for l in preprocesado.split('\n') if l.strip()]
    nivel_indentacion = 0
    contenido_formateado = []
    indent_char = "    "
    for linea in lineas:
        if linea.startswith("}"):
            nivel_indentacion = max(nivel_indentacion - 1, 0)
        contenido_formateado.append(indent_char * nivel_indentacion + linea)
        if linea.endswith("{"):
            nivel_indentacion += 1
    return "\n".join(contenido_formateado)

def import_codes(codes: dict, simulation_name: str) -> bool:
    base_dir = APP_BASE_DIR
    simulation_folder = base_dir / "Simulations" / simulation_name

    if simulation_folder.exists():
        if simulation_folder.is_dir():
             print(f"Advertencia: La carpeta de simulación '{simulation_name}' ya existe en {simulation_folder}.")
        else:
             print(f"Error: Ya existe un archivo llamado '{simulation_name}' en la ubicación de Simulaciones. Elija otro nombre.")
             return False

    template_folder = base_dir / "Template"
    if not template_folder.exists() or not template_folder.is_dir():
         print(f"Error: No se encontró la carpeta 'Template' en {template_folder}. No se puede crear la simulación.")
         return False

    try:
        if not simulation_folder.exists():
            shutil.copytree(template_folder, simulation_folder)
            print(f"Estructura de Template copiada a: {simulation_folder}")
        else:
            print(f"Usando carpeta de simulación existente: {simulation_folder}")
    except Exception as e:
        print(f"Error al copiar la estructura del Template: {e}")
        return False

    assets_editor_folder = simulation_folder / "Assets" / "Editor"
    assets_scripts_folder = simulation_folder / "Assets" / "Scripts"
    assets_scripts_components = assets_scripts_folder / "Components"
    assets_scripts_systems = assets_scripts_folder / "Systems"
    assets_scripts_general = assets_scripts_folder / "General"

    assets_editor_folder.mkdir(parents=True, exist_ok=True)
    assets_scripts_components.mkdir(parents=True, exist_ok=True)
    assets_scripts_systems.mkdir(parents=True, exist_ok=True)
    assets_scripts_general.mkdir(parents=True, exist_ok=True)

    template_system_path = template_folder / "Assets" / "Scripts" / "Systems" / "GeneralSystem.cs"
    if not template_system_path.exists():
        print(f"Advertencia: No se encontró el archivo template 'GeneralSystem.cs' en {template_system_path}. Los scripts de sistema se escribirán directamente.")
        template_system_path = None

    template_create_path = template_folder / "Assets" / "Scripts" / "General" / "CreatePrefabsOnClick.cs"
    if not template_create_path.exists():
        print(f"Advertencia: No se encontró el archivo template 'CreatePrefabsOnClick.cs' en {template_create_path}. Este script se escribirá directamente.")
        template_create_path = None

    files_processed = []
    for file_name, content in codes.items():
        dest_path = ""
        new_content = content
        try:
            if file_name == "PrefabMaterialCreator.cs":
                dest_path = assets_editor_folder / file_name
                new_content = (
                    "#if UNITY_EDITOR\n"
                    "using UnityEngine;\n"
                    "using UnityEditor;\n"
                    "using System.IO;\n\n"
                    f"{content}\n"
                    "#endif\n"
                )
            elif "Component.cs" in file_name:
                dest_path = assets_scripts_components / file_name
            elif "System.cs" in file_name:
                dest_path = assets_scripts_systems / file_name
                if template_system_path:
                    try:
                        with open(template_system_path, "r", encoding="utf-8") as f:
                            template_lines = f.readlines()
                        organism_name = file_name.replace("System.cs", "")
                        new_class_declaration = f"public partial class {organism_name}System : SystemBase"
                        new_component_declaration = f"{organism_name}Component"
                        temp_content = "".join(template_lines)
                        temp_content = temp_content.replace("public partial class GeneralSystem : SystemBase", new_class_declaration)
                        temp_content = temp_content.replace("GeneralComponent", new_component_declaration)
                        template_lines = temp_content.splitlines(keepends=True)
                        insertion_index = -1
                        target_line_content = "transform.Scale=math.lerp(initialScale,maxScale,t);}"
                        for i, line in enumerate(template_lines):
                             if target_line_content in line.replace(" ", "").replace("\t", ""):
                                 insertion_index = i
                                 break
                        if insertion_index != -1:
                            template_lines.insert(insertion_index + 1, "\n" + content + "\n")
                            new_content = "".join(template_lines)
                        else:
                            print(f"Advertencia: No se encontró la línea de inserción ('{target_line_content}') en {template_system_path} para {file_name}. Se usará el contenido recibido directamente.")
                            new_content = content
                    except Exception as e:
                        print(f"Error procesando template de sistema para {file_name}: {e}. Se usará el contenido recibido directamente.")
                        new_content = content
            elif file_name == "CreatePrefabsOnClick.cs":
                 dest_path = assets_scripts_general / file_name
                 if template_create_path:
                      try:
                           with open(template_create_path, "r", encoding="utf-8") as f:
                                template_lines = f.readlines()
                           insertion_index = -1
                           target_signature = "private void CargarPrefabs()"
                           target_content_part = "Resources.LoadAll<GameObject>"
                           for i, line in enumerate(template_lines):
                                if target_signature in line and target_content_part in line:
                                     insertion_index = i
                                     break
                           if insertion_index != -1:
                                template_lines.insert(insertion_index + 1, "\n" + content + "\n")
                                new_content = "".join(template_lines)
                           else:
                                print(f"Advertencia: No se encontró la línea de inserción ('{target_signature}' y '{target_content_part}') en {template_create_path}. Se usará el contenido recibido directamente.")
                                new_content = content
                      except Exception as e:
                           print(f"Error procesando template CreatePrefabsOnClick para {file_name}: {e}. Se usará el contenido recibido directamente.")
                           new_content = content
            else:
                print(f"Advertencia: Archivo no reconocido '{file_name}'. Se colocará en Assets/Scripts/General.")
                dest_path = assets_scripts_general / file_name

            if dest_path:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dest_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Archivo '{dest_path.name}' guardado en {dest_path.parent}")
                files_processed.append(dest_path)
            else:
                 print(f"Error: No se pudo determinar la ruta de destino para '{file_name}'. Archivo omitido.")
        except Exception as e:
            print(f"Error procesando el archivo '{file_name}': {e}")

    template_system_dest = assets_scripts_systems / "GeneralSystem.cs"
    if template_system_dest.exists():
        try:
            template_system_dest.unlink()
            print(f"Archivo template '{template_system_dest.name}' eliminado de la simulación.")
        except Exception as e:
            print(f"Error al eliminar '{template_system_dest.name}': {e}")

    if files_processed:
        return True
    else:
        print("No se procesaron archivos.")
        return False

DELIMITER = "%|%"
RESPONSES_CSV = None
try:
    APP_DATA_DIR_DOCS = Path.home() / "Documents" / "UnitySimulationManagerData"
    APP_DATA_DIR_DOCS.mkdir(parents=True, exist_ok=True)
    RESPONSES_DIR_DOCS = APP_DATA_DIR_DOCS / "Responses"
    RESPONSES_DIR_DOCS.mkdir(parents=True, exist_ok=True)
    RESPONSES_CSV = RESPONSES_DIR_DOCS / "Responses.csv"
    print(f"INFO: Using data path: {RESPONSES_CSV}")
except Exception as e:
    print(f"CRITICAL ERROR: Could not determine or create user data path in Documents: {e}")
    try:
        RESPONSES_DIR = APP_BASE_DIR / "UserData" / "Responses"
        RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
        RESPONSES_CSV = RESPONSES_DIR / "Responses.csv"
        print(f"WARNING: Falling back to app-relative directory path: {RESPONSES_CSV}")
        messagebox.showwarning("Cache Location", f"Could not use Documents folder. Response cache will be stored at:\n{RESPONSES_CSV}")
    except Exception as fallback_e:
        print(f"CRITICAL ERROR: Fallback path also failed: {fallback_e}")
        messagebox.showerror("Fatal Error", "Cannot establish a data storage location. Caching and history will be disabled.")
        RESPONSES_CSV = None

def check_last_char_is_newline(filepath: Union[str, Path]) -> bool:
    if not RESPONSES_CSV: return True
    filepath = Path(filepath)
    if not filepath.exists() or filepath.stat().st_size == 0:
        return True
    try:
        with open(filepath, 'rb') as f:
            f.seek(-1, os.SEEK_END)
            last_byte = f.read(1)
            return last_byte == b'\n'
    except Exception as e:
        print(f"Warning checking last character of {filepath}: {e}")
        return False

def get_next_id(csv_path: Union[str, Path]) -> int:
    if not RESPONSES_CSV: return 1
    csv_path = Path(csv_path)
    try:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error creating directory for {csv_path}: {e}")
        raise
    if not csv_path.exists():
        return 1
    last_id = 0
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) <= 1:
            return 1
        for line in reversed(lines):
            line = line.strip()
            if line:
                try:
                    parts = line.split(DELIMITER)
                    if parts and parts[0].strip().isdigit():
                        last_id = int(parts[0].strip())
                        return last_id + 1
                except (IndexError, ValueError):
                    print(f"Warning: Skipping malformed line in CSV cache: {line[:50]}...")
                    continue
        return 1
    except FileNotFoundError:
         return 1
    except Exception as e:
         print(f"Error reading CSV {csv_path} to get ID: {e}. Starting from ID 1.")
         return 1

def write_response_to_csv(prompt: str, response: str, input_tokens: int, output_tokens: int) -> None:
    if not RESPONSES_CSV:
         print("Error: Cannot write response to CSV, data path not configured.")
         return
    try:
        file_exists = RESPONSES_CSV.exists()
        is_empty = file_exists and RESPONSES_CSV.stat().st_size == 0
        write_header = not file_exists or is_empty
        next_id = get_next_id(RESPONSES_CSV)
        needs_leading_newline = file_exists and not is_empty and not check_last_char_is_newline(RESPONSES_CSV)
        with open(RESPONSES_CSV, "a", encoding="utf-8", newline='') as f:
            if needs_leading_newline:
                f.write('\n')
            if write_header:
                header = f"id{DELIMITER}prompt{DELIMITER}response{DELIMITER}input_tokens{DELIMITER}output_tokens\n"
                f.write(header)
            clean_prompt = str(prompt).replace(DELIMITER, "<DELIM>").replace('\n', '\\n').replace('\r', '')
            clean_response = str(response).replace(DELIMITER, "<DELIM>").replace('\n', '\\n').replace('\r', '')
            line = f"{next_id}{DELIMITER}{clean_prompt}{DELIMITER}{clean_response}{DELIMITER}{input_tokens}{DELIMITER}{output_tokens}\n"
            f.write(line)
        print(f"Response saved to: {RESPONSES_CSV} (id: {next_id})")
    except IOError as e:
        print(f"Critical I/O Error writing to {RESPONSES_CSV}: {e}")
        print("Check permissions in the target folder or if the file is locked.")
        messagebox.showerror("Cache Write Error", f"Could not write to the response cache file:\n{RESPONSES_CSV}\n\nError: {e}\n\nCaching may be disabled.")
    except Exception as e:
        print(f"Unexpected error writing to CSV cache: {e}")
        traceback.print_exc()

def get_cached_response(prompt: str) -> Union[str, None]:
    if not RESPONSES_CSV or not RESPONSES_CSV.exists():
        return None
    try:
        with open(RESPONSES_CSV, "r", encoding="utf-8") as f:
             lines = f.readlines()
        clean_prompt_search = str(prompt).replace(DELIMITER, "<DELIM>").replace('\n', '\\n').replace('\r', '')
        for line in lines[1:]:
            line = line.strip()
            if not line: continue
            parts = line.split(DELIMITER)
            if len(parts) == 5:
                cached_prompt = parts[1]
                cached_response_raw = parts[2]
                if cached_prompt == clean_prompt_search:
                    original_response = cached_response_raw.replace('\\n', '\n').replace("<DELIM>", DELIMITER)
                    print(f"Cache hit found for prompt (ID: {parts[0]})")
                    return original_response
            else:
                print(f"Warning: Ignoring CSV cache line with incorrect format (parts={len(parts)}): {line[:100]}...")
    except FileNotFoundError:
         return None
    except Exception as e:
         print(f"Error reading cache from {RESPONSES_CSV}: {e}")
         return None
    return None

def api_manager(simulation_name: str, simulation_description: str, use_cache: bool = True) -> tuple[bool, Union[str, None]]:
    print(f"\n--- Starting Process for Simulation: '{simulation_name}' ---")
    print(f"Description received: \"{simulation_description}\"")
    print("\n1. Validating and formatting description with secondary model...")
    formatted_prompt, second_input_tk, second_output_tk = call_secondary_model(simulation_description)
    if formatted_prompt.startswith("Error:") or not formatted_prompt:
         error_msg = f"Error from validation model: {formatted_prompt}. Possible causes: Invalid API Key, connection issue, model unavailable/misconfigured, or required models not set in .env."
         print(f"Critical error from secondary/validation model: {error_msg}")
         return False, error_msg
    formatted_prompt_strip = formatted_prompt.strip().upper()
    if formatted_prompt_strip == "ERROR DE CONTENIDO":
        error_msg = "Invalid Content: The description must exclusively refer to E. Coli and/or S. Cerevisiae and their parameters (color, duplication time, separation percentage)."
        print("Error: " + error_msg)
        return False, error_msg
    elif formatted_prompt_strip == "ERROR CANTIDAD EXCEDIDA":
        error_msg = "Exceeded Organism Limit: The maximum number of organisms (2) was exceeded."
        print("Error: " + error_msg)
        return False, error_msg
    elif "ERROR" in formatted_prompt_strip:
        error_msg = f"Validation Model Error: {formatted_prompt.strip()}"
        print("Error: " + error_msg)
        return False, error_msg
    print(f"Description validated and formatted:\n{formatted_prompt}")
    final_response = None
    cache_hit = False
    total_input_tokens = second_input_tk
    total_output_tokens = second_output_tk
    if use_cache:
        print("\n2. Searching response cache...")
        cached_response = get_cached_response(formatted_prompt)
        if cached_response:
            print("   Response found in cache.")
            final_response = cached_response
            cache_hit = True
    else:
        print("\n2. Cache disabled. Proceeding to generate code.")
    if not final_response:
        if not cache_hit and use_cache:
             print("   Response not found in cache.")
        print("   Generating code with primary model...")
        primary_response, primary_input_tk, primary_output_tk = call_primary_model(formatted_prompt)
        total_input_tokens += primary_input_tk
        total_output_tokens += primary_output_tk
        if primary_response.startswith("Error:") or not primary_response:
            error_msg = f"Critical error from primary model: {primary_response}. Check API Key/connection/Primary Model ID ('{FINE_TUNED_MODEL_NAME}')."
            print("Error: " + error_msg)
            return False, error_msg
        if "ERROR INVALID QUESTION FORMAT" in primary_response.upper():
             error_msg = f"Format Error: The primary model rejected the formatted prompt:\n'{formatted_prompt}'\nThis might indicate an issue with the validation model's output or the primary model's training."
             print("Error: " + error_msg)
             return False, error_msg
        final_response = primary_response
        print("   Code generated.")
        if use_cache and RESPONSES_CSV:
            write_response_to_csv(formatted_prompt, final_response, total_input_tokens, total_output_tokens)
    if not final_response:
         error_msg = "Critical Error: No final response obtained (neither from cache nor API)."
         print(error_msg)
         return False, error_msg
    print("\n3. Extracting and formatting C# codes...")
    codes = separar_codigos_por_archivo(final_response)
    if not codes:
        response_preview = final_response[:200].replace('\n', ' ') + ("..." if len(final_response) > 200 else "")
        error_msg = f"Code Extraction Error: Could not extract valid C# code blocks matching the expected format (e.g., '1.File.cs{{...}}') from the response.\n\nResponse start:\n'{response_preview}'"
        print("Error: " + error_msg)
        return False, error_msg
    print(f"   Extracted and formatted {len(codes)} scripts:")
    for filename in codes.keys():
        print(f"   - {filename}")
    print(f"\n4. Importing codes into simulation '{simulation_name}'...")
    success = import_codes(codes, simulation_name)
    if success:
        final_sim_path = SIMULATIONS_DIR / simulation_name
        print(f"\n--- Process Completed Successfully ---")
        print(f"Simulation '{simulation_name}' created/updated in: {final_sim_path}")
        return True, None
    else:
        error_msg = f"File Import Error: Failed to save generated scripts for '{simulation_name}'. Check console logs and previous error messages for details on specific file issues."
        print("\n--- Process Failed (Import Stage) ---")
        print(error_msg)
        return False, error_msg

def center_window(window, width, height):
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")

def apply_icon(window):
    try:
        if ICON_PATH_MAC and ICON_PATH_MAC.exists():
            img = tk.PhotoImage(file=str(ICON_PATH_MAC))
            window.tk.call('wm', 'iconphoto', window._w, img)
            print(f"Info: macOS icon applied from {ICON_PATH_MAC}.")
        elif ICON_PATH_MAC:
            print(f"Warning: macOS icon file '{ICON_PATH_MAC}' not found.")
    except tk.TclError as e:
        if ICON_PATH_MAC:
            print(f"Warning: Icon '{ICON_PATH_MAC}' could not be applied via tk.call. Error: {e}")
    except Exception as e:
        print(f"Unexpected error applying icon: {e}")

class CustomInputDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, prompt, width=400, height=170):
        super().__init__(parent)
        self.title(title)
        apply_icon(self)
        center_window(self, width, height)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        ctk.CTkLabel(self, text=prompt, font=APP_FONT, wraplength=width-40).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.entry = ctk.CTkEntry(self, font=APP_FONT, width=width-40)
        self.entry.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="e")
        mode_idx = get_color_mode_index()
        ok_button = ctk.CTkButton(button_frame, text="OK", command=self.ok_action, width=80, font=APP_FONT,
                                  fg_color=COLOR_SUCCESS_GENERAL[mode_idx], hover_color=COLOR_INFO_GENERAL[mode_idx])
        ok_button.pack(side="left", padx=(0, 10))
        cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=self.cancel_action, width=80, font=APP_FONT,
                                      fg_color=COLOR_WARNING_GENERAL[mode_idx], hover_color=COLOR_DANGER_GENERAL[mode_idx])
        cancel_button.pack(side="left")
        self.bind("<Return>", lambda event: self.ok_action())
        self.bind("<Escape>", lambda event: self.cancel_action())
        self.entry.focus()
        self.wait_window()

    def ok_action(self):
        self.result = self.entry.get()
        self.destroy()

    def cancel_action(self):
        self.result = None
        self.destroy()

def custom_askstring(title, prompt):
    if 'main_window' in globals() and main_window and main_window.winfo_exists():
        dialog = CustomInputDialog(main_window, title, prompt)
        return dialog.result
    else:
        print(f"Warning: Main window not available for dialog '{title}'. Cannot show dialog.")
        return None

def show_tooltip(widget, text):
    global tooltip_window
    hide_tooltip()
    try:
        x, y = widget.winfo_pointerxy()
        x += 20
        y += 10
    except tk.TclError:
        return
    tooltip_window = tk.Toplevel(widget)
    tooltip_window.wm_overrideredirect(True)
    tooltip_window.wm_geometry(f"+{x}+{y}")
    label = tk.Label(tooltip_window, text=text, justify='left',
                     background="#ffffe0",
                     relief='solid', borderwidth=1,
                     font=("Segoe UI", 9))
    label.pack(ipadx=1)

def hide_tooltip():
    global tooltip_window
    if tooltip_window:
        try:
            tooltip_window.destroy()
        except tk.TclError:
            pass
        tooltip_window = None

def schedule_tooltip(widget, text):
    global tooltip_job_id
    cancel_tooltip(widget)
    tooltip_job_id = widget.after(tooltip_delay, lambda: show_tooltip(widget, text))

def cancel_tooltip(widget):
    global tooltip_job_id
    if tooltip_job_id:
        widget.after_cancel(tooltip_job_id)
        tooltip_job_id = None
    hide_tooltip()

def on_closing():
    global is_build_running
    if is_build_running:
        messagebox.showwarning("Operation in Progress", "A build or load operation is currently running. Please wait for it to finish before closing.")
        return

    if messagebox.askokcancel(
        title="Exit Confirmation",
        message="Are you sure you want to exit the Unity Simulation Manager?",
        icon='question'
        ):
        if callable(globals().get('update_status')): update_status("Closing application...")
        print("Attempting to close associated Unity instances (if any)...")
        close_unity_thread = threading.Thread(target=ensure_unity_closed, daemon=True)
        close_unity_thread.start()
        close_unity_thread.join(timeout=2.0)

        print("Destroying main window and exiting...")
        if 'main_window' in globals() and main_window:
            try:
                main_window.destroy()
            except tk.TclError:
                print("Main window already destroyed or inaccessible.")
            except Exception as e:
                print(f"Error destroying main window: {e}")
        sys.exit(0)

def disable_all_interactions():
    global is_build_running
    is_build_running = True
    mode_idx = get_color_mode_index()
    disabled_color = COLOR_DISABLED_GENERAL[mode_idx]
    try:
        if 'reload_btn' in globals(): reload_btn.configure(state="disabled", fg_color=disabled_color)
        if 'graph_btn' in globals(): graph_btn.configure(state="disabled", fg_color=disabled_color)
        if 'create_btn' in globals(): create_btn.configure(state="disabled", fg_color=disabled_color)
        if 'sidebar_frame' in globals() and sidebar_frame.winfo_exists():
            for widget in sidebar_frame.winfo_children():
                if isinstance(widget, (ctk.CTkButton, ctk.CTkSwitch)):
                    widget.configure(state="disabled")
                    if isinstance(widget, ctk.CTkButton): widget.configure(fg_color=disabled_color)
        if 'search_entry' in globals(): search_entry.configure(state="disabled")
        if 'clear_search_btn' in globals(): clear_search_btn.configure(state="disabled", fg_color=disabled_color)
        if 'sim_tree' in globals():
            sim_tree.unbind("<Button-1>")
            sim_tree.unbind("<Motion>")
            sim_tree.unbind("<Leave>")
            sim_tree.configure(cursor="watch")
        if callable(globals().get('update_status')): update_status("Operation in progress... Please wait.")
    except (NameError, tk.TclError) as e:
        print(f"Warning: Could not disable all interactions: {e}")

def enable_all_interactions():
    global is_build_running
    is_build_running = False
    try:
        if 'sidebar_frame' in globals() and sidebar_frame.winfo_exists():
            for widget in sidebar_frame.winfo_children():
                if isinstance(widget, (ctk.CTkButton, ctk.CTkSwitch)):
                    widget.configure(state="normal")
        if 'search_entry' in globals(): search_entry.configure(state="normal")
        if 'clear_search_btn' in globals(): clear_search_btn.configure(state="normal")
        if 'sim_tree' in globals():
            sim_tree.bind("<Button-1>", handle_tree_click)
            sim_tree.bind("<Motion>", handle_tree_motion)
            sim_tree.bind("<Leave>", handle_tree_leave)
            sim_tree.configure(cursor="")
        if callable(globals().get('update_button_states')):
             if 'main_window' in globals() and main_window:
                  main_window.after(10, update_button_states)
             else:
                  update_button_states()
    except (NameError, tk.TclError) as e:
        print(f"Warning: Could not re-enable all interactions: {e}")

def update_status(message):
    try:
        if 'main_window' in globals() and main_window and main_window.winfo_exists() and 'status_label' in globals():
            main_window.after(0, lambda msg=str(message): status_label.configure(text=msg))
        else:
            print(f"Status Update (GUI not ready): {message}")
    except Exception as e:
         print(f"Error updating status bar: {e}")

def handle_unity_execution_error(error, operation_name="operation"):
    error_type = type(error).__name__
    error_details = str(error)
    if isinstance(error, subprocess.CalledProcessError):
        details = f"Process exited with code {error.returncode}."
        if error.stdout: details += f"\nLast stdout: ...{error.stdout[-200:]}"
        if error.stderr: details += f"\nStderr: {error.stderr[-200:]}"
        error_details = details
    elif isinstance(error, subprocess.TimeoutExpired):
        error_details = f"Process timed out after {error.timeout} seconds."
    elif isinstance(error, FileNotFoundError):
        error_details = f"Command or project path not found: {error.filename}"
    elif isinstance(error, PermissionError):
         error_details = "Permission denied. Check file/folder permissions."
    error_message = (
        f"An error occurred during the Unity {operation_name}.\n\n"
        f"Error Type: {error_type}\n"
        f"Details: {error_details}\n\n"
        f"Possible Causes:\n"
        f"- Incorrect Unity executable path in .env.\n"
        f"- Incorrect Unity version (Required: {UNITY_REQUIRED_VERSION_STRING}).\n"
        f"- Invalid Unity project path.\n"
        f"- Insufficient permissions.\n"
        f"- Unity Editor crashed or is unresponsive.\n\n"
        f"Check the console output and Unity log files (if generated) for more information."
    )
    print(f"--- Unity Execution Error ({operation_name}) ---")
    print(f"Error: {error}")
    print(traceback.format_exc())
    print("--- End Unity Execution Error ---")
    try:
        if 'main_window' in globals() and main_window and main_window.winfo_exists():
            main_window.after(0, lambda title=f"Unity {operation_name.capitalize()} Error", msg=error_message: messagebox.showerror(title, msg))
        else:
            print("Critical Error (No GUI): " + error_message)
    except Exception as mb_error:
        print(f"Error showing messagebox for Unity error: {mb_error}")

def ensure_unity_closed():
    if not unity_path_ok or not UNITY_EXECUTABLE:
        return
    unity_processes = []
    try:
        normalized_unity_exe = Path(UNITY_EXECUTABLE).resolve()
        for proc in psutil.process_iter(['exe', 'pid', 'name']):
            try:
                proc_info = proc.info
                if proc_info['exe']:
                    proc_exe_path = Path(proc_info['exe']).resolve()
                    if proc_exe_path == normalized_unity_exe:
                        unity_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied, FileNotFoundError):
                continue
            except Exception as inner_ex:
                 print(f"  Error inspecting process PID {proc.pid}: {inner_ex}")
                 continue
    except Exception as ex:
        print(f"Error listing processes: {ex}")
        return
    if unity_processes:
        time_start = time.time()
        print(f"Attempting to terminate {len(unity_processes)} Unity instance(s)...")
        for proc in unity_processes:
            try:
                print(f"  Terminating PID {proc.pid}...")
                proc.terminate()
            except psutil.NoSuchProcess:
                 print(f"    PID {proc.pid} already terminated.")
            except psutil.Error as term_err:
                print(f"    Error terminating PID {proc.pid}: {term_err}")
        gone, alive = psutil.wait_procs(unity_processes, timeout=5)
        if alive:
            print(f"  {len(alive)} instance(s) did not terminate gracefully. Attempting to kill...")
            for proc in alive:
                try:
                    print(f"    Killing PID {proc.pid}...")
                    proc.kill()
                except psutil.NoSuchProcess:
                    print(f"      PID {proc.pid} already gone.")
                except psutil.Error as kill_err:
                    print(f"      Error killing PID {proc.pid}: {kill_err}")
            _, alive_after_kill = psutil.wait_procs(alive, timeout=3)
            if alive_after_kill:
                print(f"Warning: {len(alive_after_kill)} Unity instance(s) could not be closed forcefully.")
            else:
                 print("  All targeted instances terminated.")
        else:
             print("  All targeted instances terminated gracefully.")
        print(f"Unity closing attempt took {time.time() - time_start:.2f}s")

def open_graphs_folder(simulation_name):
    if not simulation_name:
        messagebox.showerror("Error", "No simulation name provided to open the graphics folder.")
        return
    print(f"Attempting to open graphics folder for: '{simulation_name}'")
    simulation_data_dir = find_simulation_data_path(simulation_name)
    if not simulation_data_dir:
        messagebox.showerror("Error", f"Could not find the data directory for simulation '{simulation_name}'.\nCannot open the graphics folder.")
        return
    graphs_folder_path = simulation_data_dir / GRAPHICS_SUBFOLDER
    try:
        print(f"  Ensuring existence of: {graphs_folder_path}")
        graphs_folder_path.mkdir(parents=True, exist_ok=True)
        print(f"  Opening folder: {graphs_folder_path}")
        subprocess.Popen(["open", str(graphs_folder_path)])
    except FileNotFoundError:
         cmd = 'open'
         messagebox.showerror("System Error", f"Could not find the system command ('{cmd}') to open the folder on this OS (Darwin).")
    except Exception as e:
         messagebox.showerror("Error", f"Could not open the graphics folder:\n{graphs_folder_path}\n\nError: {e}")
         print(f"Error opening graphics folder: {e}")
         traceback.print_exc()

def get_folder_size(path: Union[str, Path]) -> int:
    total = 0
    try:
        p = Path(path)
        if not p.is_dir(): return 0
        for entry in p.iterdir():
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += get_folder_size(entry)
            except (FileNotFoundError, PermissionError):
                continue
            except Exception as scan_err:
                 print(f"Warning: Error processing entry {entry}: {scan_err}")
                 continue
    except (FileNotFoundError, PermissionError):
        pass
    except Exception as e:
        print(f"Warning: Error getting folder size for {path}: {e}")
        pass
    return total

def copy_directory(src: Union[str, Path], dst: Union[str, Path]) -> bool:
    src_path = Path(src)
    dst_path = Path(dst)
    if not src_path.is_dir():
        msg = f"Source for copy is not a valid directory: {src_path}"
        print(f"Error: {msg}")
        if 'main_window' in globals() and main_window and main_window.winfo_exists():
            main_window.after(0, lambda: messagebox.showerror("Copy Error", msg))
        return False
    try:
        if dst_path.exists():
            print(f"  Destination '{dst_path}' exists, removing first...")
            try:
                if dst_path.is_dir():
                    shutil.rmtree(dst_path, ignore_errors=False)
                else:
                    dst_path.unlink()
            except Exception as rm_e:
                 print(f"  Force removal required for '{dst_path}': {rm_e}")
                 if dst_path.is_dir(): shutil.rmtree(dst_path, ignore_errors=True)
                 elif dst_path.is_file(): dst_path.unlink(missing_ok=True)
            time.sleep(0.1)
        shutil.copytree(src_path, dst_path, symlinks=False, ignore_dangling_symlinks=True)
        print(f"  Successfully copied '{src_path}' to '{dst_path}'")
        return True
    except Exception as e:
        msg = f"Error copying directory:\nFrom: {src_path}\nTo:   {dst_path}\n\nError: {e}"
        print(f"Error: {msg}")
        if 'main_window' in globals() and main_window and main_window.winfo_exists():
            main_window.after(0, lambda: messagebox.showerror("Copy Error", msg))
        if dst_path.exists() and dst_path.is_dir():
             try: shutil.rmtree(dst_path, ignore_errors=True)
             except: pass
        return False

def get_build_target_and_executable(project_path: Union[str, Path, None]) -> Tuple[Union[str, None], Union[str, None]]:
    if not project_path:
        print("Warning: Cannot determine build target, project path is None.")
        return None, None
    project_path = Path(project_path)
    executable_name = SIMULATION_PROJECT_NAME
    build_target = "OSXUniversal"
    platform_folder = "Mac"
    executable_suffix = ".app"
    build_base_dir = project_path / "Build" / platform_folder
    executable_path = build_base_dir / (executable_name + executable_suffix)
    return build_target, str(executable_path)

def get_simulations() -> list[Dict]:
    simulations = []
    if not SIMULATIONS_DIR.is_dir():
        return simulations
    try:
        for item in SIMULATIONS_DIR.iterdir():
            if item.is_dir():
                assets_path = item / "Assets"
                settings_path = item / "ProjectSettings"
                if assets_path.is_dir() and settings_path.is_dir():
                    created_str, last_opened_str = "???", "Never"
                    created_timestamp, last_opened_timestamp = 0, 0
                    try:
                        created_timestamp = item.stat().st_ctime
                        created_str = time.strftime("%y-%m-%d %H:%M", time.localtime(created_timestamp))
                    except Exception: pass
                    last_opened_file = item / "last_opened.txt"
                    if last_opened_file.is_file():
                        try:
                            with open(last_opened_file, "r") as f:
                                last_opened_timestamp = float(f.read().strip())
                            last_opened_str = time.strftime("%y-%m-%d %H:%M", time.localtime(last_opened_timestamp))
                        except (ValueError, OSError): pass
                    simulations.append({
                        "name": item.name,
                        "creation": created_str,
                        "last_opened": last_opened_str,
                        "creation_ts": created_timestamp,
                    })
    except Exception as e:
        print(f"Error reading simulations from {SIMULATIONS_DIR}: {e}")
        return []
    return simulations

def update_last_opened(sim_name: str):
    simulation_folder = SIMULATIONS_DIR / sim_name
    try:
        simulation_folder.mkdir(parents=True, exist_ok=True)
        last_opened_file = simulation_folder / "last_opened.txt"
        with open(last_opened_file, "w") as f:
            f.write(str(time.time()))
    except Exception as e:
        print(f"[Error] Failed to update last opened timestamp for '{sim_name}': {e}")

def read_last_loaded_simulation_name() -> Union[str, None]:
    global SIMULATION_LOADED_FILE
    file_path_obj = None
    current_value = SIMULATION_LOADED_FILE
    if isinstance(current_value, Path):
        file_path_obj = current_value
    elif isinstance(current_value, str) and current_value:
        print(f"Warning: read_last_loaded_simulation_name received SIMULATION_LOADED_FILE as a string ('{current_value}'). Converting to Path.")
        try:
            file_path_obj = Path(current_value)
        except Exception as e:
            print(f"Error converting string '{current_value}' to Path in read_last_loaded_simulation_name: {e}")
            return None
    elif current_value is None:
        pass
    else:
        print(f"Warning: read_last_loaded_simulation_name received SIMULATION_LOADED_FILE with unexpected type: {type(current_value)}")
        return None
    if file_path_obj and file_path_obj.exists() and file_path_obj.is_file():
        try:
            with open(file_path_obj, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return content if content else None
        except Exception as e:
            print(f"Error reading simulation name from {file_path_obj}: {e}")
            return None
    else:
        return None

def load_simulation(sim_name: str) -> bool:
    global last_simulation_loaded, SIMULATION_PROJECT_PATH, ASSETS_FOLDER, STREAMING_ASSETS_FOLDER, SIMULATION_LOADED_FILE
    if not unity_projects_path_ok or not UNITY_PROJECTS_PATH:
        messagebox.showerror("Configuration Error", "Cannot load simulation: The Unity Projects Path is not configured or invalid in the .env file.")
        return False
    try:
        base_project_path = Path(UNITY_PROJECTS_PATH)
        SIMULATION_PROJECT_PATH = base_project_path / SIMULATION_PROJECT_NAME
        ASSETS_FOLDER = SIMULATION_PROJECT_PATH / "Assets"
        STREAMING_ASSETS_FOLDER = ASSETS_FOLDER / "StreamingAssets"
        SIMULATION_LOADED_FILE = STREAMING_ASSETS_FOLDER / "simulation_loaded.txt"
    except Exception as path_e:
         messagebox.showerror("Path Error", f"Could not construct required project paths from UNITY_PROJECTS_PATH ('{UNITY_PROJECTS_PATH}').\nError: {path_e}")
         return False
    source_path = SIMULATIONS_DIR / sim_name
    if not source_path.is_dir():
        messagebox.showerror("Load Error", f"Simulation source folder not found:\n{source_path}")
        return False
    try:
        SIMULATION_PROJECT_PATH.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        messagebox.showerror("Directory Error", f"Could not create or access the target Unity project directory:\n{SIMULATION_PROJECT_PATH}\n\nError: {e}")
        return False
    current_persistent_loaded = read_last_loaded_simulation_name()
    needs_full_copy = (
        not current_persistent_loaded or
        current_persistent_loaded != sim_name or
        not ASSETS_FOLDER.is_dir()
    )
    copy_operation = "Full Copy" if needs_full_copy else "Update"
    print(f"Load '{sim_name}': Performing '{copy_operation}'.")
    copy_ok = True
    folders_to_copy = ["Assets", "Packages", "ProjectSettings"]
    if needs_full_copy:
        update_status(f"Loading '{sim_name}': Full copy (Assets, Packages, Settings)...")
        for folder_name in folders_to_copy:
            target_folder = SIMULATION_PROJECT_PATH / folder_name
            if target_folder.exists():
                 try:
                      if target_folder.is_dir(): shutil.rmtree(target_folder, ignore_errors=True)
                      else: target_folder.unlink(missing_ok=True)
                      time.sleep(0.1)
                 except Exception as rm_e: print(f"Warning: Could not remove existing '{target_folder}' before copy: {rm_e}")
        for folder_name in folders_to_copy:
            src_folder = source_path / folder_name
            dst_folder = SIMULATION_PROJECT_PATH / folder_name
            if src_folder.is_dir():
                print(f"  Copying {folder_name}...")
                if not copy_directory(src_folder, dst_folder):
                    copy_ok = False
                    break
            elif folder_name in ["Assets", "ProjectSettings"]:
                messagebox.showwarning("Missing Folder", f"Required folder '{folder_name}' is missing in the source simulation '{sim_name}'. The loaded project might be incomplete.")
                if folder_name == "Assets": copy_ok = False; break
    else:
        update_status(f"Loading '{sim_name}': Updating Assets folder...")
        src_assets = source_path / "Assets"
        dst_assets = ASSETS_FOLDER
        if src_assets.is_dir():
            if not copy_directory(src_assets, dst_assets):
                copy_ok = False
        else:
            messagebox.showerror("Load Error", f"Cannot update: 'Assets' folder is missing in the source simulation '{sim_name}'.")
            copy_ok = False
    if not copy_ok:
        update_status(f"Error during file copy for '{sim_name}'. Load cancelled.")
        return False
    try:
        STREAMING_ASSETS_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(SIMULATION_LOADED_FILE, "w") as f:
            f.write(sim_name)
        print(f"State file '{SIMULATION_LOADED_FILE.name}' updated with: {sim_name}")
    except Exception as e:
        messagebox.showwarning("State File Error", f"Could not create StreamingAssets folder or update the simulation state file:\n{SIMULATION_LOADED_FILE}\n\nError: {e}")
    update_last_opened(sim_name)
    last_simulation_loaded = sim_name
    if 'main_window' in globals() and main_window and main_window.winfo_exists():
        main_window.after(50, populate_simulations)
    elif callable(globals().get('populate_simulations')):
         populate_simulations()
    update_status(f"Simulation '{sim_name}' loaded successfully.")
    return True

def delete_simulation(sim_name: str):
    global last_simulation_loaded, all_simulations_data, SIMULATION_LOADED_FILE, SIMULATIONS_DIR
    if not sim_name:
        messagebox.showerror("Error", "No simulation name provided for deletion.")
        return
    confirm = messagebox.askyesno(
        "Confirm Deletion",
        f"Permanently delete the simulation '{sim_name}' and ALL associated data (logs, graphs, configuration)?\n\nThis action cannot be undone!",
        icon='warning'
    )
    if not confirm:
        if callable(globals().get('update_status')): update_status("Deletion cancelled.")
        print(f"Deletion of '{sim_name}' cancelled by user.")
        return
    if callable(globals().get('update_status')): update_status(f"Deleting '{sim_name}'...")
    print(f"--- Starting deletion of '{sim_name}' ---")
    errors_occurred = False
    state_file_path_obj = None
    current_state_file_value = SIMULATION_LOADED_FILE
    if isinstance(current_state_file_value, Path):
        state_file_path_obj = current_state_file_value
    elif isinstance(current_state_file_value, str) and current_state_file_value:
        try: state_file_path_obj = Path(current_state_file_value)
        except Exception as e:
            print(f"  Error converting state file string '{current_state_file_value}' to Path: {e}"); errors_occurred = True
    elif current_state_file_value is None: pass
    else:
        print(f"  Warning: Global SIMULATION_LOADED_FILE has unexpected type: {type(current_state_file_value)}"); errors_occurred = True
    if state_file_path_obj:
        if state_file_path_obj.is_file():
            try:
                loaded_name_from_file = read_last_loaded_simulation_name()
                if loaded_name_from_file == sim_name:
                    state_file_path_obj.unlink()
                    print(f"  State file '{state_file_path_obj}' deleted because it contained '{sim_name}'.")
                    if last_simulation_loaded == sim_name:
                        last_simulation_loaded = None
                        print("  Global 'last_simulation_loaded' variable cleared.")
            except Exception as e:
                print(f"  Warning: Could not read or delete state file '{state_file_path_obj}': {e}")
                errors_occurred = True
        else:
            if last_simulation_loaded == sim_name:
                 last_simulation_loaded = None
                 print("  Global 'last_simulation_loaded' cleared (state file didn't exist or wasn't a file).")
    else:
        if last_simulation_loaded == sim_name:
             last_simulation_loaded = None
             print("  Global 'last_simulation_loaded' cleared (state file path was None/invalid).")
    if isinstance(SIMULATIONS_DIR, Path):
        local_sim_path = SIMULATIONS_DIR / sim_name
        print(f"  Attempting to delete local config directory: {local_sim_path}")
        if local_sim_path.exists():
            if local_sim_path.is_dir():
                try:
                    shutil.rmtree(local_sim_path)
                    print(f"    Local config directory '{local_sim_path}' deleted.")
                except PermissionError as e:
                    messagebox.showerror("Permission Error", f"Permission denied while deleting the local configuration folder:\n{local_sim_path}\n\n{e}")
                    errors_occurred = True
                except OSError as e:
                    messagebox.showerror("System Error", f"Could not delete the local configuration folder (in use?):\n{local_sim_path}\n\n{e}")
                    errors_occurred = True
                except Exception as e:
                    messagebox.showerror("Unexpected Error", f"An unexpected error occurred deleting the local configuration folder:\n{local_sim_path}\n\n{e}")
                    traceback.print_exc()
                    errors_occurred = True
            else:
                print(f"  Warning: Expected a directory at '{local_sim_path}', but found a file. Attempting to delete file...")
                try:
                    local_sim_path.unlink()
                except Exception as e:
                     print(f"  Error deleting unexpected file at '{local_sim_path}': {e}")
                     errors_occurred = True
        else:
             print(f"  Local config directory '{local_sim_path}' not found (nothing to delete).")
    else:
        print(f"  CRITICAL ERROR: SIMULATIONS_DIR is not a Path object ({type(SIMULATIONS_DIR)}). Cannot delete local sim folder.")
        if 'main_window' in globals() and main_window and main_window.winfo_exists():
            messagebox.showerror("Internal Error", f"Configuration Error: SIMULATIONS_DIR type is {type(SIMULATIONS_DIR)}, expected Path. Cannot delete local data.")
        errors_occurred = True
    print(f"  Attempting to delete Unity data directory for '{sim_name}'...")
    unity_data_path = find_simulation_data_path(sim_name)
    if unity_data_path is None:
        print(f"  Info: Could not determine the Unity data directory path for '{sim_name}'. Skipping deletion (may not exist).")
    elif unity_data_path.exists():
        if unity_data_path.is_dir():
            try:
                shutil.rmtree(unity_data_path)
                print(f"    Unity data directory '{unity_data_path}' deleted.")
            except PermissionError as e:
                messagebox.showerror("Permission Error", f"Permission denied while deleting the Unity data folder:\n{unity_data_path}\n\n{e}")
                errors_occurred = True
            except OSError as e:
                messagebox.showerror("System Error", f"Could not delete the Unity data folder (in use?):\n{unity_data_path}\n\n{e}")
                errors_occurred = True
            except Exception as e:
                messagebox.showerror("Unexpected Error", f"An unexpected error occurred deleting the Unity data folder:\n{unity_data_path}\n\n{e}")
                traceback.print_exc()
                errors_occurred = True
        else:
            print(f"  Warning: Expected a directory at '{unity_data_path}', but found a file. File not deleted.")
            errors_occurred = True
    else:
        print(f"  Unity data directory '{unity_data_path}' not found (nothing to delete).")
    if 'all_simulations_data' in globals():
        initial_count = len(all_simulations_data)
        all_simulations_data[:] = [s for s in all_simulations_data if isinstance(s, dict) and s.get('name') != sim_name]
        if len(all_simulations_data) < initial_count:
             print(f"  Entry for '{sim_name}' removed from internal 'all_simulations_data' list.")
        else:
             print(f"  Warning: '{sim_name}' not found in internal 'all_simulations_data' list to remove.")
    print(f"--- Finished deletion process for '{sim_name}' ---")
    final_message = f"Deletion of '{sim_name}' completed"
    if errors_occurred:
        final_message += " with errors."
        print("  Errors occurred during the deletion process. Please review previous messages.")
    else:
        final_message += " successfully."
        print("  Deletion completed without reported errors.")
    if callable(globals().get('update_status')):
        update_status(final_message)
    if callable(globals().get('populate_simulations')):
        print("  Refreshing simulation list in UI...")
        if 'main_window' in globals() and main_window and main_window.winfo_exists():
             main_window.after(0, populate_simulations)
        else:
             populate_simulations()
    else:
        print("  Warning: Function 'populate_simulations' not found to refresh UI.")

def format_time(seconds: Union[float, int, None]) -> str:
    if seconds is None or seconds < 0 or math.isinf(seconds) or math.isnan(seconds):
        return "--:--:--"
    if seconds == 0:
        return "0s"
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    elif minutes > 0:
        return f"{minutes:02d}:{seconds:02d}"
    else:
        return f"{seconds}s"

def monitor_unity_progress(stop_event: threading.Event, operation_tag: str):
    global SIMULATION_PROJECT_PATH
    project_path = None
    if SIMULATION_PROJECT_PATH:
        try:
            project_path = Path(SIMULATION_PROJECT_PATH)
            if not project_path.is_dir():
                print(f"[{operation_tag}] Monitor: Project path '{project_path}' not found initially. Will check again.")
        except Exception as path_e:
            print(f"[{operation_tag}] Monitor Error: Invalid project path '{SIMULATION_PROJECT_PATH}': {path_e}")
            update_status(f"[{operation_tag}] Error: Invalid project path. Cannot monitor.")
            return
    else:
        print(f"[{operation_tag}] Monitor Error: SIMULATION_PROJECT_PATH is None. Cannot monitor.")
        update_status(f"[{operation_tag}] Error: Project path not set. Cannot monitor.")
        return
    UPDATE_INTERVAL = 1.0
    SIZE_CHECK_INTERVAL = 5.0
    last_time_update = 0
    last_size_check_time = 0
    last_logged_mb = -1.0
    start_time = time.time()
    print(f"[{operation_tag}] Monitor Thread Started. Tracking elapsed time.")
    update_status(f"[{operation_tag}] Starting...")
    while not stop_event.is_set():
        current_time = time.time()
        if current_time - last_time_update >= UPDATE_INTERVAL:
            elapsed_time = current_time - start_time
            formatted_elapsed_time = format_time(elapsed_time)
            status_message = f"[{operation_tag}] Running... Elapsed: {formatted_elapsed_time}"
            update_status(status_message.ljust(60))
            last_time_update = current_time
        if project_path and (current_time - last_size_check_time >= SIZE_CHECK_INTERVAL):
            try:
                if project_path.is_dir():
                    current_bytes = get_folder_size(project_path)
                    current_mb = current_bytes / (1024*1024)
                    if abs(current_mb - last_logged_mb) > 1.0:
                         print(f"  MONITOR [{operation_tag}]: Current size ~{current_mb:.1f} MB (at {format_time(current_time - start_time)})")
                         last_logged_mb = current_mb
                else:
                    if last_logged_mb != -999:
                         print(f"  MONITOR [{operation_tag}]: Project directory '{project_path.name}' not found during size check.")
                         last_logged_mb = -999
            except Exception as e:
                 print(f"  MONITOR [{operation_tag}]: Warning - Error checking size: {e}")
            last_size_check_time = current_time
        time.sleep(0.3)
    final_elapsed_time = time.time() - start_time
    print(f"\n[{operation_tag}] Monitor Stopped. Total Duration: {format_time(final_elapsed_time)}")
    if project_path:
        try:
            if project_path.is_dir():
                 final_bytes = get_folder_size(project_path)
                 final_mb = final_bytes / (1024*1024)
                 print(f"[{operation_tag}] Final project size: ~{final_mb:.1f} MB")
            else:
                 print(f"[{operation_tag}] Final project directory not found.")
        except Exception as e:
            print(f"[{operation_tag}] Warning - Error getting final size: {e}")

def run_unity_batchmode(exec_method: str, op_name: str, log_file_name: str, timeout: int = 600, extra_args: list = None) -> tuple[bool, Union[str, None]]:
    if not all([unity_path_ok, unity_version_ok, unity_projects_path_ok, SIMULATION_PROJECT_PATH]):
        update_status(f"Error: Cannot run Unity '{op_name}'. Check Unity configuration.")
        messagebox.showerror("Configuration Error", f"Cannot run the Unity {op_name} operation.\nPlease verify the Unity executable path, version, and projects path in Settings.")
        return False, None
    project_path_obj = Path(SIMULATION_PROJECT_PATH)
    if not project_path_obj.is_dir():
         update_status(f"Error: Project path does not exist: {project_path_obj}")
         messagebox.showerror("Project Not Found", f"The Unity project path does not exist or is not a directory:\n{project_path_obj}")
         return False, None
    log_path = project_path_obj / log_file_name
    command = [
        UNITY_EXECUTABLE,
        "-batchmode",
        "-quit",
        "-projectPath", str(project_path_obj.resolve()),
        "-executeMethod", exec_method,
        "-logFile", str(log_path.resolve())
    ]
    if extra_args:
        command.extend(extra_args)
    print(f"\n--- Running Unity ({op_name}) ---")
    print(f"Command: {' '.join(command)}")
    success = False
    stop_monitor_event = threading.Event()
    executable_path = None
    monitor_thread = threading.Thread(target=monitor_unity_progress, args=(stop_monitor_event, op_name.capitalize()), daemon=True)
    try:
        update_status(f"[{op_name.capitalize()}] Starting Unity process...")
        monitor_thread.start()
        creation_flags = 0
        process = subprocess.run(
            command,
            check=True,
            timeout=timeout,
            creationflags=creation_flags,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        print(f"--- Unity Stdout ({op_name}) ---")
        print(process.stdout[-1000:])
        print("--- End Unity Stdout ---")
        if process.stderr:
            print(f"--- Unity Stderr ({op_name}) ---")
            print(process.stderr[-1000:])
            print("--- End Unity Stderr ---")
        update_status(f"[{op_name.capitalize()}] Unity process finished successfully.")
        success = True
        if "BuildScript.PerformBuild" in exec_method:
            update_status(f"[{op_name.capitalize()}] Verifying build output...")
            _, build_exe_path_str = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
            if build_exe_path_str:
                build_exe_path = Path(build_exe_path_str)
                found = False
                for attempt in range(6):
                    time.sleep(0.5 * attempt)
                    if build_exe_path.exists() and (build_exe_path.is_file() or build_exe_path.is_dir()):
                        found = True
                        executable_path = str(build_exe_path)
                        print(f"Build output verified successfully (Attempt {attempt+1}): {executable_path}")
                        break
                    else:
                        print(f"Build output check attempt {attempt+1} failed for: {build_exe_path}")
                if found:
                    update_status(f"[{op_name.capitalize()}] Build executable verified.")
                else:
                    print(f"ERROR: Build output NOT FOUND after checks: {build_exe_path}")
                    success = False
                    handle_unity_execution_error(FileNotFoundError(f"Build output '{build_exe_path.name}' not found in '{build_exe_path.parent}' after process completion."), op_name)
                    update_status(f"[Error] {op_name.capitalize()} failed: Build output missing.")
            else:
                 print("ERROR: Could not determine expected build executable path.")
                 success = False
                 update_status(f"[Error] {op_name.capitalize()} failed: Could not determine output path.")
    except subprocess.CalledProcessError as e:
        handle_unity_execution_error(e, op_name)
        update_status(f"[Error] {op_name.capitalize()} failed (Exit Code {e.returncode}). See console/log: {log_path.name}")
    except subprocess.TimeoutExpired as e:
        handle_unity_execution_error(e, op_name)
        update_status(f"[Error] {op_name.capitalize()} timed out after {timeout}s. See log: {log_path.name}")
    except (FileNotFoundError, PermissionError) as e:
        handle_unity_execution_error(e, op_name)
        update_status(f"[Error] {op_name.capitalize()} failed (File Not Found or Permission). Check Unity path.")
    except Exception as e:
        handle_unity_execution_error(e, f"{op_name} (unexpected)")
        update_status(f"[Error] Unexpected error during {op_name}. Check console.")
    finally:
        stop_monitor_event.set()
        if monitor_thread.is_alive():
             monitor_thread.join(timeout=1.0)
    print(f"--- Unity ({op_name}) Finished. Success: {success} ---")
    return success, executable_path

def run_prefab_material_tool() -> bool:
    update_status("Running prefab/material creation tool...")
    success, _ = run_unity_batchmode(
        exec_method="PrefabMaterialCreator.CreatePrefabsAndMaterials",
        op_name="Prefab Tool",
        log_file_name="prefab_tool_log.txt",
        timeout=600
    )
    if success:
         update_status("Prefab/material tool completed successfully.")
    else:
         update_status("Error during prefab/material creation. Check logs.")
    return success

def build_simulation_task(extra_args: list, callback):
    disable_all_interactions()
    success, final_exe_path = run_unity_batchmode(
        exec_method="BuildScript.PerformBuild",
        op_name="Build",
        log_file_name="build_log.txt",
        timeout=1800,
        extra_args=extra_args
    )
    if callback:
        if 'main_window' in globals() and main_window and main_window.winfo_exists():
            main_window.after(0, lambda s=success, p=final_exe_path: callback(s, p))
        else:
             print("Warning: Main window not available for build callback.")
    if 'main_window' in globals() and main_window and main_window.winfo_exists():
        main_window.after(10, enable_all_interactions)
    else:
         enable_all_interactions()

def build_simulation_threaded(callback=None):
    build_target, _ = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
    if not build_target:
        print("Error: Could not determine build target for the current OS.")
        update_status("Error: Build target unknown. Cannot start build.")
        messagebox.showerror("Build Error", "Could not determine the build target for your operating system.")
        return
    build_thread = threading.Thread(
        target=build_simulation_task,
        args=(["-buildTarget", build_target], callback),
        daemon=True
    )
    build_thread.start()

def open_simulation_executable():
    if not SIMULATION_PROJECT_PATH:
        update_status("Error: Project path not set. Cannot find executable.")
        messagebox.showerror("Error", "Project path is not set. Load a simulation first.")
        return
    _, exe_path_str = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
    if not exe_path_str:
        messagebox.showerror("Error", "Could not determine the expected executable path for this OS.")
        return
    exe_path = Path(exe_path_str)
    if exe_path.exists():
        try:
            base_name = exe_path.name
            update_status(f"Launching: {base_name}...")
            print(f"Attempting to launch: {exe_path}")
            if exe_path.is_dir(): # .app is a directory
                 subprocess.Popen(["open", str(exe_path)])
            else:
                 raise FileNotFoundError(f".app bundle not found or is not a directory: {exe_path}")
            update_status(f"Launched {base_name}.")
        except Exception as e:
            handle_unity_execution_error(e, f"launch simulation ({exe_path.name})")
            update_status(f"Error launching simulation: {e}")
    else:
        messagebox.showerror("Executable Not Found", f"The simulation executable was not found at:\n{exe_path}\n\nPlease build the simulation first.")
        update_status("Error: Simulation executable not found.")

def open_in_unity():
    if not all([unity_path_ok, unity_projects_path_ok, UNITY_EXECUTABLE, SIMULATION_PROJECT_PATH]):
        messagebox.showerror("Configuration Error", "Cannot open in Unity. Please check Unity executable and project paths in Settings.")
        return

    project_path_obj = Path(SIMULATION_PROJECT_PATH)
    if not project_path_obj.is_dir():
        messagebox.showerror("Project Not Found", f"The project path does not exist or is not a directory:\n{project_path_obj}")
        return

    try:
        update_status(f"Opening project '{project_path_obj.name}' in Unity Editor...")
        
        # For macOS, if UNITY_EXECUTABLE points inside a .app bundle, we need to use `open` with the .app path
        # Otherwise, use the UNITY_EXECUTABLE directly.
        # The global UNITY_EXECUTABLE is already resolved to the binary inside .app if applicable.
        
        # Reconstruct .app path if UNITY_EXECUTABLE is the internal binary
        app_bundle_to_open_path_str = None
        if UNITY_EXECUTABLE and "/Contents/MacOS/Unity" in UNITY_EXECUTABLE:
            # UNITY_EXECUTABLE is like /path/to/Unity.app/Contents/MacOS/Unity
            # We want /path/to/Unity.app
            potential_app_bundle = Path(UNITY_EXECUTABLE).parent.parent.parent
            if potential_app_bundle.name.endswith(".app"):
                app_bundle_to_open_path_str = str(potential_app_bundle)

        if app_bundle_to_open_path_str:
            command = ["open", "-a", app_bundle_to_open_path_str, "--args", "-projectPath", str(project_path_obj.resolve())]
        else: # Should not happen if verification correctly sets UNITY_EXECUTABLE on macOS
            command = [UNITY_EXECUTABLE, "-projectPath", str(project_path_obj.resolve())]
            
        print(f"Launching Unity Editor with command: {' '.join(command)}")
        subprocess.Popen(command)
        update_status("Unity Editor is launching...")
    except Exception as e:
        handle_unity_execution_error(e, "open project in Unity")
        update_status("Error launching Unity Editor.")


def create_simulation_thread(sim_name: str, sim_desc: str):
    update_status(f"Creating '{sim_name}' using API...")
    success = False
    error_message_detail = f"An unknown error occurred during the creation of '{sim_name}'."
    try:
        try:
            SIMULATIONS_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            error_message_detail = f"Could not create the base simulations directory:\n{SIMULATIONS_DIR}\n\n{type(e).__name__}: {e}"
            success = False
            if 'main_window' in globals() and main_window:
                 main_window.after(0, lambda msg=error_message_detail: messagebox.showerror("Critical Setup Error", msg))
            update_status("Critical directory creation error. Cannot continue.")
            return
        success, error_message = api_manager(sim_name, sim_desc, use_cache=True)
        if success:
            final_message = f"Simulation '{sim_name}' created successfully via API."
            update_status(final_message)
            print(final_message)
            if 'main_window' in globals() and main_window:
                 main_window.after(0, lambda name=sim_name: messagebox.showinfo("Success", f"Simulation '{name}' created successfully."))
            global all_simulations_data
            all_simulations_data = get_simulations()
            if 'main_window' in globals() and main_window:
                 main_window.after(50, populate_simulations)
        else:
            error_message_detail = error_message if error_message else f"Failed to create simulation '{sim_name}'. Reason unknown (check console logs)."
            update_status(f"Error creating '{sim_name}'. Check logs.")
            print(f"Error creating '{sim_name}': {error_message_detail}")
            if 'main_window' in globals() and main_window:
                 main_window.after(0, lambda msg=error_message_detail: messagebox.showerror("Simulation Creation Failed", msg))
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        detailed_error = traceback.format_exc()
        error_message_detail = f"A critical unexpected error occurred during the simulation creation process:\n{error_type}: {error_msg}\n\nPlease check the console logs for a detailed traceback."
        if 'main_window' in globals() and main_window:
             main_window.after(0, lambda msg=error_message_detail: messagebox.showerror("Unexpected Creation Error", msg))
        update_status(f"Critical error during creation: {error_type}")
        print(f"--- CRITICAL ERROR in create_simulation_thread ---")
        print(detailed_error)
        print(f"--- End Critical Error ---")
        success = False
    finally:
        if 'main_window' in globals() and main_window:
            main_window.after(100, enable_all_interactions)
        else:
             enable_all_interactions()
        print(f"Simulation creation thread for '{sim_name}' finished. Success: {success}")
        if not success:
            print(f"Failure reason logged above or: {error_message_detail}")

def perform_verification(show_results_box=False, on_startup=False):
    global unity_path_ok, unity_version_ok, unity_projects_path_ok, apis_key_ok, apis_models_ok, initial_verification_complete
    global UNITY_EXECUTABLE, UNITY_PROJECTS_PATH, OPENAI_API_KEY, FINE_TUNED_MODEL_NAME, SECONDARY_FINE_TUNED_MODEL_NAME
    global SIMULATION_PROJECT_PATH, ASSETS_FOLDER, STREAMING_ASSETS_FOLDER, SIMULATION_LOADED_FILE, last_simulation_loaded, all_simulations_data

    if not on_startup:
        update_status("Verifying configuration...")

    load_dotenv(DOTENV_PATH, override=True)
    unity_executable_from_env = os.environ.get("UNITY_EXECUTABLE")
    UNITY_PROJECTS_PATH = os.environ.get("UNITY_PROJECTS_PATH")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    FINE_TUNED_MODEL_NAME = os.getenv("FINE_TUNED_MODEL_NAME")
    SECONDARY_FINE_TUNED_MODEL_NAME = os.getenv("2ND_FINE_TUNED_MODEL_NAME")

    unity_path_ok = unity_version_ok = unity_projects_path_ok = apis_key_ok = apis_models_ok = False
    results = []
    req_ver = UNITY_REQUIRED_VERSION_STRING

    resolved_unity_executable_str = unity_executable_from_env
    is_macos_app_bundle = False
    if platform.system() == "Darwin" and unity_executable_from_env and unity_executable_from_env.endswith(".app"):
        resolved_unity_executable_str = str(Path(unity_executable_from_env) / "Contents" / "MacOS" / "Unity")
        is_macos_app_bundle = True
    
    UNITY_EXECUTABLE = resolved_unity_executable_str

    if not unity_executable_from_env:
        results.append("❌ Unity Executable: Path missing in .env file.")
    elif not UNITY_EXECUTABLE or not Path(UNITY_EXECUTABLE).is_file():
        results.append(f"❌ Unity Executable: Path invalid or not a file:\n   '{UNITY_EXECUTABLE}' (resolved from '{unity_executable_from_env}')")
    else:
        unity_path_ok = True
        results.append(f"✅ Unity Executable: Path OK ('{UNITY_EXECUTABLE}').")
        try:
            if is_macos_app_bundle:
                # For .app bundles, check if the parent directory of the .app itself is the version string
                app_bundle_path = Path(unity_executable_from_env)
                version_folder_name = app_bundle_path.parent.name
                if version_folder_name == req_ver:
                    unity_version_ok = True
                    results.append(f"✅ Unity Version: Parent directory of '.app' ('{version_folder_name}') matches required version '{req_ver}'.")
                else:
                    results.append(f"❌ Unity Version: Parent directory of '.app' ('{version_folder_name}') does not match required version '{req_ver}'.")
            else: # Non-macOS .app path logic (e.g. direct binary path or Windows)
                # This part might need adjustment if non-macOS paths have different structures
                path_to_check_version_in = UNITY_EXECUTABLE
                if f"{os.path.sep}{req_ver}{os.path.sep}" in str(Path(path_to_check_version_in).parent):
                     unity_version_ok = True
                     results.append(f"✅ Unity Version: Path seems consistent with required version '{req_ver}'.")
                else:
                     grandparent_dir_name = Path(UNITY_EXECUTABLE).parent.parent.name
                     if grandparent_dir_name == req_ver:
                          unity_version_ok = True
                          results.append(f"✅ Unity Version: Editor parent directory '{grandparent_dir_name}' matches required version '{req_ver}'.")
                     else:
                          results.append(f"❌ Unity Version: Path does not clearly contain required version '{req_ver}'. Structure found: '.../{grandparent_dir_name}/{Path(UNITY_EXECUTABLE).parent.name}/Unity'")
        except Exception as path_err:
            results.append(f"⚠️ Unity Version: Error during path check: {path_err}")
            traceback.print_exc()


    if not UNITY_PROJECTS_PATH:
        results.append("❌ Projects Path: Missing in .env file.")
    elif not Path(UNITY_PROJECTS_PATH).is_dir():
        results.append(f"❌ Projects Path: Path invalid or not a directory:\n   '{UNITY_PROJECTS_PATH}'")
    else:
        unity_projects_path_ok = True
        results.append(f"✅ Projects Path: Directory OK.")
        try:
            base_proj_path = Path(UNITY_PROJECTS_PATH)
            SIMULATION_PROJECT_PATH = base_proj_path / SIMULATION_PROJECT_NAME
            ASSETS_FOLDER = SIMULATION_PROJECT_PATH / "Assets"
            STREAMING_ASSETS_FOLDER = ASSETS_FOLDER / "StreamingAssets"
            SIMULATION_LOADED_FILE = STREAMING_ASSETS_FOLDER / "simulation_loaded.txt"
            last_simulation_loaded = read_last_loaded_simulation_name()
        except Exception as path_e:
             results.append(f"⚠️ Project Paths: Error constructing paths: {path_e}")
             unity_projects_path_ok = False
    apis_key_ok = False
    apis_models_ok = False
    if not OPENAI_API_KEY:
        results.append("❌ API Key: Missing in .env file.")
    else:
        openai.api_key = OPENAI_API_KEY
        try:
            openai.Model.list(limit=1)
            apis_key_ok = True
            results.append("✅ API Key: Connection successful (using v0.x API).")
            primary_model_valid = False
            if not FINE_TUNED_MODEL_NAME:
                 results.append("❌ Primary Model: ID missing in .env file (Required for API creation).")
            else:
                 try:
                      openai.Model.retrieve(FINE_TUNED_MODEL_NAME)
                      results.append(f"✅ Primary Model: ID '{FINE_TUNED_MODEL_NAME}' verified.")
                      primary_model_valid = True
                 except InvalidRequestError_v0 as e:
                      results.append(f"❌ Primary Model: ID '{FINE_TUNED_MODEL_NAME}' NOT FOUND or invalid. Error: {e}")
                 except Exception as model_error:
                      results.append(f"❌ Primary Model: Error verifying ID '{FINE_TUNED_MODEL_NAME}'. Error: {type(model_error).__name__}: {model_error}")
            apis_models_ok = primary_model_valid
            if SECONDARY_FINE_TUNED_MODEL_NAME:
                try:
                    openai.Model.retrieve(SECONDARY_FINE_TUNED_MODEL_NAME)
                    results.append(f"✅ Secondary Model: ID '{SECONDARY_FINE_TUNED_MODEL_NAME}' verified.")
                except InvalidRequestError_v0:
                    results.append(f"⚠️ Secondary Model: ID '{SECONDARY_FINE_TUNED_MODEL_NAME}' NOT FOUND or invalid.")
                except Exception as sec_model_error:
                    results.append(f"⚠️ Secondary Model: Error verifying ID '{SECONDARY_FINE_TUNED_MODEL_NAME}'. Error: {type(sec_model_error).__name__}")
        except AuthenticationError_v0 as auth_err:
             results.append(f"❌ API Key: Authentication failed. Invalid or expired key? Error: {auth_err}")
             apis_key_ok = False; apis_models_ok = False
        except APIConnectionError_v0 as conn_err:
             results.append(f"❌ API Connection: Failed to connect to OpenAI. Check network/firewall. Error: {conn_err}")
             apis_key_ok = False; apis_models_ok = False
        except Exception as api_err:
             results.append(f"❌ API Error: Unexpected error during API verification. Error: {type(api_err).__name__}: {api_err}")
             apis_key_ok = False; apis_models_ok = False
             print(f"Unexpected API verification error: {api_err}")
             traceback.print_exc()
    if not initial_verification_complete:
        initial_verification_complete = True
    unity_status = "Unity OK" if unity_path_ok and unity_version_ok and unity_projects_path_ok else "Unity ERR"
    api_status = "API OK" if apis_key_ok and apis_models_ok else "API ERR"
    final_status_string = f"Status: {unity_status} | {api_status}"
    try:
        if 'main_window' in globals() and main_window and main_window.winfo_exists():
            main_window.after(0, lambda: update_status(final_status_string))
            main_window.after(50, update_button_states)
            all_simulations_data = get_simulations()
            main_window.after(100, filter_simulations)
            if on_startup:
                error_messages = []
                if not unity_path_ok: error_messages.append("- Invalid Unity Executable path in .env.")
                elif not unity_version_ok: error_messages.append(f"- Unity path does not seem to match required version ({req_ver}).")
                if not unity_projects_path_ok: error_messages.append("- Invalid Unity Projects path in .env.")
                if not (unity_path_ok and unity_version_ok and unity_projects_path_ok):
                     error_messages.append("  (Core Unity features like Build/Load may fail)")
                api_errors_found = False
                if not OPENAI_API_KEY: error_messages.append("- OpenAI API Key missing in .env."); api_errors_found=True
                elif not apis_key_ok: error_messages.append("- OpenAI API Key invalid or connection failed."); api_errors_found=True
                else:
                    if not FINE_TUNED_MODEL_NAME: error_messages.append("- Primary fine-tuned model ID missing in .env."); api_errors_found=True
                    elif not apis_models_ok: error_messages.append("- Primary fine-tuned model ID invalid/not found."); api_errors_found=True
                if api_errors_found:
                     error_messages.append("  (API-based simulation creation will be disabled)")
                if error_messages:
                    startup_message = "Initial Configuration Issues Found:\n\n" + "\n".join(error_messages) + "\n\nPlease use 'Settings' to correct the .env file and then click 'Verify Config'."
                    main_window.after(300, lambda m=startup_message: messagebox.showwarning("Initial Configuration Issues", m))
        else:
            print(f"Verification Status (No GUI): {final_status_string}")
    except Exception as ui_update_err:
         print(f"Error updating GUI after verification: {ui_update_err}")
    if show_results_box:
        results_text = "Configuration Verification Results:\n\n" + "\n".join(results)
        all_checks_ok = unity_path_ok and unity_version_ok and unity_projects_path_ok and apis_key_ok and apis_models_ok
        if 'main_window' in globals() and main_window and main_window.winfo_exists():
             message_type = messagebox.showinfo if all_checks_ok else messagebox.showwarning
             popup_title = "Verification Complete" if all_checks_ok else "Verification Issues Found"
             main_window.after(0, lambda title=popup_title, msg=results_text: message_type(title, msg))
        else:
             print("\n--- Verification Results ---")
             print(results_text)
             print("--- End Verification Results ---")

def open_config_window():
    if 'main_window' not in globals() or not main_window: return
    config_win = ctk.CTkToplevel(main_window)
    config_win.title("Settings (.env Configuration)")
    apply_icon(config_win)
    center_window(config_win, 700, 200)
    config_win.resizable(False, False)
    config_win.transient(main_window)
    config_win.grab_set()
    frame = ctk.CTkFrame(config_win)
    frame.pack(fill="both", expand=True, padx=20, pady=20)
    frame.grid_columnconfigure(1, weight=1)
    entries = {}
    def create_row(parent_frame, row_index, label_text, env_variable_name, dict_key, browse_for_file=True):
        ctk.CTkLabel(parent_frame, text=label_text, anchor="w", font=APP_FONT).grid(row=row_index, column=0, padx=(0, 10), pady=5, sticky="w")
        current_value = os.environ.get(env_variable_name, "")
        entry_var = ctk.StringVar(value=current_value)
        entries[dict_key] = entry_var
        entry_widget = ctk.CTkEntry(parent_frame, textvariable=entry_var, font=APP_FONT)
        entry_widget.grid(row=row_index, column=1, padx=5, pady=5, sticky="ew")
        def browse_action():
            initial_dir = "/"
            current_path = entry_var.get()
            if current_path:
                potential_dir = Path(current_path)
                if potential_dir.is_file(): initial_dir = str(potential_dir.parent)
                elif potential_dir.is_dir(): initial_dir = str(potential_dir)
                elif potential_dir.name.endswith(".app") and potential_dir.parent.is_dir(): initial_dir = str(potential_dir.parent)

            elif dict_key == "projects_path" and Path.home().is_dir():
                initial_dir = str(Path.home())
            selected_path = None
            if browse_for_file: # For Unity Executable, allow selecting .app bundle
                selected_path = filedialog.askopenfilename(
                    title=f"Select {label_text}",
                    initialdir=initial_dir,
                    parent=config_win,
                    filetypes=[("Application", "*.app")] if platform.system() == "Darwin" else None
                )
            else: # Browse for directory
                selected_path = filedialog.askdirectory(
                    title=f"Select {label_text}",
                    initialdir=initial_dir,
                    parent=config_win
                )
            if selected_path:
                entry_var.set(selected_path)
        browse_button = ctk.CTkButton(parent_frame, text="...", width=30, command=browse_action, font=APP_FONT)
        browse_button.grid(row=row_index, column=2, padx=(5, 0), pady=5)
    create_row(frame, 0, "Unity Executable (.app):", "UNITY_EXECUTABLE", "unity_exe", browse_for_file=True)
    create_row(frame, 1, "Unity Projects Folder:", "UNITY_PROJECTS_PATH", "projects_path", browse_for_file=False)
    button_frame_bottom = ctk.CTkFrame(config_win, fg_color="transparent")
    button_frame_bottom.pack(fill="x", padx=20, pady=(0, 20))
    button_frame_bottom.columnconfigure(0, weight=1)
    button_frame_bottom.columnconfigure(1, weight=0)
    button_frame_bottom.columnconfigure(2, weight=0)
    button_frame_bottom.columnconfigure(3, weight=1)
    def save_config_action():
        api_key = os.getenv("OPENAI_API_KEY","")
        model1 = os.getenv("FINE_TUNED_MODEL_NAME","")
        model2 = os.getenv("2ND_FINE_TUNED_MODEL_NAME","")
        unity_exe_path = entries['unity_exe'].get().strip()
        projects_folder_path = entries['projects_path'].get().strip()
        if not unity_exe_path or not projects_folder_path:
            messagebox.showerror("Input Error", "Both Unity Executable Path and Projects Folder Path are required.", parent=config_win)
            return
        try:
            with open(DOTENV_PATH, "w", encoding='utf-8') as f:
                f.write(f"UNITY_EXECUTABLE={unity_exe_path}\n")
                f.write(f"UNITY_PROJECTS_PATH={projects_folder_path}\n")
                f.write(f"OPENAI_API_KEY={api_key}\n")
                f.write(f"FINE_TUNED_MODEL_NAME={model1}\n")
                f.write(f"2ND_FINE_TUNED_MODEL_NAME={model2}\n")
            messagebox.showinfo("Success", "Settings saved to .env file.\nRe-running verification...", parent=config_win)
            config_win.destroy()
            if 'main_window' in globals() and main_window:
                 main_window.after(100, lambda: perform_verification(show_results_box=True))
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not write to the .env file:\n{e}", parent=config_win)
    mode_idx = get_color_mode_index()
    save_button = ctk.CTkButton(button_frame_bottom, text="Save and Verify", command=save_config_action, font=APP_FONT,
                                fg_color=COLOR_SUCCESS_GENERAL[mode_idx], hover_color=COLOR_INFO_GENERAL[mode_idx])
    save_button.grid(row=0, column=1, padx=10, pady=10)
    cancel_button = ctk.CTkButton(button_frame_bottom, text="Cancel", command=config_win.destroy, font=APP_FONT,
                                  fg_color=COLOR_WARNING_GENERAL[mode_idx], hover_color=COLOR_DANGER_GENERAL[mode_idx])
    cancel_button.grid(row=0, column=2, padx=10, pady=10)
    config_win.wait_window()

def cleanup_simulation_logger_data(actual_simulation_names: set):
    print("\n--- Starting Simulation Logger Data Cleanup ---")
    logger_data_path = None
    try:
        persistent_path = find_unity_persistent_path(UNITY_PRODUCT_NAME)
        if not persistent_path:
            print("  Skipping cleanup: Could not find Unity persistent data path.")
            return
        logger_data_path = persistent_path / LOG_SUBFOLDER
        if not logger_data_path.is_dir():
            print(f"  Skipping cleanup: Logger data directory not found at '{logger_data_path}'.")
            return
        print(f"  Checking logger data directory: {logger_data_path}")
        deleted_count = 0
        error_count = 0
        for item in logger_data_path.iterdir():
            if item.is_dir():
                folder_name = item.name
                if folder_name not in actual_simulation_names:
                    print(f"  Found orphaned logger data folder: '{folder_name}'. Deleting...")
                    try:
                        shutil.rmtree(item)
                        print(f"    Successfully deleted '{item}'.")
                        deleted_count += 1
                    except PermissionError:
                        print(f"    Error: Permission denied deleting '{item}'. Skipping.")
                        error_count += 1
                    except OSError as e:
                        print(f"    Error deleting '{item}' (possibly in use?): {e}. Skipping.")
                        error_count += 1
                    except Exception as e:
                        print(f"    Unexpected error deleting '{item}': {e}. Skipping.")
                        traceback.print_exc()
                        error_count += 1
        print(f"--- Logger Data Cleanup Finished ---")
        if deleted_count > 0:
            print(f"  Deleted {deleted_count} orphaned logger data folder(s).")
        else:
            print(f"  No orphaned logger data folders found to delete.")
        if error_count > 0:
            print(f"  Encountered {error_count} error(s) during deletion.")
    except Exception as e:
        print(f"  Error during logger data cleanup process (Path: {logger_data_path}): {e}")
        traceback.print_exc()

def populate_simulations():
    if not initial_verification_complete:
        return
    if callable(globals().get('update_status')): update_status("Reloading simulation list and performing cleanup...")
    global all_simulations_data, last_simulation_loaded, SIMULATION_LOADED_FILE
    all_simulations_data = get_simulations()
    actual_sim_names = {sim['name'] for sim in all_simulations_data if isinstance(sim, dict) and 'name' in sim}
    print(f"Found {len(actual_sim_names)} simulations in {SIMULATIONS_DIR}.")
    current_loaded_in_file = read_last_loaded_simulation_name()
    last_simulation_loaded = current_loaded_in_file
    if current_loaded_in_file and current_loaded_in_file not in actual_sim_names:
        print(f"Warning: Loaded simulation '{current_loaded_in_file}' in state file does not exist in {SIMULATIONS_DIR}.")
        state_file_path = None
        if isinstance(SIMULATION_LOADED_FILE, Path):
            state_file_path = SIMULATION_LOADED_FILE
        elif isinstance(SIMULATION_LOADED_FILE, str):
             try: state_file_path = Path(SIMULATION_LOADED_FILE)
             except Exception: pass
        if state_file_path and state_file_path.is_file():
            print(f"  Attempting to delete invalid state file: {state_file_path}")
            try:
                state_file_path.unlink()
                print("    Successfully deleted invalid state file.")
                last_simulation_loaded = None
            except PermissionError:
                print("    Error: Permission denied deleting state file.")
            except Exception as e:
                print(f"    Error deleting state file: {e}")
        else:
            print(f"  State file not found or path invalid ({SIMULATION_LOADED_FILE}), cannot delete.")
            last_simulation_loaded = None
    cleanup_simulation_logger_data(actual_sim_names)
    all_simulations_data.sort(key=lambda x: x.get('name', '').lower())
    filter_simulations()
    status_msg = f"List refreshed. Found {len(all_simulations_data)} total simulation(s)."
    if last_simulation_loaded:
         status_msg += f" ('{last_simulation_loaded}' is loaded)"
    if callable(globals().get('update_status')): update_status(status_msg)
    if callable(globals().get('update_button_states')): update_button_states()

def filter_simulations(event=None):
    if 'sim_tree' not in globals() or 'search_entry' not in globals():
        return
    search_term = search_entry.get().lower().strip()
    try:
        for item in sim_tree.get_children():
            sim_tree.delete(item)
    except tk.TclError as e:
        print(f"Warning: Error clearing treeview items: {e}")
        return
    displayed_count = 0
    for sim_data in all_simulations_data:
        if search_term and search_term not in sim_data['name'].lower():
            continue
        is_loaded = (sim_data["name"] == last_simulation_loaded)
        row_tag = "evenrow" if displayed_count % 2 == 0 else "oddrow"
        item_tags = [row_tag]
        if is_loaded:
            item_tags.append("loaded")
        loaded_symbol = loaded_indicator_text if is_loaded else ""
        play_symbol = play_icon_text
        delete_symbol = delete_icon_text
        try:
            sim_tree.insert("", "end", iid=sim_data["name"],
                            values=(
                                sim_data["name"],
                                sim_data["creation"],
                                sim_data["last_opened"],
                                loaded_symbol,
                                play_symbol,
                                delete_symbol
                            ),
                            tags=tuple(item_tags))
            displayed_count += 1
        except tk.TclError as e:
            print(f"Error inserting simulation '{sim_data.get('name', 'N/A')}' into treeview: {e}")
    status_msg = status_label.cget("text")
    if initial_verification_complete:
        if search_term:
            status_msg = f"Displaying {displayed_count} of {len(all_simulations_data)} simulation(s) matching '{search_term}'."
        else:
            status_msg = f"Displaying {len(all_simulations_data)} simulation(s)."
        if last_simulation_loaded:
             status_msg += f" ('{last_simulation_loaded}' is loaded)"
    update_status(status_msg)
    if 'last_sort_column' in globals() and last_sort_column:
        current_reverse = sort_order.get(last_sort_column, False)
        sort_column(sim_tree, last_sort_column, current_reverse)
    update_button_states()

def clear_search():
    if 'search_entry' in globals():
        search_entry.delete(0, 'end')
        filter_simulations()

def update_button_states():
    if 'main_window' not in globals() or not main_window or not main_window.winfo_exists() or is_build_running:
        return
    has_selection = bool(sim_tree.selection())
    can_create = apis_key_ok and apis_models_ok
    def get_state(enabled_condition):
        return "normal" if enabled_condition else "disabled"
    settings_enabled = not is_build_running
    verify_enabled = not is_build_running
    unity_down_enabled = not is_build_running
    about_enabled = not is_build_running
    theme_switch_enabled = not is_build_running
    exit_enabled = not is_build_running
    reload_enabled = not is_build_running
    graph_enabled = has_selection and not is_build_running
    create_enabled = can_create and not is_build_running
    search_enabled = not is_build_running
    mode_idx = get_color_mode_index()
    disabled_fg = COLOR_DISABLED_GENERAL[mode_idx]
    try:
        if 'reload_btn' in globals(): reload_btn.configure(state=get_state(reload_enabled), fg_color=BTN_RELOAD_FG_COLOR[mode_idx] if reload_enabled else disabled_fg)
        if 'graph_btn' in globals(): graph_btn.configure(state=get_state(graph_enabled), fg_color=BTN_GRAPH_FG_COLOR[mode_idx] if graph_enabled else disabled_fg)
        if 'create_btn' in globals(): create_btn.configure(state=get_state(create_enabled), fg_color=BTN_CREATE_FG_COLOR[mode_idx] if create_enabled else disabled_fg)
        if 'settings_btn' in globals(): settings_btn.configure(state=get_state(settings_enabled), fg_color=BTN_SETTINGS_FG_COLOR[mode_idx] if settings_enabled else disabled_fg)
        if 'verify_btn' in globals(): verify_btn.configure(state=get_state(verify_enabled), fg_color=BTN_VERIFY_FG_COLOR[mode_idx] if verify_enabled else disabled_fg)
        if 'unity_down_btn' in globals(): unity_down_btn.configure(state=get_state(unity_down_enabled), fg_color=BTN_UNITY_DOWN_FG_COLOR[mode_idx] if unity_down_enabled else disabled_fg)
        if 'about_btn' in globals(): about_btn.configure(state=get_state(about_enabled), fg_color=BTN_ABOUT_FG_COLOR[mode_idx] if about_enabled else disabled_fg)
        if 'exit_btn' in globals(): exit_btn.configure(state=get_state(exit_enabled), fg_color=BTN_EXIT_FG_COLOR[mode_idx] if exit_enabled else disabled_fg)
        if 'theme_switch' in globals(): theme_switch.configure(state=get_state(theme_switch_enabled))
        if 'search_entry' in globals(): search_entry.configure(state=get_state(search_enabled))
        if 'clear_search_btn' in globals(): clear_search_btn.configure(state=get_state(search_enabled), fg_color=BTN_CLEARSEARCH_FG_COLOR[mode_idx] if search_enabled else disabled_fg)
    except (NameError, tk.TclError) as e:
        print(f"Warning: Could not update button states: {e}")

def on_load_simulation_request(simulation_name: str):
    global is_build_running
    if is_build_running:
        print("Load request ignored: Build/Load already in progress.")
        return
    print(f"Load/Run request received for: {simulation_name}")
    if not all([unity_path_ok, unity_version_ok, unity_projects_path_ok]):
        messagebox.showerror("Unity Configuration Error", "Cannot load simulation: Unity path, version, or projects path is invalid. Please check Settings.")
        return
    if simulation_name == last_simulation_loaded:
        update_status(f"'{simulation_name}' is already loaded. Showing options...")
        update_last_opened(simulation_name)
        _, current_executable = get_build_target_and_executable(SIMULATION_PROJECT_PATH)
        if 'main_window' in globals() and main_window:
            main_window.after(0, lambda s=simulation_name, p=current_executable: show_options_window(s, p))
        return
    disable_all_interactions()
    update_status(f"Starting load process for '{simulation_name}'...")
    load_thread = threading.Thread(target=load_simulation_logic, args=(simulation_name,), daemon=True)
    load_thread.start()

def load_simulation_logic(simulation_name: str):
    load_successful = False
    try:
        update_status(f"Load '{simulation_name}': Ensuring Unity is closed...");
        ensure_unity_closed()
        update_status(f"Load '{simulation_name}': Copying simulation files...");
        copy_ok = load_simulation(simulation_name)
        if copy_ok:
            update_status(f"Load '{simulation_name}': Running prefab/material tool...");
            prefab_ok = run_prefab_material_tool()
            if prefab_ok:
                update_status(f"Load '{simulation_name}': Starting simulation build...");
                build_simulation_threaded(callback=lambda ok, path: build_callback(ok, simulation_name, path))
                load_successful = True
            else:
                update_status(f"Error in post-load (prefab tool) for '{simulation_name}'. Build cancelled.")
                messagebox.showerror("Post-Load Error", f"The prefab/material creation tool failed for '{simulation_name}'.\nThe simulation build has been cancelled. Check console/logs.")
                if 'main_window' in globals() and main_window: main_window.after(10, enable_all_interactions)
        else:
            update_status(f"Error loading files for '{simulation_name}'. Load process stopped.");
            if 'main_window' in globals() and main_window: main_window.after(10, enable_all_interactions)
    except Exception as e:
        print(f"CRITICAL ERROR in load_simulation_logic for '{simulation_name}': {e}")
        import traceback
        traceback.print_exc()
        update_status(f"Critical error during load sequence for '{simulation_name}'. Check console.")
        if 'main_window' in globals() and main_window: main_window.after(10, enable_all_interactions)

def build_callback(success: bool, simulation_name: str, executable_path: Union[str, None]):
    if success:
        if executable_path and Path(executable_path).exists():
            update_status(f"Build for '{simulation_name}' completed successfully.")
            print(f"Build successful for '{simulation_name}'. Executable at: {executable_path}")
            show_options_window(simulation_name, executable_path)
        elif executable_path:
             update_status(f"Build '{simulation_name}' finished, but executable not found: {executable_path}")
             print(f"Error: Build process reported success, but executable missing at: {executable_path}")
             messagebox.showerror("Build Error", f"Build for '{simulation_name}' completed, but the executable was not found at the expected location:\n{executable_path}\n\nPlease check the build log.")
        else:
            update_status(f"Build '{simulation_name}' finished, but executable path unknown.")
            print(f"Error: Build process reported success, but could not determine executable path.")
            messagebox.showerror("Build Error", f"Build for '{simulation_name}' completed, but the executable path could not be determined.")
    else:
        update_status(f"Build process for '{simulation_name}' failed. Check logs/console.")
        print(f"Build failed for '{simulation_name}'.")

def on_delete_simulation_request(simulation_name: str):
    global is_build_running
    if is_build_running:
        print("Delete request ignored: Build/Load in progress.")
        return
    print(f"Delete request received for: {simulation_name}")
    delete_simulation(simulation_name)

def on_show_graphs_thread():
    global is_build_running
    if is_build_running:
        print("Show Graphs request ignored: Build/Load in progress.")
        return
    selected_items = sim_tree.selection()
    if not selected_items:
        messagebox.showwarning("No Selection", "Please select a simulation from the list to view its statistics.")
        return
    sim_name = sim_tree.item(selected_items[0], "values")[0]
    disable_all_interactions()
    update_status(f"Generating statistics graphs for '{sim_name}'...")
    graph_thread = threading.Thread(target=show_graphs_logic, args=(sim_name,), daemon=True)
    graph_thread.start()

def show_graphs_logic(sim_name: str):
    if not callable(globals().get('find_simulation_data_path')) or \
       not callable(globals().get('SimulationGraphics')) or \
       not callable(globals().get('open_graphs_folder')):
        messagebox.showerror("Internal Error", "Required graph generation functions (find_simulation_data_path, SimulationGraphics, open_graphs_folder) are not defined.")
        if 'main_window' in globals() and main_window: main_window.after(0, enable_all_interactions)
        return
    try:
        if callable(globals().get('update_status')): update_status(f"Locating data for '{sim_name}'...")
        print(f"--- Starting graph logic for: '{sim_name}' ---")
        simulation_data_dir = find_simulation_data_path(sim_name)
        if not simulation_data_dir:
            if callable(globals().get('update_status')): update_status(f"Error: Data directory not found for '{sim_name}'.")
            return
        print(f"  Data directory found: {simulation_data_dir}")
        csv_path = simulation_data_dir / CSV_FILENAME
        graphs_dir = simulation_data_dir / GRAPHICS_SUBFOLDER
        if not csv_path.is_file():
            messagebox.showerror("Missing Data",
                                 f"The required statistics file ('{CSV_FILENAME}') for simulation '{sim_name}' was not found in:\n{simulation_data_dir}\n\nCannot generate graphs.")
            if callable(globals().get('update_status')): update_status(f"Error: Statistics CSV file missing for '{sim_name}'.")
            return
        if callable(globals().get('update_status')): update_status(f"Generating graphs for '{sim_name}'...")
        print(f"  Calling SimulationGraphics for '{sim_name}'...")
        SimulationGraphics(sim_name)
        if callable(globals().get('update_status')): update_status(f"Graph generation attempted. Opening graphs folder for '{sim_name}'...")
        print(f"  Calling open_graphs_folder for '{sim_name}'...")
        open_graphs_folder(sim_name)
        if callable(globals().get('update_status')): update_status(f"Graph process completed for '{sim_name}'.")
    except FileNotFoundError as e:
        messagebox.showerror("File Error", f"A required file was not found during the graph process:\n{e}")
        if callable(globals().get('update_status')): update_status(f"Error: File not found while processing '{sim_name}'.")
        print(f"show_graphs_logic - FileNotFoundError: {e}")
        traceback.print_exc()
    except Exception as e:
        messagebox.showerror("Unexpected Error", f"An unexpected error occurred while processing graphs for '{sim_name}':\n{type(e).__name__}: {e}")
        if callable(globals().get('update_status')): update_status(f"Error processing graphs for '{sim_name}'. Check console.")
        print(f"show_graphs_logic - Unexpected Exception: {e}")
        traceback.print_exc()
    finally:
        try:
            if 'main_window' in globals() and main_window is not None and main_window.winfo_exists():
                 main_window.after(0, enable_all_interactions)
            elif callable(globals().get('enable_all_interactions')):
                 enable_all_interactions()()
        except NameError:
            print("Warning: 'main_window' or 'enable_all_interactions' not defined globally for UI re-enabling.")
        except Exception as e:
            print(f"Error in finally block attempting to re-enable UI: {e}")

def on_create_simulation():
    global is_build_running
    if is_build_running:
        print("Create request ignored: Build/Load in progress.")
        return
    if not apis_key_ok or not apis_models_ok:
        messagebox.showerror("API Configuration Error", "Cannot create simulation: Invalid or unverified OpenAI API Key or Primary Model ID.\nPlease check Settings and Verify Config.")
        return
    sim_name = custom_askstring("Create New Simulation", "Enter a unique name for the new simulation:")
    if sim_name is None:
        update_status("Simulation creation cancelled.")
        return
    sim_name = sim_name.strip()
    invalid_chars = r'<>:"/\|?*' + "".join(map(chr, range(32)))
    if not sim_name:
         messagebox.showerror("Invalid Name", "Simulation name cannot be empty.")
         update_status("Invalid simulation name (empty).")
         return
    if any(c in invalid_chars for c in sim_name):
        messagebox.showerror("Invalid Name", f"Simulation name '{sim_name}' contains invalid characters ({invalid_chars}).")
        update_status("Invalid simulation name (characters).")
        return
    if (SIMULATIONS_DIR / sim_name).exists():
        messagebox.showerror("Name Exists", f"A simulation named '{sim_name}' already exists. Please choose a different name.")
        update_status(f"Simulation '{sim_name}' already exists.")
        return
    sim_desc = custom_askstring("Simulation Description", "Provide a brief description for the simulation (e.g., 'EColi red fast, SCerevisiae blue slow'):")
    if sim_desc is None:
        update_status("Simulation creation cancelled.")
        return
    sim_desc = sim_desc.strip()
    if not sim_desc:
         if not messagebox.askyesno("Empty Description", "The description is empty. Continue anyway?", icon='question'):
              update_status("Simulation creation cancelled.")
              return
    disable_all_interactions()
    update_status(f"Initiating creation of '{sim_name}' via API...")
    creation_thread = threading.Thread(target=create_simulation_thread, args=(sim_name, sim_desc), daemon=True)
    creation_thread.start()

def show_options_window(simulation_name: str, executable_path: Union[str, None]):
    if 'main_window' not in globals() or not main_window: return
    options_win = ctk.CTkToplevel(main_window)
    options_win.title(f"Options for '{simulation_name}'")
    apply_icon(options_win)
    center_window(options_win, 380, 200)
    options_win.resizable(False, False)
    options_win.transient(main_window)
    options_win.grab_set()
    frame = ctk.CTkFrame(options_win)
    frame.pack(expand=True, fill="both", padx=20, pady=20)
    ctk.CTkLabel(frame, text=f"Simulation '{simulation_name}' is loaded and built.", font=APP_FONT_BOLD).pack(pady=(0, 15))
    executable_exists = executable_path and Path(executable_path).exists()
    run_button_state = "normal" if executable_exists else "disabled"
    def run_and_close():
        open_simulation_executable()
        options_win.destroy()
    def open_unity_and_close():
        open_in_unity()
        options_win.destroy()
    mode_idx = get_color_mode_index()
    run_button = ctk.CTkButton(frame, text="Run Simulation", command=run_and_close, state=run_button_state, font=APP_FONT, height=40,
                               fg_color=COLOR_SUCCESS_GENERAL[mode_idx] if executable_exists else COLOR_DISABLED_GENERAL[mode_idx],
                               hover_color=COLOR_INFO_GENERAL[mode_idx] if executable_exists else COLOR_DISABLED_GENERAL[mode_idx])
    run_button.pack(pady=8, fill="x", padx=10)
    if not executable_exists:
        reason = f"Executable not found at:\n{executable_path}" if executable_path else "Executable path is unknown."
        ctk.CTkLabel(frame, text=reason, text_color="gray", font=("Segoe UI", 9)).pack(pady=(0, 5))
    open_editor_button = ctk.CTkButton(frame, text="Open Project in Unity Editor", command=open_unity_and_close, font=APP_FONT, height=40,
                                     fg_color="#1E88E5", hover_color="#42A5F5")
    open_editor_button.pack(pady=8, fill="x", padx=10)
    update_status(f"Options available for loaded simulation '{simulation_name}'.")
    options_win.wait_window()

def handle_tree_click(event):
    global is_build_running
    if is_build_running: return
    region = sim_tree.identify_region(event.x, event.y)
    item_id = sim_tree.identify_row(event.y)
    if region == "cell" and item_id:
        column_id_str = sim_tree.identify_column(event.x)
        if not column_id_str:
            cancel_tooltip(sim_tree)
            return
        try:
            column_index = int(column_id_str.replace('#','')) - 1
            column_ids_tuple = sim_tree['columns']
            if 0 <= column_index < len(column_ids_tuple):
                column_name = column_ids_tuple[column_index]
                simulation_name = sim_tree.item(item_id, "values")[0]
                sim_tree.selection_set(item_id)
                sim_tree.focus(item_id)
                update_button_states()
                hide_tooltip()
                if column_name == "col_load":
                    print(f"Action Click: Load/Run '{simulation_name}'")
                    on_load_simulation_request(simulation_name)
                elif column_name == "col_delete":
                    print(f"Action Click: Delete '{simulation_name}'")
                    on_delete_simulation_request(simulation_name)
            else: cancel_tooltip(sim_tree)
        except (ValueError, IndexError, tk.TclError) as e:
            print(f"Error processing Treeview click: {e}")
            cancel_tooltip(sim_tree)
    elif region == "heading":
        pass
    else:
        cancel_tooltip(sim_tree)

def handle_tree_motion(event):
    global is_build_running
    if is_build_running: return
    region = sim_tree.identify_region(event.x, event.y)
    item_id = sim_tree.identify_row(event.y)
    if region == "cell" and item_id:
        column_id_str = sim_tree.identify_column(event.x)
        if not column_id_str: cancel_tooltip(sim_tree); return
        try:
            column_index = int(column_id_str.replace('#','')) - 1
            column_ids_tuple = sim_tree['columns']
            if 0 <= column_index < len(column_ids_tuple):
                column_name = column_ids_tuple[column_index]
                tooltip_text = None
                simulation_name = sim_tree.item(item_id, 'values')[0]
                if column_name == "col_load":
                    tooltip_text = f"Load / Run Simulation '{simulation_name}'"
                elif column_name == "col_delete":
                    tooltip_text = f"Delete Simulation '{simulation_name}'"
                elif column_name == "col_loaded":
                    cell_value = sim_tree.set(item_id, column=column_name)
                    if cell_value == loaded_indicator_text:
                        tooltip_text = f"Simulation '{simulation_name}' is currently loaded in the Unity project."
                if tooltip_text:
                    schedule_tooltip(sim_tree, tooltip_text)
                else:
                    cancel_tooltip(sim_tree)
            else: cancel_tooltip(sim_tree)
        except (ValueError, IndexError, tk.TclError) as e:
            cancel_tooltip(sim_tree)
    else:
        cancel_tooltip(sim_tree)

def handle_tree_leave(event):
    cancel_tooltip(sim_tree)

def load_logo(image_path: Union[str, Path], target_width: int) -> Union[ImageTk.PhotoImage, None]:
    global logo_photo_ref
    try:
        image_path_obj = Path(image_path) # Ensure it's a Path object
        if not image_path_obj.is_file():
            print(f"Warning: Logo image not found at '{image_path_obj}'")
            return None

        img = Image.open(image_path_obj)
        width_percent = (target_width / float(img.size[0]))
        new_height = int((float(img.size[1]) * float(width_percent)))
        img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
        logo_photo_ref = ImageTk.PhotoImage(img)
        return logo_photo_ref
    except FileNotFoundError: # Should be caught by is_file() check, but defensive
        print(f"Warning: Logo image not found at '{image_path}' (during Image.open)")
        return None
    except Exception as e:
        print(f"Error loading or processing logo image '{image_path}': {e}")
        return None

def update_treeview_style():
    if 'sim_tree' not in globals() or 'main_window' not in globals() or not main_window.winfo_exists():
        return
    mode_idx = get_color_mode_index()
    mode_str = "Dark" if mode_idx == 1 else "Light"
    try:
        bg_color = main_window._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        fg_color = main_window._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
        select_bg_color = main_window._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        select_fg_color = main_window._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["text_color"])
        header_bg_color = main_window._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["border_color"])
        header_fg_color = fg_color
        odd_row_bg = main_window._apply_appearance_mode(("#FFFFFF", "#3A3A3A"))
        even_row_bg = main_window._apply_appearance_mode(("#F5F5F5", "#343434"))
        loaded_row_bg = main_window._apply_appearance_mode(("#E8F5E9", "#2E7D32"))
        loaded_row_fg = fg_color
    except Exception as e:
        print(f"Error getting theme colors for Treeview: {e}. Using fallback colors.")
        if mode_str == "Dark":
            bg_color, fg_color = "#2B2B2B", "white"
            select_bg_color, select_fg_color = "#565B5E", "white"
            header_bg_color, header_fg_color = "#4A4D50", "white"
            odd_row_bg, even_row_bg = "#3A3A3A", "#343434"
            loaded_row_bg, loaded_row_fg = "#2E7D32", "white"
        else:
            bg_color, fg_color = "#FFFFFF", "black"
            select_bg_color, select_fg_color = "#DDF0FF", "black"
            header_bg_color, header_fg_color = "#EAEAEA", "black"
            odd_row_bg, even_row_bg = "#FFFFFF", "#F5F5F5"
            loaded_row_bg, loaded_row_fg = "#E8F5E9", "black"
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        print("Warning: ttk theme 'clam' not available. Using default theme.")
    style.configure("Treeview",
                    background=bg_color,
                    foreground=fg_color,
                    fieldbackground=bg_color,
                    rowheight=28,
                    font=TREEVIEW_FONT)
    style.configure("Treeview.Heading",
                    font=TREEVIEW_HEADER_FONT,
                    background=header_bg_color,
                    foreground=header_fg_color,
                    relief="flat",
                    padding=(10, 5))
    style.map("Treeview.Heading",
              relief=[('active', 'groove'), ('!active', 'flat')])
    style.map('Treeview',
              background=[('selected', select_bg_color)],
              foreground=[('selected', select_fg_color)])
    sim_tree.tag_configure('oddrow', background=odd_row_bg, foreground=fg_color)
    sim_tree.tag_configure('evenrow', background=even_row_bg, foreground=fg_color)
    sim_tree.tag_configure('loaded', background=loaded_row_bg, foreground=loaded_row_fg)

def toggle_appearance_mode():
    current_mode = ctk.get_appearance_mode()
    new_mode = "Dark" if current_mode == "Light" else "Light"
    print(f"Switching appearance mode to: {new_mode}")
    ctk.set_appearance_mode(new_mode)
    if 'theme_switch' in globals() and theme_switch:
        theme_switch.configure(text=f"{new_mode} Mode")
    if 'main_window' in globals() and main_window:
         main_window.after(50, update_treeview_style)
    mode_idx = get_color_mode_index()
    try:
        logo_path = LOGO_PATHS[mode_idx]
        new_logo_photo = load_logo(logo_path, LOGO_WIDTH - 20) # Recalculate new logo width
        if new_logo_photo and 'sidebar_frame' in globals() and sidebar_frame.winfo_exists():
             logo_widget = None
             for w in sidebar_frame.winfo_children():
                  if isinstance(w, ctk.CTkLabel) and hasattr(w, 'image'):
                       logo_widget = w
                       break
             if logo_widget:
                 logo_widget.configure(image=new_logo_photo)
                 logo_widget.image = new_logo_photo
        if 'settings_btn' in globals(): settings_btn.configure(fg_color=BTN_SETTINGS_FG_COLOR[mode_idx], hover_color=BTN_SETTINGS_HOVER_COLOR[mode_idx], text_color=BTN_SETTINGS_TEXT_COLOR[mode_idx])
        if 'verify_btn' in globals(): verify_btn.configure(fg_color=BTN_VERIFY_FG_COLOR[mode_idx], hover_color=BTN_VERIFY_HOVER_COLOR[mode_idx], text_color=BTN_VERIFY_TEXT_COLOR[mode_idx])
        if 'unity_down_btn' in globals(): unity_down_btn.configure(fg_color=BTN_UNITY_DOWN_FG_COLOR[mode_idx], hover_color=BTN_UNITY_DOWN_HOVER_COLOR[mode_idx], text_color=BTN_UNITY_DOWN_TEXT_COLOR[mode_idx])
        if 'about_btn' in globals(): about_btn.configure(fg_color=BTN_ABOUT_FG_COLOR[mode_idx], hover_color=BTN_ABOUT_HOVER_COLOR[mode_idx], text_color=BTN_ABOUT_TEXT_COLOR[mode_idx])
        if 'exit_btn' in globals(): exit_btn.configure(fg_color=BTN_EXIT_FG_COLOR[mode_idx], hover_color=BTN_EXIT_HOVER_COLOR[mode_idx], text_color=BTN_EXIT_TEXT_COLOR[mode_idx])
        if 'reload_btn' in globals(): reload_btn.configure(fg_color=BTN_RELOAD_FG_COLOR[mode_idx], hover_color=BTN_RELOAD_HOVER_COLOR[mode_idx], text_color=BTN_RELOAD_TEXT_COLOR[mode_idx])
        if 'graph_btn' in globals(): graph_btn.configure(fg_color=BTN_GRAPH_FG_COLOR[mode_idx], hover_color=BTN_GRAPH_HOVER_COLOR[mode_idx], text_color=BTN_GRAPH_TEXT_COLOR[mode_idx])
        if 'create_btn' in globals(): create_btn.configure(fg_color=BTN_CREATE_FG_COLOR[mode_idx], hover_color=BTN_CREATE_HOVER_COLOR[mode_idx], text_color=BTN_CREATE_TEXT_COLOR[mode_idx])
        if 'clear_search_btn' in globals(): clear_search_btn.configure(fg_color=BTN_CLEARSEARCH_FG_COLOR[mode_idx], hover_color=BTN_CLEARSEARCH_HOVER_COLOR[mode_idx], text_color=BTN_CLEARSEARCH_TEXT_COLOR[mode_idx])
        update_button_states()
        print("Widget colors updated for new theme.")
    except NameError as e:
        print(f"Warning: Button color update failed (widget might not exist yet): {e}")
    except Exception as e:
        print(f"Error updating widget colors for theme: {e}")

main_window = ctk.CTk()
apply_icon(main_window)
main_window.title("Unity Simulation Manager v1.0")
initial_width=1050
initial_height=700
center_window(main_window, initial_width, initial_height)
main_window.resizable(True, True)
main_window.minsize(850, 550)
main_window.columnconfigure(0, weight=0)
main_window.columnconfigure(1, weight=1)
main_window.rowconfigure(0, weight=1)
main_window.rowconfigure(1, weight=0)
sidebar_width=200
sidebar_frame = ctk.CTkFrame(main_window, width=sidebar_width, corner_radius=5, fg_color=COLOR_SIDEBAR_BG)
sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
sidebar_frame.grid_propagate(False)
sidebar_frame.columnconfigure(0, weight=1)
initial_mode = ctk.get_appearance_mode()
mode_idx = get_color_mode_index()
logo_path = LOGO_PATHS[mode_idx]
logo_photo = load_logo(logo_path, LOGO_WIDTH - 20)
if logo_photo:
    logo_label = ctk.CTkLabel(sidebar_frame, image=logo_photo, text="")
    logo_label.pack(pady=(20, 10), padx=10)
    logo_label.image = logo_photo
else:
    ctk.CTkLabel(sidebar_frame, text="[Logo]", font=(APP_FONT[0], 14, "italic")).pack(pady=(20, 10), padx=10)
ctk.CTkLabel(sidebar_frame, text="Menu", font=(APP_FONT[0], 16, "bold")).pack(pady=(5, 15), padx=10)
settings_btn = ctk.CTkButton(sidebar_frame, text="Settings (.env)", command=open_config_window, font=APP_FONT,
                             fg_color=BTN_SETTINGS_FG_COLOR[mode_idx], hover_color=BTN_SETTINGS_HOVER_COLOR[mode_idx], text_color=BTN_SETTINGS_TEXT_COLOR[mode_idx])
settings_btn.pack(fill="x", padx=15, pady=5)
verify_btn = ctk.CTkButton(sidebar_frame, text="Verify Config", command=lambda: perform_verification(show_results_box=True), font=APP_FONT,
                           fg_color=BTN_VERIFY_FG_COLOR[mode_idx], hover_color=BTN_VERIFY_HOVER_COLOR[mode_idx], text_color=BTN_VERIFY_TEXT_COLOR[mode_idx])
verify_btn.pack(fill="x", padx=15, pady=5)
separator = ctk.CTkFrame(sidebar_frame, height=2, fg_color="gray")
separator.pack(fill="x", padx=15, pady=15)

class UnityHubInfoDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message_text, download_url):
        super().__init__(parent)
        self.title(title)
        apply_icon(self)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self._message = message_text
        self._download_url = download_url
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.message_label = ctk.CTkLabel(self, text=self._message, font=APP_FONT, justify="left", wraplength=400)
        self.message_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")
        link_frame = ctk.CTkFrame(self, fg_color="transparent")
        link_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")
        link_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(link_frame, text="Download Link:", font=APP_FONT_BOLD).grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.link_entry = ctk.CTkEntry(link_frame, font=APP_FONT)
        self.link_entry.insert(0, self._download_url)
        self.link_entry.configure(state="readonly")
        self.link_entry.grid(row=0, column=1, sticky="ew")
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=(10, 20), sticky="e")
        mode_idx = get_color_mode_index()
        self.copy_button = ctk.CTkButton(button_frame, text="Copy Link", command=self.copy_link, width=100, font=APP_FONT,
                                         fg_color=BTN_RELOAD_FG_COLOR[mode_idx], hover_color=BTN_RELOAD_HOVER_COLOR[mode_idx])
        self.copy_button.pack(side="left", padx=(0, 10))
        open_button = ctk.CTkButton(button_frame, text="Open Page", command=self.open_download_page, width=100, font=APP_FONT,
                                       fg_color=BTN_GRAPH_FG_COLOR[mode_idx], hover_color=BTN_GRAPH_HOVER_COLOR[mode_idx])
        open_button.pack(side="left", padx=(0, 10))
        close_button = ctk.CTkButton(button_frame, text="Close", command=self.destroy, width=80, font=APP_FONT,
                                      fg_color=COLOR_WARNING_GENERAL[mode_idx], hover_color=COLOR_DANGER_GENERAL[mode_idx])
        close_button.pack(side="left")
        self.update_idletasks()
        width = max(450, self.winfo_reqwidth())
        height = self.winfo_reqheight()
        center_window(self, width, height)
        self.bind("<Escape>", lambda e: self.destroy())
        self.after(100, self.link_entry.focus)
        self.wait_window()

    def copy_link(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self._download_url)
            print(f"Copied to clipboard: {self._download_url}")
            original_text = self.copy_button.cget("text")
            self.copy_button.configure(text="Copied!", state="disabled")
            self.after(1500, lambda: self.copy_button.configure(text=original_text, state="normal"))
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
            messagebox.showerror("Clipboard Error", f"Could not copy link to clipboard:\n{e}", parent=self)

    def open_download_page(self):
        try:
            webbrowser.open(self._download_url)
            self.destroy()
        except Exception as e:
            print(f"Error opening URL in browser: {e}")
            messagebox.showerror("Browser Error", f"Could not open the download page in your browser:\n{e}", parent=self)

def handle_unity_download_click():
    if not 'UNITY_REQUIRED_VERSION_STRING' in globals() or not UNITY_REQUIRED_VERSION_STRING:
        print("Error: UNITY_REQUIRED_VERSION_STRING constant is not defined.")
        if 'main_window' in globals() and main_window and main_window.winfo_exists():
             messagebox.showerror("Internal Error", "The required Unity version is not configured internally.", parent=main_window)
        return
    unity_version_hash = "b2e806cf271c"
    unity_hub_uri = f"unityhub://{UNITY_REQUIRED_VERSION_STRING}/{unity_version_hash}"
    build_support_module_text = "- Mac Build Support (Mono or IL2CPP - check project needs)"
    hub_download_link = "https://public-cdn.cloud.unity3d.com/hub/prod/UnityHubSetup.dmg"
    os_name = "macOS"
    instructions = (
        "To install the correct Unity Editor version using this tool:\n\n"
        "1. Install Unity Hub using the link below if you haven't already.\n"
        "   (Close the Hub after installation if it opens automatically).\n\n"
        "2. Close this message, then click the 'Download Unity Editor' button in this application again.\n"
        f"   This should prompt Unity Hub to open and start installing the required Editor version ({UNITY_REQUIRED_VERSION_STRING}).\n\n"
        "3. In the Unity Hub installation options, carefully review the modules to add. Ensure the following are selected:\n"
        "   - Microsoft Visual Studio Community (or your preferred IDE)\n"
        f"   {build_support_module_text}\n\n"
        "4. Complete the installation process within Unity Hub."
    )
    troubleshooting = (
        "\n" + ("-" * 45) + "\n\n"
        "If Unity Hub did NOT open or prompt for installation:\n"
        "- Ensure Unity Hub is installed and running.\n"
        f"- Try opening the link manually in your browser (might trigger Hub): {unity_hub_uri}\n"
        "- If issues persist, you may need to manually find and install the specific Editor version ({UNITY_REQUIRED_VERSION_STRING}) via the Unity Hub 'Installs' section and 'Add' button, then select 'Install from archive'."
    )
    full_message_text = instructions + troubleshooting
    try:
        print(f"Attempting to open Unity Hub link: {unity_hub_uri}")
        opened = webbrowser.open(unity_hub_uri)
        if not opened:
            print("Warning: webbrowser.open returned False. System might not have handler for unityhub://")
    except Exception as e:
        print(f"Error attempting to open unityhub:// link: {e}")
    if 'main_window' in globals() and main_window and main_window.winfo_exists():
        dialog = UnityHubInfoDialog(
            parent=main_window,
            title="Download Unity Editor / Hub Instructions",
            message_text=full_message_text,
            download_url=hub_download_link
        )
    else:
        print("INFO (Unity Download Instructions - No GUI):")
        print(full_message_text)
        print(f"Unity Hub Download Link ({os_name}): {hub_download_link}")

unity_down_btn = ctk.CTkButton(sidebar_frame, text="Download Unity Editor",
                              command=handle_unity_download_click,
                              font=APP_FONT,
                              fg_color=BTN_UNITY_DOWN_FG_COLOR[mode_idx], hover_color=BTN_UNITY_DOWN_HOVER_COLOR[mode_idx], text_color=BTN_UNITY_DOWN_TEXT_COLOR[mode_idx])
unity_down_btn.pack(fill="x", padx=15, pady=5)
about_btn = ctk.CTkButton(sidebar_frame, text="About",
                          command=lambda: messagebox.showinfo("About", "Unity Simulation Manager v1.0.\n\nAuthors:\nIván Cáceres S.\nTobías Guerrero Ch."),
                          font=APP_FONT,
                          fg_color=BTN_ABOUT_FG_COLOR[mode_idx], hover_color=BTN_ABOUT_HOVER_COLOR[mode_idx], text_color=BTN_ABOUT_TEXT_COLOR[mode_idx])
about_btn.pack(fill="x", padx=15, pady=5)
theme_switch = ctk.CTkSwitch(sidebar_frame, text=f"{initial_mode} Mode", command=toggle_appearance_mode, font=APP_FONT)
theme_switch.pack(fill="x", side='bottom', padx=15, pady=(10, 5))
if initial_mode == "Dark": theme_switch.select()
else: theme_switch.deselect()
exit_btn = ctk.CTkButton(sidebar_frame, text="Exit Application", command=on_closing, font=APP_FONT,
                         fg_color=BTN_EXIT_FG_COLOR[mode_idx], hover_color=BTN_EXIT_HOVER_COLOR[mode_idx], text_color=BTN_EXIT_TEXT_COLOR[mode_idx])
exit_btn.pack(fill="x", side='bottom', padx=15, pady=(5, 20))
main_content_frame = ctk.CTkFrame(main_window, corner_radius=5)
main_content_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
main_content_frame.columnconfigure(0, weight=1)
main_content_frame.rowconfigure(0, weight=0)
main_content_frame.rowconfigure(1, weight=0)
main_content_frame.rowconfigure(2, weight=1)
main_content_frame.rowconfigure(3, weight=0)
header_frame = ctk.CTkFrame(main_content_frame, fg_color="transparent")
header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
header_frame.columnconfigure(0, weight=1)
ctk.CTkLabel(header_frame, text="Unity Simulation Manager", font=TITLE_FONT, anchor="center").grid(row=0, column=0, pady=(0, 10))
search_frame = ctk.CTkFrame(main_content_frame, fg_color="transparent")
search_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 5))
search_frame.columnconfigure(1, weight=1)
ctk.CTkLabel(search_frame, text="Search:", font=APP_FONT).grid(row=0, column=0, padx=(5, 5), pady=5)
search_entry = ctk.CTkEntry(search_frame, placeholder_text="Type simulation name to filter...", font=APP_FONT)
search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
search_entry.bind("<KeyRelease>", filter_simulations)
clear_search_btn = ctk.CTkButton(search_frame, text="Clear", width=60, font=APP_FONT, command=clear_search,
                                fg_color=BTN_CLEARSEARCH_FG_COLOR[mode_idx], hover_color=BTN_CLEARSEARCH_HOVER_COLOR[mode_idx], text_color=BTN_CLEARSEARCH_TEXT_COLOR[mode_idx])
clear_search_btn.grid(row=0, column=2, padx=(5, 5), pady=5)
tree_frame = ctk.CTkFrame(main_content_frame, corner_radius=5)
tree_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
tree_frame.columnconfigure(0, weight=1)
tree_frame.rowconfigure(0, weight=1)
columns = ("col_name", "col_created", "col_last_used", "col_loaded", "col_load", "col_delete")
sim_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
sim_tree.heading("col_name", text="Simulation Name", anchor='w')
sim_tree.column("col_name", width=250, minwidth=150, anchor="w", stretch=tk.YES)
sim_tree.heading("col_created", text="Created", anchor='center')
sim_tree.column("col_created", width=120, minwidth=100, anchor="center", stretch=tk.NO)
sim_tree.heading("col_last_used", text="Last Used", anchor='center')
sim_tree.column("col_last_used", width=120, minwidth=100, anchor="center", stretch=tk.NO)
sim_tree.heading("col_loaded", text="Loaded", anchor='center')
sim_tree.column("col_loaded", width=70, minwidth=60, stretch=tk.NO, anchor="center")
sim_tree.heading("col_load", text="Load/Run", anchor='center')
sim_tree.column("col_load", width=90, minwidth=80, stretch=tk.NO, anchor="center")
sim_tree.heading("col_delete", text="Delete", anchor='center')
sim_tree.column("col_delete", width=80, minwidth=70, stretch=tk.NO, anchor="center")
last_sort_column = None
sort_order = {col: False for col in columns if col not in ["col_load", "col_delete", "col_loaded"]}

def sort_column(tree, col, reverse):
    if col in ["col_load", "col_delete", "col_loaded"]:
        return
    global last_sort_column, sort_order
    try:
        data = [(tree.set(item, col), item) for item in tree.get_children('')]
        def get_sort_key(value_str):
            if col in ("col_created", "col_last_used"):
                if value_str in ("???", "Never") or not value_str: return 0
                try:
                    return time.mktime(time.strptime(value_str, "%y-%m-%d %H:%M"))
                except ValueError: return 0
            else: return str(value_str).lower()
        data.sort(key=lambda t: get_sort_key(t[0]), reverse=reverse)
        for i, (_, item) in enumerate(data):
            tree.move(item, '', i)
        sort_order[col] = reverse
        last_sort_column = col
        for c in sort_order:
             current_heading = tree.heading(c)
             heading_text = current_heading['text'].replace(' ▲', '').replace(' ▼', '')
             if c == col:
                 heading_text += (' ▼' if reverse else ' ▲')
             tree.heading(c, text=heading_text, command=lambda c_ref=c: sort_column(tree, c_ref, not sort_order.get(c_ref, False)))
    except Exception as e:
        print(f"Error sorting column '{col}': {e}")

for col_name in columns:
    if col_name not in ["col_load", "col_delete", "col_loaded"]:
        current_text = sim_tree.heading(col_name)['text']
        anchor_dir = 'w' if col_name=='col_name' else 'center'
        sim_tree.heading(col_name, text=current_text, command=lambda c=col_name: sort_column(sim_tree, c, False), anchor=anchor_dir)

sim_tree.grid(row=0, column=0, sticky="nsew")
scrollbar = ctk.CTkScrollbar(tree_frame, command=sim_tree.yview)
scrollbar.grid(row=0, column=1, sticky="ns")
sim_tree.configure(yscrollcommand=scrollbar.set)
sim_tree.bind('<<TreeviewSelect>>', lambda e: update_button_states())
sim_tree.bind("<Button-1>", handle_tree_click)
sim_tree.bind("<Motion>", handle_tree_motion)
sim_tree.bind("<Leave>", handle_tree_leave)
button_frame_bottom = ctk.CTkFrame(main_content_frame, fg_color="transparent")
button_frame_bottom.grid(row=3, column=0, pady=(10, 10), padx=10, sticky="ew")
button_frame_bottom.columnconfigure(0, weight=1)
button_frame_bottom.columnconfigure(1, weight=0)
button_frame_bottom.columnconfigure(2, weight=0)
button_frame_bottom.columnconfigure(3, weight=0)
button_frame_bottom.columnconfigure(4, weight=1)
button_height=35
reload_btn = ctk.CTkButton(button_frame_bottom, text="Reload List", command=populate_simulations, font=APP_FONT, height=button_height,
                           fg_color=BTN_RELOAD_FG_COLOR[mode_idx], hover_color=BTN_RELOAD_HOVER_COLOR[mode_idx], text_color=BTN_RELOAD_TEXT_COLOR[mode_idx])
reload_btn.grid(row=0, column=1, padx=10, pady=5)
graph_btn = ctk.CTkButton(button_frame_bottom, text="Simulation Statistics", command=on_show_graphs_thread, font=APP_FONT, height=button_height,
                          fg_color=BTN_GRAPH_FG_COLOR[mode_idx], hover_color=BTN_GRAPH_HOVER_COLOR[mode_idx], text_color=BTN_GRAPH_TEXT_COLOR[mode_idx])
graph_btn.grid(row=0, column=2, padx=10, pady=5)
create_btn = ctk.CTkButton(button_frame_bottom, text="Create Sim (API)", command=on_create_simulation, font=APP_FONT, height=button_height,
                           fg_color=BTN_CREATE_FG_COLOR[mode_idx], hover_color=BTN_CREATE_HOVER_COLOR[mode_idx], text_color=BTN_CREATE_TEXT_COLOR[mode_idx])
create_btn.grid(row=0, column=3, padx=10, pady=5)
status_frame = ctk.CTkFrame(main_window, height=25, corner_radius=0)
status_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
status_label = ctk.CTkLabel(status_frame, text="Initializing...", anchor="w", font=STATUS_FONT)
status_label.pack(side="left", fill="x", expand=True, padx=10, pady=3)

if __name__ == "__main__":
    main_window.after(10, update_treeview_style)
    update_button_states()
    update_status("Performing initial configuration verification...")
    initial_verify_thread = threading.Thread(target=perform_verification, args=(False, True), daemon=True)
    initial_verify_thread.start()
    main_window.protocol("WM_DELETE_WINDOW", on_closing)
    main_window.mainloop()