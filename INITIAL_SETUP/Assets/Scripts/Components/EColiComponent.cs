using Unity.Entities;
using Unity.Mathematics;

public struct EColiComponent : IComponentData
{
    // Crecimiento
    public float GrowthRate;       // Velocidad de crecimiento
    public float MaxScale;         // Tamaño máximo (por ejemplo, 1.0)
    public float GrowthTime;       // Tiempo acumulado de crecimiento
    public float GrowthDuration;   // Cuánto dura el crecimiento (e.g. 1200 frames)
    
    // División
    public float TimeSinceLastDivision;
    public float DivisionInterval;
    public bool HasGeneratedChild;
    
    // Jerarquía
    public Entity Parent;
    public bool IsInitialCell;

    // Umbral de separación (70% = 0.7f, etc.)
    public float SeparationThreshold;
}
