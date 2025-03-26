import openai
import os
import csv
from dotenv import load_dotenv
import tiktoken
import sys

# Cargar las variables de entorno desde el archivo .env ubicado en la carpeta superior
load_dotenv(dotenv_path="../.env")

# Obtiene la API Key y los nombres de los modelos
openai.api_key = os.getenv("OPENAI_API_KEY")
FINE_TUNED_MODEL_NAME = os.getenv("FINE_TUNED_MODEL_NAME")
SECOND_FINE_TUNED_MODEL_NAME = os.getenv("2ND_FINE_TUNED_MODEL_NAME")

# System prompts para cada modelo
SYSTEM_MESSAGE_PRIMARY = (
    "Eres un modelo especializado en generar código C# para simulaciones de Unity. Considera que los tiempos son en segundos; además, los colores en Unity se expresan en valores RGB divididos en 255. Debes contestar tal cual como se te fue entrenado, sin agregar nada más de lo que se espera en C#. No puedes responder en ningún otro lenguaje de programación ni añadir comentarios o palabras innecesarias. Solo puedes responder a consultas relacionadas con simulaciones en Unity sobre EColi, SCerevisiae o ambas, donde se indiquen: - El color de la(s) célula(s). - El tiempo de duplicación en minutos. - El porcentaje de crecimiento para separarse del padre. Tu respuesta debe incluir estrictamente estos scripts en el orden especificado: - Si se piden ambas (EColi y SCerevisiae): 1.PrefabMaterialCreator.cs, 2.CreatePrefabsOnClick.cs, 3.EColiComponent.cs, 4.SCerevisiaeComponent.cs, 5.EColiSystem.cs, 6.SCerevisiaeSystem.cs. - Si se pide solo EColi: 1.PrefabMaterialCreator.cs, 2.CreatePrefabsOnClick.cs, 3.EColiComponent.cs, 4.EColiSystem.cs. - Si se pide solo SCerevisiae: 1.PrefabMaterialCreator.cs, 2.CreatePrefabsOnClick.cs, 3.SCerevisiaeComponent.cs, 4.SCerevisiaeSystem.cs - Si se pide 2 EColi: 1.PrefabMaterialCreator.cs, 2.CreatePrefabsOnClick.cs, 3.EColi_1Component.cs, 4.EColi_2Component.cs, 5.EColi_1System.cs, 6.EColi_2System.cs. - Si se pide 2 SCerevisiae: 1.PrefabMaterialCreator.cs, 2.CreatePrefabsOnClick.cs, 3.SCerevisiae_1Component.cs, 4.SCerevisiae_2Component.cs, 5.SCerevisiae_1System.cs, 6.SCerevisiae_2System.cs. El formato de cada script debe ser \"1.PrefabMaterialCreator.cs{...}2.CreatePrefabsOnClick.cs{...}\" etc. Cualquier pregunta que no cumpla con las características anteriores será respondida con: \"ERROR FORMATO DE PREGUNTA.\"."
)

SYSTEM_MESSAGE_SECONDARY = (
    "Eres un traductor especializado en simulaciones biológicas para Unity. Tu función exclusiva es convertir descripciones en lenguaje natural en especificaciones técnicas estructuradas para EColi y SCerevisiae. Requisitos obligatorios: 1. Solo procesarás 1 o 2 organismos por solicitud 2. Organismos permitidos: exclusivamente EColi (bacteria) y SCerevisiae (levadura) 3. Parámetros requeridos para cada organismo: - Color (en formato nombre o adjetivo+color) - Tiempo de duplicación (en minutos) - Porcentaje de separación padre-hijo (50-95%) Instrucciones estrictas: • Si la solicitud menciona otros organismos, fenómenos no biológicos, o está fuera del contexto de simulaciones celulares: responde exactamente 'ERROR DE CONTENIDO' • Usa el formato: '[Cantidad] [Organismo]. El [Organismo] debe ser de color [color], duplicarse cada [X] minutos y el hijo se separa del padre cuando alcanza el [Y]% del crecimiento.' • Para múltiples organismos del mismo tipo usa sufijos numéricos (Ej: EColi_1, SCerevisiae_2) • Asigna valores por defecto coherentes cuando el usuario no especifique parámetros"
)

def count_tokens(text: str) -> int:
    try:
        encoding = tiktoken.encoding_for_model(FINE_TUNED_MODEL_NAME)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def check_api_connection() -> bool:
    try:
        openai.Model.list()
        return True
    except Exception as e:
        print("Error al conectar con la API:", e)
        return False

def call_api_generic(pregunta: str, model_name: str, system_message: str) -> tuple:
    if not check_api_connection():
        return "", 0, 0

    try:
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": pregunta}
        ]
        
        input_tokens = count_tokens(system_message) + count_tokens(pregunta)
        response = openai.ChatCompletion.create(
            model=model_name,
            messages=messages,
            temperature=0,
            timeout=30
        )
        
        reply = response.choices[0].message["content"].strip()
        output_tokens = count_tokens(reply)
        return reply, input_tokens, output_tokens
    except Exception as e:
        print(f"Error al llamar al modelo {model_name}: {e}")
        return "", 0, 0

def call_primary_model(pregunta: str) -> tuple:
    return call_api_generic(pregunta, FINE_TUNED_MODEL_NAME, SYSTEM_MESSAGE_PRIMARY)

def call_secondary_model(pregunta: str) -> tuple:
    return call_api_generic(pregunta, SECOND_FINE_TUNED_MODEL_NAME, SYSTEM_MESSAGE_SECONDARY)

if __name__ == "__main__":
    # Test del modelo secundario
    test_prompt = "Necesito una simulación con una bacteria roja que se divide cada 5 minutos"
    reply, _, _ = call_secondary_model(test_prompt)
    print("Test modelo secundario:", reply)