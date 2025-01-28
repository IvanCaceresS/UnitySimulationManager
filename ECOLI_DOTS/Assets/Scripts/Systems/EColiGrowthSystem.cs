using Unity.Entities;
using Unity.Transforms;
using Unity.Mathematics;
using Unity.Physics;
using Unity.Physics.Extensions;
using UnityEngine;

namespace ECS
{
    public partial struct EColiGrowthAndDivisionSystem : ISystem
    {
        public void OnUpdate(ref SystemState state)
        {
            var ecb = new EntityCommandBuffer(Unity.Collections.Allocator.Temp);
            var deltaTime = SystemAPI.Time.DeltaTime;

            foreach (var (transform, growth, entity) in SystemAPI.Query<RefRW<LocalTransform>, RefRW<GrowthComponent>>().WithEntityAccess().WithAll<EColiTag>())
            {
                // Crecimiento de la célula madre
                if (transform.ValueRW.Scale < growth.ValueRW.MaxScale)
                {
                    growth.ValueRW.GrowthTime += deltaTime; // Incrementar el tiempo de crecimiento
                    if (growth.ValueRW.GrowthTime <= growth.ValueRW.GrowthDuration)
                    {
                        transform.ValueRW.Scale += growth.ValueRW.GrowthRate * deltaTime;
                        transform.ValueRW.Scale = math.min(transform.ValueRW.Scale, growth.ValueRW.MaxScale);
                    }

                    // Aplicar fuerza física durante el crecimiento
                    if (state.EntityManager.HasComponent<PhysicsVelocity>(entity))
                    {
                        var velocity = state.EntityManager.GetComponentData<PhysicsVelocity>(entity);
                        velocity.Linear += math.up() * 0.1f * deltaTime; // Empujar ligeramente hacia arriba
                        state.EntityManager.SetComponentData(entity, velocity);
                    }
                }

                // Control de división: solo genera hija si está completamente crecida
                if (transform.ValueRW.Scale >= growth.ValueRW.MaxScale)
                {
                    growth.ValueRW.TimeSinceLastDivision += deltaTime;

                    if (growth.ValueRW.TimeSinceLastDivision >= growth.ValueRW.DivisionInterval)
                    {
                        // Crear célula hija
                        Entity newEColi = ecb.Instantiate(entity);

                        // Configurar Transform inicial de la hija
                        var newTransform = transform.ValueRW;
                        newTransform.Scale = 0.01f; // La hija comienza pequeña
                        newTransform.Position = transform.ValueRW.Position + math.up() * (transform.ValueRW.Scale * 0.25f); // Posición inicial en el eje Y
                        ecb.SetComponent(newEColi, newTransform);

                        // Configurar el componente GrowthComponent de la hija
                        ecb.SetComponent(newEColi, new GrowthComponent
                        {
                            GrowthRate = growth.ValueRW.GrowthRate,
                            MaxScale = growth.ValueRW.MaxScale,
                            TimeSinceLastDivision = 0f,
                            DivisionInterval = growth.ValueRW.DivisionInterval,
                            GrowthTime = 0f,
                            GrowthDuration = growth.ValueRW.GrowthDuration,
                            HasGeneratedChild = false,
                            Parent = entity // Vincular hija a madre
                        });

                        // Reiniciar el tiempo de división de la madre
                        growth.ValueRW.TimeSinceLastDivision = 0f;
                    }
                }

                // Mantener a la hija unida al padre y desplazarla gradualmente hacia el extremo
                if (growth.ValueRW.Parent != Entity.Null)
                {
                    var parentTransform = SystemAPI.GetComponent<LocalTransform>(growth.ValueRW.Parent);

                    if (transform.ValueRW.Scale < 0.7f * growth.ValueRW.MaxScale)
                    {
                        // Desplazamiento progresivo hacia el extremo de la madre en el eje Y
                        float progress = transform.ValueRW.Scale / (0.7f * growth.ValueRW.MaxScale);
                        float offset = math.lerp(parentTransform.Scale * -2.0f, parentTransform.Scale * 3.25f, progress); // Desplazamiento progresivo
                        float3 up = math.mul(parentTransform.Rotation, new float3(0f, 1f, 0f)); // Eje Y
                        transform.ValueRW.Position = parentTransform.Position + up * offset; // Desplazar en el eje Y
                        transform.ValueRW.Rotation = parentTransform.Rotation; // Alinear rotación con el padre
                        ecb.SetComponent(entity, transform.ValueRW);
                    }
                    else
                    {
                        // Separar a la hija completamente al alcanzar el 70% de su tamaño
                        growth.ValueRW.Parent = Entity.Null; // Desvincular de la madre

                        // Reducir velocidad al separar
                        if (state.EntityManager.HasComponent<PhysicsVelocity>(entity))
                        {
                            var velocity = state.EntityManager.GetComponentData<PhysicsVelocity>(entity);
                            velocity.Linear *= 0.1f; // Reducir velocidad lineal al 10%
                            velocity.Angular *= 0.0f; // Reducir rotación al 0%
                            ecb.SetComponent(entity, velocity);
                        }
                    }
                }

                // Configurar amortiguación para simular viscosidad
                if (!state.EntityManager.HasComponent<PhysicsDamping>(entity))
                {
                    ecb.AddComponent(entity, new PhysicsDamping
                    {
                        Linear = 0.0f, // Amortiguación lineal (resistencia al movimiento)
                        Angular = 10.0f // Amortiguación angular (resistencia a rotaciones)
                    });
                }
            }

            ecb.Playback(state.EntityManager);
            ecb.Dispose();
        }
    }

    public struct GrowthComponent : IComponentData
    {
        public float GrowthRate; // Velocidad de crecimiento
        public float MaxScale; // Tamaño máximo
        public float TimeSinceLastDivision; // Tiempo desde la última división
        public float DivisionInterval; // Intervalo entre divisiones (2400 frames)
        public float GrowthTime; // Tiempo actual de crecimiento
        public float GrowthDuration; // Duración del crecimiento (1200 frames)
        public bool HasGeneratedChild; // Bandera para controlar la generación
        public Entity Parent; // Referencia a la célula madre
    }
}
