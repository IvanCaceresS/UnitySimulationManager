using Unity.Burst;
using Unity.Collections;
using Unity.Entities;
using Unity.Jobs;
using Unity.Mathematics;
using Unity.Physics;
using Unity.Physics.Extensions;
using Unity.Transforms;
using UnityEngine;

[BurstCompile]
[UpdateInGroup(typeof(SimulationSystemGroup))]
public partial class EColiSystem : SystemBase
{
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
                      ref EColiComponent organism) =>
        {
            float maxScale = organism.MaxScale;
            // Actualizamos los tiempos de crecimiento y división.
            organism.GrowthDuration = organism.DivisionInterval = organism.TimeReference * organism.SeparationThreshold;

            // --- Crecimiento ---
            if (transform.Scale < maxScale)
            {
                organism.GrowthTime += deltaTime;
                float t = math.clamp(organism.GrowthTime / organism.GrowthDuration, 0f, 1f);
                float initialScale = organism.IsInitialCell ? maxScale : 0.01f;
                transform.Scale = math.lerp(initialScale, maxScale, t);
            }

            // --- División ---
            if (transform.Scale >= maxScale)
            {
                organism.TimeSinceLastDivision += deltaTime;
                if (organism.TimeSinceLastDivision >= organism.DivisionInterval)
                {
                    // Se genera un número aleatorio basado en entityInQueryIndex
                    Unity.Mathematics.Random rng = new Unity.Mathematics.Random((uint)(entityInQueryIndex + 1) * 12345);
                    
                    // Genera un sentido de separación aleatorio
                    int sign = rng.NextFloat() < 0.5f ? 1 : -1;

                    Entity child = ecb.Instantiate(entityInQueryIndex, entity);
                    LocalTransform childTransform = transform;
                    childTransform.Scale = 0.01f;

                    EColiComponent childData = organism;
                    childData.GrowthTime = 0f;
                    childData.TimeSinceLastDivision = 0f;
                    childData.HasGeneratedChild = false;
                    childData.IsInitialCell = false;
                    childData.Parent = entity;
                    // Asignar el sentido de separación al hijo
                    childData.SeparationSign = sign;

                    float3 upDir = math.mul(transform.Rotation, new float3(0, sign, 0));
                    childTransform.Position = transform.Position + upDir * (transform.Scale * 0.25f);

                    ecb.SetComponent(entityInQueryIndex, child, childTransform);
                    ecb.SetComponent(entityInQueryIndex, child, childData);
                    organism.TimeSinceLastDivision = 0f;
                }
            }

            // --- Anclaje ---
            if (!organism.IsInitialCell && organism.Parent != Entity.Null &&
                parentMap.TryGetValue(organism.Parent, out ParentData parentData))
            {
                if (transform.Scale < organism.SeparationThreshold * maxScale)
                {
                    float offset = math.lerp(0f, parentData.Scale * 4.9f, transform.Scale / maxScale);
                    float3 up = math.mul(parentData.Rotation, new float3(0, organism.SeparationSign, 0));
                    transform.Position = parentData.Position + up * offset;
                    transform.Rotation = parentData.Rotation;
                }
                else
                {
                    // Una vez que el hijo alcanza o supera el umbral, se separa del padre.
                    organism.Parent = Entity.Null;
                }
            }

            // Actualizar componentes mediante el ECB.
            ecb.SetComponent(entityInQueryIndex, entity, transform);
            ecb.SetComponent(entityInQueryIndex, entity, organism);
        }).ScheduleParallel(Dependency);
        ecbSystem.AddJobHandleForProducer(Dependency);

        // ---------------------------------------------------------------------
        // PASO FINAL: Liberar el NativeParallelHashMap.
        // ---------------------------------------------------------------------
        Dependency = parentMap.Dispose(Dependency);
    }
}
