using UnityEngine;
using Unity.Entities;
using ECS;

public class DebugOverlay : MonoBehaviour
{
    private float deltaTime = 0.0f;
    private int eColiCount = 0;
    private int frameCount = 0; // Contador de frames transcurridos

    void Update()
    {
        // Calcula los FPS
        deltaTime += (Time.unscaledDeltaTime - deltaTime) * 0.1f;

        // Incrementa el contador de frames
        frameCount++;

        // Reinicia y actualiza el contador de entidades con EColiTag
        eColiCount = 0;

        foreach (var world in World.All)
        {
            if (world.Name == "Default World" && world.EntityManager != null)
            {
                // Busca entidades con el componente EColiTag
                EntityQuery eColiQuery = world.EntityManager.CreateEntityQuery(typeof(ECS.EColiTag));
                eColiQuery.CompleteDependency();
                eColiCount += eColiQuery.CalculateEntityCount();
            }
        }
    }

    void OnGUI()
    {
        int width = Screen.width;

        // Define el estilo del texto
        GUIStyle style = new GUIStyle
        {
            alignment = TextAnchor.UpperRight,
            fontSize = 20,
            normal = { textColor = Color.white }
        };

        // Muestra los FPS, la cantidad de entidades E. Coli y el contador de frames
        string text = $"FPS: {1.0f / deltaTime:0.0}\nE. Coli: {eColiCount}\nFrames: {frameCount}";
        GUI.Label(new Rect(width - 200, 10, 200, 100), text, style);
    }
}
