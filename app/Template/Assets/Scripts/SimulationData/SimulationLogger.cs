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
/// NO registra datos nuevos mientras la simulación está pausada (GameStateManager.IsPaused == true).
/// </summary>
public class SimulationLogger : MonoBehaviour
{
    // --- Constantes ---
    private const string CsvSeparator = ";";
    private const string CsvFileName = "SimulationStats.csv";

    // --- Configuración del Batching/Buffering ---
    private const int MaxBufferSize = 100;
    private const float BatchWriteInterval = 1.0f; // Escribe al menos cada 1 segundo

    // --- Variables ---
    [SerializeField]
    private string simulationName = "DefaultSimulation";
    private string logFilePath;
    private bool isLogging = false;
    private Left_GUI leftGui;
    private List<string> logBuffer = new List<string>();
    private float lastBatchWriteTime = 0f;

    #region Unity Lifecycle Methods

    private void Start()
    {
        ReadSimulationNameFromFile();

        leftGui = FindFirstObjectByType<Left_GUI>();
        if (leftGui == null)
        {
            Debug.LogError("SimulationLogger: No se encontró Left_GUI. Logger desactivado.");
            enabled = false;
            return;
        }

        SetupLogFilePath();

        if (!Application.isEditor)
        {
            StartCoroutine(WaitForOrganismNamesAndStartLogging());
        }
        else
        {
             Debug.Log("SimulationLogger: En modo Editor. Usa el botón 'Iniciar captación' para empezar.");
        }
    }

    /// <summary>
    /// Gestiona la adición de logs al buffer y la escritura a disco.
    /// Ahora comprueba si la simulación está pausada antes de añadir nuevos datos.
    /// </summary>
    private void Update()
    {
        if (isLogging) // Solo procesar si el logging está activo
        {
            // --- ¡CAMBIO PRINCIPAL AQUÍ! ---
            // Solo generar y añadir líneas al buffer si la simulación NO está pausada.
            if (!GameStateManager.IsPaused) // <--- Añadida esta condición
            {
                // 1. Generar la línea de datos para el frame actual
                string logLine = GenerateLogLine();

                if (!string.IsNullOrEmpty(logLine))
                {
                    // 2. Añadirla al buffer en memoria (solo si no está pausado)
                    logBuffer.Add(logLine);
                }
            }
            // --- FIN DEL CAMBIO ---

            // 3. Comprobar si se debe escribir el buffer a disco
            //    Esto se hace independientemente de si está pausado, para asegurar que
            //    los datos recolectados *antes* de pausar se guarden eventualmente.
            if (logBuffer.Count >= MaxBufferSize || Time.time - lastBatchWriteTime >= BatchWriteInterval)
            {
                WriteBufferToFile();
            }
        }
    }

    // --- OnGUI (Sin cambios) ---
    private void OnGUI()
    {
        if (Application.isEditor)
        {
            Rect buttonRect = new Rect(10, Screen.height - 50, 250, 40);
            string buttonText = isLogging ? "Finalizar captación (Batch)" : "Iniciar captación (Batch)";

            if (GUI.Button(buttonRect, buttonText))
            {
                if (isLogging) { StopLogging(); }
                else
                {
                    if (leftGui != null && leftGui.enabled) { StartLogging(); }
                    else { Debug.LogWarning("SimulationLogger: Left_GUI no listo."); }
                }
            }
        }
    }

    // --- OnApplicationQuit (Sin cambios) ---
    private void OnApplicationQuit()
    {
        if (isLogging)
        {
            Debug.Log("SimulationLogger: Cerrando aplicación, escribiendo buffer restante...");
            WriteBufferToFile();
        }
    }

    #endregion

    #region Logging Control Methods

    // --- WaitForOrganismNamesAndStartLogging (Sin cambios) ---
    private IEnumerator WaitForOrganismNamesAndStartLogging()
    {
        Debug.Log("SimulationLogger: Esperando Left_GUI...");
        while (leftGui == null || leftGui.validComponentTypes == null || !leftGui.validComponentTypes.Any())
        {
            yield return null;
        }
        Debug.Log($"SimulationLogger: Left_GUI listo. Iniciando logging automático.");
        StartLogging();
    }

    // --- StartLogging (Sin cambios) ---
    public void StartLogging()
    {
        if (isLogging) { Debug.LogWarning("SimulationLogger: Logging ya iniciado."); return; }
        if (leftGui == null || !leftGui.enabled) { Debug.LogError("SimulationLogger: Left_GUI no disponible."); return; }

        if (File.Exists(logFilePath))
        {
            try { File.Delete(logFilePath); Debug.Log($"SimulationLogger: Archivo anterior eliminado."); }
            catch (Exception ex) { Debug.LogError($"SimulationLogger: Error eliminando archivo anterior: {ex.Message}"); }
        }

        isLogging = true;
        logBuffer.Clear();
        lastBatchWriteTime = Time.time;
        WriteCSVHeader();
        Debug.Log("SimulationLogger: Captación iniciada (modo Batch). No se registrará durante pausa.");
    }

    // --- StopLogging (Sin cambios) ---
    public void StopLogging()
    {
         if (!isLogging) { Debug.LogWarning("SimulationLogger: Logging ya detenido."); return; }
        isLogging = false;
        WriteBufferToFile(); // Escribe datos restantes
        Debug.Log($"SimulationLogger: Captación finalizada. Archivo: {logFilePath}");
    }

    #endregion

    #region Data Handling and File IO

    // --- ReadSimulationNameFromFile (Sin cambios) ---
     private void ReadSimulationNameFromFile()
    {
        string simulationLoadedFile = Path.Combine(Application.streamingAssetsPath, "simulation_loaded.txt");
        Debug.Log($"SimulationLogger: Buscando nombre simulación en: {simulationLoadedFile}");
        if (File.Exists(simulationLoadedFile))
        {
            try
            {
                string loadedName = File.ReadAllText(simulationLoadedFile).Trim();
                if (!string.IsNullOrEmpty(loadedName)) { simulationName = loadedName; Debug.Log($"SimulationLogger: Nombre simulación cargado: {simulationName}"); }
                else { Debug.LogWarning("SimulationLogger: simulation_loaded.txt vacío. Usando 'DefaultSimulation'."); simulationName = "DefaultSimulation"; }
            }
            catch (Exception ex) { Debug.LogError($"SimulationLogger: Error leyendo simulation_loaded.txt: {ex.Message}. Usando 'DefaultSimulation'."); simulationName = "DefaultSimulation"; }
        }
        else { Debug.LogWarning("SimulationLogger: No se encontró simulation_loaded.txt. Usando 'DefaultSimulation'."); simulationName = "DefaultSimulation"; }
    }

    // --- SetupLogFilePath (Sin cambios) ---
    private void SetupLogFilePath()
    {
        try
        {
            string documentsPath = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
            string folderPath = Path.Combine(documentsPath, "SimulationLoggerData", simulationName);
            if (!Directory.Exists(folderPath)) { Directory.CreateDirectory(folderPath); Debug.Log($"SimulationLogger: Carpeta logs creada: {folderPath}"); }
            logFilePath = Path.Combine(folderPath, CsvFileName);
            Debug.Log($"SimulationLogger: Archivo CSV: {logFilePath}");
        }
        catch (Exception ex) { Debug.LogError($"SimulationLogger: Error crítico configurando ruta logs: {ex.Message}. Logger desactivado."); enabled = false; }
    }

    // --- GenerateLogLine (Sin cambios) ---
    private string GenerateLogLine()
    {
        if (leftGui == null || leftGui.entityCounts == null || leftGui.OrganismNames == null) { return null; }

        StringBuilder csvLine = new StringBuilder();
        string timestamp = DateTime.Now.ToString("dd-MM-yyyy HH:mm:ss", CultureInfo.InvariantCulture);
        csvLine.Append(timestamp);
        csvLine.Append(CsvSeparator).Append(leftGui.cachedFPS.ToString("F2", CultureInfo.InvariantCulture));
        csvLine.Append(CsvSeparator).Append(leftGui.cachedRealTime.ToString("F2", CultureInfo.InvariantCulture));
        csvLine.Append(CsvSeparator).Append(leftGui.cachedSimulatedTime.ToString("F2", CultureInfo.InvariantCulture));
        csvLine.Append(CsvSeparator).Append(GameStateManager.DeltaTime.ToString("F4", CultureInfo.InvariantCulture));
        csvLine.Append(CsvSeparator).Append(leftGui.cachedFrameCount.ToString(CultureInfo.InvariantCulture));
        csvLine.Append(CsvSeparator).Append(GameStateManager.IsPaused ? "Sí" : "No"); // Se sigue registrando el estado "Pausado"

        foreach (var orgName in leftGui.OrganismNames)
        {
            leftGui.entityCounts.TryGetValue(orgName, out int count);
            csvLine.Append(CsvSeparator).Append(count.ToString(CultureInfo.InvariantCulture));
        }
        return csvLine.ToString();
    }

    // --- WriteBufferToFile (Sin cambios) ---
    private void WriteBufferToFile()
    {
        if (logBuffer == null || logBuffer.Count == 0) { return; }

        try
        {
            string batchContent = string.Join(Environment.NewLine, logBuffer) + Environment.NewLine;
            File.AppendAllText(logFilePath, batchContent);
            logBuffer.Clear();
            lastBatchWriteTime = Time.time;
        }
        catch (IOException ioEx) { Debug.LogError($"SimulationLogger: Error IO escribiendo buffer: {ioEx.Message}"); }
        catch (Exception ex) { Debug.LogError($"SimulationLogger: Error general escribiendo buffer: {ex.Message}"); }
    }

    // --- WriteCSVHeader (Sin cambios) ---
    private void WriteCSVHeader()
    {
         if (leftGui == null) { Debug.LogError("SimulationLogger: No se puede escribir encabezado, Left_GUI nulo."); return; }
        List<string> headers = new List<string> { "Timestamp", "FPS", "RealTime", "SimulatedTime", "DeltaTime", "FrameCount", "Pausado" };
        if (leftGui.OrganismNames != null) { headers.AddRange(leftGui.OrganismNames); }
        else { Debug.LogWarning("SimulationLogger: Left_GUI.OrganismNames nulo al escribir encabezado."); }
        string headerLine = string.Join(CsvSeparator, headers) + Environment.NewLine;
        try { File.AppendAllText(logFilePath, headerLine); } // Append porque StartLogging ya borró el archivo
        catch (Exception ex) { Debug.LogError($"SimulationLogger: Error escribiendo encabezado: {ex.Message}"); }
    }

    #endregion
}