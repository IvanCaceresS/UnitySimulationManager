#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using System.IO;
public static class PrefabMaterialCreator
{
    private const string prefabFolder="Assets/Resources/Prefabs";
    private const string materialFolder="Assets/Resources/PrefabsMaterials";
    [MenuItem("Tools/Crear Prefabs y Materiales")]public static void CreatePrefabsAndMaterials()
    {
        if(!AssetDatabase.IsValidFolder(prefabFolder))
        {
            AssetDatabase.CreateFolder("Assets/Resources","Prefabs");
            Debug.Log("Carpeta creada: "+prefabFolder);
        }
        if(!AssetDatabase.IsValidFolder(materialFolder))
        {
            AssetDatabase.CreateFolder("Assets/Resources","PrefabsMaterials");
            Debug.Log("Carpeta creada: "+materialFolder);
        }
        CreatePrefabAndMaterial("SCerevisiae",PrimitiveType.Sphere,new Vector3(5f,5f,5f),new Vector3(90f,0f,0f),ColliderType.Sphere);
        CreatePrefabAndMaterial("EColi",PrimitiveType.Capsule,new Vector3(0.5f,2f,0.5f),new Vector3(90f,0f,0f),ColliderType.Capsule);
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log("Prefabs y materiales creados exitosamente.");
    }
    private enum ColliderType
    {
        Sphere,Capsule
    }
    private static void CreatePrefabAndMaterial(string name,PrimitiveType primitiveType,Vector3 scale,Vector3 rotation,ColliderType colliderType)
    {
        GameObject obj=GameObject.CreatePrimitive(primitiveType);
        obj.name=name;
        obj.transform.rotation=Quaternion.Euler(rotation);
        obj.transform.localScale=scale;
        Collider existingCollider=obj.GetComponent<Collider>();
        if(existingCollider!=null)Object.DestroyImmediate(existingCollider);
        switch(colliderType)
        {
            case ColliderType.Sphere:obj.AddComponent<SphereCollider>();
            break;
            case ColliderType.Capsule:obj.AddComponent<CapsuleCollider>();
            break;
        }
        Shader shader=Shader.Find("Universal Render Pipeline/Lit");
        if(shader==null)
        {
            Debug.LogError("Shader 'Universal Render Pipeline/Lit' no se encontró. Asegúrate de que URP esté instalado y configurado.");
            return;
        }
        Material mat=new Material(shader);
        if(name=="SCerevisiae")mat.color = new Color(0f, 0f, 1f, 1f);
        else if(name=="EColi")mat.color = new Color(0f, 1f, 0f, 1f);
        else mat.color = new Color(1f, 1f, 1f, 1f);
        string matPath=Path.Combine(materialFolder,name+".mat");
        AssetDatabase.CreateAsset(mat,matPath);
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Renderer renderer=obj.GetComponent<Renderer>();
        if(renderer!=null)renderer.sharedMaterial=mat;
        string prefabPath=Path.Combine(prefabFolder,name+".prefab");
        PrefabUtility.SaveAsPrefabAsset(obj,prefabPath);
        Object.DestroyImmediate(obj);
    }
}
#endif
