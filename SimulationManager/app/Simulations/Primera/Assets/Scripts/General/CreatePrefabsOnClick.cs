using UnityEngine;
using Unity.Entities;
using Unity.Mathematics;
using Unity.Transforms;
using Unity.Rendering;
using Unity.Collections;
using Unity.Physics;
using Unity.Physics.Authoring;
using UnityEngine.UI;
using System.Collections;
using System.Collections.Generic;

using Material = Unity.Physics.Material;

public class CreatePrefabsOnClick : MonoBehaviour
{
    private Camera mainCamera;
    private List<GameObject> prefabs;
    private int currentPrefabIndex = 0;
    private bool isWaitingForClick = false;
    private GameObject messageCanvas;
    private Text messageText;
    private EntityManager entityManager;
    private EntityQuery spawnerQuery;

    void Start()
    {
        mainCamera = Camera.main;
        if (mainCamera == null)
        {
            Debug.LogError("CreatePrefabsOnClick: No se encontró una cámara principal.");
            return;
        }

        entityManager = World.DefaultGameObjectInjectionWorld.EntityManager;
        CrearMensajeUI();
        CargarPrefabs();

        if (prefabs.Count == 0)
        {
            Debug.LogError("No se encontraron prefabs en Resources/Prefabs.");
            return;
        }

        Debug.Log($"Se encontraron {prefabs.Count} prefabs.");

        spawnerQuery = entityManager.CreateEntityQuery(typeof(PrefabEntityComponent));

        SolicitarColocacion();
    }

    void Update()
    {
        if (isWaitingForClick && Input.GetMouseButtonDown(0))
        {
            UnityEngine.Ray ray = mainCamera.ScreenPointToRay(Input.mousePosition);
            if (UnityEngine.Physics.Raycast(ray, out UnityEngine.RaycastHit hit))
            {
                Vector3 spawnPosition = hit.point;
                CrearEntidad(spawnPosition);
                currentPrefabIndex++;
                if (currentPrefabIndex < prefabs.Count)
                {
                    SolicitarColocacion();
                }
                else
                {
                    OnAllPrefabsPlaced();
                }
            }
        }
    }

    private void CargarPrefabs(){prefabs = new List<GameObject>(Resources.LoadAll<GameObject>("Prefabs"));}
private void CrearEntidad(Vector3 position)
{
    if(currentPrefabIndex>=prefabs.Count)return;
    NativeArray<Entity>spawnerEntities=spawnerQuery.ToEntityArray(Allocator.Temp);
    if(currentPrefabIndex>=spawnerEntities.Length)
    {
        Debug.LogError($"No se encontró spawner en índice {currentPrefabIndex}");
        spawnerEntities.Dispose();
        return;
    }
    Entity spawner=spawnerEntities[currentPrefabIndex];
    spawnerEntities.Dispose();
    Entity prefabEntity=entityManager.GetComponentData<PrefabEntityComponent>(spawner).prefab;
    Entity entity=entityManager.Instantiate(prefabEntity);
    float originalScale=entityManager.GetComponentData<LocalTransform>(prefabEntity).Scale;
    quaternion originalRotation=entityManager.GetComponentData<LocalTransform>(prefabEntity).Rotation;
    float randYRot=UnityEngine.Random.Range(0f,360f);
    quaternion newRotation=math.mul(originalRotation,quaternion.RotateY(math.radians(randYRot)));
    float heightOffset=originalScale*0.5f;
    float3 adjustedPosition=new float3(position.x,math.max(position.y+heightOffset,heightOffset),position.z);
    entityManager.SetComponentData(entity,new LocalTransform
    {
        Position=adjustedPosition,Rotation=newRotation,Scale=originalScale
    }
    );
    string prefabName=prefabs[currentPrefabIndex].name;
    switch(prefabName)
    {
        case"EColi":entityManager.AddComponentData(entity,new EColiComponent
        {
            TimeReference=1200f,SeparationThreshold=0.7f,MaxScale=1.0f,GrowthTime=0f,GrowthDuration=1200f*0.7f,TimeSinceLastDivision=0f,DivisionInterval=1200f*0.7f,HasGeneratedChild=false,Parent=Entity.Null,IsInitialCell=true,SeparationSign=0
        }
        );
        break;
        case"SCerevisiae":entityManager.AddComponentData(entity,new SCerevisiaeComponent
        {
            TimeReference=5400f,SeparationThreshold=0.7f,MaxScale=5.0f,GrowthTime=0f,GrowthDuration=5400f*0.7f,TimeSinceLastDivision=0f,DivisionInterval=5400f*0.7f,HasGeneratedChild=false,Parent=Entity.Null,IsInitialCell=true,SeparationSign=0,GrowthDirection=new float3(0,1,0)
        }
        );
        break;
        default:Debug.LogWarning($"No hay componente ECS para '{prefabName}'");
        break;
    }
    AddPhysicsComponents(entity,prefabName,originalScale);
    Debug.Log($"Entidad '{prefabName}' creada en {adjustedPosition}");
}
private void AddPhysicsComponents(Entity entity,string prefabName,float scale)
{
    BlobAssetReference<Unity.Physics.Collider>collider=default;
    Material mat=new Material
    {
        Friction=8f,Restitution=0f
    }
    ;
    switch(prefabName)
    {
        case"EColi":collider=Unity.Physics.CapsuleCollider.Create(new CapsuleGeometry
        {
            Vertex0=new float3(0,-scale,0),Vertex1=new float3(0,scale,0),Radius=0.25f
        }
        ,CollisionFilter.Default,mat);
        break;
        case"SCerevisiae":collider=Unity.Physics.SphereCollider.Create(new SphereGeometry
        {
            Center=float3.zero,Radius=scale*0.1f
        }
        ,CollisionFilter.Default,mat);
        break;
        default:Debug.LogWarning($"No collider para '{prefabName}'");
        return;
    }
    entityManager.AddComponentData(entity,new PhysicsCollider
    {
        Value=collider
    }
    );
    if(collider.IsCreated)
    {
        var massProps=collider.Value.MassProperties;
        entityManager.AddComponentData(entity,PhysicsMass.CreateDynamic(massProps,1f));
    }
    entityManager.AddComponentData(entity,new PhysicsVelocity
    {
        Linear=float3.zero,Angular=float3.zero
    }
    );
    entityManager.AddComponentData(entity,new PhysicsGravityFactor
    {
        Value=1f
    }
    );
    entityManager.AddComponentData(entity,new PhysicsDamping
    {
        Linear=0f,Angular=50f
    }
    );
    Debug.Log($"Física añadida a '{prefabName}' (fricción alta, damping angular)");
}

    private void SolicitarColocacion()
    {
        if (currentPrefabIndex >= prefabs.Count) return;

        string prefabName = prefabs[currentPrefabIndex].name;
        messageText.text = $"Por favor, clickee para colocar '{prefabName}'.";
        isWaitingForClick = true;
    }

    private void OnAllPrefabsPlaced()
    {
        Debug.Log("Todos los prefabs colocados.");
        messageText.text = "Todos los prefabs han sido colocados.";
        isWaitingForClick = false;
        StartCoroutine(ShowFinalMessageAndCompleteSetup());
    }

    private IEnumerator ShowFinalMessageAndCompleteSetup()
    {
        yield return new WaitForSeconds(0.5f);
        messageCanvas.SetActive(false);

        GameStateManager.CompleteSetup();
    }

    private void CrearMensajeUI()
    {
        messageCanvas = new GameObject("MessageCanvas");
        Canvas canvas = messageCanvas.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        messageCanvas.AddComponent<CanvasScaler>().uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        messageCanvas.AddComponent<GraphicRaycaster>();

        GameObject textObject = new GameObject("MessageText");
        textObject.transform.SetParent(messageCanvas.transform);
        messageText = textObject.AddComponent<Text>();
        messageText.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        messageText.alignment = TextAnchor.MiddleCenter;
        messageText.fontSize = 16;
        messageText.color = Color.black;
        messageText.fontStyle = FontStyle.BoldAndItalic;

        RectTransform textTransform = messageText.GetComponent<RectTransform>();
        textTransform.sizeDelta = new Vector2(1000, 100);
        textTransform.anchoredPosition = new Vector2(0, 200);
        messageCanvas.SetActive(true);
    }

    public void ResetSimulation()
    {
        var queryDesc = new EntityQueryDesc
        {
            All = new[] { ComponentType.ReadOnly<SceneSection>() },
            None = new[]
            {
                ComponentType.ReadOnly<PrefabEntityComponent>(),
                ComponentType.ReadOnly<PlaneComponent>()
            }
        };

        var subsceneQuery = entityManager.CreateEntityQuery(queryDesc);
        var toDestroy = subsceneQuery.ToEntityArray(Allocator.Temp);

        entityManager.DestroyEntity(toDestroy);
        toDestroy.Dispose();

        Debug.Log("Se han eliminado entidades excepto spawners y plano.");

        currentPrefabIndex = 0;
        isWaitingForClick = false;
        messageCanvas.SetActive(true);

        SolicitarColocacion();
    }
}
