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

// Alias para evitar confusión al usar el struct "Material" de DOTS Physics
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
            Debug.LogError("CreatePrefabsOnClick: No se encontró una cámara principal en la escena.");
            return;
        }

        entityManager = World.DefaultGameObjectInjectionWorld.EntityManager;
        CrearMensajeUI();
        CargarPrefabs();

        if (prefabs.Count == 0)
        {
            Debug.LogError("CreatePrefabsOnClick: No se encontraron prefabs en Resources/Prefabs.");
            return;
        }

        Debug.Log("CreatePrefabsOnClick: Se encontraron " + prefabs.Count + " prefabs.");
        
        // Este query busca las entidades que tienen el componente PrefabEntityComponent
        // para luego instanciar entidades a partir de dichos prefabs.
        spawnerQuery = entityManager.CreateEntityQuery(typeof(PrefabEntityComponent));

        // Iniciamos el primer clic para colocar el primer prefab
        SolicitarColocacion();
    }

    void Update()
    {
        if (isWaitingForClick && Input.GetMouseButtonDown(0))
        {
            // Usamos UnityEngine.Ray y UnityEngine.RaycastHit
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

    private void CargarPrefabs()
    {
        // Cargamos prefabs desde Resources/Prefabs
        prefabs = new List<GameObject>(Resources.LoadAll<GameObject>("Prefabs"));
    }

    private void CrearEntidad(Vector3 position)
    {
        if (currentPrefabIndex >= prefabs.Count)
            return;

        NativeArray<Entity> spawnerEntities = spawnerQuery.ToEntityArray(Allocator.Temp);
        if (currentPrefabIndex >= spawnerEntities.Length)
        {
            Debug.LogError("CreatePrefabsOnClick: No se encontró un spawner correspondiente al prefab en el índice " + currentPrefabIndex);
            spawnerEntities.Dispose();
            return;
        }

        // Obtenemos el prefab ECS desde PrefabEntityComponent
        Entity spawner = spawnerEntities[currentPrefabIndex];
        spawnerEntities.Dispose();

        Entity prefabEntity = entityManager.GetComponentData<PrefabEntityComponent>(spawner).prefab;
        Entity entity = entityManager.Instantiate(prefabEntity);

        // Leemos la escala y rotación base del prefab
        float originalScale = entityManager.GetComponentData<LocalTransform>(prefabEntity).Scale;
        quaternion originalRotation = entityManager.GetComponentData<LocalTransform>(prefabEntity).Rotation;

        // Rotación aleatoria en Y
        float randomYRotation = UnityEngine.Random.Range(0f, 360f);
        quaternion newRotation = math.mul(originalRotation, quaternion.RotateY(math.radians(randomYRotation)));

        // Ajustamos la posición para que no quede enterrado
        float heightOffset = originalScale * 0.5f;
        float3 adjustedPosition = new float3(
            position.x,
            math.max(position.y + heightOffset, heightOffset),
            position.z
        );

        // Asignamos el LocalTransform final
        entityManager.SetComponentData(entity, new LocalTransform
        {
            Position = adjustedPosition,
            Rotation = newRotation,
            Scale = originalScale
        });

        // Dependiendo del nombre del prefab, añadimos un componente ECS
        string prefabName = prefabs[currentPrefabIndex].name;
        switch (prefabName)
        {
            case "Cube":
                entityManager.AddComponentData(entity, new CubeComponent());
                break;
            case "EColi":
                entityManager.AddComponentData(entity, new EColiComponent
                {
                    TimeReference         = 1200f,
                    SeparationThreshold   = 0.7f,

                    MaxScale              = 1.0f,
                    GrowthTime            = 0f,
                    GrowthDuration        = 1200f * 0.7f,    // 840 frames aprox.

                    TimeSinceLastDivision = 0f,
                    DivisionInterval      = 1200f * 0.7f,    // 840 frames

                    HasGeneratedChild     = false,
                    Parent                = Entity.Null,
                    IsInitialCell         = true,
                    SeparationSign        = 0
                });
                break;
            case "SCerevisiae":
                entityManager.AddComponentData(entity, new SCerevisiaeComponent());
                break;
            default:
                Debug.LogWarning($"CreatePrefabsOnClick: No hay un componente ECS definido para el prefab '{prefabName}'");
                break;
        }

        // Añadimos la parte de física (collider, mass, etc.)
        AddPhysicsComponents(entity, prefabName, originalScale);

        Debug.Log($"CreatePrefabsOnClick: Entidad '{prefabName}' creada en {adjustedPosition}");
    }

    private void AddPhysicsComponents(Entity entity, string prefabName, float scale)
    {
        // Vamos a crear un collider con un Material de DOTS Physics
        // que tenga Friction y Restitution personalizadas
        BlobAssetReference<Unity.Physics.Collider> collider = default;

        // Creamos un "Material" de DOTS Physics con alta fricción, poco rebote, etc.
        Material mat = new Material
        {
            Friction    = 8f,   // Alto => difícil rodar
            Restitution = 0f    // Sin rebote
        };

        switch (prefabName)
        {
            case "Cube":
                collider = Unity.Physics.BoxCollider.Create(
                    new BoxGeometry
                    {
                        Center      = float3.zero,
                        Orientation = quaternion.identity,
                        Size        = new float3(scale, scale, scale),
                        BevelRadius = 0.05f
                    },
                    CollisionFilter.Default,
                    mat // Pasamos el material
                );
                break;

            case "EColi":
                // Por ejemplo, una cápsula vertical
                collider = Unity.Physics.CapsuleCollider.Create(
                    new CapsuleGeometry
                    {
                        Vertex0 = new float3(0, -scale, 0),
                        Vertex1 = new float3(0,  scale, 0),
                        Radius  = 0.25f
                    },
                    CollisionFilter.Default,
                    mat
                );
                break;

            case "SCerevisiae":
                // Podrías darle un material distinto, menor fricción, algo de rebote, etc.
                mat.Friction    = 5f;
                mat.Restitution = 0.1f;
                collider = Unity.Physics.SphereCollider.Create(
                    new SphereGeometry
                    {
                        Center = float3.zero,
                        Radius = scale * 0.1f
                    },
                    CollisionFilter.Default,
                    mat
                );
                break;

            default:
                Debug.LogWarning($"CreatePrefabsOnClick: No se pudo asignar un collider para '{prefabName}'");
                return;
        }

        // Asignamos el collider en la entidad
        entityManager.AddComponentData(entity, new PhysicsCollider { Value = collider });

        // Calculamos masa si el collider está OK
        if (collider.IsCreated)
        {
            var massProperties = collider.Value.MassProperties;
            entityManager.AddComponentData(entity, PhysicsMass.CreateDynamic(massProperties, 1f));
        }

        // PhysicsVelocity por defecto
        entityManager.AddComponentData(entity, new PhysicsVelocity
        {
            Linear  = float3.zero,
            Angular = float3.zero
        });

        // Gravedad normal
        entityManager.AddComponentData(entity, new PhysicsGravityFactor { Value = 1f });

        // Añadimos o definimos un PhysicsDamping alto en Angular para frenar la rotación
        entityManager.AddComponentData(entity, new PhysicsDamping
        {
            Linear  = 0f,
            Angular = 50f
        });

        Debug.Log($"CreatePrefabsOnClick: Física añadida a '{prefabName}' con alta fricción y damping angular");
    }

    private void SolicitarColocacion()
    {
        if (currentPrefabIndex >= prefabs.Count)
            return;

        string prefabName = prefabs[currentPrefabIndex].name;
        messageText.text = "Por favor, clickee donde quiere colocar el organismo '" + prefabName + "'.";
        isWaitingForClick = true;
    }

    private void OnAllPrefabsPlaced()
    {
        Debug.Log("CreatePrefabsOnClick: Todos los prefabs han sido colocados.");
        messageText.text = "Todos los prefabs han sido colocados.";
        isWaitingForClick = false;
        StartCoroutine(ShowFinalMessageAndCompleteSetup());
    }

    private IEnumerator ShowFinalMessageAndCompleteSetup()
    {
        yield return new WaitForSeconds(0.5f);
        messageCanvas.SetActive(false);

        // Si existe GameStateManager.CompleteSetup()
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

    /// <summary>
    /// Método para resetear la simulación: elimina entidades existentes
    /// y vuelve a dejar el sistema listo para crear nuevos prefabs.
    /// </summary>
    public void ResetSimulation()
    {
        // 1) Query: Entidades de SubScene que NO sean Prefabs ni el plano
        var queryDesc = new EntityQueryDesc
        {
            All = new[] { ComponentType.ReadOnly<SceneSection>() },
            None = new[]
            {
                ComponentType.ReadOnly<PrefabEntityComponent>(), // Excluye spawners
                ComponentType.ReadOnly<PlaneComponent>()         // Excluye el plano
            }
        };

        var subsceneQuery = entityManager.CreateEntityQuery(queryDesc);
        var toDestroy = subsceneQuery.ToEntityArray(Allocator.Temp);

        // 2) Destruir únicamente esas entidades
        entityManager.DestroyEntity(toDestroy);
        toDestroy.Dispose();
        
        Debug.Log("CreatePrefabsOnClick: Se han eliminado todas las entidades de la subescena, excepto los spawners y el plano.");

        // 3) Resetear nuestro estado interno
        currentPrefabIndex = 0;
        isWaitingForClick = false;
        messageCanvas.SetActive(true);

        // 4) Volver a solicitar la colocación desde cero
        SolicitarColocacion();
    }
}
