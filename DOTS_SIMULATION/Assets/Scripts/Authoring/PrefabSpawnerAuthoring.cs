using UnityEngine;
using Unity.Entities;
using System.Collections.Generic;

public class PrefabSpawnerAuthoring : MonoBehaviour {}

class PrefabSpawnerBaker : Baker<PrefabSpawnerAuthoring>
{
    public override void Bake(PrefabSpawnerAuthoring authoring)
    {
        GameObject[] loadedPrefabs = Resources.LoadAll<GameObject>("Prefabs");
        if (loadedPrefabs.Length == 0)
        {
            Debug.LogError("PrefabSpawnerAuthoring: No se encontraron prefabs en Resources/Prefabs.");
            return;
        }
        
        foreach (var prefab in loadedPrefabs)
        {
            Entity entity = CreateAdditionalEntity(TransformUsageFlags.None);
            AddComponent(entity, new PrefabEntityComponent
            {
                prefab = GetEntity(prefab, TransformUsageFlags.Dynamic)
            });
            // No se puede usar SetName directamente en Baker. Unity no lo permite en este contexto.
            Debug.Log("PrefabSpawnerAuthoring: Entidad creada para " + prefab.name);
        }
    }
}

public struct PrefabEntityComponent : IComponentData
{
    public Entity prefab;
}
