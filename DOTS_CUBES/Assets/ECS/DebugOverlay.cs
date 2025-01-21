using UnityEngine;
using Unity.Entities;
using ECS;

public class DebugOverlay : MonoBehaviour
{
    private float deltaTime = 0.0f;
    private World defaultWorld;

    void Start()
    {
        // Obtén el mundo predeterminado
        defaultWorld = World.DefaultGameObjectInjectionWorld;
    }

    void Update()
    {
        // Calcula los FPS
        deltaTime += (Time.unscaledDeltaTime - deltaTime) * 0.1f;
    }

    void OnGUI()
    {
        int width = Screen.width;
        int height = Screen.height;

        // Define el estilo del texto
        GUIStyle style = new GUIStyle();

        Rect rect = new Rect(width - 200, 10, 200, 100);
        style.alignment = TextAnchor.UpperRight;
        style.fontSize = 20;
        style.normal.textColor = Color.white;

        // Calcula los FPS
        float fps = 1.0f / deltaTime;

        // Obtén la cantidad de cubos en la escena
        int cubeCount = 0;
        if (defaultWorld != null && defaultWorld.EntityManager != null)
        {
            EntityQuery cubeQuery = defaultWorld.EntityManager.CreateEntityQuery(typeof(CubeComponent));
            cubeCount = cubeQuery.CalculateEntityCount();
        }

        // Muestra los FPS y la cantidad de cubos
        string text = $"FPS: {fps:0.0}\nCubes: {cubeCount}";
        GUI.Label(rect, text, style);
    }
}
