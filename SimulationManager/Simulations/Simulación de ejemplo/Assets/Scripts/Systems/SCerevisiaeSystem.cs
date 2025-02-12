using Unity.Burst;
using Unity.Collections;
using Unity.Entities;
using Unity.Jobs;
using Unity.Mathematics;
using Unity.Transforms;
using UnityEngine;
using Unity.Physics;
using Unity.Physics.Extensions;
using CapsuleCollider = Unity.Physics.CapsuleCollider;

[BurstCompile]
[UpdateInGroup(typeof(SimulationSystemGroup))]
public partial class SCerevisiaeSystem : SystemBase
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
        // PASO 2: Obtener el EntityCommandBuffer.
        // ---------------------------------------------------------------------
        EndSimulationEntityCommandBufferSystem ecbSystem =
            World.GetOrCreateSystemManaged<EndSimulationEntityCommandBufferSystem>();
        var ecb = ecbSystem.CreateCommandBuffer().AsParallelWriter();

        // ---------------------------------------------------------------------
        // PASO 3: Lógica de crecimiento, división y anclaje para SCerevisiae.
        // ---------------------------------------------------------------------
        Dependency = Entities
            .WithReadOnly(parentMap)
            .ForEach((Entity entity, int entityInQueryIndex,
                      ref LocalTransform transform,
                      ref SCerevisiaeComponent sc) =>
        {
            float maxScale = sc.MaxScale;
            sc.GrowthDuration = sc.DivisionInterval = sc.TimeReference * sc.SeparationThreshold;

            // --- Crecimiento ---
            if (transform.Scale < maxScale)
            {
                sc.GrowthTime += deltaTime;
                float t = math.clamp(sc.GrowthTime / sc.GrowthDuration, 0f, 1f);
                float initialScale = sc.IsInitialCell ? maxScale : 0.01f;
                transform.Scale = math.lerp(initialScale, maxScale, t);
            }

            // --- División ---
            if (transform.Scale >= maxScale)
            {
                sc.TimeSinceLastDivision += deltaTime;
                if (sc.TimeSinceLastDivision >= sc.DivisionInterval)
                {
                    // Se genera un número aleatorio basado en entityInQueryIndex
                    Unity.Mathematics.Random rng = new Unity.Mathematics.Random((uint)(entityInQueryIndex + 1) * 99999);

                    // Generar un ángulo aleatorio entre 0 y 2π (división en el plano XY)
                    float angle = rng.NextFloat(0f, math.PI * 2f);
                    float3 randomDir = new float3(math.cos(angle), math.sin(angle), 0f);

                    Entity child = ecb.Instantiate(entityInQueryIndex, entity);
                    LocalTransform childTransform = transform;
                    childTransform.Scale = 0.01f;

                    SCerevisiaeComponent childData = sc;
                    childData.GrowthTime = 0f;
                    childData.TimeSinceLastDivision = 0f;
                    childData.IsInitialCell = false;
                    childData.Parent = entity;
                    // Asignar la dirección de crecimiento aleatoria al hijo
                    childData.GrowthDirection = randomDir;

                    // La posición inicial se hereda; se actualizará en el paso de anclaje
                    childTransform.Position = transform.Position;

                    ecb.SetComponent(entityInQueryIndex, child, childTransform);
                    ecb.SetComponent(entityInQueryIndex, child, childData);
                    sc.TimeSinceLastDivision = 0f;
                }
            }

            // --- Anclaje ---
            if (!sc.IsInitialCell && sc.Parent != Entity.Null &&
                parentMap.TryGetValue(sc.Parent, out ParentData parentData))
            {
                if (transform.Scale < sc.SeparationThreshold * maxScale)
                {
                    float ratio = math.clamp(transform.Scale / (sc.SeparationThreshold * maxScale), 0f, 1f);
                    float offset = (parentData.Scale * 0.5f) * ratio;
                    // Convertir la dirección de crecimiento, definida en el espacio local del padre,
                    // a dirección en el espacio mundial utilizando la rotación del padre.
                    float3 worldDir = math.mul(parentData.Rotation, sc.GrowthDirection);
                    transform.Position = parentData.Position + worldDir * offset;
                    transform.Rotation = parentData.Rotation;
                }
                else
                {
                    // Una vez que el hijo alcanza o supera el umbral, se separa del padre.
                    sc.Parent = Entity.Null;
                }
            }

            // Actualizar componentes mediante el ECB.
            ecb.SetComponent(entityInQueryIndex, entity, transform);
            ecb.SetComponent(entityInQueryIndex, entity, sc);
        }).ScheduleParallel(Dependency);
        ecbSystem.AddJobHandleForProducer(Dependency);

        // ---------------------------------------------------------------------
        // PASO FINAL: Liberar el NativeParallelHashMap.
        // ---------------------------------------------------------------------
        Dependency = parentMap.Dispose(Dependency);
    }
}
