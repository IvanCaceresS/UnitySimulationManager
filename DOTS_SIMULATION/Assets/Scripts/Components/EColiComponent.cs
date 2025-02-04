using Unity.Entities;
using Unity.Mathematics;

public struct EColiComponent : IComponentData
{
    // Crecimiento
    public float MaxScale;         // Escala máxima (por ejemplo, 1.0)
    public float GrowthTime;       // Tiempo acumulado de crecimiento
    public float GrowthDuration;   // Duración total del crecimiento (por ejemplo, 1200 frames)

    // División
    public float TimeSinceLastDivision;
    public float DivisionInterval;
    public bool HasGeneratedChild;

    // Jerarquía
    public Entity Parent;
    public bool IsInitialCell;

    // Umbral de separación (por ejemplo, 0.7 equivale al 70% del tamaño máximo)
    public float SeparationThreshold;
    
    // Nueva propiedad para fijar la dirección de separación:
    // 1 = hacia arriba, -1 = hacia abajo.
    // Por defecto 0 (no asignado); se asigna al crear una hija.
    public int SeparationSign;
}

