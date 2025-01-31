using Unity.Burst;
using Unity.Entities;
using Unity.Transforms;
using Unity.Mathematics;
using Unity.Physics;            // Quita si no usas DOTS Physics
using Unity.Physics.Extensions; // Quita si no usas DOTS Physics
using UnityEngine;              // Para math.up()

[BurstCompile]
public partial struct EColiSystem : ISystem
{
    public void OnCreate(ref SystemState state) {}
    public void OnDestroy(ref SystemState state) {}

    public void OnUpdate(ref SystemState state)
    {
        // Solo ejecuta la lógica si el setup está completo y no está pausado
        if (!GameStateManager.IsSetupComplete || GameStateManager.IsPaused)
            return;

        // 1 frame = 1s * DeltaTime de la simulación (si así lo decidiste)
        float simDeltaTime = 1f * GameStateManager.DeltaTime;
        var ecb = new EntityCommandBuffer(Unity.Collections.Allocator.Temp);

        // Recorremos todas las entidades con LocalTransform + EColiComponent
        foreach (var (transform, ecoli, entity) in SystemAPI
                 .Query<RefRW<LocalTransform>, RefRW<EColiComponent>>()
                 .WithEntityAccess())
        {
            //-----------------------------------------------------
            // 1) Crecimiento hasta MaxScale
            //-----------------------------------------------------
            float currentScale = transform.ValueRO.Scale;
            float maxScale     = ecoli.ValueRO.MaxScale;

            if (currentScale < maxScale)
            {
                // Aumentar tiempo de crecimiento en función del tiempo simulado
                ecoli.ValueRW.GrowthTime += simDeltaTime;

                // Mientras no exceda GrowthDuration, aumenta la escala
                if (ecoli.ValueRW.GrowthTime <= ecoli.ValueRO.GrowthDuration)
                {
                    float newScale = currentScale + (ecoli.ValueRO.GrowthRate * simDeltaTime);
                    newScale = math.min(newScale, maxScale);
                    transform.ValueRW.Scale = newScale;
                }

                // Empuje leve hacia arriba (si usas DOTS Physics)
                if (state.EntityManager.HasComponent<PhysicsVelocity>(entity))
                {
                    var velocity = state.EntityManager.GetComponentData<PhysicsVelocity>(entity);
                    velocity.Linear += math.up() * 0.1f * simDeltaTime;
                    ecb.SetComponent(entity, velocity);
                }
            }

            //-----------------------------------------------------
            // 2) División: solo si alcanzó el MaxScale
            //-----------------------------------------------------
            if (transform.ValueRO.Scale >= maxScale)
            {
                ecoli.ValueRW.TimeSinceLastDivision += simDeltaTime;

                // Cuando supere el DivisionInterval, crea la hija
                if (ecoli.ValueRO.TimeSinceLastDivision >= ecoli.ValueRO.DivisionInterval)
                {
                    Entity childEntity = ecb.Instantiate(entity);

                    // La hija empieza muy pequeña
                    var childTransform = transform.ValueRO;
                    childTransform.Scale = 0.01f;
                    // La colocamos en la misma posición de la madre (o un poco por encima)
                    childTransform.Position = transform.ValueRO.Position + math.up() * (transform.ValueRO.Scale * 0.25f);
                    ecb.SetComponent(childEntity, childTransform);

                    // Copiamos datos del padre a la hija
                    var childData = ecoli.ValueRW;
                    childData.GrowthTime            = 0f;
                    childData.TimeSinceLastDivision = 0f;
                    childData.HasGeneratedChild     = false;
                    childData.Parent                = entity;  // La hija tiene como padre a la madre
                    childData.IsInitialCell         = false;   // No es una célula inicial
                    // childData.SeparationThreshold  // hereda
                    ecb.SetComponent(childEntity, childData);

                    // Reiniciamos el timer de división de la madre
                    ecoli.ValueRW.TimeSinceLastDivision = 0f;
                }
            }

            //-----------------------------------------------------
            // 3) Lógica de anclaje (la hija “sale” del padre)
            //-----------------------------------------------------
            // Solo aplica si la hija NO es la célula inicial y tiene un padre
            if (!ecoli.ValueRO.IsInitialCell && ecoli.ValueRO.Parent != Entity.Null)
            {
                var parentTransform = SystemAPI.GetComponent<LocalTransform>(ecoli.ValueRO.Parent);
                float childScale = transform.ValueRO.Scale;

                // threshold = 0.7f => se separa al 70% del tamaño final
                float threshold = ecoli.ValueRO.SeparationThreshold; 

                // Mientras la hija no supere el umbral *su* MaxScale
                if (childScale < threshold * maxScale)
                {
                    // El "progreso" de la hija es su escala actual entre su escala máxima
                    float progress = childScale / maxScale;

                    // offset: parte en 0 cuando la hija es 0.01f, y
                    //         avanza hasta un valor que la “empuje” fuera del padre.
                    // Por ejemplo, 3.25f * parentTransform.Scale es la distancia final.
                    // Ajusta a tu gusto para que visualmente “salga del extremo”.
                    float offset = math.lerp(0f, parentTransform.Scale * 3.25f, progress);

                    float3 up = math.mul(parentTransform.Rotation, new float3(0,1,0));
                    transform.ValueRW.Position = parentTransform.Position + up * offset;

                    // Copiamos también la rotación del padre
                    transform.ValueRW.Rotation = parentTransform.Rotation;

                    ecb.SetComponent(entity, transform.ValueRW);
                }
                else
                {
                    // Al superar el 70%, se libera del padre
                    ecoli.ValueRW.Parent = Entity.Null;

                    // Reducir velocidad al separar (si usas DOTS Physics)
                    if (state.EntityManager.HasComponent<PhysicsVelocity>(entity))
                    {
                        var velocity = state.EntityManager.GetComponentData<PhysicsVelocity>(entity);
                        velocity.Linear *= 0.1f;
                        velocity.Angular = float3.zero;
                        ecb.SetComponent(entity, velocity);
                    }
                }
            }

            //-----------------------------------------------------
            // 4) PhysicsDamping (opcional)
            //-----------------------------------------------------
            if (!state.EntityManager.HasComponent<PhysicsDamping>(entity))
            {
                ecb.AddComponent(entity, new PhysicsDamping
                {
                    Linear = 0.0f,
                    Angular = 10.0f
                });
            }

            //-----------------------------------------------------
            // 5) Aplicar los cambios
            //-----------------------------------------------------
            ecb.SetComponent(entity, transform.ValueRW);
            ecb.SetComponent(entity, ecoli.ValueRW);
        }

        ecb.Playback(state.EntityManager);
        ecb.Dispose();
    }
}
