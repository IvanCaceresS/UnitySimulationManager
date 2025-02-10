using Unity.Burst;
using Unity.Collections;
using Unity.Entities;
using Unity.Jobs;
using Unity.Mathematics;
using Unity.Physics;
using Unity.Physics.Extensions;
using Unity.Transforms;
using UnityEngine;
using CapsuleCollider = Unity.Physics.CapsuleCollider;

[BurstCompile]
[UpdateInGroup(typeof(SimulationSystemGroup))]
public partial class EColiSystem : SystemBase
{
    const float ColliderUpdateThreshold = 0.01f;

    protected override void OnUpdate()
    {
        // Comprobamos el estado global
        if (!GameStateManager.IsSetupComplete || GameStateManager.IsPaused)
            return;

        float deltaTime = GameStateManager.DeltaTime;

        // ---------------------------------------------------------------------
        // PASO 1: Construir el NativeParallelHashMap de ParentData a partir de
        // LocalTransform.
        // ---------------------------------------------------------------------
        EntityQuery query = GetEntityQuery(typeof(LocalTransform));
        int capacity = math.max(1024, query.CalculateEntityCount() * 2);
        NativeParallelHashMap<Entity, ParentData> parentMap =
            new NativeParallelHashMap<Entity, ParentData>(capacity, Allocator.TempJob);
        var parentMapWriter = parentMap.AsParallelWriter();
        Dependency = Entities.ForEach((Entity e, in LocalTransform transform) =>
        {
            parentMapWriter.TryAdd(e, new ParentData
            {
                Position = transform.Position,
                Rotation = transform.Rotation,
                Scale    = transform.Scale
            });
        }).ScheduleParallel(Dependency);

        // ---------------------------------------------------------------------
        // PASO 2: Obtener el EntityCommandBuffer para postergar cambios.
        // ---------------------------------------------------------------------
        EndSimulationEntityCommandBufferSystem ecbSystem =
            World.GetOrCreateSystemManaged<EndSimulationEntityCommandBufferSystem>();
        var ecb = ecbSystem.CreateCommandBuffer().AsParallelWriter();

        // ---------------------------------------------------------------------
        // PASO 3: Lógica de crecimiento, división y anclaje para EColi.
        // ---------------------------------------------------------------------
        Dependency = Entities
            .WithReadOnly(parentMap)
            .ForEach((Entity entity, int entityInQueryIndex,
                      ref LocalTransform transform,
                      ref EColiComponent ecoli) =>
        {
            float currentScale = transform.Scale;
            float maxScale = ecoli.MaxScale;
            // Actualizamos los tiempos de crecimiento y división.
            ecoli.GrowthDuration = ecoli.DivisionInterval = ecoli.TimeReference * ecoli.SeparationThreshold;

            // --- Crecimiento ---
            if (currentScale < maxScale)
            {
                ecoli.GrowthTime += deltaTime;
                // Se clampa el factor de interpolación a [0,1] para que, aun si se supera GrowthDuration,
                // el valor resultante sea 1 (es decir, se asigne maxScale).
                float t = math.clamp(ecoli.GrowthTime / ecoli.GrowthDuration, 0f, 1f);
                float initialScale = ecoli.IsInitialCell ? maxScale : 0.01f;
                float newScale = math.lerp(initialScale, maxScale, t);

                // Actualizar el collider si la célula no tiene padre y el cambio es significativo.
                if (ecoli.Parent == Entity.Null && math.abs(newScale - currentScale) > ColliderUpdateThreshold)
                {
                    var newCollider = CapsuleCollider.Create(new CapsuleGeometry
                    {
                        Vertex0 = new float3(0, -newScale * 2f, 0),
                        Vertex1 = new float3(0,  newScale * 2f, 0),
                        Radius  = newScale * 0.25f
                    });
                    ecb.SetComponent(entityInQueryIndex, entity,
                        new PhysicsCollider { Value = newCollider });
                }
                transform.Scale = newScale;
            }

            // --- División ---
            if (transform.Scale >= maxScale)
            {
                ecoli.TimeSinceLastDivision += deltaTime;
                if (ecoli.TimeSinceLastDivision >= ecoli.DivisionInterval)
                {
                    Unity.Mathematics.Random rng = new Unity.Mathematics.Random((uint)(entityInQueryIndex + 1) * 12345);
                    int sign = rng.NextFloat() < 0.5f ? 1 : -1;

                    Entity child = ecb.Instantiate(entityInQueryIndex, entity);
                    LocalTransform childTransform = transform;
                    childTransform.Scale = 0.01f;

                    EColiComponent childData = ecoli;
                    childData.GrowthTime = 0f;
                    childData.TimeSinceLastDivision = 0f;
                    childData.HasGeneratedChild = false;
                    childData.IsInitialCell = false;
                    childData.Parent = entity;
                    childData.SeparationSign = sign;

                    float3 upDir = math.mul(transform.Rotation, new float3(0, sign, 0));
                    childTransform.Position = transform.Position + upDir * (transform.Scale * 0.25f);

                    ecb.SetComponent(entityInQueryIndex, child, childTransform);
                    ecb.SetComponent(entityInQueryIndex, child, childData);

                    ecoli.TimeSinceLastDivision = 0f;
                }
            }

            // --- Anclaje ---
            if (!ecoli.IsInitialCell && ecoli.Parent != Entity.Null &&
                parentMap.TryGetValue(ecoli.Parent, out ParentData parentData))
            {
                if (transform.Scale < ecoli.SeparationThreshold * maxScale)
                {
                    float offset = math.lerp(0f, parentData.Scale * 4.9f, transform.Scale / maxScale);
                    float3 up = math.mul(parentData.Rotation, new float3(0, ecoli.SeparationSign, 0));
                    transform.Position = parentData.Position + up * offset;
                    transform.Rotation = parentData.Rotation;
                }
                else
                {
                    ecoli.Parent = Entity.Null;
                }
            }

            // Actualizar componentes mediante el ECB.
            ecb.SetComponent(entityInQueryIndex, entity, transform);
            ecb.SetComponent(entityInQueryIndex, entity, ecoli);
        }).ScheduleParallel(Dependency);
        ecbSystem.AddJobHandleForProducer(Dependency);

        // ---------------------------------------------------------------------
        // PASO FINAL: Liberar el NativeParallelHashMap.
        // ---------------------------------------------------------------------
        Dependency = parentMap.Dispose(Dependency);
    }
}
