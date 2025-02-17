import openai
import os
import csv
from dotenv import load_dotenv
import tiktoken

# Cargar las variables de entorno desde el archivo .env ubicado en la carpeta superior
load_dotenv(dotenv_path="../.env")

# Obtiene la API Key y el nombre del modelo fine-tuned
openai.api_key = os.getenv("OPENAI_API_KEY")
FINE_TUNED_MODEL_NAME = os.getenv("FINE_TUNED_MODEL_NAME")

# System prompt (instrucción para el modelo)
SYSTEM_MESSAGE = (
    "Eres un modelo especializado en generar código C# para simulaciones de Unity. "
    "Considera que los tiempos son en segundos y con un rango de 0.9 a 1.1 el valor en segundos; "
    "además, los colores en Unity se expresan en valores RGB divididos en 255. "
    "Debes contestar tal cual como se te fue entrenado, sin agregar nada más de lo que se espera en C#. "
    "No puedes responder en ningún otro lenguaje de programación ni añadir comentarios o palabras innecesarias. "
    "Solo puedes responder a consultas relacionadas con simulaciones en Unity sobre e.coli, s.cerevisiae o ambas, donde se indiquen: "
    "- El color de la(s) célula(s). "
    "- El tiempo de duplicación en minutos. "
    "- El porcentaje de crecimiento para separarse del padre. "
    "Tu respuesta debe incluir estrictamente estos scripts en el orden especificado:\n"
    " - Si se piden ambas (e.coli y s.cerevisiae):\n"
    "   1.PrefabMaterialCreator.cs\n"
    "   2.CreatePrefabsOnClick.cs\n"
    "   3.EColiComponent.cs\n"
    "   4.SCerevisiaeComponent.cs\n"
    "   5.EColiSystem.cs\n"
    "   6.SCerevisiaeSystem.cs\n"
    " - Si se pide solo e.coli:\n"
    "   1.PrefabMaterialCreator.cs\n"
    "   2.CreatePrefabsOnClick.cs\n"
    "   3.EColiComponent.cs\n"
    "   4.EColiSystem.cs\n"
    " - Si se pide solo s.cerevisiae:\n"
    "   1.PrefabMaterialCreator.cs\n"
    "   2.CreatePrefabsOnClick.cs\n"
    "   3.SCerevisiaeComponent.cs\n"
    "   4.SCerevisiaeSystem.cs\n\n"
    "El formato de cada script debe ser:\n"
    "\"1.PrefabMaterialCreator.cs{...}2.CreatePrefabsOnClick.cs{...}\" etc. "
    "Cualquier pregunta que no cumpla con las características anteriores (es decir, que no mencione e.coli y/o s.cerevisiae, color, "
    "tiempo de duplicación y porcentaje de separación) será respondida con: \"ERROR FORMATO DE PREGUNTA.\". "
    "Y recuerda, responde tal cual como se te entrenó"
)

def count_tokens(text: str) -> int:
    """
    Cuenta la cantidad de tokens del texto usando la codificación adecuada para el modelo.
    """
    try:
        encoding = tiktoken.encoding_for_model(FINE_TUNED_MODEL_NAME)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def call_api(pregunta: str) -> tuple:
    """
    Llama a la API de OpenAI usando el modelo fine-tuned y devuelve la respuesta generada,
    junto con la cantidad de tokens de entrada y salida.

    :param pregunta: El prompt o pregunta a enviar.
    :return: Tuple (respuesta, input_tokens, output_tokens)
    """
    try:
        # Construir el listado de mensajes con el system prompt y el mensaje del usuario.
        messages = [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": pregunta}
        ]
        
        # Estimar tokens de entrada (aproximación sumando los tokens del system prompt y la pregunta)
        input_tokens = count_tokens(SYSTEM_MESSAGE) + count_tokens(pregunta)
        
        response = openai.ChatCompletion.create(
            model=FINE_TUNED_MODEL_NAME,
            messages=messages,
            temperature=0,  # Temperatura 0 para salida determinista
        )
        
        reply = response.choices[0].message["content"].strip()
        output_tokens = count_tokens(reply)
        return reply, input_tokens, output_tokens
    except Exception as e:
        print(f"Error al llamar a la API: {e}")
        return "", 0, 0

if __name__ == "__main__":
    # Ejemplo de prueba: se puede ejecutar este archivo para verificar el funcionamiento
    sample_pregunta = (
        "Generar código para crear prefabs y materiales en Unity con e.coli y s.cerevisiae, "
        "donde el color de la célula de SCerevisiae sea azul, el tiempo de duplicación sea de 10 minutos "
        "y el porcentaje de crecimiento para separarse sea 0.7."
    )
    reply, in_tokens, out_tokens = call_api(sample_pregunta)
    print("Respuesta de la API:")
    print(reply)
    print("Input tokens:", in_tokens)
    print("Output tokens:", out_tokens)
