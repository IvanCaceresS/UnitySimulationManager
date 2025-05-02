using UnityEngine;
using System;
using System.Collections.Generic;
using Unity.Entities;
using System.Reflection;
using System.Linq;

public class Left_GUI : MonoBehaviour
{
    // --- Parámetros de la interfaz ajustados ---
    private const int GUIFontSize = 20;
    private const int GUIWidth = 400;
    private const int GUIHeight = 24;
    // --- Fin de ajustes ---

    private const int GUIXPosition = 10;
    private const int GUIYPosition = 0;

    // Variables de tiempo y FPS
    private float simulationStartTime = 0f;
    private float accumulatedRealTime = 0f;
    public float cachedRealTime = 0f;
    public float cachedSimulatedTime = 0f;
    public float cachedFPS = 0f;
    public int cachedFrameCount = 0;
    private bool hasStartedSimulation = false;

    // Intervalo para actualizar el conteo de entidades (YA NO SE USA)
    // private const float entityCountUpdateInterval = 2.0f; // Eliminado
    // private float lastEntityCountUpdateTime = 0f; // Eliminado

    // Conteo de entidades y tipos
    public Dictionary<string, int> entityCounts = new Dictionary<string, int>();
    public List<Type> validComponentTypes = new List<Type>();
    private Dictionary<Type, EntityQuery> entityQueries = new Dictionary<Type, EntityQuery>();

    // GUIStyle
    private GUIStyle labelStyle;

    public IEnumerable<string> OrganismNames
    {
        get
        {
            List<string> names = validComponentTypes
                .Select(t => t.Name.Replace("Component", ""))
                .ToList();
            names.Sort();
            names.Add("Organism count");
            return names;
        }
    }

    void Start()
    {
        GameStateManager.OnSetupComplete += EnableGUI;
        this.enabled = false;
        CacheValidComponentTypes();
        ResetCachedValues();
    }

    void OnDestroy()
    {
        GameStateManager.OnSetupComplete -= EnableGUI;
        // Dispose queries on destroy
        foreach(var query in entityQueries.Values)
        {
            query.Dispose();
        }
        entityQueries.Clear();
    }

    private void EnableGUI()
    {
        Debug.Log("Left_GUI: Activating GUI interface.");
        this.enabled = true;
        ResetCachedValues();
    }

    void Update()
    {
        // --- Cálculo de FPS (sin cambios) ---
        if (Time.unscaledDeltaTime > Mathf.Epsilon)
        {
            cachedFPS = 1f / Time.unscaledDeltaTime;
        }
        else
        {
            cachedFPS = 0f;
        }

        if (hasStartedSimulation)
        {
            if (!GameStateManager.IsPaused)
            {
                // --- Actualización de tiempos (sin cambios) ---
                accumulatedRealTime += Time.deltaTime;
                cachedRealTime = accumulatedRealTime;
                cachedFrameCount++;
                cachedSimulatedTime = cachedFrameCount * GameStateManager.DeltaTime;

                // --- ACTUALIZACIÓN DEL CONTEO DE ENTIDADES POR FRAME ---
                // Se llama a UpdateEntityCounts() en cada frame si no está pausado.
                UpdateEntityCounts();
                // --------------------------------------------------------

                // --- Bloque del intervalo de tiempo eliminado ---
                // if (Time.realtimeSinceStartup - lastEntityCountUpdateTime >= entityCountUpdateInterval)
                // {
                //     // UpdateEntityCounts(); // Movido fuera del if
                //     // lastEntityCountUpdateTime = Time.realtimeSinceStartup; // Eliminado
                // }
                // --------------------------------------------------
            }
        }
        else
        {
            cachedRealTime = 0f;
            cachedSimulatedTime = 0f;
            cachedFrameCount = 0;
        }
    }

    public void StartSimulation()
    {
        hasStartedSimulation = true;
        simulationStartTime = Time.realtimeSinceStartup;
        accumulatedRealTime = 0f;
        cachedFrameCount = 0;
        cachedSimulatedTime = 0f;
        entityCounts.Clear();
        // lastEntityCountUpdateTime = Time.realtimeSinceStartup; // Eliminado
        UpdateEntityCounts(); // Llama una vez al inicio
    }

    public void ResetSimulation()
    {
        hasStartedSimulation = false;
        ResetCachedValues();
    }

    private void ResetCachedValues()
    {
        simulationStartTime = 0f;
        accumulatedRealTime = 0f;
        cachedRealTime = 0f;
        cachedSimulatedTime = 0f;
        cachedFPS = 0f;
        cachedFrameCount = 0;
        entityCounts.Clear();
        // lastEntityCountUpdateTime = Time.realtimeSinceStartup; // Eliminado
    }

    // --- UpdateEntityCounts() sin cambios en su lógica interna ---
    private void UpdateEntityCounts()
    {
        // Check World validity first
        if (World.DefaultGameObjectInjectionWorld == null || !World.DefaultGameObjectInjectionWorld.IsCreated)
        {
             // Debug.LogWarning("Left_GUI: World not ready for entity count update."); // Reduce log spam
             entityCounts.Clear();
             entityCounts["Organism count"] = 0;
             return;
        }
        var entityManager = World.DefaultGameObjectInjectionWorld.EntityManager;
        if (entityManager == null) return; // Extra safety check

        var currentCounts = new Dictionary<string, int>();
        int totalEntities = 0;

        foreach (var kvp in entityQueries)
        {
            try
            {
                // Calculate count - this might throw if the query became invalid due to structural changes.
                int count = kvp.Value.CalculateEntityCount();
                string name = kvp.Key.Name.Replace("Component", "");
                currentCounts[name] = count;
                totalEntities += count;
            }
            catch (InvalidOperationException ex)
            {
                 Debug.LogError($"Left_GUI: Error calculating entity count for {kvp.Key.Name}: {ex.Message}");
                 // Optionally mark this query for potential re-creation later if errors persist
            }
             catch (Exception ex) // Catch other potential exceptions
             {
                 Debug.LogError($"Left_GUI: Unexpected error calculating entity count for {kvp.Key.Name}: {ex.Message}\n{ex.StackTrace}");
             }
        }
        currentCounts["Organism count"] = totalEntities;
        entityCounts = currentCounts;
    }

    // --- CacheValidComponentTypes() sin cambios ---
    private void CacheValidComponentTypes()
    {
        if (World.DefaultGameObjectInjectionWorld == null || !World.DefaultGameObjectInjectionWorld.IsCreated)
        {
             Debug.LogWarning("Left_GUI: World not ready for caching component types.");
             return;
        }
        var entityManager = World.DefaultGameObjectInjectionWorld.EntityManager;
        if (entityManager == null) return;

        // Dispose existing queries before clearing
        foreach(var query in entityQueries.Values)
        {
            query.Dispose();
        }
        entityQueries.Clear();
        validComponentTypes.Clear(); // Clear the type list as well

        try
        {
            foreach (Type type in Assembly.GetExecutingAssembly().GetTypes())
            {
                if (type.IsValueType && !type.IsAbstract && !type.IsGenericTypeDefinition && typeof(IComponentData).IsAssignableFrom(type))
                {
                    string typeName = type.Name;
                    if (typeName.EndsWith("Component") && typeName != "PrefabEntityComponent" && typeName != "PlaneComponent")
                    {
                        validComponentTypes.Add(type);
                        var query = entityManager.CreateEntityQuery(ComponentType.ReadOnly(type));
                        entityQueries.Add(type, query);
                    }
                }
            }
        }
        catch (Exception ex)
        {
             Debug.LogError($"Left_GUI: Error during component type caching: {ex.Message}\n{ex.StackTrace}");
        }
         Debug.Log($"Left_GUI: Finished caching component types. Found {validComponentTypes.Count} valid types.");
    }

    // --- OnGUI() sin cambios ---
    void OnGUI()
    {
        if (labelStyle == null)
        {
            labelStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = GUIFontSize,
                normal = { textColor = Color.white },
                alignment = TextAnchor.MiddleLeft
            };
        }

        if (!GameStateManager.IsSetupComplete) return;

        DisplaySimulationStats();
    }

    // --- DisplaySimulationStats() sin cambios ---
    private void DisplaySimulationStats()
{
    int y = GUIYPosition + 5; // Posición inicial Y

    // --- Sección de estadísticas de simulación (sin cambios) ---
    GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), $"FPS: {cachedFPS:F1}", labelStyle); y += GUIHeight;
    GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), $"Real Time: {FormatTime(cachedRealTime)}", labelStyle); y += GUIHeight;
    GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), $"Simulated Time: {FormatTime(cachedSimulatedTime)}", labelStyle); y += GUIHeight;

    float timeMultiplier = GameStateManager.DeltaTime * 60f; // Asumiendo 60 FPS como base para el multiplicador? O debería ser 1/DeltaTime? Revisar lógica si es necesario.
    string multiplierText = hasStartedSimulation ? $"{timeMultiplier:F2}x" : "N/A";
    // Corrección: El multiplicador de tiempo generalmente se define externamente o como la relación entre tiempo simulado y tiempo real.
    // Si DeltaTime es el paso de tiempo fijo de la simulación, el multiplicador podría ser GameStateManager.TimeMultiplier si existe, o calculado de otra forma.
    // Usaremos el cálculo anterior por ahora, pero tenlo en cuenta.
    GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), $"Time Multiplier: {multiplierText}", labelStyle); y += GUIHeight; // Considerar usar GameStateManager.TimeMultiplier si existe

    GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), $"DeltaTime: {GameStateManager.DeltaTime:F4}", labelStyle); y += GUIHeight;
    GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), $"Elapsed Frames: {cachedFrameCount}", labelStyle); y += GUIHeight;
    GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), $"Paused: {(GameStateManager.IsPaused ? "Yes" : "No")}", labelStyle); y += GUIHeight;

    y += 5; // Espacio
    GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), "--- Entities ---", labelStyle); y += GUIHeight;

    // --- Nueva lógica para ordenar y mostrar entidades ---

    // 1. Intentar obtener la entrada "Organism count"
    KeyValuePair<string, int> organismCountEntry = default;
    bool hasOrganismCount = false;
    if (entityCounts.TryGetValue("Organism count", out int totalCount))
    {
        organismCountEntry = new KeyValuePair<string, int>("Organism count", totalCount);
        hasOrganismCount = true;
    }

    // 2. Crear una lista solo con los organismos específicos (excluyendo "Organism count")
    List<KeyValuePair<string, int>> specificOrganisms = entityCounts
        .Where(pair => pair.Key != "Organism count")
        .ToList();

    // 3. Ordenar la lista de organismos específicos alfabéticamente
    specificOrganisms.Sort((pair1, pair2) => pair1.Key.CompareTo(pair2.Key));

    // 4. Mostrar los organismos específicos ordenados
    foreach (var entry in specificOrganisms)
    {
        GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), $"{entry.Key}: {entry.Value}", labelStyle);
        y += GUIHeight;
    }

    // 5. Mostrar "Organism count" al final, si existe
    if (hasOrganismCount)
    {
        GUI.Label(new Rect(GUIXPosition, y, GUIWidth, GUIHeight), $"{organismCountEntry.Key}: {organismCountEntry.Value}", labelStyle);
        y += GUIHeight; // Asegúrate de incrementar 'y' también aquí
    }
    // --- Fin de la nueva lógica ---
}

    // --- FormatTime() sin cambios ---
    private string FormatTime(float timeInSeconds)
    {
        TimeSpan t = TimeSpan.FromSeconds(timeInSeconds);
        string formatted = "";
        if (t.Days > 0) formatted += $"{t.Days}d ";
        if (t.Hours > 0 || !string.IsNullOrEmpty(formatted)) formatted += $"{t.Hours:D2}h ";
        if (t.Minutes > 0 || !string.IsNullOrEmpty(formatted)) formatted += $"{t.Minutes:D2}m ";
        formatted += $"{t.Seconds:D2}s";
        if (string.IsNullOrEmpty(formatted)) formatted = "0s";
        return formatted;
    }
}