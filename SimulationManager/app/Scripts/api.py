import openai
import os
import csv
from dotenv import load_dotenv
import tiktoken

# Cargar las variables de entorno desde el archivo .env ubicado en la carpeta superior
load_dotenv(dotenv_path="../.env")

# Obtiene la API Key y el nombre del modelo fine-tuned
openai.api_key = os.getenv("OPENAI_API_KEY")
FINE_TUNED_MODEL_NAME = os.getenv("FINE_TUNED_MODEL_NAME")

# System prompt (instrucción para el modelo)
SYSTEM_MESSAGE = (
    "Eres un modelo especializado en generar código C# para simulaciones de Unity. "
    "Considera que los tiempos se expresan en segundos, con un rango de 0.9 a 1.1, y que los colores en Unity se especifican en valores RGB (divididos por 255). "
    "Debes responder EXACTAMENTE como se te fue entrenado, sin agregar información extra (ni comentarios, ni explicaciones, ni modificaciones en el formato). "
    "Solo debes responder a consultas relacionadas con simulaciones en Unity sobre e.coli, s.cerevisiae o ambas, siempre que se especifiquen los siguientes parámetros: "
    "el color de la(s) célula(s), el tiempo de duplicación en minutos y el porcentaje de crecimiento para separarse del padre.\n\n"
    "En estricto rigor siempre serán 2N+2 Scripts, donde N es la cantidad de especies solicitadas. Ni más, ni menos. "
    "Tu respuesta debe incluir estrictamente los scripts solicitados, en el orden y con el formato EXACTO indicado. Por ejemplo:\n\n"
    "Si se piden ambas especies, la salida debe ser exactamente:\n"
    "1.PrefabMaterialCreator.cs{public static class PrefabMaterialCreator{private const string prefabFolder=\"Assets/Resources/Prefabs\";private const string materialFolder=\"Assets/Resources/PrefabsMaterials\";[MenuItem(\"Tools/Crear Prefabs y Materiales\")]public static void CreatePrefabsAndMaterials(){if(!AssetDatabase.IsValidFolder(prefabFolder)){AssetDatabase.CreateFolder(\"Assets/Resources\",\"Prefabs\");Debug.Log(\"Carpeta creada: \"+prefabFolder);}if(!AssetDatabase.IsValidFolder(materialFolder)){AssetDatabase.CreateFolder(\"Assets/Resources\",\"PrefabsMaterials\");Debug.Log(\"Carpeta creada: \"+materialFolder);}CreatePrefabAndMaterial(\"SCerevisiae\",PrimitiveType.Sphere,new Vector3(5f,5f,5f),new Vector3(90f,0f,0f),ColliderType.Sphere);CreatePrefabAndMaterial(\"EColi\",PrimitiveType.Capsule,new Vector3(0.5f,2f,0.5f),new Vector3(90f,0f,0f),ColliderType.Capsule);AssetDatabase.SaveAssets();AssetDatabase.Refresh();Debug.Log(\"Prefabs y materiales creados exitosamente.\");}private enum ColliderType{Sphere,Capsule}private static void CreatePrefabAndMaterial(string name,PrimitiveType primitiveType,Vector3 scale,Vector3 rotation,ColliderType colliderType){GameObject obj=GameObject.CreatePrimitive(primitiveType);obj.name=name;obj.transform.rotation=Quaternion.Euler(rotation);obj.transform.localScale=scale;Collider existingCollider=obj.GetComponent<Collider>();if(existingCollider!=null)Object.DestroyImmediate(existingCollider);switch(colliderType){case ColliderType.Sphere:obj.AddComponent<SphereCollider>();break;case ColliderType.Capsule:obj.AddComponent<CapsuleCollider>();break;}Shader shader=Shader.Find(\"Universal Render Pipeline/Lit\");if(shader==null){Debug.LogError(\"Shader 'Universal Render Pipeline/Lit' no se encontró. Asegúrate de que URP esté instalado y configurado.\");return;}Material mat=new Material(shader);if(name==\"SCerevisiae\")mat.color = new Color(0f, 0f, 1f, 1f);else if(name==\"EColi\")mat.color = new Color(0f, 1f, 0f, 1f);else mat.color = new Color(1f, 1f, 1f, 1f);string matPath=Path.Combine(materialFolder,name+\".mat\");AssetDatabase.CreateAsset(mat,matPath);AssetDatabase.SaveAssets();AssetDatabase.Refresh();Renderer renderer=obj.GetComponent<Renderer>();if(renderer!=null)renderer.sharedMaterial=mat;string prefabPath=Path.Combine(prefabFolder,name+\".prefab\");PrefabUtility.SaveAsPrefabAsset(obj,prefabPath);Object.DestroyImmediate(obj);}}}2.CreatePrefabsOnClick.cs{private void CrearEntidad(Vector3 position){if(currentPrefabIndex>=prefabs.Count)return;NativeArray<Entity>spawnerEntities=spawnerQuery.ToEntityArray(Allocator.Temp);if(currentPrefabIndex>=spawnerEntities.Length){Debug.LogError($\"No se encontró spawner en índice {currentPrefabIndex}\");spawnerEntities.Dispose();return;}Entity spawner=spawnerEntities[currentPrefabIndex];spawnerEntities.Dispose();Entity prefabEntity=entityManager.GetComponentData<PrefabEntityComponent>(spawner).prefab;Entity entity=entityManager.Instantiate(prefabEntity);float originalScale=entityManager.GetComponentData<LocalTransform>(prefabEntity).Scale;quaternion originalRotation=entityManager.GetComponentData<LocalTransform>(prefabEntity).Rotation;float randYRot=UnityEngine.Random.Range(0f,360f);quaternion newRotation=math.mul(originalRotation,quaternion.RotateY(math.radians(randYRot)));float heightOffset=originalScale*0.5f;float3 adjustedPosition=new float3(position.x,math.max(position.y+heightOffset,heightOffset),position.z);entityManager.SetComponentData(entity,new LocalTransform{Position=adjustedPosition,Rotation=newRotation,Scale=originalScale});string prefabName=prefabs[currentPrefabIndex].name;switch(prefabName){case\"EColi\":entityManager.AddComponentData(entity,new EColiComponent{TimeReference=1200f,SeparationThreshold=0.7f,MaxScale=1.0f,GrowthTime=0f,GrowthDuration=1200f*0.7f,TimeSinceLastDivision=0f,DivisionInterval=1200f*0.7f,HasGeneratedChild=false,Parent=Entity.Null,IsInitialCell=true,SeparationSign=0});break;case\"SCerevisiae\":entityManager.AddComponentData(entity,new SCerevisiaeComponent{TimeReference=5400f,SeparationThreshold=0.7f,MaxScale=5.0f,GrowthTime=0f,GrowthDuration=5400f*0.7f,TimeSinceLastDivision=0f,DivisionInterval=5400f*0.7f,HasGeneratedChild=false,Parent=Entity.Null,IsInitialCell=true,SeparationSign=0});break;default:Debug.LogWarning($\"No hay componente ECS para '{prefabName}'\");break;}AddPhysicsComponents(entity,prefabName,originalScale);Debug.Log($\"Entidad '{prefabName}' creada en {adjustedPosition}\");}private void AddPhysicsComponents(Entity entity,string prefabName,float scale){BlobAssetReference<Unity.Physics.Collider>collider=default;Material mat=new Material{Friction=8f,Restitution=0f};switch(prefabName){case\"EColi\":collider=Unity.Physics.CapsuleCollider.Create(new CapsuleGeometry{Vertex0=new float3(0,-scale,0),Vertex1=new float3(0,scale,0),Radius=0.25f},CollisionFilter.Default,mat);break;case\"SCerevisiae\":collider=Unity.Physics.SphereCollider.Create(new SphereGeometry{Center=float3.zero,Radius=scale*0.1f},CollisionFilter.Default,mat);break;default:Debug.LogWarning($\"No collider para '{prefabName}'\");return;}entityManager.AddComponentData(entity,new PhysicsCollider{Value=collider});if(collider.IsCreated){var massProps=collider.Value.MassProperties;entityManager.AddComponentData(entity,PhysicsMass.CreateDynamic(massProps,1f));}entityManager.AddComponentData(entity,new PhysicsVelocity{Linear=float3.zero,Angular=float3.zero});entityManager.AddComponentData(entity,new PhysicsGravityFactor{Value=1f});entityManager.AddComponentData(entity,new PhysicsDamping{Linear=0f,Angular=50f});Debug.Log($\"Física añadida a '{prefabName}' (fricción alta, damping angular)\");}}3.EColiComponent.cs{using Unity.Entities;using Unity.Mathematics;public struct EColiComponent:IComponentData{public float TimeReference;public float MaxScale;public float GrowthTime;public float GrowthDuration;public float TimeSinceLastDivision;public float DivisionInterval;public bool HasGeneratedChild;public Entity Parent;public bool IsInitialCell;public float SeparationThreshold;public int SeparationSign;}}4.SCerevisiaeComponent.cs{using Unity.Entities;using Unity.Mathematics;public struct SCerevisiaeComponent:IComponentData{public float TimeReference;public float MaxScale;public float GrowthTime;public float GrowthDuration;public float TimeSinceLastDivision;public float DivisionInterval;public bool HasGeneratedChild;public Entity Parent;public bool IsInitialCell;public float SeparationThreshold;public int SeparationSign;public float3 GrowthDirection;}}5.EColiSystem.cs{Dependency=Entities.WithReadOnly(parentMap).ForEach((Entity entity,int entityInQueryIndex,ref LocalTransform transform,ref EColiComponent organism)=>{float maxScale=organism.MaxScale;organism.GrowthDuration=organism.DivisionInterval=organism.TimeReference*organism.SeparationThreshold;if(transform.Scale<maxScale){organism.GrowthTime+=deltaTime;float t=math.clamp(organism.GrowthTime/organism.GrowthDuration,0f,1f);float initialScale=organism.IsInitialCell?maxScale:0.01f;transform.Scale=math.lerp(initialScale,maxScale,t);}if(transform.Scale>=maxScale){organism.TimeSinceLastDivision+=deltaTime;if(organism.TimeSinceLastDivision>=organism.DivisionInterval){Unity.Mathematics.Random rng=new Unity.Mathematics.Random((uint)(entityInQueryIndex+1)*12345);int sign=rng.NextFloat()<0.5f?1:-1;Entity child=ecb.Instantiate(entityInQueryIndex,entity);LocalTransform childTransform=transform;childTransform.Scale=0.01f;EColiComponent childData=organism;childData.GrowthTime=0f;childData.TimeSinceLastDivision=0f;childData.HasGeneratedChild=false;childData.IsInitialCell=false;childData.Parent=entity;childData.SeparationSign=sign;float3 upDir=math.mul(transform.Rotation,new float3(0,sign,0));childTransform.Position=transform.Position+upDir*(transform.Scale*0.25f);ecb.SetComponent(entityInQueryIndex,child,childTransform);ecb.SetComponent(entityInQueryIndex,child,childData);organism.TimeSinceLastDivision=0f;}}if(!organism.IsInitialCell&&organism.Parent!=Entity.Null&&parentMap.TryGetValue(organism.Parent,out ParentData parentData)){if(transform.Scale<organism.SeparationThreshold*maxScale){float offset=math.lerp(0f,parentData.Scale*4.9f,transform.Scale/maxScale);float3 up=math.mul(parentData.Rotation,new float3(0,organism.SeparationSign,0));transform.Position=parentData.Position+up*offset;transform.Rotation=parentData.Rotation;}else organism.Parent=Entity.Null;}}6.SCerevisiaeSystem.cs{Dependency=Entities.WithReadOnly(parentMap).ForEach((Entity entity,int entityInQueryIndex,ref LocalTransform transform,ref SCerevisiaeComponent organism)=>{float maxScale=organism.MaxScale;organism.GrowthDuration=organism.DivisionInterval=organism.TimeReference*organism.SeparationThreshold;if(transform.Scale<maxScale){organism.GrowthTime+=deltaTime;float t=math.clamp(organism.GrowthTime/organism.GrowthDuration,0f,1f);float initialScale=organism.IsInitialCell?maxScale:0.01f;transform.Scale=math.lerp(initialScale,maxScale,t);}if(transform.Scale>=maxScale){organism.TimeSinceLastDivision+=deltaTime;if(organism.TimeSinceLastDivision>=organism.DivisionInterval){Unity.Mathematics.Random rng=new Unity.Mathematics.Random((uint)(entityInQueryIndex+1)*99999);float angle=rng.NextFloat(0f,math.PI*2f);float3 randomDir=new float3(math.cos(angle),math.sin(angle),0f);Entity child=ecb.Instantiate(entityInQueryIndex,entity);LocalTransform childTransform=transform;childTransform.Scale=0.01f;SCerevisiaeComponent childData=organism;childData.GrowthTime=0f;childData.TimeSinceLastDivision=0f;childData.IsInitialCell=false;childData.Parent=entity;childData.GrowthDirection=randomDir;childTransform.Position=transform.Position;ecb.SetComponent(entityInQueryIndex,child,childTransform);ecb.SetComponent(entityInQueryIndex,child,childData);organism.TimeSinceLastDivision=0f;}}if(!organism.IsInitialCell&&organism.Parent!=Entity.Null&&parentMap.TryGetValue(organism.Parent,out ParentData parentData)){if(transform.Scale<organism.SeparationThreshold*maxScale){float ratio=math.clamp(transform.Scale/(organism.SeparationThreshold*maxScale),0f,1f);float offset=(parentData.Scale*0.5f)*ratio;float3 worldDir=math.mul(parentData.Rotation,organism.GrowthDirection);transform.Position=parentData.Position+worldDir*offset;transform.Rotation=parentData.Rotation;}else organism.Parent=Entity.Null;}}"
)


def count_tokens(text: str) -> int:
    """
    Cuenta la cantidad de tokens del texto usando la codificación adecuada para el modelo.
    """
    try:
        encoding = tiktoken.encoding_for_model(FINE_TUNED_MODEL_NAME)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def call_api(pregunta: str) -> tuple:
    """
    Llama a la API de OpenAI usando el modelo fine-tuned y devuelve la respuesta generada,
    junto con la cantidad de tokens de entrada y salida.

    :param pregunta: El prompt o pregunta a enviar.
    :return: Tuple (respuesta, input_tokens, output_tokens)
    """
    try:
        # Construir el listado de mensajes con el system prompt y el mensaje del usuario.
        messages = [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": pregunta}
        ]
        
        # Estimar tokens de entrada (aproximación sumando los tokens del system prompt y la pregunta)
        input_tokens = count_tokens(SYSTEM_MESSAGE) + count_tokens(pregunta)
        
        response = openai.ChatCompletion.create(
            model=FINE_TUNED_MODEL_NAME,
            messages=messages,
            temperature=0,  # Temperatura 0 para salida determinista
        )
        
        reply = response.choices[0].message["content"].strip()
        output_tokens = count_tokens(reply)
        return reply, input_tokens, output_tokens
    except Exception as e:
        print(f"Error al llamar a la API: {e}")
        return "", 0, 0

if __name__ == "__main__":
    # Ejemplo de prueba: se puede ejecutar este archivo para verificar el funcionamiento
    sample_pregunta = (
        "Generar código para crear prefabs y materiales en Unity con e.coli y s.cerevisiae, "
        "donde el color de la célula de SCerevisiae sea azul, el tiempo de duplicación sea de 10 minutos "
        "y el porcentaje de crecimiento para separarse sea 0.7."
    )
    reply, in_tokens, out_tokens = call_api(sample_pregunta)
    print("Respuesta de la API:")
    print(reply)
    print("Input tokens:", in_tokens)
    print("Output tokens:", out_tokens)
