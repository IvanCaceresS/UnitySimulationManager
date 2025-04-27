#!/bin/bash
set -e # Salir inmediatamente si un comando falla

# --- Configuración ---
VENV_DIR=".venv"
REQUIREMENTS_FILE="./requirements.txt"
MAIN_SCRIPT="./main.py" # Nombre del script principal para PyInstaller
BUILD_NAME="SimulationManager" # Nombre del ejecutable final
ICON_WIN="img/icono.ico" # Icono para Windows y Linux
ICON_MAC="img/icono.icns" # Icono para macOS
# Elementos (archivos/directorios) a copiar a la carpeta ./dist
ITEMS_TO_COPY=("./.env" "./img" "./Template") # <-- Nombre de variable y contenido actualizado
BUILD_DIST_DIR="./dist" # Directorio de salida por defecto de PyInstaller
BUILD_DIR="./build" # Directorio temporal creado por PyInstaller
SPEC_FILE="./${BUILD_NAME}.spec" # Archivo spec creado por PyInstaller

echo "Iniciando script de configuración, build y copia..."

# --- 1. Eliminar entorno virtual existente si existe ---
if [ -d "$VENV_DIR" ]; then
    echo "Eliminando entorno virtual existente '$VENV_DIR'..."
    rm -rf "$VENV_DIR"
    echo "Entorno virtual eliminado."
fi

# --- 2. Verificar si Python está disponible ---
if ! command -v python &> /dev/null; then
    echo "Error: Python no está instalado o no se encuentra en PATH."
    echo "Por favor, instala Python (idealmente 3.x) y asegúrate de que sea accesible desde tu terminal."
    exit 1
fi
echo "Python encontrado."

# --- 3. Crear nuevo entorno virtual ---
echo "Creando nuevo entorno virtual '$VENV_DIR'..."
python -m venv "$VENV_DIR"
echo "Entorno virtual creado."

# --- 4. Determinar y Activar Entorno Virtual ---
VENV_ACTIVATE=""
case "$OSTYPE" in
    linux*|darwin*)
        VENV_ACTIVATE="$VENV_DIR/bin/activate"
        ;;
    msys*|mingw*)
        VENV_ACTIVATE="$VENV_DIR/Scripts/activate"
        ;;
    *)
        echo "Advertencia: Tipo de SO desconocido '$OSTYPE'. Asumiendo ruta de activación tipo Linux/macOS."
        VENV_ACTIVATE="$VENV_DIR/bin/activate"
        ;;
esac

if [ ! -f "$VENV_ACTIVATE" ]; then
    echo "Error: No se pudo encontrar el script de activación del entorno virtual en '$VENV_ACTIVATE'."
    echo "Por favor, verifica la estructura del directorio '$VENV_DIR'."
    exit 1
fi

echo "Activando entorno virtual..."
source "$VENV_ACTIVATE"
echo "Entorno virtual activado. Usando Python de: $(command -v python)"


# --- 5. Actualizar pip e instalar PyInstaller y dependencias ---
echo "Actualizando pip, setuptools, wheel e instalando PyInstaller..."
python -m pip install --upgrade pip setuptools wheel
pip install pyinstaller

if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Instalando dependencias adicionales desde '$REQUIREMENTS_FILE'..."
    pip install --no-cache-dir -r "$REQUIREMENTS_FILE"
    echo "Dependencias instaladas."
else
    echo "Advertencia: '$REQUIREMENTS_FILE' no encontrado, omitiendo instalación de dependencias adicionales."
fi

# --- 6. Verificar si el script principal para la build existe ---
if [ ! -f "$MAIN_SCRIPT" ]; then
    echo "Error: El script principal '$MAIN_SCRIPT' para PyInstaller no fue encontrado."
    echo "Asegúrate de que tu archivo principal se llame '$MAIN_SCRIPT' y esté en la raíz del proyecto."
    exit 1
fi
echo "Script principal '$MAIN_SCRIPT' encontrado."

# --- 7. Determinar icono y construir con PyInstaller ---
echo "Preparando y ejecutando PyInstaller build..."

ICON_TO_USE=""
PYINSTALLER_CMD="pyinstaller --onefile --windowed --name \"$BUILD_NAME\""

case "$OSTYPE" in
    darwin*)
        if [ -f "$ICON_MAC" ]; then
            ICON_TO_USE="$ICON_MAC"
            PYINSTALLER_CMD="$PYINSTALLER_CMD --icon=\"$ICON_TO_USE\""
            echo "Usando icono para macOS: '$ICON_TO_USE'"
        else
            echo "Advertencia: Icono para macOS '$ICON_MAC' no encontrado. La build continuará sin icono."
        fi
        ;;
    linux*|msys*|mingw*)
        if [ -f "$ICON_WIN" ]; then
            ICON_TO_USE="$ICON_WIN"
            PYINSTALLER_CMD="$PYINSTALLER_CMD --icon=\"$ICON_TO_USE\""
             echo "Usando icono para Windows/Linux: '$ICON_TO_USE'"
        else
             echo "Advertencia: Icono para Windows/Linux '$ICON_WIN' no encontrado. La build continuará sin icono."
        fi
        ;;
    *)
        echo "Advertencia: Tipo de SO desconocido '$OSTYPE'. No se usará icono."
        ;;
esac

PYINSTALLER_CMD="$PYINSTALLER_CMD \"$MAIN_SCRIPT\""

echo "Ejecutando comando PyInstaller: $PYINSTALLER_CMD"
eval $PYINSTALLER_CMD

echo "Build de PyInstaller finalizada."

# --- 8. Copiar elementos (archivos/directorios) adicionales a la carpeta dist ---
echo "Copiando elementos necesarios a '$BUILD_DIST_DIR'..." # <-- Mensaje actualizado

if [ ! -d "$BUILD_DIST_DIR" ]; then
    echo "Error: El directorio de salida de PyInstaller '$BUILD_DIST_DIR' no fue encontrado después de la build."
    echo "La build de PyInstaller pudo haber fallado. Revisa los mensajes anteriores."
    exit 1
fi

# Iterar sobre la lista de elementos a copiar
for item in "${ITEMS_TO_COPY[@]}"; do # <-- Nombre de variable actualizado en el bucle
    # Verificar si el elemento (archivo o directorio) fuente existe
    if [ -e "$item" ]; then # <-- ¡Verificación corregida! [-e] verifica si existe
        echo "Copiando '$item' a '$BUILD_DIST_DIR/'..."
        # 'cp -r' funciona para archivos y directorios.
        # El '/' final en el destino asegura que el elemento fuente se copie DENTRO de dist.
        cp -r "$item" "$BUILD_DIST_DIR/"
        echo "Copiado exitoso."
    else
        echo "Advertencia: Elemento fuente '$item' no encontrado. Omitiendo copia." # <-- Mensaje actualizado
    fi
done

echo "Copia de elementos finalizada." # <-- Mensaje actualizado

# --- 9. Limpiar archivos y directorios temporales de PyInstaller ---
echo "Iniciando limpieza de archivos y directorios temporales de PyInstaller..."

if [ -d "$BUILD_DIR" ]; then
    echo "Eliminando directorio '$BUILD_DIR'..."
    rm -rf "$BUILD_DIR"
    echo "'$BUILD_DIR' eliminado."
else
    echo "Directorio '$BUILD_DIR' no encontrado, omitiendo eliminación."
fi

if [ -f "$SPEC_FILE" ]; then
    echo "Eliminando archivo '$SPEC_FILE'..."
    rm "$SPEC_FILE"
    echo "'$SPEC_FILE' eliminado."
else
    echo "Archivo '$SPEC_FILE' no encontrado, omitiendo eliminación."
fi

echo "Limpieza finalizada."

# --- Finalización ---
echo ""
echo "------------------------------------------------------------------"
echo "Script completado exitosamente."
echo "El ejecutable '$BUILD_NAME' y los elementos copiados se encuentran en la carpeta '$BUILD_DIST_DIR'."
echo "Los archivos temporales de la build ('$BUILD_DIR' y '$SPEC_FILE') han sido eliminados."
echo "------------------------------------------------------------------"