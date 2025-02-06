using Unity.Entities;
using Unity.Mathematics;

/// <summary>
/// Componente ECS para SCerevisiae,
/// control de tiempo, crecimiento, duplicación, anclaje.
/// </summary>
public struct SCerevisiaeComponent : IComponentData
{
    public float TimeReference;      // e.g. 5400f = 90 min
    // Crecimiento
    public float MaxScale;
    public float GrowthTime;
    public float GrowthDuration;

    // División
    public float TimeSinceLastDivision;
    public float DivisionInterval;
    public bool HasGeneratedChild;

    // Jerarquía
    public Entity Parent;
    public bool IsInitialCell;

    // Anclaje
    public float SeparationThreshold; // p.ej. 0.7
    public int SeparationSign;
}
