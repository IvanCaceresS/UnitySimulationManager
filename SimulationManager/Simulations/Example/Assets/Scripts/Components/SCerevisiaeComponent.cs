using Unity.Entities;
using Unity.Mathematics;

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
    
    // NUEVO: Dirección de crecimiento aleatoria (en el espacio local del padre)
    public float3 GrowthDirection;
}
