using Unity.Entities;
using UnityEngine;

namespace ECS
{
    public class EColiSpawnerAuthoring : MonoBehaviour
    {
        public GameObject prefab;
    }

    public class EColiSpawnerBaker : Baker<EColiSpawnerAuthoring>
    {
        public override void Bake(EColiSpawnerAuthoring authoring)
        {
            Entity entity = GetEntity(TransformUsageFlags.None);

            AddComponent(entity, new EColiSpawnerComponent
            {
                prefab = GetEntity(authoring.prefab, TransformUsageFlags.Dynamic)
            });
        }
    }

    public struct EColiSpawnerComponent : IComponentData
    {
        public Entity prefab;
    }
}
