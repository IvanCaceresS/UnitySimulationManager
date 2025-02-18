using UnityEngine;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Globalization;

public class SimulationLogger : MonoBehaviour
{
    private const float LogInterval = 5f;             // Intervalo de 5 segundos para registrar datos
    private const string CsvSeparator = ";";          // Separador de campos en el CSV
    private const string CsvFileName = "SimulationStats.csv";

    // Nombre de la simulación (se leerá de simulation_loaded.txt; si no existe, se usará "DefaultSimulation")
    [SerializeField]
    private string simulationName = "DefaultSimulation";

    private float lastLogTime = 0f;
    private string logFilePath;
    private bool isLogging = false;
    private Left_GUI leftGui;

    private void Start()
    {
        // Intentar leer simulation_loaded.txt desde StreamingAssets
        string simulationLoadedFile = Path.Combine(Application.streamingAssetsPath, "simulation_loaded.txt");
        Debug.Log($"SimulationLogger: Leyendo {simulationLoadedFile}...");
        if (File.Exists(simulationLoadedFile))
        {
            try
            {
                string loadedName = File.ReadAllText(simulationLoadedFile).Trim();
                if (!string.IsNullOrEmpty(loadedName))
                {
                    simulationName = loadedName;
                    Debug.Log($"SimulationLogger: Nombre de simulación actualizado a: {simulationName}");
                }
                else
                {
                    simulationName = "DefaultSimulation";
                    Debug.LogWarning("SimulationLogger: El archivo simulation_loaded.txt está vacío. Usando 'DefaultSimulation'.");
                }
            }
            catch (Exception ex)
            {
                Debug.LogError("SimulationLogger: Error al leer simulation_loaded.txt: " + ex.Message);
                simulationName = "DefaultSimulation";
            }
        }
        else
        {
            simulationName = "DefaultSimulation";
            Debug.LogWarning("SimulationLogger: No se encontró simulation_loaded.txt en StreamingAssets. Usando 'DefaultSimulation'.");
        }

        leftGui = FindFirstObjectByType<Left_GUI>();
        if (leftGui == null)
        {
            Debug.LogError("SimulationLogger: No se encontró Left_GUI en la escena.");
            enabled = false;
            return;
        }

        // Utilizar la carpeta "My Documents" para almacenar los resultados, según la consigna.
        string documentsPath = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
        // Construir la ruta: Documents\SimulationLoggerData\<simulationName>
        string folderPath = Path.Combine(documentsPath, "SimulationLoggerData", simulationName);

        // Crear la carpeta si no existe
        if (!Directory.Exists(folderPath))
        {
            try
            {
                Directory.CreateDirectory(folderPath);
            }
            catch (Exception ex)
            {
                Debug.LogError($"SimulationLogger: Error al crear la carpeta '{folderPath}': {ex.Message}");
                enabled = false;
                return;
            }
        }

        // Definir la ruta completa del archivo CSV
        logFilePath = Path.Combine(folderPath, CsvFileName);
        Debug.Log($"SimulationLogger: El CSV se almacenará en: {logFilePath}");

        // En build (no en editor) arrancar automáticamente la captura
        if (!Application.isEditor)
        {
            StartLogging();
        }
    }

    private void Update()
    {
        if (isLogging && Time.time - lastLogTime >= LogInterval)
        {
            lastLogTime = Time.time;
            LogAllData();
        }
    }

    private void OnGUI()
    {
        // En editor se muestra el botón para iniciar/detener
        if (Application.isEditor)
        {
            string buttonText = isLogging ? "Finalizar captación de estadísticas" : "Iniciar captación de estadísticas";
            if (GUI.Button(new Rect(10, Screen.height - 50, 250, 40), buttonText))
            {
                if (isLogging)
                    StopLogging();
                else
                    StartLogging();
            }
        }
    }

    /// <summary>
    /// Inicia la captura de datos: elimina el archivo CSV anterior (si existe) y escribe el encabezado.
    /// </summary>
    private void StartLogging()
    {
        // Eliminar el archivo anterior para comenzar de cero
        if (File.Exists(logFilePath))
        {
            try
            {
                File.Delete(logFilePath);
            }
            catch (Exception ex)
            {
                Debug.LogError($"SimulationLogger: Error al eliminar el archivo anterior: {ex.Message}");
            }
        }

        isLogging = true;
        lastLogTime = Time.time;
        WriteCSVHeader();
        Debug.Log("SimulationLogger: Captación de estadísticas iniciada.");
    }

    /// <summary>
    /// Detiene la captura de datos.
    /// </summary>
    private void StopLogging()
    {
        isLogging = false;
        Debug.Log($"SimulationLogger: Captación de estadísticas finalizada. Archivo guardado en: {logFilePath}");
    }

    /// <summary>
    /// Registra en una línea los datos actuales de la simulación y el conteo de organismos.
    /// </summary>
    private void LogAllData()
    {
        if (leftGui == null || !isLogging)
            return;

        StringBuilder csvLine = new StringBuilder();

        // 1. Timestamp (formateado)
        csvLine.Append(DateTime.Now.ToString("dd-MM-yyyy HH:mm:ss", CultureInfo.InvariantCulture));
        csvLine.Append(CsvSeparator);

        // 2. Datos de la simulación (obtenidos desde Left_GUI y GameStateManager)
        csvLine.Append(leftGui.cachedFPS.ToString("F2", CultureInfo.InvariantCulture)).Append(CsvSeparator);
        csvLine.Append(leftGui.cachedRealTime.ToString("F2", CultureInfo.InvariantCulture)).Append(CsvSeparator);
        csvLine.Append(leftGui.cachedSimulatedTime.ToString("F2", CultureInfo.InvariantCulture)).Append(CsvSeparator);
        csvLine.Append(GameStateManager.DeltaTime.ToString("F2", CultureInfo.InvariantCulture)).Append(CsvSeparator);
        csvLine.Append(leftGui.cachedFrameCount.ToString(CultureInfo.InvariantCulture)).Append(CsvSeparator);
        csvLine.Append(GameStateManager.IsPaused ? "Sí" : "No");

        // 3. Conteo de organismos
        foreach (var orgName in leftGui.OrganismNames)
        {
            int count = 0;
            if (leftGui.entityCounts != null && leftGui.entityCounts.TryGetValue(orgName, out count))
            {
                // valor obtenido
            }
            csvLine.Append(CsvSeparator).Append(count.ToString(CultureInfo.InvariantCulture));
        }

        csvLine.AppendLine();

        try
        {
            File.AppendAllText(logFilePath, csvLine.ToString());
        }
        catch (Exception ex)
        {
            Debug.LogError($"SimulationLogger: Error al escribir en el CSV: {ex.Message}");
        }
    }

    /// <summary>
    /// Escribe el encabezado del CSV con los nombres de las columnas.
    /// </summary>
    private void WriteCSVHeader()
    {
        List<string> headers = new List<string>
        {
            "Timestamp",
            "FPS",
            "RealTime",
            "SimulatedTime",
            "DeltaTime",
            "FrameCount",
            "Pausado"
        };

        if (leftGui != null && leftGui.OrganismNames != null)
            headers.AddRange(leftGui.OrganismNames);

        string headerLine = string.Join(CsvSeparator, headers) + Environment.NewLine;
        try
        {
            File.AppendAllText(logFilePath, headerLine);
        }
        catch (Exception ex)
        {
            Debug.LogError($"SimulationLogger: Error al escribir el encabezado en el CSV: {ex.Message}");
        }
    }
}
