using Unity.Burst;
using Unity.Entities;
using Unity.Transforms;
using Unity.Mathematics;
using Unity.Physics;            // Quita si no usas DOTS Physics
using Unity.Physics.Extensions; // Quita si no usas DOTS Physics
using UnityEngine;              // Para algunos helpers

[BurstCompile]
public partial struct EColiSystem : ISystem
{
    // Umbral para actualizar el collider (solo se recrea si la diferencia en escala es mayor que este valor)
    const float ColliderUpdateThreshold = 0.01f;
 
    public void OnCreate(ref SystemState state) { }
    public void OnDestroy(ref SystemState state) { }
    
    public void OnUpdate(ref SystemState state)
    {
        // Solo se procesa si la simulación está lista y no está pausada
        if (!GameStateManager.IsSetupComplete || GameStateManager.IsPaused)
            return;
        
        float simDeltaTime = GameStateManager.DeltaTime;
        var entityManager = state.EntityManager;
        var ecb = new EntityCommandBuffer(Unity.Collections.Allocator.Temp);
        
        // Itera sobre todas las entidades con LocalTransform y EColiComponent
        foreach (var (transform, ecoli, entity) in SystemAPI
                 .Query<RefRW<LocalTransform>, RefRW<EColiComponent>>()
                 .WithEntityAccess())
        {
            // Actualiza GrowthDuration y DivisionInterval en función de TimeReference y SeparationThreshold
            ecoli.ValueRW.GrowthDuration = ecoli.ValueRO.TimeReference * ecoli.ValueRO.SeparationThreshold;
            ecoli.ValueRW.DivisionInterval = ecoli.ValueRW.GrowthDuration;
 
            float currentScale = transform.ValueRO.Scale;
            float maxScale = ecoli.ValueRO.MaxScale;
            bool isIndependent = (ecoli.ValueRO.Parent == default); // Padre es Entity.Null.
            bool hasCollider = entityManager.HasComponent<PhysicsCollider>(entity);
            bool hasVelocity = entityManager.HasComponent<PhysicsVelocity>(entity);
 
            // --- 1) Crecimiento ---
            if (currentScale < maxScale)
            {
                ecoli.ValueRW.GrowthTime += simDeltaTime;
                // Para células hijas se parte de 0.01; para iniciales, ya nacen completas.
                float initialScale = ecoli.ValueRO.IsInitialCell ? maxScale : 0.01f;
 
                if (ecoli.ValueRW.GrowthTime <= ecoli.ValueRO.GrowthDuration)
                {
                    float t = ecoli.ValueRW.GrowthTime / ecoli.ValueRO.GrowthDuration;
                    float newScale = math.lerp(initialScale, maxScale, t);
                    transform.ValueRW.Scale = newScale;
 
                    // Actualiza el collider solo si la célula es independiente y el cambio es significativo.
                    if (isIndependent && hasCollider && math.abs(newScale - currentScale) > ColliderUpdateThreshold)
                    {
                        BlobAssetReference<Unity.Physics.Collider> newCollider =
                            Unity.Physics.CapsuleCollider.Create(new CapsuleGeometry
                            {
                                Vertex0 = new float3(0, -newScale * 2.0f, 0),
                                Vertex1 = new float3(0, newScale * 2.0f, 0),
                                Radius  = newScale * 0.25f
                            });
                        ecb.SetComponent(entity, new PhysicsCollider { Value = newCollider });
                    }
                }
 
                // Aplica un impulso hacia arriba solo si la célula es independiente.
                if (isIndependent && hasVelocity)
                {
                    var velocity = entityManager.GetComponentData<PhysicsVelocity>(entity);
                    velocity.Linear += new float3(0, 1, 0) * 0.1f * simDeltaTime;
                    velocity.Linear.y = math.clamp(velocity.Linear.y, -1f, 0.0f);
                    ecb.SetComponent(entity, velocity);
                }
            }
 
            // --- 2) División: creación de la hija ---
            if (transform.ValueRO.Scale >= maxScale)
            {
                ecoli.ValueRW.TimeSinceLastDivision += simDeltaTime;
                if (ecoli.ValueRO.TimeSinceLastDivision >= ecoli.ValueRO.DivisionInterval)
                {
                    Entity childEntity = ecb.Instantiate(entity);
                    
                    // Configura el transform de la hija: inicia con escala pequeña.
                    var childTransform = transform.ValueRO;
                    childTransform.Scale = 0.01f;
                    
                    // Fijar la dirección "up" de la hija de forma aleatoria (50%: (0,1,0); 50%: (0,-1,0)).
                    int separationSign = (UnityEngine.Random.value < 0.5f) ? 1 : -1;
                    
                    // Configura los datos de la hija, reiniciando GrowthTime y TimeSinceLastDivision, asignando el padre.
                    var childData = ecoli.ValueRW;
                    childData.GrowthTime = 0f;
                    childData.TimeSinceLastDivision = 0f;
                    childData.HasGeneratedChild = false;
                    childData.Parent = entity;  // La hija conserva al padre.
                    childData.IsInitialCell = false;
                    childData.SeparationSign = separationSign;
                    ecb.SetComponent(childEntity, childData);
                    
                    // Posiciona la hija usando la dirección fija.
                    float3 localUp = new float3(0, separationSign, 0);
                    float3 upDir = math.mul(transform.ValueRO.Rotation, localUp);
                    childTransform.Position = transform.ValueRO.Position + upDir * (transform.ValueRO.Scale * 0.25f);
                    ecb.SetComponent(childEntity, childTransform);
                    
                    ecoli.ValueRW.TimeSinceLastDivision = 0f;
                }
            }
 
            // --- 3) Lógica de anclaje: separación progresiva ---
            if (!ecoli.ValueRO.IsInitialCell && ecoli.ValueRO.Parent != default)
            {
                var parentTransform = SystemAPI.GetComponent<LocalTransform>(ecoli.ValueRO.Parent);
                float childScale = transform.ValueRO.Scale;
                float threshold = ecoli.ValueRO.SeparationThreshold; // Ej.: 0.7 (70%)
                
                if (childScale < threshold * maxScale)
                {
                    float progress = childScale / maxScale;
                    float offset = math.lerp(0f, parentTransform.Scale * 4.9f, progress);
                    // Usa la dirección almacenada (fijada al nacer) para que no cambie durante el crecimiento.
                    int separationSign = ecoli.ValueRO.SeparationSign;
                    float3 localUp = new float3(0, separationSign, 0);
                    float3 up = math.mul(parentTransform.Rotation, localUp);
                    
                    transform.ValueRW.Position = parentTransform.Position + up * offset;
                    transform.ValueRW.Rotation = parentTransform.Rotation;
                    ecb.SetComponent(entity, transform.ValueRW);
                }
                else
                {
                    // Libera el anclaje.
                    ecoli.ValueRW.Parent = default;
                    
                    if (hasVelocity)
                    {
                        var velocity = entityManager.GetComponentData<PhysicsVelocity>(entity);
                        velocity.Linear *= 0.1f;
                        velocity.Angular = float3.zero;
                        ecb.SetComponent(entity, velocity);
                    }
                    
                    if (hasCollider)
                    {
                        BlobAssetReference<Unity.Physics.Collider> newCollider =
                            Unity.Physics.CapsuleCollider.Create(new CapsuleGeometry
                            {
                                Vertex0 = new float3(0, -transform.ValueRO.Scale * 2.0f, 0),
                                Vertex1 = new float3(0, transform.ValueRO.Scale * 2.0f, 0),
                                Radius  = transform.ValueRO.Scale * 0.25f
                            });
                        ecb.SetComponent(entity, new PhysicsCollider { Value = newCollider });
                    }
                }
            }
 
            // --- 4) PhysicsDamping (opcional) ---
            if (!entityManager.HasComponent<PhysicsDamping>(entity))
            {
                ecb.AddComponent(entity, new PhysicsDamping { Linear = 0.0f, Angular = 10.0f });
            }
 
            ecb.SetComponent(entity, transform.ValueRW);
            ecb.SetComponent(entity, ecoli.ValueRW);
        }
 
        ecb.Playback(entityManager);
        ecb.Dispose();
    }
}
