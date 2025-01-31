using Unity.Burst;
using Unity.Entities;
using Unity.Transforms;
using Unity.Mathematics;

[BurstCompile]
public partial struct CubeSystem : ISystem
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

        float deltaTime = SystemAPI.Time.DeltaTime;

        foreach (var transform in SystemAPI.Query<RefRW<LocalTransform>>().WithAll<CubeComponent>())
        {
            transform.ValueRW = transform.ValueRW.RotateY(deltaTime * math.radians(45f));
        }
    }
}
