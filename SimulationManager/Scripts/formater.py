import os
import re
import sys

def split_braces_outside_strings(code: str) -> str:
    """
    Inserta saltos de línea antes y después de '{' y '}' solo cuando estamos fuera de un string en C#.
    """
    result_lines = []
    in_string = False  # Detectamos si estamos dentro de comillas dobles

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
    """
    Separa la respuesta en bloques de código asignados a cada archivo y formatea el contenido.
    :param respuesta: Cadena con la respuesta del modelo.
    :return: Diccionario con los nombres de los archivos y sus contenidos formateados.
    """
    patrones = re.findall(r'(\d+)\.(\w+\.cs)\{(.*?)}(?=\d+\.|$)', respuesta, re.DOTALL)
    if not patrones:
        print("No se encontraron bloques de código en la respuesta.")
        return {}
    
    codigos = {}
    for _, archivo, contenido in patrones:
        codigos[archivo] = format_csharp(contenido.strip())
    return codigos

def format_csharp(contenido: str) -> str:
    """
    Formatea el contenido para C# aplicando indentación adecuada y separación de bloques.
    :param contenido: Código C# sin formatear.
    :return: Código C# formateado.
    """
    # 1. Separar llaves solo fuera de strings
    preprocesado = split_braces_outside_strings(contenido)
    # 2. Insertar salto de línea después de ';'
    preprocesado = re.sub(r';', r';\n', preprocesado)
    # 3. Eliminar dobles saltos de línea
    preprocesado = re.sub(r'\n\s*\n', '\n', preprocesado)
    # 4. Ajustar indentación
    lineas = [l.strip() for l in preprocesado.split('\n') if l.strip()]
    nivel_indentacion = 0
    contenido_formateado = []
    for linea in lineas:
        if linea.startswith("}"):
            nivel_indentacion = max(nivel_indentacion - 1, 0)
        contenido_formateado.append("    " * nivel_indentacion + linea)
        if linea.endswith("{"):
            nivel_indentacion += 1
    return "\n".join(contenido_formateado)

def main():
    """
    1. Recibe el string completo de la respuesta como argumento.
    2. Separa los bloques de código y los formatea.
    3. Imprime el diccionario resultante con los nombres de archivo y su contenido.
    """
    if len(sys.argv) < 2:
        print("Uso: formater.py STRING")
        return

    respuesta = sys.argv[1]
    codigos = separar_codigos_por_archivo(respuesta)
    print("Se encontró la siguiente cantidad de archivos:", len(codigos))

    for archivo, contenido in codigos.items():
        print(f"{archivo}:\n{contenido}\n")

    # Retornar los códigos formateados
    return codigos

if __name__ == "__main__":
    main()
