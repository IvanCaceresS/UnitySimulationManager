using Unity.Burst;
using Unity.Collections;
using Unity.Entities;
using Unity.Jobs;      // Para JobHandle si tu ECS lo requiere
using Unity.Mathematics;
using Unity.Physics;
using Unity.Physics.Extensions;
using Unity.Transforms;
using UnityEngine;

// Evitar conflicto con UnityEngine.CapsuleCollider
using CapsuleCollider = Unity.Physics.CapsuleCollider;

[BurstCompile]
[UpdateInGroup(typeof(SimulationSystemGroup))]
public partial class EColiSystem : SystemBase
{
    struct ParentData
    {
        public float3 Position;
        public quaternion Rotation;
        public float Scale;
    }

    const float ColliderUpdateThreshold = 0.01f;

    [BurstCompile]
    protected override void OnUpdate()
    {
        bool isSetupComplete = GameStateManager.IsSetupComplete;
        bool isPaused        = GameStateManager.IsPaused;
        float simDeltaTime   = GameStateManager.DeltaTime;

        if (!isSetupComplete || isPaused)
            return;

        // ----------------------------------------------------------------
        // Calculamos cuántas entidades tienen LocalTransform
        // para asignar una capacidad superior al HashMap
        // ----------------------------------------------------------------
        EntityQuery localTransformQuery = GetEntityQuery(typeof(LocalTransform));
        int entityCount = localTransformQuery.CalculateEntityCount();

        // Factor de seguridad, por ejemplo x2
        int capacity = math.max(1024, entityCount * 2);

        // Creamos el HashMap con capacidad >= cantidad real de entidades
        var parentMap  = new NativeParallelHashMap<Entity, ParentData>(capacity, Allocator.TempJob);
        var mapWriter  = parentMap.AsParallelWriter();

        // PASO A: Llenar parentMap EN PARALELO
        Entities
            .ForEach((Entity e, in LocalTransform transform) =>
            {
                mapWriter.TryAdd(e, new ParentData
                {
                    Position = transform.Position,
                    Rotation = transform.Rotation,
                    Scale    = transform.Scale
                });
            })
            .ScheduleParallel();

        Dependency.Complete(); // Esperamos a que termine antes de usar el mapa

        // PASO B: Lógica de EColi
        var ecb         = new EntityCommandBuffer(Allocator.TempJob);
        var ecbParallel = ecb.AsParallelWriter();

        Entities
            .WithReadOnly(parentMap)  // Ahora solo lo leemos
            .ForEach((Entity entity, int entityInQueryIndex,
                      ref LocalTransform transform,
                      ref EColiComponent ecoli) =>
            {
                float currentScale = transform.Scale;
                float maxScale     = ecoli.MaxScale;

                ecoli.GrowthDuration   = ecoli.TimeReference * ecoli.SeparationThreshold;
                ecoli.DivisionInterval = ecoli.GrowthDuration;

                // -- Crecimiento --
                if (currentScale < maxScale)
                {
                    ecoli.GrowthTime += simDeltaTime;
                    float initialScale = ecoli.IsInitialCell ? maxScale : 0.01f;

                    if (ecoli.GrowthTime <= ecoli.GrowthDuration)
                    {
                        float t        = ecoli.GrowthTime / ecoli.GrowthDuration;
                        float newScale = math.lerp(initialScale, maxScale, t);
                        transform.Scale = newScale;

                        if (ecoli.Parent == Entity.Null &&
                            math.abs(newScale - currentScale) > ColliderUpdateThreshold)
                        {
                            var newCollider =
                                CapsuleCollider.Create(new CapsuleGeometry
                                {
                                    Vertex0 = new float3(0, -newScale * 2f, 0),
                                    Vertex1 = new float3(0,  newScale * 2f, 0),
                                    Radius  = newScale * 0.25f
                                });
                            ecbParallel.SetComponent(entityInQueryIndex, entity,
                                new PhysicsCollider { Value = newCollider });
                        }
                    }
                }

                // -- División --
                if (transform.Scale >= maxScale)
                {
                    ecoli.TimeSinceLastDivision += simDeltaTime;
                    if (ecoli.TimeSinceLastDivision >= ecoli.DivisionInterval)
                    {
                        var rng  = new Unity.Mathematics.Random((uint)(entityInQueryIndex + 1) * 12345);
                        int sign = (rng.NextFloat() < 0.5f) ? 1 : -1;

                        Entity childEntity = ecbParallel.Instantiate(entityInQueryIndex, entity);
                        LocalTransform childTransform = transform;
                        childTransform.Scale = 0.01f;

                        var childData = ecoli;
                        childData.GrowthTime            = 0f;
                        childData.TimeSinceLastDivision = 0f;
                        childData.HasGeneratedChild     = false;
                        childData.IsInitialCell         = false;
                        childData.Parent                = entity;
                        childData.SeparationSign        = sign;

                        float3 localUp = new float3(0, sign, 0);
                        float3 upDir   = math.mul(transform.Rotation, localUp);
                        childTransform.Position = transform.Position + upDir * (transform.Scale * 0.25f);

                        ecbParallel.SetComponent(entityInQueryIndex, childEntity, childTransform);
                        ecbParallel.SetComponent(entityInQueryIndex, childEntity, childData);

                        ecoli.TimeSinceLastDivision = 0f;
                    }
                }

                // -- Anclaje --
                if (!ecoli.IsInitialCell && ecoli.Parent != Entity.Null)
                {
                    if (parentMap.TryGetValue(ecoli.Parent, out var parentData))
                    {
                        float childScale = transform.Scale;
                        float threshold  = ecoli.SeparationThreshold;

                        if (childScale < threshold * maxScale)
                        {
                            float progress = childScale / maxScale;
                            float offset   = math.lerp(0f, parentData.Scale * 4.9f, progress);

                            float3 localUp = new float3(0, ecoli.SeparationSign, 0);
                            float3 up      = math.mul(parentData.Rotation, localUp);

                            transform.Position = parentData.Position + up * offset;
                            transform.Rotation = parentData.Rotation;
                        }
                        else
                        {
                            ecoli.Parent = Entity.Null;
                            // Podrías modificar velocity, collider, etc.
                        }
                    }
                }

                // Guardamos
                ecbParallel.SetComponent(entityInQueryIndex, entity, transform);
                ecbParallel.SetComponent(entityInQueryIndex, entity, ecoli);

            })
            .ScheduleParallel();

        Dependency.Complete();

        ecb.Playback(EntityManager);
        ecb.Dispose();
        parentMap.Dispose();
    }
}
