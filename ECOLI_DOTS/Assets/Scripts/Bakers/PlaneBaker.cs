using Unity.Entities;
using Unity.Physics;

public class PlaneBaker : Baker<PlaneAuthoring>
{
    public override void Bake(PlaneAuthoring authoring)
    {
        var entity = GetEntity(TransformUsageFlags.None);

        // Crear un material de física con alta fricción
        Unity.Physics.Material material = new Unity.Physics.Material
        {
            Friction = 1.0f, // Alta fricción para evitar deslizamientos
            Restitution = 0.0f // Rebote bajo
        };

        // Crear un PhysicsCollider para el plano
        var collider = Unity.Physics.BoxCollider.Create(
            new Unity.Physics.BoxGeometry
            {
                Center = Unity.Mathematics.float3.zero,
                Size = new Unity.Mathematics.float3(100f, 0.1f, 100f), // Ajustar tamaño del plano
                Orientation = Unity.Mathematics.quaternion.identity
            },
            CollisionFilter.Default, // Usar filtro de colisión por defecto
            material // Asignar el material con alta fricción
        );

        // Añadir el PhysicsCollider al plano
        AddComponent(entity, new PhysicsCollider
        {
            Value = collider
        });

        // Añadir un componente de masa infinita para que el plano sea estático
        AddComponent(entity, new Unity.Physics.PhysicsMass
        {
            InverseMass = 0f // Estático
        });
    }
}
