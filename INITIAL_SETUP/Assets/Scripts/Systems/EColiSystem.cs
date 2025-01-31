using Unity.Burst;
using Unity.Entities;
using Unity.Transforms;
using Unity.Mathematics;

[BurstCompile]
public partial struct EColiSystem : ISystem
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

        foreach (var transform in SystemAPI.Query<RefRW<LocalTransform>>().WithAll<EColiComponent>())
        {
            float3 randomDirection = math.normalize(new float3(
                UnityEngine.Random.Range(-1f, 1f),
                0,
                UnityEngine.Random.Range(-1f, 1f)
            ));

            transform.ValueRW.Position += randomDirection * deltaTime;
        }
    }
}
