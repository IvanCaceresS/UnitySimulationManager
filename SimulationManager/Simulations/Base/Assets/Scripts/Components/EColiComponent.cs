using Unity.Entities;
using Unity.Mathematics;

public struct EColiComponent : IComponentData
{
    // Tiempo de referencia para la simulación
    public float TimeReference;    // Por ejemplo, 1200f

    // Crecimiento
    public float MaxScale;         // Tamaño máximo (por ejemplo, 1.0)
    public float GrowthTime;       // Tiempo acumulado de crecimiento
    public float GrowthDuration;   // Duración total del crecimiento (TimeReference * SeparationThreshold)
    
    // División
    public float TimeSinceLastDivision;
    public float DivisionInterval; // Igual a GrowthDuration
    
    public bool HasGeneratedChild;
    
    // Jerarquía
    public Entity Parent;
    public bool IsInitialCell;
    
    // Umbral de separación (por ejemplo, 0.7 equivale al 70% del tamaño máximo)
    public float SeparationThreshold;
    
    // Dirección fija de separación (1 = hacia arriba, -1 = hacia abajo)
    // Se asigna al crear una hija y se mantiene durante su crecimiento.
    public int SeparationSign;
}
