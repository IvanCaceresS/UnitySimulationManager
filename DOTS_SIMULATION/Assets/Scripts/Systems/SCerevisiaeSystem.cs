using Unity.Burst;
using Unity.Collections;
using Unity.Entities;
using Unity.Jobs;
using Unity.Mathematics;
using Unity.Transforms;
using UnityEngine;
using Unity.Physics;           // Si requieres colisionadores, de lo contrario puedes omitirlo.
using Unity.Physics.Extensions;
using CapsuleCollider = Unity.Physics.CapsuleCollider;

//
// NOTA: Se asume que la definición única de ParentData ya existe en un archivo compartido.
// Por ejemplo:
//
// public struct ParentData
// {
//     public float3 Position;
//     public quaternion Rotation;
//     public float Scale;
// }
//

// Sistema de SCerevisiae
[BurstCompile]
[UpdateInGroup(typeof(SimulationSystemGroup))]
public partial class SCerevisiaeSystem : SystemBase
{
    // (Opcional) Valor para actualizar colliders si se requiere.
    const float ColliderUpdateThreshold = 0.01f;

    protected override void OnUpdate()
    {
        // --- Variables de estado global (tomadas de GameStateManager) ---
        bool isSetupComplete = GameStateManager.IsSetupComplete;
        bool isPaused = GameStateManager.IsPaused;
        float simDeltaTime = GameStateManager.DeltaTime;
        if (!isSetupComplete || isPaused)
            return;
        float deltaTime = simDeltaTime; // Copia local para usar en lambdas

        // --- PASO 1: Construir un NativeParallelHashMap con la LocalTransform de todas las entidades ---
        EntityQuery localTransformQuery = GetEntityQuery(typeof(LocalTransform));
        int entityCount = localTransformQuery.CalculateEntityCount();
        int capacity = math.max(1024, entityCount * 2);

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

        // --- PASO 2: Obtener el ECB (Entity Command Buffer) ---
        // Aquí utilizamos un cast explícito para convertir el SystemHandle retornado
        // por GetOrCreateSystemManaged en la instancia real del EndSimulationEntityCommandBufferSystem.
        EndSimulationEntityCommandBufferSystem ecbSystem =
            (EndSimulationEntityCommandBufferSystem)World.GetOrCreateSystemManaged<EndSimulationEntityCommandBufferSystem>();
        var ecb = ecbSystem.CreateCommandBuffer().AsParallelWriter();

        // --- PASO 3: Lógica de crecimiento, división y anclaje de SCerevisiae ---
        JobHandle scJobHandle = Entities
            .WithReadOnly(parentMap)
            .ForEach((Entity entity, int entityInQueryIndex,
                      ref LocalTransform transform,
                      ref SCerevisiaeComponent sc) =>
            {
                float currentScale = transform.Scale;
                float maxScale = sc.MaxScale;

                // Actualiza duraciones (puedes ajustar estos cálculos según tus necesidades)
                sc.GrowthDuration = sc.TimeReference * sc.SeparationThreshold;
                sc.DivisionInterval = sc.GrowthDuration;

                // --- Crecimiento ---
                if (currentScale < maxScale)
                {
                    sc.GrowthTime += deltaTime;
                    float initialScale = sc.IsInitialCell ? maxScale : 0.01f;
                    if (sc.GrowthTime <= sc.GrowthDuration)
                    {
                        float t = sc.GrowthTime / sc.GrowthDuration;
                        float newScale = math.lerp(initialScale, maxScale, t);
                        transform.Scale = newScale;
                    }
                }

                // --- División ---
                // Cuando la célula alcanza su tamaño máximo, se acumula el tiempo de división.
                // Si se supera el intervalo, se crea una célula hija y se reinicia el contador.
                if (transform.Scale >= maxScale)
                {
                    sc.TimeSinceLastDivision += deltaTime;
                    if (sc.TimeSinceLastDivision >= sc.DivisionInterval)
                    {
                        Unity.Mathematics.Random rng =
                            new Unity.Mathematics.Random((uint)(entityInQueryIndex + 1) * 99999);
                        int sign = (rng.NextFloat() < 0.5f) ? 1 : -1;

                        // Crear la hija
                        Entity childEntity = ecb.Instantiate(entityInQueryIndex, entity);
                        LocalTransform childTransform = transform;
                        childTransform.Scale = 0.01f; // La hija nace pequeña

                        SCerevisiaeComponent childData = sc;
                        childData.GrowthTime = 0f;
                        childData.TimeSinceLastDivision = 0f;
                        childData.IsInitialCell = false;
                        childData.Parent = entity;
                        childData.SeparationSign = sign;
                        childTransform.Position = transform.Position;

                        ecb.SetComponent(entityInQueryIndex, childEntity, childTransform);
                        ecb.SetComponent(entityInQueryIndex, childEntity, childData);

                        // Reiniciar el contador de división de la madre para permitir futuras divisiones
                        sc.TimeSinceLastDivision = 0f;
                    }
                }

                // --- Anclaje ---
                if (!sc.IsInitialCell && sc.Parent != Entity.Null)
                {
                    if (parentMap.TryGetValue(sc.Parent, out ParentData parentData))
                    {
                        float childScale = transform.Scale;
                        float threshold = sc.SeparationThreshold;
                        if (childScale < threshold * maxScale)
                        {
                            float ratio = childScale / (threshold * maxScale);
                            ratio = math.clamp(ratio, 0f, 1f);
                            float radius = parentData.Scale * 0.5f; // Mitad del tamaño del padre
                            float offset = radius * ratio;

                            float3 localUp = new float3(0, 0, sc.SeparationSign);
                            float3 up = math.mul(parentData.Rotation, localUp);

                            transform.Position = parentData.Position + up * offset;
                            transform.Rotation = parentData.Rotation;
                        }
                        else
                        {
                            sc.Parent = Entity.Null;
                        }
                    }
                }

                ecb.SetComponent(entityInQueryIndex, entity, transform);
                ecb.SetComponent(entityInQueryIndex, entity, sc);
            })
            .ScheduleParallel(Dependency);
        Dependency = scJobHandle;
        ecbSystem.AddJobHandleForProducer(Dependency);

        // --- PASO FINAL: Liberar el NativeParallelHashMap ---
        Dependency = parentMap.Dispose(Dependency);
    }
}
