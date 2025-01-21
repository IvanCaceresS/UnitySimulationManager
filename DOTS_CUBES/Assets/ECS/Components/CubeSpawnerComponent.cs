using Unity.Entities;
using Unity.Mathematics;

public struct CubeSpawnerComponent : IComponentData
{
    public Entity prefab;
    public float3 spawnPos;
    public float nextSpawnTime;
    public float spawnRate;
}