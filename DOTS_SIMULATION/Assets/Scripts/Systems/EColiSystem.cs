using Unity.Burst;
using Unity.Collections;
using Unity.Entities;
using Unity.Jobs;
using Unity.Mathematics;
using Unity.Physics;
using Unity.Physics.Extensions;
using Unity.Transforms;
using UnityEngine;
// Evitamos conflictos con el collider de UnityEngine.
using CapsuleCollider = Unity.Physics.CapsuleCollider;

//
// Definición de ParentData a nivel de namespace para evitar problemas con Burst.
//
public struct ParentData
{
    public float3 Position;
    public quaternion Rotation;
    public float Scale;
}

//
// Sistema de simulación de EColi
//
[BurstCompile]
[UpdateInGroup(typeof(SimulationSystemGroup))]
public partial class EColiSystem : SystemBase
{
    const float ColliderUpdateThreshold = 0.01f;

    protected override void OnUpdate()
    {
        // Variables locales simples para evitar capturas problemáticas en los lambdas.
        bool isSetupComplete = GameStateManager.IsSetupComplete;
        bool isPaused = GameStateManager.IsPaused;
        float simDeltaTime = GameStateManager.DeltaTime;
        if (!isSetupComplete || isPaused)
            return;
        float deltaTime = simDeltaTime; // Copia local para usar en los lambdas

        // -------------------------------------------------------------------------
        // PASO PRELIMINAR: Calcular la capacidad para el NativeParallelHashMap.
        // -------------------------------------------------------------------------
        EntityQuery localTransformQuery = GetEntityQuery(typeof(LocalTransform));
        int entityCount = localTransformQuery.CalculateEntityCount();
        int capacity = math.max(1024, entityCount * 2);

        // -------------------------------------------------------------------------
        // PASO A: Crear y llenar el NativeParallelHashMap con datos de LocalTransform.
        // -------------------------------------------------------------------------
        NativeParallelHashMap<Entity, ParentData> parentMap =
            new NativeParallelHashMap<Entity, ParentData>(capacity, Allocator.TempJob);
        var parentMapWriter = parentMap.AsParallelWriter();

        JobHandle parentMapJobHandle = Entities
            .ForEach((Entity e, in LocalTransform transform) =>
            {
                ParentData pd = new ParentData
                {
                    Position = transform.Position,
                    Rotation = transform.Rotation,
                    Scale = transform.Scale
                };
                parentMapWriter.TryAdd(e, pd);
            })
            .ScheduleParallel(Dependency);
        Dependency = parentMapJobHandle;

        // -------------------------------------------------------------------------
        // PASO B: Obtener el ECB del EndSimulationEntityCommandBufferSystem.
        // Se usa GetOrCreateSystemManaged para obtener la instancia administrada.
        // -------------------------------------------------------------------------
        EndSimulationEntityCommandBufferSystem ecbSystem =
            World.GetOrCreateSystemManaged<EndSimulationEntityCommandBufferSystem>();
        var ecb = ecbSystem.CreateCommandBuffer().AsParallelWriter();

        // -------------------------------------------------------------------------
        // PASO C: Lógica de EColi (crecimiento, división y anclaje) usando el mapa.
        // Se indica que se usa parentMap en modo lectura con WithReadOnly.
        // -------------------------------------------------------------------------
        JobHandle eColiJobHandle = Entities
            .WithReadOnly(parentMap)
            .ForEach((Entity entity, int entityInQueryIndex,
                      ref LocalTransform transform,
                      ref EColiComponent ecoli) =>
            {
                float currentScale = transform.Scale;
                float maxScale = ecoli.MaxScale;

                // Actualizamos duraciones de crecimiento y división.
                ecoli.GrowthDuration = ecoli.TimeReference * ecoli.SeparationThreshold;
                ecoli.DivisionInterval = ecoli.GrowthDuration;

                // --- Crecimiento ---
                if (currentScale < maxScale)
                {
                    ecoli.GrowthTime += deltaTime;
                    float initialScale = ecoli.IsInitialCell ? maxScale : 0.01f;
                    if (ecoli.GrowthTime <= ecoli.GrowthDuration)
                    {
                        float t = ecoli.GrowthTime / ecoli.GrowthDuration;
                        float newScale = math.lerp(initialScale, maxScale, t);
                        transform.Scale = newScale;

                        // Actualiza el collider si el cambio es significativo y sin padre.
                        if (ecoli.Parent == Entity.Null &&
                            math.abs(newScale - currentScale) > ColliderUpdateThreshold)
                        {
                            var newCollider = CapsuleCollider.Create(new CapsuleGeometry
                            {
                                Vertex0 = new float3(0, -newScale * 2f, 0),
                                Vertex1 = new float3(0, newScale * 2f, 0),
                                Radius  = newScale * 0.25f
                            });
                            ecb.SetComponent(entityInQueryIndex, entity,
                                new PhysicsCollider { Value = newCollider });
                        }
                    }
                }

                // --- División ---
                if (transform.Scale >= maxScale)
                {
                    ecoli.TimeSinceLastDivision += deltaTime;
                    if (ecoli.TimeSinceLastDivision >= ecoli.DivisionInterval)
                    {
                        Unity.Mathematics.Random rng =
                            new Unity.Mathematics.Random((uint)(entityInQueryIndex + 1) * 12345);
                        int sign = (rng.NextFloat() < 0.5f) ? 1 : -1;

                        Entity childEntity = ecb.Instantiate(entityInQueryIndex, entity);
                        LocalTransform childTransform = transform;
                        childTransform.Scale = 0.01f;

                        EColiComponent childData = ecoli;
                        childData.GrowthTime = 0f;
                        childData.TimeSinceLastDivision = 0f;
                        childData.HasGeneratedChild = false;
                        childData.IsInitialCell = false;
                        childData.Parent = entity;
                        childData.SeparationSign = sign;

                        float3 localUp = new float3(0, sign, 0);
                        float3 upDir = math.mul(transform.Rotation, localUp);
                        childTransform.Position = transform.Position + upDir * (transform.Scale * 0.25f);

                        ecb.SetComponent(entityInQueryIndex, childEntity, childTransform);
                        ecb.SetComponent(entityInQueryIndex, childEntity, childData);

                        ecoli.TimeSinceLastDivision = 0f;
                    }
                }

                // --- Anclaje ---
                if (!ecoli.IsInitialCell && ecoli.Parent != Entity.Null)
                {
                    if (parentMap.TryGetValue(ecoli.Parent, out ParentData parentData))
                    {
                        float childScale = transform.Scale;
                        float threshold = ecoli.SeparationThreshold;
                        if (childScale < threshold * maxScale)
                        {
                            float progress = childScale / maxScale;
                            float offset = math.lerp(0f, parentData.Scale * 4.9f, progress);

                            float3 localUp = new float3(0, ecoli.SeparationSign, 0);
                            float3 up = math.mul(parentData.Rotation, localUp);

                            transform.Position = parentData.Position + up * offset;
                            transform.Rotation = parentData.Rotation;
                        }
                        else
                        {
                            ecoli.Parent = Entity.Null;
                        }
                    }
                }

                // Se actualizan los componentes en la entidad.
                ecb.SetComponent(entityInQueryIndex, entity, transform);
                ecb.SetComponent(entityInQueryIndex, entity, ecoli);
            })
            .ScheduleParallel(Dependency);
        Dependency = eColiJobHandle;
        ecbSystem.AddJobHandleForProducer(Dependency);

        // -------------------------------------------------------------------------
        // PASO FINAL: Liberar el NativeParallelHashMap cuando ya no se use.
        // -------------------------------------------------------------------------
        Dependency = parentMap.Dispose(Dependency);
    }
}
