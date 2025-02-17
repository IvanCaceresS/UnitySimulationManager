using Unity.Entities;
using Unity.Mathematics;
public struct EColiComponent:IComponentData
{
    public float TimeReference;
    public float MaxScale;
    public float GrowthTime;
    public float GrowthDuration;
    public float TimeSinceLastDivision;
    public float DivisionInterval;
    public bool HasGeneratedChild;
    public Entity Parent;
    public bool IsInitialCell;
    public float SeparationThreshold;
    public int SeparationSign;
}