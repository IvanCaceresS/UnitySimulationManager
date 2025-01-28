using Unity.Entities;
using Unity.Transforms;
using Unity.Mathematics;
using Unity.Physics;

namespace ECS
{
    public partial struct EColiSpawnerSystem : ISystem
    {
        public void OnUpdate(ref SystemState state)
        {
            if (!SystemAPI.TryGetSingletonEntity<EColiSpawnerComponent>(out Entity spawnerEntity))
                return;

            var spawner = SystemAPI.GetComponent<EColiSpawnerComponent>(spawnerEntity);

            // Verificar si ya existen entidades con EColiTag
            bool hasEColiEntities = SystemAPI.QueryBuilder()
                                             .WithAll<EColiTag>()
                                             .Build()
                                             .CalculateEntityCount() > 0;

            // Si no existen entidades EColi, crear una nueva
            if (!hasEColiEntities)
            {
                // Instanciar la entidad a partir del prefab
                Entity eColi = state.EntityManager.Instantiate(spawner.prefab);

                // Configurar su transformación inicial
                state.EntityManager.AddComponentData(eColi, new LocalTransform
                {
                    Position = new float3(0f, 0.5f, 0f), // Posición inicial elevada
                    Rotation = quaternion.Euler(math.radians(90f), 0f, 0f),
                    Scale = 0.01f // Escala inicial
                });

                // Añadir etiqueta para identificarla como EColi
                state.EntityManager.AddComponent<EColiTag>(eColi);

                // Añadir el componente GrowthComponent para crecimiento
                state.EntityManager.AddComponentData(eColi, new GrowthComponent
                {
                    GrowthRate = 0.2f,
                    MaxScale = 1.0f,
                    TimeSinceLastDivision = 0f,
                    DivisionInterval = 5.0f, // 5 segundos entre divisiones
                    GrowthTime = 0f,
                    GrowthDuration = 12f, // Duración del crecimiento
                    HasGeneratedChild = false
                });

                // Crear un CapsuleCollider con parámetros ajustados para colisiones
                BlobAssetReference<Unity.Physics.Collider> capsuleCollider = Unity.Physics.CapsuleCollider.Create(
                    new CapsuleGeometry
                    {
                        Vertex0 = new float3(0, -0.5f, 0),
                        Vertex1 = new float3(0, 0.5f, 0),
                        Radius = 0.3f
                    }
                );

                // Añadir el PhysicsCollider
                state.EntityManager.AddComponentData(eColi, new PhysicsCollider
                {
                    Value = capsuleCollider
                });

                // Configurar masa dinámica con mayor resistencia a giros
                var massProperties = capsuleCollider.Value.MassProperties;
                var physicsMass = PhysicsMass.CreateDynamic(massProperties, 1f);
                physicsMass.InverseInertia = new float3(0.05f, 0.05f, 0.05f); // Reducir susceptibilidad a rotación
                state.EntityManager.AddComponentData(eColi, physicsMass);

                // Añadir velocidad inicial con valores limitados
                state.EntityManager.AddComponentData(eColi, new PhysicsVelocity
                {
                    Linear = float3.zero, // Sin movimiento inicial
                    Angular = float3.zero // Sin rotación inicial
                });

                // Configurar el factor de gravedad bajo (simula medio viscoso)
                state.EntityManager.AddComponentData(eColi, new PhysicsGravityFactor { Value = 0.1f });

                // Log para confirmar la creación
                UnityEngine.Debug.Log($"EColi entity created with physics in World: {state.World.Name}");
            }
        }
    }
}
