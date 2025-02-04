using UnityEngine;
using System;
using System.Collections.Generic;
using Unity.Entities;
using System.Reflection;

public class Left_GUI : MonoBehaviour
{
    private readonly Rect sliderRect = new Rect(30, 30, 300, 30);
    private float simulationStartTime;
    private float cachedRealTime;
    private float cachedSimulatedTime;
    private float cachedFPS;
    private int cachedFrameCount;
    private bool hasStartedSimulation = false; // Solo inicia cuando se presione "Start Simulation"

    private Dictionary<string, int> entityCounts = new Dictionary<string, int>();

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
            UpdateEntityCounts(); // Actualizar conteo de entidades en cada frame
        }
    }

    public void StartSimulation()
    {
        hasStartedSimulation = true;
        ResetCachedValues(); // Reinicia los valores al comenzar la simulación
    }

    public void ResetSimulation()
    {
        hasStartedSimulation = false;
        ResetCachedValues(); // Restablece los valores
    }

    private void ResetCachedValues()
    {
        // Registro la hora real actual como el "nuevo inicio"
        simulationStartTime = Time.time;
        cachedRealTime = 0f;
        cachedSimulatedTime = 0f;
        cachedFPS = 0f;
        cachedFrameCount = 0;
        entityCounts.Clear(); // Reiniciar conteo de entidades
    }

    private void CacheValues()
    {
        // Aumenta el conteo de frames
        cachedFrameCount++;

        // Tiempo real transcurrido desde que se reseteó/inició
        cachedRealTime = Time.time - simulationStartTime;

        // Calculamos FPS en tiempo real
        cachedFPS = 1f / Time.deltaTime;

        // Tiempo simulado deseado:
        // "cada_frame_pasado * 1segundo * GameStateManager.DeltaTime"
        cachedSimulatedTime = cachedFrameCount * (1f * GameStateManager.DeltaTime);
    }


    private void UpdateEntityCounts()
    {
        entityCounts.Clear();
        var entityManager = World.DefaultGameObjectInjectionWorld.EntityManager;
        int totalEntities = 0;

        // Buscar todos los tipos de componentes que terminan en "Component" (excepto PrefabEntity)
        foreach (Type type in Assembly.GetExecutingAssembly().GetTypes())
        {
            if (type.IsValueType && typeof(IComponentData).IsAssignableFrom(type) && type.Name.EndsWith("Component") && type.Name != "PrefabEntityComponent" && type.Name != "PlaneComponent")
            {
                int count = entityManager.CreateEntityQuery(ComponentType.ReadOnly(type)).CalculateEntityCount();
                entityCounts[type.Name.Replace("Component", "")] = count;
                totalEntities += count;
            }
        }

        // Agregar el total al final
        entityCounts["Total"] = totalEntities;
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

        // 🔹 Mostrar la cantidad de cada tipo de entidad (ignorando PrefabEntity)
        int offsetY = 240;
        foreach (var entry in entityCounts)
        {
            GUI.Label(new Rect(sliderRect.x, sliderRect.y + offsetY, 300, 25), $"{entry.Key}: {entry.Value}", labelStyle);
            offsetY += 30;
        }
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
