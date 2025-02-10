using UnityEngine;
using System;
using System.Collections.Generic;
using Unity.Entities;
using System.Reflection;
using System.Linq;

public class Left_GUI : MonoBehaviour
{
    // Parámetros de la interfaz
    private const int GUIFontSize = 10;
    private const int GUIWidth = 300;
    private const int GUIHeight = 30;
    private const int GUIXPosition = 10;
    private const int GUIYPosition = 0;
    private readonly Rect sliderRect = new Rect(GUIXPosition, GUIYPosition, GUIWidth, GUIHeight);

    // Variables de tiempo y FPS
    private float simulationStartTime;
    public float cachedRealTime;
    public float cachedSimulatedTime;
    public float cachedFPS;
    public int cachedFrameCount;
    private bool hasStartedSimulation = false; // Se activa al presionar "Start Simulation"

    // Intervalo para actualizar el conteo de entidades (en segundos)
    private const float entityCountUpdateInterval = 2.0f;
    private float lastEntityCountUpdateTime;

    // Conteo de entidades y tipos (cache de reflection y queries)
    public Dictionary<string, int> entityCounts = new Dictionary<string, int>();
    private List<Type> validComponentTypes = new List<Type>();
    private Dictionary<Type, EntityQuery> entityQueries = new Dictionary<Type, EntityQuery>();

    // GUIStyle se inicializará de forma lazy en OnGUI
    private GUIStyle labelStyle;

    /// <summary>
    /// Propiedad que devuelve los nombres de los organismos a partir de los tipos válidos.
    /// Se remueve la parte "Component", se ordenan alfabéticamente y se añade "Cantidad de organismos".
    /// </summary>
    public IEnumerable<string> OrganismNames
    {
        get
        {
            List<string> names = validComponentTypes
                .Select(t => t.Name.Replace("Component", ""))
                .ToList();
            names.Sort();
            names.Add("Cantidad de organismos");
            return names;
        }
    }

    void Start()
    {
        GameStateManager.OnSetupComplete += EnableGUI;
        this.enabled = false; // Se activa al completar el setup
        CacheValidComponentTypes();
    }

    void OnDestroy()
    {
        GameStateManager.OnSetupComplete -= EnableGUI;
        // Opcional: si deseas liberar los queries, puedes recorrer entityQueries y disponerlos.
        // foreach (var query in entityQueries.Values)
        // {
        //     query.Dispose();
        // }
    }

    private void EnableGUI()
    {
        Debug.Log("Left_GUI: Activando interfaz GUI.");
        this.enabled = true;
        ResetCachedValues();
    }

    void Update()
    {
        // Actualizar siempre el FPS y el tiempo real usando Time.realtimeSinceStartup
        cachedFPS = 1f / Time.deltaTime;
        cachedRealTime = Time.realtimeSinceStartup - simulationStartTime;

        // Si la simulación está activa y no está pausada, actualizamos el tiempo simulado y el conteo de frames
        if (hasStartedSimulation && !GameStateManager.IsPaused)
        {
            cachedFrameCount++;
            cachedSimulatedTime = cachedFrameCount * GameStateManager.DeltaTime;

            // Actualizar el conteo de entidades solo cada cierto intervalo para optimizar el rendimiento
            if (Time.realtimeSinceStartup - lastEntityCountUpdateTime >= entityCountUpdateInterval)
            {
                UpdateEntityCounts();
                lastEntityCountUpdateTime = Time.realtimeSinceStartup;
            }
        }
    }

    public void StartSimulation()
    {
        hasStartedSimulation = true;
        ResetCachedValues();
    }

    public void ResetSimulation()
    {
        hasStartedSimulation = false;
        ResetCachedValues();
    }

    /// <summary>
    /// Reinicia los contadores de tiempo, frames y FPS.
    /// </summary>
    private void ResetCachedValues()
    {
        simulationStartTime = Time.realtimeSinceStartup;
        cachedRealTime = 0f;
        cachedSimulatedTime = 0f;
        cachedFPS = 0f;
        cachedFrameCount = 0;
        entityCounts.Clear();
        lastEntityCountUpdateTime = Time.realtimeSinceStartup;
    }

    /// <summary>
    /// Actualiza el conteo de entidades usando los queries cacheados.
    /// </summary>
    private void UpdateEntityCounts()
    {
        entityCounts.Clear();
        int totalEntities = 0;
        var entityManager = World.DefaultGameObjectInjectionWorld.EntityManager;

        foreach (var kvp in entityQueries)
        {
            int count = kvp.Value.CalculateEntityCount();
            string name = kvp.Key.Name.Replace("Component", "");
            entityCounts[name] = count;
            totalEntities += count;
        }
        entityCounts["Cantidad de organismos"] = totalEntities;
    }

    /// <summary>
    /// Cachea la lista de tipos válidos que implementan IComponentData (filtrados por nombre)
    /// y crea los EntityQuery correspondientes.
    /// </summary>
    private void CacheValidComponentTypes()
    {
        validComponentTypes.Clear();
        entityQueries.Clear();

        foreach (Type type in Assembly.GetExecutingAssembly().GetTypes())
        {
            if (type.IsValueType && typeof(IComponentData).IsAssignableFrom(type))
            {
                string typeName = type.Name;
                if (typeName.EndsWith("Component") && typeName != "PrefabEntityComponent" && typeName != "PlaneComponent")
                {
                    validComponentTypes.Add(type);
                    var query = World.DefaultGameObjectInjectionWorld.EntityManager.CreateEntityQuery(ComponentType.ReadOnly(type));
                    entityQueries.Add(type, query);
                }
            }
        }
    }

    void OnGUI()
    {
        // Inicializa labelStyle de forma lazy.
        if (labelStyle == null)
        {
            labelStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = GUIFontSize,
                normal = { textColor = Color.black }
            };
        }

        if (!GameStateManager.IsSetupComplete) return;

        DisplaySimulationStats();
    }

    private void DisplaySimulationStats()
    {
        int y = GUIYPosition + GUIFontSize;
        GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), $"FPS: {cachedFPS:F1}.", labelStyle);
        y += GUIFontSize;
        GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), $"Tiempo Real: {FormatTime(cachedRealTime)}.", labelStyle);
        y += GUIFontSize;
        GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), $"Tiempo Simulado: {FormatTime(cachedSimulatedTime)}.", labelStyle);
        y += GUIFontSize;
        GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), $"Multiplicador de tiempo: {(GameStateManager.DeltaTime * cachedFPS):F0} x Tiempo Real.", labelStyle);
        y += GUIFontSize;
        GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), $"DeltaTime: {GameStateManager.DeltaTime:F2}.", labelStyle);
        y += GUIFontSize;
        GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), $"Frames Transcurridos: {cachedFrameCount}.", labelStyle);
        y += GUIFontSize;
        GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), $"Pausado: {(GameStateManager.IsPaused ? "Sí" : "No")}.", labelStyle);
        y += GUIFontSize;

        foreach (var entry in entityCounts)
        {
            if (entry.Value > 0)
            {
                GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), $"{entry.Key}: {entry.Value}.", labelStyle);
                y += GUIFontSize;
            }
        }
    }

    private string FormatTime(float timeInSeconds)
    {
        int days = Mathf.FloorToInt(timeInSeconds / 86400f);
        int hours = Mathf.FloorToInt((timeInSeconds % 86400f) / 3600f);
        int minutes = Mathf.FloorToInt((timeInSeconds % 3600f) / 60f);
        int seconds = Mathf.FloorToInt(timeInSeconds % 60f);
        return $"{days:D2} días: {hours:D2} horas: {minutes:D2} minutos: {seconds:D2} segundos";
    }
}
