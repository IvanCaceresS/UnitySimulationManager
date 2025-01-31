using Unity.Burst;
using Unity.Entities;
using Unity.Transforms;
using Unity.Mathematics;

[BurstCompile]
public partial struct SCerevisiaeSystem : ISystem
{
    public void OnCreate(ref SystemState state) {}

    public void OnDestroy(ref SystemState state) {}

    public void OnUpdate(ref SystemState state)
    {
        // Solo ejecuta la lógica si el setup está completo y no está pausado
        if (!GameStateManager.IsSetupComplete || GameStateManager.IsPaused)
        {
            return;
        }

        float time = (float)SystemAPI.Time.ElapsedTime;

        foreach (var transform in SystemAPI.Query<RefRW<LocalTransform>>().WithAll<SCerevisiaeComponent>())
        {
            float scaleFactor = math.sin(time) * 0.5f + 1.5f;
            transform.ValueRW.Scale = scaleFactor;
        }
    }
}
