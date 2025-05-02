using UnityEngine;
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Globalization;
using System.Linq;

/// <summary>
/// Registra estadísticas de la simulación en un archivo CSV utilizando escritura por lotes (batching).
/// Guarda los datos en Application.persistentDataPath/SimulationLoggerData/[NombreSimulacion].
/// NO registra datos nuevos mientras la simulación está pausada (GameStateManager.IsPaused == true).
/// MODIFICADO: Retrasa la escritura del encabezado hasta el primer volcado de buffer para asegurar que los nombres de organismos estén listos.
/// </summary>
public class SimulationLogger : MonoBehaviour
{
    // --- Constantes ---
    private const string LogTag = "[SimulationLogger]";
    private const string LogSubfolder = "SimulationLoggerData";
    private const string CsvSeparator = ";";
    private const string CsvFileName = "SimulationStats.csv";

    // --- Configuración del Batching/Buffering ---
    private const int MaxBufferSize = 100;
    private const float BatchWriteInterval = 1.0f; // Segundos

    // --- Variables ---
    [Tooltip("Nombre base para la simulación si no se carga desde 'simulation_loaded.txt'.")]
    [SerializeField]
    private string simulationName = "DefaultSimulation";
    private string logFilePath;
    private string simulationFolderPath;
    private bool isLogging = false;
    private Left_GUI leftGui;
    private List<string> logBuffer = new List<string>();
    private float lastBatchWriteTime = 0f;
    private string currentPersistentPath;

    // --- NUEVA VARIABLE ---
    private bool headerWritten = false; // Para controlar si el encabezado ya se escribió

    #region Unity Lifecycle Methods

    private void Awake()
    {
        currentPersistentPath = Application.persistentDataPath;
        Debug.Log($"{LogTag} Awake: Script inicializando. persistentDataPath = '{currentPersistentPath}'");
    }

    private void Start()
    {
        Debug.Log($"{LogTag} Start: Iniciando configuración...");
        ReadSimulationNameFromFile();
        leftGui = FindFirstObjectByType<Left_GUI>();
        if (leftGui == null)
        {
            Debug.LogError($"{LogTag} Start: No se encontró {nameof(Left_GUI)}. Logger desactivado.");
            enabled = false; return;
        }
        Debug.Log($"{LogTag} Start: {nameof(Left_GUI)} encontrado.");
        if (!SetupLogFilePath())
        {
             enabled = false; return;
        }

        if (!Application.isEditor)
        {
            Debug.Log($"{LogTag} Start: En modo Build, iniciando corutina para esperar a {nameof(Left_GUI)}...");
            StartCoroutine(WaitForOrganismNamesAndStartLogging());
        }
        else
        {
            Debug.Log($"{LogTag} Start: En modo Editor.");
        }
        Debug.Log($"{LogTag} Start: Configuración completada.");
    }

    private void Update()
    {
        if (!isLogging) return;

        try
        {
             bool isPaused = GameStateManager.IsPaused;
             if (!isPaused)
             {
                 string logLine = GenerateLogLine();
                 if (!string.IsNullOrEmpty(logLine))
                 {
                     logBuffer.Add(logLine);
                 }
             }

             // Escribir si buffer lleno o por tiempo (y si hay algo en el buffer)
             if (logBuffer.Count >= MaxBufferSize || (Time.time - lastBatchWriteTime >= BatchWriteInterval && logBuffer.Count > 0) )
             {
                 WriteBufferToFile(); // Intentará escribir header si es necesario
             }
        }
        catch (Exception ex)
        {
             Debug.LogError($"{LogTag} Update: Error inesperado: {ex.ToString()}");
        }
    }

    private void OnGUI()
    {
        if (Application.isEditor)
        {
            Rect buttonRect = new Rect(10, Screen.height - 50, 250, 40);
            string buttonText = isLogging ? "Finalizar captación (Batch)" : "Iniciar captación (Batch)";
            if (GUI.Button(buttonRect, buttonText))
            {
                if (isLogging) { StopLogging(); }
                else {
                    bool guiReady = leftGui != null && leftGui.enabled;
                    bool namesReady = leftGui?.OrganismNames != null && leftGui.OrganismNames.Any();
                    if (guiReady && namesReady) { StartLogging(); }
                    else { Debug.LogWarning($"{LogTag} OnGUI: No se puede iniciar. {nameof(Left_GUI)} no está listo (Enabled: {guiReady}, Names Loaded: {namesReady})."); }
                }
            }
        }
    }

    private void OnApplicationQuit()
    {
        Debug.Log($"{LogTag} OnApplicationQuit: Aplicación cerrando.");
        if (isLogging && logBuffer.Count > 0)
        {
            Debug.Log($"{LogTag} OnApplicationQuit: Escribiendo buffer restante ({logBuffer.Count} líneas)...");
            WriteBufferToFile(); // Intentará escribir header si no se escribió antes
        }
        isLogging = false;
    }

     private void OnDestroy()
     {
         Debug.Log($"{LogTag} OnDestroy: Objeto Logger destruido.");
         if (isLogging && logBuffer.Count > 0)
         {
             Debug.LogWarning($"{LogTag} OnDestroy: Destruido mientras loggeaba con buffer pendiente. Guardado final...");
             WriteBufferToFile();
         }
         isLogging = false;
     }

    #endregion

    #region Logging Control Methods

    private IEnumerator WaitForOrganismNamesAndStartLogging()
    {
        Debug.Log($"{LogTag} {nameof(WaitForOrganismNamesAndStartLogging)}: Iniciada. Esperando condiciones...");
        while (true)
        {
             bool guiExists = leftGui != null;
             bool guiEnabled = guiExists && leftGui.enabled;
             bool namesAvailable = guiEnabled && leftGui?.OrganismNames != null && leftGui.OrganismNames.Any();

             if (guiExists && guiEnabled && namesAvailable)
             {
                 Debug.Log($"{LogTag} {nameof(WaitForOrganismNamesAndStartLogging)}: ¡Condiciones cumplidas! Iniciando logging.");
                 StartLogging();
                 yield break;
             }
             yield return new WaitForSeconds(0.2f);
        }
    }

    public void StartLogging()
    {
        Debug.Log($"{LogTag} {nameof(StartLogging)}: Intento de iniciar captación...");
        if (isLogging) { Debug.LogWarning($"{LogTag} {nameof(StartLogging)}: Ya activo."); return; }

        // Validaciones
        if (leftGui == null || !leftGui.enabled) { Debug.LogError($"{LogTag} {nameof(StartLogging)}: Falló - {nameof(Left_GUI)} no disponible."); return; }
        if (leftGui.OrganismNames == null || !leftGui.OrganismNames.Any()) { Debug.LogError($"{LogTag} {nameof(StartLogging)}: Falló - {nameof(Left_GUI)} no tiene nombres de organismos."); return; }
        if (string.IsNullOrEmpty(logFilePath)) { Debug.LogError($"{LogTag} {nameof(StartLogging)}: Falló - Ruta de archivo no configurada."); return; }

        // Borrar Archivo Anterior
        if (File.Exists(logFilePath))
        {
            Debug.Log($"{LogTag} {nameof(StartLogging)}: Archivo anterior existe en '{logFilePath}'. Intentando eliminar...");
            try { File.Delete(logFilePath); Debug.Log($"{LogTag} {nameof(StartLogging)}: Archivo anterior eliminado."); }
            catch (Exception ex) { Debug.LogError($"{LogTag} {nameof(StartLogging)}: Error eliminando '{logFilePath}': {ex.ToString()}. Abortando inicio."); return; }
        } else {
            Debug.Log($"{LogTag} {nameof(StartLogging)}: No existe archivo anterior en '{logFilePath}'.");
        }

        // --- CAMBIO: NO escribir encabezado aquí ---
        // WriteCSVHeader(); // <-- Línea eliminada

        // Configurar Estado
        isLogging = true;
        logBuffer.Clear();
        lastBatchWriteTime = Time.time;
        headerWritten = false; // <-- Asegurar que el flag esté en false al iniciar

        Debug.Log($"{LogTag} {nameof(StartLogging)}: *** Captación iniciada ***. Guardando en: {logFilePath}. El encabezado se escribirá con los primeros datos."); // Mensaje actualizado
    }

    public void StopLogging()
    {
       Debug.Log($"{LogTag} {nameof(StopLogging)}: Intento de detener captación...");
       if (!isLogging) { Debug.LogWarning($"{LogTag} {nameof(StopLogging)}: Ya detenido."); return; }

       isLogging = false;
       WriteBufferToFile(); // Escribe buffer restante (y header si es necesario)
       Debug.Log($"{LogTag} {nameof(StopLogging)}: *** Captación finalizada ***. Archivo: {logFilePath}");
    }

    #endregion

    #region Data Handling and File IO

    private void ReadSimulationNameFromFile()
    {
        string simulationLoadedFile = Path.Combine(Application.streamingAssetsPath, "simulation_loaded.txt");
        Debug.Log($"{LogTag} {nameof(ReadSimulationNameFromFile)}: Buscando nombre en '{simulationLoadedFile}'");
        try {
             if (File.Exists(simulationLoadedFile)) {
                 string loadedName = File.ReadAllText(simulationLoadedFile).Trim();
                 if (!string.IsNullOrEmpty(loadedName)) {
                     simulationName = loadedName;
                     Debug.Log($"{LogTag} {nameof(ReadSimulationNameFromFile)}: Nombre cargado: '{simulationName}'");
                 } else {
                     Debug.LogWarning($"{LogTag} {nameof(ReadSimulationNameFromFile)}: Archivo vacío. Usando '{simulationName}'.");
                 }
             } else {
                 Debug.LogWarning($"{LogTag} {nameof(ReadSimulationNameFromFile)}: Archivo no encontrado. Usando '{simulationName}'.");
             }
        } catch (Exception ex) {
             Debug.LogError($"{LogTag} {nameof(ReadSimulationNameFromFile)}: Error leyendo: {ex.ToString()}. Usando '{simulationName}'.");
             simulationName = "DefaultSimulation";
        }
    }

    private bool SetupLogFilePath()
    {
        Debug.Log($"{LogTag} {nameof(SetupLogFilePath)}: Configurando rutas...");
        try {
            if (string.IsNullOrEmpty(currentPersistentPath)) {
                 Debug.LogError($"{LogTag} {nameof(SetupLogFilePath)}: persistentDataPath nulo."); return false;
            }
            Debug.Log($"{LogTag} {nameof(SetupLogFilePath)}: Usando base: '{currentPersistentPath}'");
            simulationFolderPath = Path.Combine(currentPersistentPath, LogSubfolder, simulationName);
            Debug.Log($"{LogTag} {nameof(SetupLogFilePath)}: Ruta carpeta logs: '{simulationFolderPath}'");
            if (!Directory.Exists(simulationFolderPath)) {
                Debug.Log($"{LogTag} {nameof(SetupLogFilePath)}: Creando directorio...");
                try { Directory.CreateDirectory(simulationFolderPath); Debug.Log($"{LogTag} {nameof(SetupLogFilePath)}: Directorio creado."); }
                catch (Exception dex) { Debug.LogError($"{LogTag} {nameof(SetupLogFilePath)}: ERROR al crear directorio '{simulationFolderPath}': {dex.ToString()}"); return false; }
            } else { Debug.Log($"{LogTag} {nameof(SetupLogFilePath)}: Directorio ya existe."); }
            logFilePath = Path.Combine(simulationFolderPath, CsvFileName);
            Debug.Log($"{LogTag} {nameof(SetupLogFilePath)}: Ruta archivo CSV: '{logFilePath}'");
            return true;
        } catch (Exception ex) {
            Debug.LogError($"{LogTag} {nameof(SetupLogFilePath)}: Error crítico configurando rutas: {ex.ToString()}");
            logFilePath = null; simulationFolderPath = null;
            return false;
        }
    }


    private string GenerateLogLine()
    {
        if (leftGui == null || leftGui.OrganismNames == null) return null;

        try {
             StringBuilder csvLine = new StringBuilder();
             string timestamp = DateTime.Now.ToString("dd-MM-yyyy HH:mm:ss", CultureInfo.InvariantCulture);
             csvLine.Append(timestamp);
             csvLine.Append(CsvSeparator).Append(leftGui.cachedFPS.ToString("F2", CultureInfo.InvariantCulture));
             csvLine.Append(CsvSeparator).Append(leftGui.cachedRealTime.ToString("F2", CultureInfo.InvariantCulture));
             csvLine.Append(CsvSeparator).Append(leftGui.cachedSimulatedTime.ToString("F2", CultureInfo.InvariantCulture));
             csvLine.Append(CsvSeparator).Append(GameStateManager.DeltaTime.ToString("F4", CultureInfo.InvariantCulture));
             csvLine.Append(CsvSeparator).Append(leftGui.cachedFrameCount.ToString(CultureInfo.InvariantCulture));
             csvLine.Append(CsvSeparator).Append(GameStateManager.IsPaused ? "Sí" : "No");

             if (leftGui.OrganismNames.Any() && leftGui.entityCounts != null) {
                 foreach (var orgName in leftGui.OrganismNames) {
                     leftGui.entityCounts.TryGetValue(orgName, out int count);
                     csvLine.Append(CsvSeparator).Append(count.ToString(CultureInfo.InvariantCulture));
                 }
             } // else: No añadir columnas si no hay nombres

             return csvLine.ToString();
        } catch (Exception ex) {
             Debug.LogError($"{LogTag} {nameof(GenerateLogLine)}: Error generando línea: {ex.ToString()}");
             return null;
        }
    }


    private void WriteBufferToFile()
    {
        // Verificar si necesitamos escribir el encabezado ANTES de procesar el buffer
        if (!headerWritten)
        {
            Debug.Log($"{LogTag} {nameof(WriteBufferToFile)}: Encabezado aún no escrito. Intentando escribir encabezado...");
            if (WriteCSVHeader()) // Intenta escribir header, devuelve true si OK
            {
                headerWritten = true; // Marcar como escrito si tuvo éxito
                Debug.Log($"{LogTag} {nameof(WriteBufferToFile)}: Encabezado escrito exitosamente.");
            }
            else
            {
                Debug.LogError($"{LogTag} {nameof(WriteBufferToFile)}: Falló la escritura del encabezado. No se escribirán datos del buffer para evitar corrupción.");
                // Considerar detener el logging aquí si el header falla:
                // isLogging = false;
                // enabled = false;
                return; // Salir para no escribir datos sin encabezado
            }
        }

        // Si llegamos aquí, el encabezado ya está escrito (o se acaba de escribir)
        // Ahora procesamos el buffer si no está vacío
        if (logBuffer == null || logBuffer.Count == 0) {
            // Debug.Log($"{LogTag} {nameof(WriteBufferToFile)}: Buffer vacío, nada más que escribir esta vez.");
             return;
        }
        if (string.IsNullOrEmpty(logFilePath)) {
             Debug.LogError($"{LogTag} {nameof(WriteBufferToFile)}: Intento de escribir buffer pero la ruta del archivo es inválida.");
             logBuffer.Clear();
             return;
         }

        List<string> bufferToWrite = new List<string>(logBuffer);
        logBuffer.Clear();
        // Debug.Log($"{LogTag} {nameof(WriteBufferToFile)}: Preparando para escribir {bufferToWrite.Count} líneas del buffer..."); // Log opcional

        try
        {
            string batchContent = string.Join(Environment.NewLine, bufferToWrite) + Environment.NewLine;
            // USAR AppendAllText para AÑADIR las líneas después del encabezado
            File.AppendAllText(logFilePath, batchContent, System.Text.Encoding.UTF8);
            lastBatchWriteTime = Time.time;
            // Debug.Log($"{LogTag} {nameof(WriteBufferToFile)}: {bufferToWrite.Count} líneas del buffer escritas exitosamente."); // Log opcional
        }
        catch (Exception ex) // Captura cualquier excepción de escritura
        {
            // Loguear el error detallado
            Debug.LogError($"{LogTag} {nameof(WriteBufferToFile)}: Error escribiendo buffer a '{logFilePath}': {ex.ToString()}");
            // Considerar añadir las líneas de vuelta al buffer para reintentar? (Riesgo de memoria)
            // logBuffer.InsertRange(0, bufferToWrite);
        }
    }


    /// <summary>
    /// Escribe la línea de encabezado al archivo CSV.
    /// Devuelve true si la escritura fue exitosa, false en caso contrario.
    /// </summary>
    private bool WriteCSVHeader() // Ahora devuelve bool
    {
        Debug.Log($"{LogTag} {nameof(WriteCSVHeader)}: Construyendo y escribiendo encabezado...");
        // Validaciones
        if (leftGui == null) { Debug.LogError($"{LogTag} {nameof(WriteCSVHeader)}: Falló - {nameof(Left_GUI)} es nulo."); return false; }
        // Verificar que los nombres estén disponibles AHORA MISMO
        if (leftGui.OrganismNames == null || !leftGui.OrganismNames.Any()) {
            Debug.LogError($"{LogTag} {nameof(WriteCSVHeader)}: Falló - {nameof(Left_GUI)}.OrganismNames es nulo o vacío en este momento. No se puede escribir encabezado completo.");
            // Decidir si escribir un header incompleto o fallar. Fallar es más seguro.
            return false;
        }
        if (string.IsNullOrEmpty(logFilePath)) { Debug.LogError($"{LogTag} {nameof(WriteCSVHeader)}: Falló - Ruta de archivo no configurada."); return false; }

        // Construcción del encabezado
        List<string> headers = new List<string> { "Timestamp", "FPS", "RealTime", "SimulatedTime", "DeltaTime", "FrameCount", "Pausado" };
        // Añadir nombres de organismos (ya verificamos que existen)
        headers.AddRange(leftGui.OrganismNames);
        string headerLine = string.Join(CsvSeparator, headers) + Environment.NewLine;
        Debug.Log($"{LogTag} {nameof(WriteCSVHeader)}: Encabezado a escribir: {headerLine.Trim()}");

        // Escritura (con try-catch)
        try
        {
            // Usar WriteAllText para CREAR el archivo SOLO con el encabezado.
            // Si ya existía (porque StartLogging falló al borrar), lo sobrescribirá.
            File.WriteAllText(logFilePath, headerLine, System.Text.Encoding.UTF8);
            Debug.Log($"{LogTag} {nameof(WriteCSVHeader)}: Encabezado escrito exitosamente en '{logFilePath}'.");
            return true; // Éxito
        }
        catch (Exception ex)
        {
            // Loguear el error detallado
            Debug.LogError($"{LogTag} {nameof(WriteCSVHeader)}: ¡ERROR al escribir encabezado en '{logFilePath}'!: {ex.ToString()}");
            return false; // Fallo
        }
    }

    #endregion
}