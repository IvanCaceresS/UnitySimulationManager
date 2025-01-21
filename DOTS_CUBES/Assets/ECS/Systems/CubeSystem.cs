using Unity.Entities;
using Unity.Burst;
using Unity.Collections;
using Unity.Mathematics;
using Unity.Transforms;
using ECS;

[BurstCompile]
public partial struct CubeSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        EntityManager entityManager = state.EntityManager;

        NativeArray<Entity> entities = entityManager.GetAllEntities(Allocator.Temp);

        foreach (Entity entity in entities)
        {
            if (entityManager.HasComponent<CubeComponent>(entity))
            {
                CubeComponent cube = entityManager.GetComponentData<CubeComponent>(entity);
                LocalTransform localTransform = entityManager.GetComponentData<LocalTransform>(entity);

                float3 moveDirection = cube.moveDirection * SystemAPI.Time.DeltaTime * cube.moveSpeed;

                localTransform.Position = localTransform.Position + moveDirection;
                entityManager.SetComponentData<LocalTransform>(entity, localTransform);

                if (cube.moveSpeed > 0)
                {
                    cube.moveSpeed -= 1 * SystemAPI.Time.DeltaTime;
                }
                else
                {
                    cube.moveSpeed = 0;
                }
                entityManager.SetComponentData<CubeComponent>(entity, cube);
            }
        }
    }
}