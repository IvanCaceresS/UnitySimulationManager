using Unity.Burst;
using Unity.Collections;
using Unity.Entities;
using Unity.Jobs; // Para .ScheduleParallel()
using Unity.Mathematics;
using Unity.Physics;
using Unity.Physics.Extensions;
using Unity.Transforms;
using UnityEngine;

// Ajustamos el update group según tu proyecto
[BurstCompile]
[UpdateInGroup(typeof(SimulationSystemGroup))]
public partial class SCerevisiaeSystem : SystemBase
{
    struct ParentData
    {
        public float3 Position;
        public quaternion Rotation;
        public float Scale;
    }

    // Opcional si quieres un umbral de recreación de collider
    const float ColliderUpdateThreshold = 0.01f;

    [BurstCompile]
    protected override void OnUpdate()
    {
        // Leemos flags fuera del job-lambda
        bool isSetupComplete = GameStateManager.IsSetupComplete;
        bool isPaused        = GameStateManager.IsPaused;
        float simDeltaTime   = GameStateManager.DeltaTime;

        if (!isSetupComplete || isPaused)
            return;

        // == 1) Creamos un hash map con la LocalTransform de todas las entidades ==

        EntityQuery localTransformQuery = GetEntityQuery(typeof(LocalTransform));
        int entityCount = localTransformQuery.CalculateEntityCount();
        int capacity = math.max(1024, entityCount * 2);

        var parentMap = new NativeParallelHashMap<Entity, ParentData>(capacity, Allocator.TempJob);
        var mapWriter = parentMap.AsParallelWriter();

        // PASO A: Llenar parentMap en paralelo
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
            .ScheduleParallel(); // Retorna un JobHandle implícitamente acoplado a "Dependency"

        // Esperamos a que termine antes de usar parentMap
        Dependency.Complete();

        // == 2) Lógica SCerevisiae ==
        var ecb         = new EntityCommandBuffer(Allocator.TempJob);
        var ecbParallel = ecb.AsParallelWriter();

        Entities
            .WithReadOnly(parentMap)
            .ForEach((Entity entity, int entityInQueryIndex,
                      ref LocalTransform transform,
                      ref SCerevisiaeComponent sc) =>
            {
                float currentScale = transform.Scale;
                float maxScale     = sc.MaxScale;

                // Ajustamos Durations
                sc.GrowthDuration   = sc.TimeReference * sc.SeparationThreshold;
                sc.DivisionInterval = sc.GrowthDuration;

                // --- Crecimiento ---
                if (currentScale < maxScale)
                {
                    sc.GrowthTime += simDeltaTime;

                    float initialScale = sc.IsInitialCell ? maxScale : 0.01f;
                    if (sc.GrowthTime <= sc.GrowthDuration)
                    {
                        float t = sc.GrowthTime / sc.GrowthDuration;
                        float newScale = math.lerp(initialScale, maxScale, t);
                        transform.Scale = newScale;
                    }
                }

                // --- División ---
                if (transform.Scale >= maxScale)
                {
                    sc.TimeSinceLastDivision += simDeltaTime;
                    // solo crea hija si no la ha creado ya
                    if (!sc.HasGeneratedChild && sc.TimeSinceLastDivision >= sc.DivisionInterval)
                    {
                        // Random semilla por entityInQueryIndex
                        var rng  = new Unity.Mathematics.Random((uint)(entityInQueryIndex+1) * 99999);
                        int sign = (rng.NextFloat() < 0.5f) ? 1 : -1;

                        // Creamos la hija
                        Entity childEntity = ecbParallel.Instantiate(entityInQueryIndex, entity);

                        // Ajustamos la hija
                        LocalTransform childTransform = transform;
                        childTransform.Scale = 0.01f;

                        var childData = sc;
                        childData.GrowthTime            = 0f;
                        childData.TimeSinceLastDivision = 0f;
                        childData.HasGeneratedChild     = false;
                        childData.IsInitialCell         = false;
                        childData.Parent                = entity;
                        childData.SeparationSign        = sign;

                        // nace en el centro (o donde gustes)
                        childTransform.Position = transform.Position;

                        ecbParallel.SetComponent(entityInQueryIndex, childEntity, childTransform);
                        ecbParallel.SetComponent(entityInQueryIndex, childEntity, childData);

                        // la madre no vuelve a crear hija hasta que se separe
                        sc.HasGeneratedChild     = true;
                        sc.TimeSinceLastDivision = 0f;
                    }
                }

                // --- Anclaje ---
                if (!sc.IsInitialCell && sc.Parent != Entity.Null)
                {
                    if (parentMap.TryGetValue(sc.Parent, out var parentData))
                    {
                        float childScale = transform.Scale;
                        float threshold  = sc.SeparationThreshold;

                        // mientras no supere threshold*maxScale => anclado
                        if (childScale < threshold * maxScale)
                        {
                            // ratio 0..1
                            float ratio = childScale / (threshold * maxScale);
                            ratio       = math.clamp(ratio, 0f, 1f);

                            float radius = parentData.Scale * 0.5f; // la mitad del scale del padre
                            float offset = radius * ratio;

                            float3 localUp = new float3(0, sc.SeparationSign, 0);
                            float3 up      = math.mul(parentData.Rotation, localUp);

                            transform.Position = parentData.Position + up * offset;
                            transform.Rotation = parentData.Rotation;
                        }
                        else
                        {
                            // se suelta
                            sc.Parent = Entity.Null;
                            // en parallel no reescribimos la madre -> single approach
                        }
                    }
                }

                // guardamos
                ecbParallel.SetComponent(entityInQueryIndex, entity, transform);
                ecbParallel.SetComponent(entityInQueryIndex, entity, sc);

            })
            .ScheduleParallel(); // devuelve JobHandle acoplado a "Dependency"

        // Esperamos el final
        Dependency.Complete();

        // Reproducimos
        ecb.Playback(EntityManager);
        ecb.Dispose();
        parentMap.Dispose();
    }
}
