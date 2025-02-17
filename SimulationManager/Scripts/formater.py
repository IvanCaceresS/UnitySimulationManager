import os
import re
import sys

def split_braces_outside_strings(code: str) -> str:
    """
    Inserta saltos de línea antes y después de '{' y '}' solo cuando estamos fuera de un string en C#.
    """
    result_lines = []
    in_string = False  # Detectamos si estamos dentro de comillas dobles

    for line in code.splitlines(keepends=True):
        new_line_chars = []
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '"':
                in_string = not in_string
                new_line_chars.append(ch)
            elif ch == '{' and not in_string:
                new_line_chars.append('\n{\n')
            elif ch == '}' and not in_string:
                new_line_chars.append('\n}\n')
            else:
                new_line_chars.append(ch)
            i += 1
        result_lines.append(''.join(new_line_chars))
    return ''.join(result_lines)

def separar_codigos_por_archivo(respuesta: str) -> dict:
    """
    Separa la respuesta en bloques de código asignados a cada archivo y formatea el contenido.
    :param respuesta: Cadena con la respuesta del modelo.
    :return: Diccionario con los nombres de los archivos y sus contenidos formateados.
    """
    patrones = re.findall(r'(\d+)\.(\w+\.cs)\{(.*?)}(?=\d+\.|$)', respuesta, re.DOTALL)
    if not patrones:
        print("No se encontraron bloques de código en la respuesta.")
        return {}
    
    codigos = {}
    for _, archivo, contenido in patrones:
        codigos[archivo] = format_csharp(contenido.strip())
    return codigos

def format_csharp(contenido: str) -> str:
    """
    Formatea el contenido para C# aplicando indentación adecuada y separación de bloques.
    :param contenido: Código C# sin formatear.
    :return: Código C# formateado.
    """
    # 1. Separar llaves solo fuera de strings
    preprocesado = split_braces_outside_strings(contenido)
    # 2. Insertar salto de línea después de ';'
    preprocesado = re.sub(r';', r';\n', preprocesado)
    # 3. Eliminar dobles saltos de línea
    preprocesado = re.sub(r'\n\s*\n', '\n', preprocesado)
    # 4. Ajustar indentación
    lineas = [l.strip() for l in preprocesado.split('\n') if l.strip()]
    nivel_indentacion = 0
    contenido_formateado = []
    for linea in lineas:
        if linea.startswith("}"):
            nivel_indentacion = max(nivel_indentacion - 1, 0)
        contenido_formateado.append("    " * nivel_indentacion + linea)
        if linea.endswith("{"):
            nivel_indentacion += 1
    return "\n".join(contenido_formateado)

def main():
    """
    1. Recibe el string completo de la respuesta como argumento.
    2. Separa los bloques de código y los formatea.
    3. Imprime el diccionario resultante con los nombres de archivo y su contenido.
    """
    if len(sys.argv) < 2:
        print("Uso: formater.py STRING")
        return

    #respuesta = sys.argv[1]
    respuesta = "1.PrefabMaterialCreator.cs{public static class PrefabMaterialCreator{private const string prefabFolder=\"Assets/Resources/Prefabs\";private const string materialFolder=\"Assets/Resources/PrefabsMaterials\";[MenuItem(\"Tools/Crear Prefabs y Materiales\")]public static void CreatePrefabsAndMaterials(){if(!AssetDatabase.IsValidFolder(prefabFolder)){AssetDatabase.CreateFolder(\"Assets/Resources\",\"Prefabs\");Debug.Log(\"Carpeta creada: \"+prefabFolder);}if(!AssetDatabase.IsValidFolder(materialFolder)){AssetDatabase.CreateFolder(\"Assets/Resources\",\"PrefabsMaterials\");Debug.Log(\"Carpeta creada: \"+materialFolder);}CreatePrefabAndMaterial(\"SCerevisiae\",PrimitiveType.Sphere,new Vector3(5f,5f,5f),new Vector3(90f,0f,0f),ColliderType.Sphere);CreatePrefabAndMaterial(\"EColi\",PrimitiveType.Capsule,new Vector3(0.5f,2f,0.5f),new Vector3(90f,0f,0f),ColliderType.Capsule);AssetDatabase.SaveAssets();AssetDatabase.Refresh();Debug.Log(\"Prefabs y materiales creados exitosamente.\");}private enum ColliderType{Sphere,Capsule}private static void CreatePrefabAndMaterial(string name,PrimitiveType primitiveType,Vector3 scale,Vector3 rotation,ColliderType colliderType){GameObject obj=GameObject.CreatePrimitive(primitiveType);obj.name=name;obj.transform.rotation=Quaternion.Euler(rotation);obj.transform.localScale=scale;Collider existingCollider=obj.GetComponent<Collider>();if(existingCollider!=null)Object.DestroyImmediate(existingCollider);switch(colliderType){case ColliderType.Sphere:obj.AddComponent<SphereCollider>();break;case ColliderType.Capsule:obj.AddComponent<CapsuleCollider>();break;}Shader shader=Shader.Find(\"Universal Render Pipeline/Lit\");if(shader==null){Debug.LogError(\"Shader 'Universal Render Pipeline/Lit' no se encontró. Asegúrate de que URP esté instalado y configurado.\");return;}Material mat=new Material(shader);if(name==\"SCerevisiae\")mat.color = new Color(0f, 0f, 1f, 1f);else if(name==\"EColi\")mat.color = new Color(0f, 1f, 0f, 1f);else mat.color = new Color(1f, 1f, 1f, 1f);string matPath=Path.Combine(materialFolder,name+\".mat\");AssetDatabase.CreateAsset(mat,matPath);AssetDatabase.SaveAssets();AssetDatabase.Refresh();Renderer renderer=obj.GetComponent<Renderer>();if(renderer!=null)renderer.sharedMaterial=mat;string prefabPath=Path.Combine(prefabFolder,name+\".prefab\");PrefabUtility.SaveAsPrefabAsset(obj,prefabPath);Object.DestroyImmediate(obj);}}}2.CreatePrefabsOnClick.cs{private void CrearEntidad(Vector3 position){if(currentPrefabIndex>=prefabs.Count)return;NativeArray<Entity>spawnerEntities=spawnerQuery.ToEntityArray(Allocator.Temp);if(currentPrefabIndex>=spawnerEntities.Length){Debug.LogError($\"No se encontró spawner en índice {currentPrefabIndex}\");spawnerEntities.Dispose();return;}Entity spawner=spawnerEntities[currentPrefabIndex];spawnerEntities.Dispose();Entity prefabEntity=entityManager.GetComponentData<PrefabEntityComponent>(spawner).prefab;Entity entity=entityManager.Instantiate(prefabEntity);float originalScale=entityManager.GetComponentData<LocalTransform>(prefabEntity).Scale;quaternion originalRotation=entityManager.GetComponentData<LocalTransform>(prefabEntity).Rotation;float randYRot=UnityEngine.Random.Range(0f,360f);quaternion newRotation=math.mul(originalRotation,quaternion.RotateY(math.radians(randYRot)));float heightOffset=originalScale*0.5f;float3 adjustedPosition=new float3(position.x,math.max(position.y+heightOffset,heightOffset),position.z);entityManager.SetComponentData(entity,new LocalTransform{Position=adjustedPosition,Rotation=newRotation,Scale=originalScale});string prefabName=prefabs[currentPrefabIndex].name;switch(prefabName){case\"EColi\":entityManager.AddComponentData(entity,new EColiComponent{TimeReference=1200f,SeparationThreshold=0.7f,MaxScale=1.0f,GrowthTime=0f,GrowthDuration=1200f*0.7f,TimeSinceLastDivision=0f,DivisionInterval=1200f*0.7f,HasGeneratedChild=false,Parent=Entity.Null,IsInitialCell=true,SeparationSign=0});break;case\"SCerevisiae\":entityManager.AddComponentData(entity,new SCerevisiaeComponent{TimeReference=5400f,SeparationThreshold=0.7f,MaxScale=5.0f,GrowthTime=0f,GrowthDuration=5400f*0.7f,TimeSinceLastDivision=0f,DivisionInterval=5400f*0.7f,HasGeneratedChild=false,Parent=Entity.Null,IsInitialCell=true,SeparationSign=0});break;default:Debug.LogWarning($\"No hay componente ECS para '{prefabName}'\");break;}AddPhysicsComponents(entity,prefabName,originalScale);Debug.Log($\"Entidad '{prefabName}' creada en {adjustedPosition}\");}private void AddPhysicsComponents(Entity entity,string prefabName,float scale){BlobAssetReference<Unity.Physics.Collider>collider=default;Material mat=new Material{Friction=8f,Restitution=0f};switch(prefabName){case\"EColi\":collider=Unity.Physics.CapsuleCollider.Create(new CapsuleGeometry{Vertex0=new float3(0,-scale,0),Vertex1=new float3(0,scale,0),Radius=0.25f},CollisionFilter.Default,mat);break;case\"SCerevisiae\":collider=Unity.Physics.SphereCollider.Create(new SphereGeometry{Center=float3.zero,Radius=scale*0.1f},CollisionFilter.Default,mat);break;default:Debug.LogWarning($\"No collider para '{prefabName}'\");return;}entityManager.AddComponentData(entity,new PhysicsCollider{Value=collider});if(collider.IsCreated){var massProps=collider.Value.MassProperties;entityManager.AddComponentData(entity,PhysicsMass.CreateDynamic(massProps,1f));}entityManager.AddComponentData(entity,new PhysicsVelocity{Linear=float3.zero,Angular=float3.zero});entityManager.AddComponentData(entity,new PhysicsGravityFactor{Value=1f});entityManager.AddComponentData(entity,new PhysicsDamping{Linear=0f,Angular=50f});Debug.Log($\"Física añadida a '{prefabName}' (fricción alta, damping angular)\");}}3.EColiComponent.cs{using Unity.Entities;using Unity.Mathematics;public struct EColiComponent:IComponentData{public float TimeReference;public float MaxScale;public float GrowthTime;public float GrowthDuration;public float TimeSinceLastDivision;public float DivisionInterval;public bool HasGeneratedChild;public Entity Parent;public bool IsInitialCell;public float SeparationThreshold;public int SeparationSign;}}4.SCerevisiaeComponent.cs{using Unity.Entities;using Unity.Mathematics;public struct SCerevisiaeComponent:IComponentData{public float TimeReference;public float MaxScale;public float GrowthTime;public float GrowthDuration;public float TimeSinceLastDivision;public float DivisionInterval;public bool HasGeneratedChild;public Entity Parent;public bool IsInitialCell;public float SeparationThreshold;public int SeparationSign;public float3 GrowthDirection;}}5.EColiSystem.cs{using Unity.Burst;using Unity.Collections;using Unity.Entities;using Unity.Jobs;using Unity.Mathematics;using Unity.Physics;using Unity.Physics.Extensions;using Unity.Transforms;using UnityEngine;[BurstCompile][UpdateInGroup(typeof(SimulationSystemGroup))]public partial class EColiSystem:SystemBase{protected override void OnUpdate(){if(!GameStateManager.IsSetupComplete||GameStateManager.IsPaused)return;float deltaTime=GameStateManager.DeltaTime;EntityQuery query=GetEntityQuery(typeof(LocalTransform));int capacity=math.max(1024,query.CalculateEntityCount()*2);NativeParallelHashMap<Entity,ParentData>parentMap=new NativeParallelHashMap<Entity,ParentData>(capacity,Allocator.TempJob);var parentMapWriter=parentMap.AsParallelWriter();Dependency=Entities.ForEach((Entity e,in LocalTransform transform)=>{parentMapWriter.TryAdd(e,new ParentData{Position=transform.Position,Rotation=transform.Rotation,Scale=transform.Scale});}).ScheduleParallel(Dependency);EndSimulationEntityCommandBufferSystem ecbSystem=World.GetOrCreateSystemManaged<EndSimulationEntityCommandBufferSystem>();var ecb=ecbSystem.CreateCommandBuffer().AsParallelWriter();Dependency=Entities.WithReadOnly(parentMap).ForEach((Entity entity,int entityInQueryIndex,ref LocalTransform transform,ref EColiComponent organism)=>{float maxScale=organism.MaxScale;organism.GrowthDuration=organism.DivisionInterval=organism.TimeReference*organism.SeparationThreshold;if(transform.Scale<maxScale){organism.GrowthTime+=deltaTime;float t=math.clamp(organism.GrowthTime/organism.GrowthDuration,0f,1f);float initialScale=organism.IsInitialCell?maxScale:0.01f;transform.Scale=math.lerp(initialScale,maxScale,t);}if(transform.Scale>=maxScale){organism.TimeSinceLastDivision+=deltaTime;if(organism.TimeSinceLastDivision>=organism.DivisionInterval){Unity.Mathematics.Random rng=new Unity.Mathematics.Random((uint)(entityInQueryIndex+1)*12345);int sign=rng.NextFloat()<0.5f?1:-1;Entity child=ecb.Instantiate(entityInQueryIndex,entity);LocalTransform childTransform=transform;childTransform.Scale=0.01f;EColiComponent childData=organism;childData.GrowthTime=0f;childData.TimeSinceLastDivision=0f;childData.HasGeneratedChild=false;childData.IsInitialCell=false;childData.Parent=entity;childData.SeparationSign=sign;float3 upDir=math.mul(transform.Rotation,new float3(0,sign,0));childTransform.Position=transform.Position+upDir*(transform.Scale*0.25f);ecb.SetComponent(entityInQueryIndex,child,childTransform);ecb.SetComponent(entityInQueryIndex,child,childData);organism.TimeSinceLastDivision=0f;}}if(!organism.IsInitialCell&&organism.Parent!=Entity.Null&&parentMap.TryGetValue(organism.Parent,out ParentData parentData)){if(transform.Scale<organism.SeparationThreshold*maxScale){float offset=math.lerp(0f,parentData.Scale*4.9f,transform.Scale/maxScale);float3 up=math.mul(parentData.Rotation,new float3(0,organism.SeparationSign,0));transform.Position=parentData.Position+up*offset;transform.Rotation=parentData.Rotation;}else organism.Parent=Entity.Null;}ecb.SetComponent(entityInQueryIndex,entity,transform);ecb.SetComponent(entityInQueryIndex,entity,organism);}).ScheduleParallel(Dependency);ecbSystem.AddJobHandleForProducer(Dependency);Dependency=parentMap.Dispose(Dependency);}private struct ParentData{public float3 Position;public quaternion Rotation;public float Scale;}}}6.SCerevisiaeSystem.cs{using Unity.Burst;using Unity.Collections;using Unity.Entities;using Unity.Jobs;using Unity.Mathematics;using Unity.Physics;using Unity.Physics.Extensions;using Unity.Transforms;using UnityEngine;[BurstCompile][UpdateInGroup(typeof(SimulationSystemGroup))]public partial class SCerevisiaeSystem:SystemBase{protected override void OnUpdate(){if(!GameStateManager.IsSetupComplete||GameStateManager.IsPaused)return;float deltaTime=GameStateManager.DeltaTime;EntityQuery query=GetEntityQuery(typeof(LocalTransform));int capacity=math.max(1024,query.CalculateEntityCount()*2);NativeParallelHashMap<Entity,ParentData>parentMap=new NativeParallelHashMap<Entity,ParentData>(capacity,Allocator.TempJob);var parentMapWriter=parentMap.AsParallelWriter();Dependency=Entities.ForEach((Entity e,in LocalTransform transform)=>{parentMapWriter.TryAdd(e,new ParentData{Position=transform.Position,Rotation=transform.Rotation,Scale=transform.Scale});}).ScheduleParallel(Dependency);EndSimulationEntityCommandBufferSystem ecbSystem=World.GetOrCreateSystemManaged<EndSimulationEntityCommandBufferSystem>();var ecb=ecbSystem.CreateCommandBuffer().AsParallelWriter();Dependency=Entities.WithReadOnly(parentMap).ForEach((Entity entity,int entityInQueryIndex,ref LocalTransform transform,ref SCerevisiaeComponent organism)=>{float maxScale=organism.MaxScale;organism.GrowthDuration=organism.DivisionInterval=organism.TimeReference*organism.SeparationThreshold;if(transform.Scale<maxScale){organism.GrowthTime+=deltaTime;float t=math.clamp(organism.GrowthTime/organism.GrowthDuration,0f,1f);float initialScale=organism.IsInitialCell?maxScale:0.01f;transform.Scale=math.lerp(initialScale,maxScale,t);}if(transform.Scale>=maxScale){organism.TimeSinceLastDivision+=deltaTime;if(organism.TimeSinceLastDivision>=organism.DivisionInterval){Unity.Mathematics.Random rng=new Unity.Mathematics.Random((uint)(entityInQueryIndex+1)*99999);float angle=rng.NextFloat(0f,math.PI*2f);float3 randomDir=new float3(math.cos(angle),math.sin(angle),0f);Entity child=ecb.Instantiate(entityInQueryIndex,entity);LocalTransform childTransform=transform;childTransform.Scale=0.01f;SCerevisiaeComponent childData=organism;childData.GrowthTime=0f;childData.TimeSinceLastDivision=0f;childData.IsInitialCell=false;childData.Parent=entity;childData.GrowthDirection=randomDir;childTransform.Position=transform.Position;ecb.SetComponent(entityInQueryIndex,child,childTransform);ecb.SetComponent(entityInQueryIndex,child,childData);organism.TimeSinceLastDivision=0f;}}if(!organism.IsInitialCell&&organism.Parent!=Entity.Null&&parentMap.TryGetValue(organism.Parent,out ParentData parentData)){if(transform.Scale<organism.SeparationThreshold*maxScale){float ratio=math.clamp(transform.Scale/(organism.SeparationThreshold*maxScale),0f,1f);float offset=(parentData.Scale*0.5f)*ratio;float3 worldDir=math.mul(parentData.Rotation,organism.GrowthDirection);transform.Position=parentData.Position+worldDir*offset;transform.Rotation=parentData.Rotation;}else organism.Parent=Entity.Null;}ecb.SetComponent(entityInQueryIndex,entity,transform);ecb.SetComponent(entityInQueryIndex,entity,organism);}).ScheduleParallel(Dependency);ecbSystem.AddJobHandleForProducer(Dependency);Dependency=parentMap.Dispose(Dependency);}private struct ParentData{public float3 Position;public quaternion Rotation;public float Scale;}}}"
    codigos = separar_codigos_por_archivo(respuesta)
    print("Se encontró la siguiente cantidad de archivos:", len(codigos))

    for archivo, contenido in codigos.items():
        print(f"{archivo}:\n{contenido}\n")

    # Retornar los códigos formateados
    return codigos

if __name__ == "__main__":
    main()
