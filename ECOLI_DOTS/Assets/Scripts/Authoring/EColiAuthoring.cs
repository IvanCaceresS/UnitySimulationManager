using UnityEngine;
using Unity.Entities;
using ECS;


public class EColiAuthoring : MonoBehaviour
{
    public float GrowthRate = 0.01f; // Velocidad de crecimiento
    public float MaxScale = 1f; // Tamaño máximo
}

public class EColiBaker : Baker<EColiAuthoring>
{
    public override void Bake(EColiAuthoring authoring)
    {
        var entity = GetEntity(TransformUsageFlags.Dynamic);

        // Añadir el componente de crecimiento
        AddComponent(entity, new GrowthComponent
        {
            GrowthRate = authoring.GrowthRate,
            MaxScale = authoring.MaxScale,
            HasGeneratedChild = false
        });

        // Añadir la etiqueta de EColi
        AddComponent<EColiTag>(entity);
    }
}

// Componente de crecimiento
public struct GrowthComponent : IComponentData
{
    public float GrowthRate; // Velocidad de crecimiento
    public float MaxScale; // Escala máxima
    public bool HasGeneratedChild; // Flag para evitar duplicaciones repetidas
}

