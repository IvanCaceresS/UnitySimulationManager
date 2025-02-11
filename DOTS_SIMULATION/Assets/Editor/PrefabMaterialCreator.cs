#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using System.IO;

public static class PrefabMaterialCreator
{
    // Rutas donde se guardarán los prefabs y materiales
    private const string prefabFolder = "Assets/Resources/Prefabs";
    private const string materialFolder = "Assets/Resources/PrefabsMaterials";

    [MenuItem("Tools/Crear Prefabs y Materiales")]
    public static void CreatePrefabsAndMaterials()
    {
        // Crear las carpetas si no existen
        if (!AssetDatabase.IsValidFolder(prefabFolder))
        {
            AssetDatabase.CreateFolder("Assets/Resources", "Prefabs");
            Debug.Log("Carpeta creada: " + prefabFolder);
        }
        if (!AssetDatabase.IsValidFolder(materialFolder))
        {
            AssetDatabase.CreateFolder("Assets/Resources", "PrefabsMaterials");
            Debug.Log("Carpeta creada: " + materialFolder);
        }

        // Crear cada prefab y su material asociado
        CreatePrefabAndMaterial("Cube", PrimitiveType.Cube, new Vector3(1f, 1f, 1f), new Vector3(90f, 0f, 0f), ColliderType.Box);
        CreatePrefabAndMaterial("SCerevisiae", PrimitiveType.Sphere, new Vector3(5f, 5f, 5f), new Vector3(90f, 0f, 0f), ColliderType.Sphere);
        CreatePrefabAndMaterial("EColi", PrimitiveType.Capsule, new Vector3(0.5f, 2f, 0.5f), new Vector3(90f, 0f, 0f), ColliderType.Capsule);

        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log("Prefabs y materiales creados exitosamente.");
    }

    // Enumeración para seleccionar el tipo de collider
    private enum ColliderType { Box, Sphere, Capsule }

    private static void CreatePrefabAndMaterial(string name, PrimitiveType primitiveType, Vector3 scale, Vector3 rotation, ColliderType colliderType)
    {
        // Crear el objeto primitivo
        GameObject obj = GameObject.CreatePrimitive(primitiveType);
        obj.name = name;
        obj.transform.rotation = Quaternion.Euler(rotation);
        obj.transform.localScale = scale;

        // Eliminar el collider que crea CreatePrimitive (por seguridad) y agregar el deseado
        Collider existingCollider = obj.GetComponent<Collider>();
        if (existingCollider != null)
            Object.DestroyImmediate(existingCollider);

        switch (colliderType)
        {
            case ColliderType.Box:
                obj.AddComponent<BoxCollider>();
                break;
            case ColliderType.Sphere:
                obj.AddComponent<SphereCollider>();
                break;
            case ColliderType.Capsule:
                obj.AddComponent<CapsuleCollider>();
                break;
        }

        // Crear el material usando el shader URP Lit
        Shader shader = Shader.Find("Universal Render Pipeline/Lit");
        if (shader == null)
        {
            Debug.LogError("Shader 'Universal Render Pipeline/Lit' no se encontró. Asegúrate de que URP esté instalado y configurado.");
            return;
        }
        Material mat = new Material(shader);
        // Asignar color según el nombre
        if (name == "Cube")
            mat.color = Color.red;
        else if (name == "SCerevisiae")
            mat.color = Color.blue;
        else if (name == "EColi")
            mat.color = Color.green;
        else
            mat.color = Color.white;

        // Guardar el material en Assets/Resources/PrefabsMaterials
        string matPath = Path.Combine(materialFolder, name + ".mat");
        AssetDatabase.CreateAsset(mat, matPath);
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();

        // Asignar el material al Renderer del objeto
        Renderer renderer = obj.GetComponent<Renderer>();
        if (renderer != null)
            renderer.sharedMaterial = mat;

        // Guardar el objeto como prefab en Assets/Resources/Prefabs
        string prefabPath = Path.Combine(prefabFolder, name + ".prefab");
        PrefabUtility.SaveAsPrefabAsset(obj, prefabPath);

        // Destruir el objeto de la escena
        Object.DestroyImmediate(obj);
    }
}
#endif
