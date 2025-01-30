using UnityEngine;
using System;

public class Left_GUI : MonoBehaviour
{
    private readonly Rect sliderRect = new Rect(30, 30, 300, 30);
    private float cachedRealTime;
    private float cachedSimulatedTime;
    private float cachedFPS;
    private int cachedFrameCount;
    private bool hasStartedSimulation = false; // Solo inicia cuando se presione "Start Simulation"

    void Start()
    {
        GameStateManager.OnSetupComplete += EnableGUI;
        this.enabled = false; // Se desactiva hasta que el setup esté completo
    }

    void OnDestroy()
    {
        GameStateManager.OnSetupComplete -= EnableGUI;
    }

    private void EnableGUI()
    {
        Debug.Log("Left_GUI: Activando interfaz GUI.");
        this.enabled = true;
        ResetCachedValues();
    }

    void Update()
    {
        if (hasStartedSimulation && !GameStateManager.IsPaused)
        {
            CacheValues();
        }
    }

    /// <summary>
    /// Método llamado desde Right_GUI cuando el usuario presiona "Start Simulation".
    /// </summary>
    public void StartSimulation()
    {
        hasStartedSimulation = true;
        ResetCachedValues(); // Reinicia los valores al comenzar la simulación
    }

    /// <summary>
    /// Método llamado desde Right_GUI cuando el usuario presiona "Reiniciar".
    /// </summary>
    public void ResetSimulation()
    {
        hasStartedSimulation = false;
        ResetCachedValues(); // Restablece los valores
    }

    private void ResetCachedValues()
    {
        cachedRealTime = 0f;
        cachedSimulatedTime = 0f;
        cachedFPS = 0f;
        cachedFrameCount = 0;
    }

    private void CacheValues()
    {
        cachedRealTime = Time.time;
        cachedSimulatedTime = Time.time * GameStateManager.DeltaTime * 1f / Time.deltaTime;
        cachedFPS = 1f / Time.deltaTime;
        cachedFrameCount += 1;
    }

    void OnGUI()
    {
        if (!GameStateManager.IsSetupComplete) return;

        DisplaySimulationStats();
    }

    private void DisplaySimulationStats()
    {
        GUIStyle labelStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 14,
            normal = { textColor = Color.white }
        };

        string pauseStatus = GameStateManager.IsPaused ? "Sí" : "No";

        GUI.Label(new Rect(sliderRect.x, sliderRect.y + 30, 300, 25), $"FPS: {cachedFPS:F1}.", labelStyle);
        GUI.Label(new Rect(sliderRect.x, sliderRect.y + 60, 300, 25), $"Tiempo Real: {FormatTime(cachedRealTime)}.", labelStyle);
        GUI.Label(new Rect(sliderRect.x, sliderRect.y + 90, 300, 25), $"Tiempo Simulado: {FormatTime(cachedSimulatedTime)}.", labelStyle);
        GUI.Label(new Rect(sliderRect.x, sliderRect.y + 120, 300, 25), $"Tiempo Simulado es: {GameStateManager.DeltaTime * cachedFPS:F1} veces el tiempo Real.", labelStyle);
        GUI.Label(new Rect(sliderRect.x, sliderRect.y + 150, 300, 25), $"Escala de Tiempo: {GameStateManager.DeltaTime:F2}.", labelStyle);
        GUI.Label(new Rect(sliderRect.x, sliderRect.y + 180, 300, 25), $"Frames Transcurridos: {cachedFrameCount}.", labelStyle);
        GUI.Label(new Rect(sliderRect.x, sliderRect.y + 210, 300, 25), $"Pausado: {pauseStatus}.", labelStyle);
    }

    private string FormatTime(float timeInSeconds)
    {
        int days = Mathf.FloorToInt(timeInSeconds / 86400f);
        int hours = Mathf.FloorToInt((timeInSeconds % 86400f) / 3600f);
        int minutes = Mathf.FloorToInt((timeInSeconds % 3600f) / 60f);
        int seconds = Mathf.FloorToInt(timeInSeconds % 60f);
        return $"{days:D2}:{hours:D2}:{minutes:D2}:{seconds:D2}";
    }
}
