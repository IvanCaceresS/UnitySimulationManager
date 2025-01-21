using Unity.Entities;
using UnityEngine;

namespace ECS
{
    public class CubeSpawnerAuthoring : MonoBehaviour
    {
        public GameObject prefab;
        public float spawnRate;
    }

    class CubeSpawnerBaker : Baker<CubeSpawnerAuthoring>
    {
        public override void Bake(CubeSpawnerAuthoring authoring)
        {
            Entity entity = GetEntity(TransformUsageFlags.None);

            AddComponent(entity, new CubeSpawnerComponent
            {
                prefab = GetEntity(authoring.prefab, TransformUsageFlags.Dynamic),
                spawnPos = authoring.transform.position,
                nextSpawnTime = 0.0f,
                spawnRate = authoring.spawnRate
            });
        }
    }
}