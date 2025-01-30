using UnityEngine;
using UnityEngine.SceneManagement;

public class Right_GUI : MonoBehaviour
{
    public bool isPaused = true;
    private bool showDeltaTimeWindow = true;
    private bool showControls = false;
    private string deltaTimeInput = "1.00";
    private int[] fpsLevels = { 60, 144, 200, 500, 1000 };
    private int currentFPSIndex = 0;
    private string initialSceneName;

    void Start()
    {   
        GameStateManager.OnSetupComplete += EnableGUI;
        initialSceneName = SceneManager.GetActiveScene().name;
        QualitySettings.vSyncCount = 0;
        Application.targetFrameRate = fpsLevels[currentFPSIndex];
        deltaTimeInput = GameStateManager.DeltaTime.ToString("F2");
    }

    void OnDestroy()
    {
        GameStateManager.OnSetupComplete -= EnableGUI;
    }

    private void EnableGUI()
    {
        Debug.Log("Right_GUI: Activando interfaz GUI.");
        this.enabled = true;
    }

    void OnGUI()
    {
        if (!GameStateManager.IsSetupComplete) return;

        if (showDeltaTimeWindow)
        {
            ShowDeltaTimeWindow();
        }
        else
        {
            if (GUI.Button(new Rect(Screen.width - 120, 360, 100, 30), "Reiniciar"))
            {
                RestartSimulation();
            }

            if (GUI.Button(new Rect(Screen.width - 120, 400, 100, 30), "Salir"))
            {
                ExitSimulation();
            }

            string pauseButtonText = isPaused ? "Reanudar" : "Pausar";
            if (GUI.Button(new Rect(Screen.width - 120, 280, 100, 30), pauseButtonText))
            {
                TogglePause();
            }

            if (GUI.Button(new Rect(Screen.width - 120, 320, 100, 30), $"FPS: {fpsLevels[currentFPSIndex]}"))
            {
                ToggleFPSLimit();
            }
        }

        if (showControls)
        {
            DisplayControlsGUI();
        }

        if (GUI.Button(new Rect(Screen.width - 120, 200, 100, 30), "Controles"))
        {
            showControls = !showControls;
        }
    }

    private void ShowDeltaTimeWindow()
    {
        GUI.Box(new Rect(Screen.width / 2 - 150, Screen.height / 2 - 120, 300, 240), "Configuración de Simulación");
        GUI.Label(new Rect(Screen.width / 2 - 140, Screen.height / 2 - 80, 280, 30), "Ingrese deltaTime (0.01 - 99.99):");

        // Verifica si el usuario dejó el campo vacío
        if (string.IsNullOrWhiteSpace(deltaTimeInput))
        {
            deltaTimeInput = "1.00"; // Valor por defecto si el usuario no ha ingresado nada
        }

        deltaTimeInput = GUI.TextField(new Rect(Screen.width / 2 - 140, Screen.height / 2 - 50, 280, 25), deltaTimeInput);

        // Se intenta parsear, pero si falla se usa el último valor válido
        float deltaTime;
        if (!float.TryParse(deltaTimeInput, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out deltaTime))
        {
            deltaTime = 1.00f; // Mantiene el valor por defecto en caso de error
        }

        // Clamping para que siempre esté en el rango permitido
        deltaTime = Mathf.Clamp(deltaTime, 0.01f, 99.99f);

        // Siempre se muestra la barra de desplazamiento, incluso si el usuario no ingresa nada
        deltaTime = GUI.HorizontalSlider(new Rect(Screen.width / 2 - 140, Screen.height / 2 - 10, 280, 20), deltaTime, 0.01f, 99.99f);
        deltaTimeInput = deltaTime.ToString("F2", System.Globalization.CultureInfo.InvariantCulture);

        if (GUI.Button(new Rect(Screen.width / 2 - 140, Screen.height / 2 + 50, 280, 30), "Start Simulation"))
        {
            GameStateManager.SetDeltaTime(deltaTime);
            showDeltaTimeWindow = false;
            TogglePause();

            // Llamamos a Left_GUI para iniciar la simulación
            Left_GUI leftGUI = FindFirstObjectByType<Left_GUI>();
            if (leftGUI != null)
            {
                leftGUI.StartSimulation();
            }
        }
    }

    private void RestartSimulation()
    {
        // Si NO quieres recargar la escena y solo reiniciar las entidades:
        GameStateManager.ResetGameState();

        // Buscamos el script que maneja la creación de entidades
        CreatePrefabsOnClick spawner = FindFirstObjectByType<CreatePrefabsOnClick>();
        if (spawner != null)
        {
            // Llamamos a nuestro método que borra las entidades y reinicia la lógica
            spawner.ResetSimulation();
        }
        else
        {
            Debug.LogWarning("Right_GUI: No se encontró CreatePrefabsOnClick en la escena.");
        }
        // Llamamos a Left_GUI para resetear valores
        Left_GUI leftGUI = FindFirstObjectByType<Left_GUI>();
        if (leftGUI != null)
        {
            leftGUI.ResetSimulation();
        }
        
        // 🔹 REACTIVAMOS LA VENTANA PARA DEFINIR EL DELTATIME 🔹
        showDeltaTimeWindow = true;
        // Si prefieres seguir recargando la escena en vez de hacer el reseteo "en caliente", 
        // comenta lo anterior y descomenta la siguiente línea:
        // SceneManager.LoadScene(initialSceneName);
    }

    private void ExitSimulation()
    {
        #if UNITY_EDITOR
        UnityEditor.EditorApplication.isPlaying = false;
        #else
        Application.Quit();
        #endif
    }

    private void DisplayControlsGUI()
    {
        GUI.Box(new Rect(Screen.width - 250, 10, 240, 200), "Controles de Cámara");
        GUI.Label(new Rect(Screen.width - 240, 40, 220, 20), "WASD: Moverse");
        GUI.Label(new Rect(Screen.width - 240, 60, 220, 20), "Espacio: Elevarse");
        GUI.Label(new Rect(Screen.width - 240, 80, 220, 20), "Ctrl: Descender");
        GUI.Label(new Rect(Screen.width - 240, 100, 220, 20), "Click Derecho: Rotar");
        GUI.Label(new Rect(Screen.width - 240, 120, 220, 20), "Rueda del Mouse: Zoom");
        GUI.Label(new Rect(Screen.width - 240, 140, 220, 20), "C: Alternar Vista Cenital");
        GUI.Label(new Rect(Screen.width - 240, 160, 220, 20), "Botón FPS: Alternar Límite");
    }

    private void TogglePause()
    {
        isPaused = !isPaused;
        Time.timeScale = isPaused ? 0 : 1;
        GameStateManager.SetPauseState(isPaused);
    }


    private void ToggleFPSLimit()
    {
        currentFPSIndex = (currentFPSIndex + 1) % fpsLevels.Length;
        QualitySettings.vSyncCount = 0;
        Application.targetFrameRate = fpsLevels[currentFPSIndex];
    }
}
