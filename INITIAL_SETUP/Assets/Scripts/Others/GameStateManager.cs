using UnityEngine;
using System;

public static class GameStateManager
{
    public static bool IsSetupComplete { get; private set; } = false;

    public static event Action OnSetupComplete;

    public static void CompleteSetup()
    {
        IsSetupComplete = true;
        OnSetupComplete?.Invoke(); // Notifica a los scripts suscritos
    }
}
