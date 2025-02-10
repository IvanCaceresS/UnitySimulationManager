using UnityEngine;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Globalization;

public class SimulationLogger : MonoBehaviour
{
    private const float LogInterval = 5f;         // Intervalo de 30 segundos para registrar datos
    private const string CsvSeparator = ";";         // Separador de campos para evitar confusiones
    private float lastLogTime = 0f;
    private string logFilePath;
    private bool isLogging = false;                  // Se activa con el botón
    private Left_GUI leftGui;
    
    void Start()
    {
        leftGui = FindFirstObjectByType<Left_GUI>();
        if (leftGui == null)
        {
            Debug.LogError("SimulationLogger: No se encontró Left_GUI en la escena.");
            enabled = false;
            return;
        }
        
        logFilePath = Path.Combine(Application.persistentDataPath, "SimulationStats.csv");
    }
    
    void Update()
    {
        if (isLogging && Time.time - lastLogTime >= LogInterval)
        {
            lastLogTime = Time.time;
            LogAllData();
        }
    }
    
    void OnGUI()
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
    
    /// <summary>
    /// Inicia la captura de datos y escribe el encabezado si es necesario.
    /// </summary>
    private void StartLogging()
    {
        isLogging = true;
        lastLogTime = Time.time;
        
        if (!File.Exists(logFilePath))
            WriteCSVHeader();
        
        Debug.Log("Captación de estadísticas iniciada.");
    }
    
    /// <summary>
    /// Detiene la captura de datos.
    /// </summary>
    private void StopLogging()
    {
        isLogging = false;
        Debug.Log("Captación de estadísticas finalizada. Archivo guardado en: " + logFilePath);
    }
    
    /// <summary>
    /// Registra en una única línea los datos de la simulación y el conteo de organismos.
    /// </summary>
    private void LogAllData()
    {
        if (leftGui == null || !isLogging)
            return;
        
        StringBuilder csvLine = new StringBuilder();
        
        // 1. Timestamp (formateado, ej.: "dd-MM-yyyy HH:mm:ss")
        csvLine.Append(DateTime.Now.ToString("dd-MM-yyyy HH:mm:ss", CultureInfo.InvariantCulture));
        csvLine.Append(CsvSeparator);
        
        // 2. Datos de la simulación (obtenidos desde Left_GUI)
        csvLine.Append(leftGui.cachedFPS.ToString("F2", CultureInfo.InvariantCulture)).Append(CsvSeparator);
        csvLine.Append(leftGui.cachedRealTime.ToString("F2", CultureInfo.InvariantCulture)).Append(CsvSeparator);
        csvLine.Append(leftGui.cachedSimulatedTime.ToString("F2", CultureInfo.InvariantCulture)).Append(CsvSeparator);
        csvLine.Append(GameStateManager.DeltaTime.ToString("F2", CultureInfo.InvariantCulture)).Append(CsvSeparator);
        csvLine.Append(leftGui.cachedFrameCount.ToString(CultureInfo.InvariantCulture)).Append(CsvSeparator);
        csvLine.Append(GameStateManager.IsPaused ? "Sí" : "No");
        
        // 3. Conteo de organismos: se recorren los nombres expuestos por Left_GUI
        foreach (var orgName in leftGui.OrganismNames)
        {
            int count = 0;
            if (leftGui.entityCounts != null && leftGui.entityCounts.ContainsKey(orgName))
                count = leftGui.entityCounts[orgName];
            csvLine.Append(CsvSeparator).Append(count.ToString(CultureInfo.InvariantCulture));
        }
        
        csvLine.AppendLine();
        File.AppendAllText(logFilePath, csvLine.ToString());
    }
    
    /// <summary>
    /// Escribe el encabezado del CSV con las columnas.
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
        
        // Se agregan los nombres de los organismos (incluyendo "Cantidad de organismos")
        if (leftGui != null)
            headers.AddRange(leftGui.OrganismNames);
        
        File.AppendAllText(logFilePath, string.Join(CsvSeparator, headers) + Environment.NewLine);
    }
}
