using UnityEngine;
using UnityEngine.SceneManagement;
using System.Collections; // Necesario para las corrutinas

public class Right_GUI : MonoBehaviour
{
    // Parámetros de la simulación y de la GUI
    public bool isPaused = true;
    private bool showDeltaTimeWindow = true;
    private bool showControls = false;
    private string deltaTimeInput = "1.00";
    private int[] fpsLevels = { 60, 144, 500, 1000, -1 };
    private int currentFPSIndex = 0;
    private string initialSceneName;
    private static float LowDeltaTimeLimit = 0.01f;
    private static float HighDeltaTimeLimit = 40.00f;

    // Estilos de GUI (se inicializan en OnGUI)
    private GUIStyle buttonStyle;
    private GUIStyle labelStyle;
    private GUIStyle windowStyle;

    // Bandera para controlar el avance de frame
    private bool isAdvancingFrame = false;

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

        // Inicializa estilos de forma lazy en OnGUI
        if (buttonStyle == null)
        {
            buttonStyle = new GUIStyle(GUI.skin.button)
            {
                fontSize = 12,
                normal = { textColor = Color.white }
            };
        }
        if (labelStyle == null)
        {
            labelStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = 12,
                normal = { textColor = Color.white }
            };
        }
        if (windowStyle == null)
        {
            windowStyle = new GUIStyle(GUI.skin.box)
            {
                fontSize = 14,
                normal = { textColor = Color.white }
            };
        }

        if (showDeltaTimeWindow)
        {
            ShowDeltaTimeWindow();
        }
        else
        {
            int buttonWidth = 80;
            int buttonHeight = 30;
            int margin = 10;
            int startX = Screen.width - buttonWidth - margin;
            int startY = margin;
            
            // Usamos buttonIndex para ir apilando los botones verticalmente
            int buttonIndex = 0;

            // 1) Botón de FPS
            if (GUI.Button(new Rect(startX, startY + buttonIndex * (buttonHeight + margin),
                                    buttonWidth, buttonHeight), 
                        $"FPS: {fpsLevels[currentFPSIndex]}", buttonStyle))
            {
                ToggleFPSLimit();
            }
            buttonIndex++;

            // 2) Botón Reanudar / Pausar
            if (GUI.Button(new Rect(startX, startY + buttonIndex * (buttonHeight + margin),
                                    buttonWidth, buttonHeight), 
                        isPaused ? "Reanudar" : "Pausar", buttonStyle))
            {
                TogglePause();
            }
            buttonIndex++;

            // 3) Botón Reiniciar
            if (GUI.Button(new Rect(startX, startY + buttonIndex * (buttonHeight + margin),
                                    buttonWidth, buttonHeight), 
                        "Reiniciar", buttonStyle))
            {
                RestartSimulation();
            }
            buttonIndex++;

            // 4) Botón Salir
            if (GUI.Button(new Rect(startX, startY + buttonIndex * (buttonHeight + margin),
                                    buttonWidth, buttonHeight), 
                        "Salir", buttonStyle))
            {
                ExitSimulation();
            }
            buttonIndex++;

            // 5) Botón “+1 Frame” (solo si está en pausa)
            if (isPaused)
            {
                if (GUI.Button(new Rect(startX, startY + buttonIndex * (buttonHeight + margin),
                                        buttonWidth, buttonHeight),
                            "+1 Frame", buttonStyle))
                {
                    AdvanceOneFrame();
                }
                buttonIndex++;
            }
        }

        // Botón para mostrar/ocultar controles de cámara en la esquina inferior derecha
        if (GUI.Button(new Rect(Screen.width - 120, Screen.height - 40, 100, 30), "Controles", buttonStyle))
        {
            showControls = !showControls;
        }

        if (showControls)
        {
            DisplayControlsGUI();
        }
    }


    private void ShowDeltaTimeWindow()
    {
        int windowWidth = 300;
        int windowHeight = 120;
        Rect windowRect = new Rect((Screen.width - windowWidth) / 2, (Screen.height - windowHeight) / 2, windowWidth, windowHeight);

        GUI.Window(0, windowRect, DeltaTimeWindow, "Configuración de Simulación", windowStyle);
    }

    private void DeltaTimeWindow(int windowID)
    {
        GUIStyle centeredLabelStyle = new GUIStyle(labelStyle)
        {
            alignment = TextAnchor.MiddleCenter
        };

        GUILayout.BeginVertical();
        GUILayout.FlexibleSpace();
        
        GUILayout.BeginHorizontal();
        GUILayout.FlexibleSpace();
        GUILayout.Label($"Ingrese deltaTime ({LowDeltaTimeLimit} - {HighDeltaTimeLimit}):", centeredLabelStyle, GUILayout.Width(280));
        GUILayout.FlexibleSpace();
        GUILayout.EndHorizontal();

        GUILayout.BeginHorizontal();
        GUILayout.FlexibleSpace();
        deltaTimeInput = GUILayout.TextField(deltaTimeInput, GUILayout.Width(50));
        GUILayout.FlexibleSpace();
        GUILayout.EndHorizontal();

        GUILayout.BeginHorizontal();
        GUILayout.FlexibleSpace();
        float parsedDeltaTime;
        if (!float.TryParse(deltaTimeInput, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out parsedDeltaTime))
            parsedDeltaTime = 1.00f;
        parsedDeltaTime = Mathf.Clamp(parsedDeltaTime, LowDeltaTimeLimit, HighDeltaTimeLimit);
        parsedDeltaTime = GUILayout.HorizontalSlider(parsedDeltaTime, LowDeltaTimeLimit, HighDeltaTimeLimit, GUILayout.Width(280));
        deltaTimeInput = parsedDeltaTime.ToString("F2", System.Globalization.CultureInfo.InvariantCulture);
        GUILayout.FlexibleSpace();
        GUILayout.EndHorizontal();

        GUILayout.BeginHorizontal();
        GUILayout.FlexibleSpace();
        if (GUILayout.Button("Start Simulation", GUILayout.Width(280)))
        {
            GameStateManager.SetDeltaTime(parsedDeltaTime);
            showDeltaTimeWindow = false;
            isPaused = false;
            Time.timeScale = 1;
            GameStateManager.SetPauseState(isPaused);

            Left_GUI leftGUI = FindFirstObjectByType<Left_GUI>();
            if (leftGUI != null)
            {
                leftGUI.StartSimulation();
            }
        }
        GUILayout.FlexibleSpace();
        GUILayout.EndHorizontal();

        GUILayout.FlexibleSpace();
        GUILayout.EndVertical();
    }

    private void DisplayControlsGUI()
    {
        Rect rect = new Rect(Screen.width - 200, Screen.height - 240, 180, 190);
        GUI.Box(rect, "Controles de Cámara", windowStyle);

        GUILayout.BeginArea(new Rect(Screen.width - 180, Screen.height - 220, 170, 180));
        GUILayout.Label("WASD: Moverse", labelStyle);
        GUILayout.Label("Espacio: Elevarse", labelStyle);
        GUILayout.Label("Ctrl: Descender", labelStyle);
        GUILayout.Label("Click Derecho: Rotar", labelStyle);
        GUILayout.Label("Rueda del Mouse: Zoom", labelStyle);
        GUILayout.Label("C: Alternar Vista Cenital", labelStyle);
        GUILayout.Label("Botón FPS: Alternar Límite", labelStyle);
        GUILayout.EndArea();
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

    private void RestartSimulation()
    {
        isPaused = false;
        Time.timeScale = 1;
        GameStateManager.SetPauseState(isPaused);
        GameStateManager.ResetGameState();

        CreatePrefabsOnClick spawner = FindFirstObjectByType<CreatePrefabsOnClick>();
        if (spawner != null)
            spawner.ResetSimulation();
        else
            Debug.LogWarning("Right_GUI: No se encontró CreatePrefabsOnClick en la escena.");

        Left_GUI leftGUI = FindFirstObjectByType<Left_GUI>();
        if (leftGUI != null)
            leftGUI.ResetSimulation();

        showDeltaTimeWindow = true;
    }

    private void ExitSimulation()
    {
#if UNITY_EDITOR
        UnityEditor.EditorApplication.isPlaying = false;
#else
        Application.Quit();
#endif
    }

    // Función para avanzar un frame cuando la simulación está pausada
    private void AdvanceOneFrame()
    {
        if (!isAdvancingFrame)
        {
            StartCoroutine(AdvanceOneFrameCoroutine());
        }
    }

    private IEnumerator AdvanceOneFrameCoroutine()
    {
        isAdvancingFrame = true;

        // Guardar el estado anterior de pausa
        bool prevIsPaused = isPaused;

        // Quitar la pausa lógicamente para que la simulación no se salte el frame
        isPaused = false;
        GameStateManager.SetPauseState(false);

        // Quitar la pausa real (timeScale)
        Time.timeScale = 1;

        // Esperar un frame de física si tu lógica está en FixedUpdate,
        // o bien un frame normal con "yield return null" si está en Update.
        yield return new WaitForFixedUpdate();
        // yield return null;  // <- usar si tu Update es donde corre la lógica

        // Volver a pausar todo
        Time.timeScale = 0;
        isPaused = prevIsPaused;
        GameStateManager.SetPauseState(true);

        isAdvancingFrame = false;
    }

}
