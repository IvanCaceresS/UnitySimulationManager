using UnityEngine;
using Unity.Entities;
using Unity.Mathematics;
using Unity.Transforms;
using Unity.Rendering;
using Unity.Collections;
using UnityEngine.UI;
using System.Collections;
using System.Collections.Generic;

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
        
        SolicitarColocacion();
    }

    void Update()
    {
        if (isWaitingForClick && Input.GetMouseButtonDown(0))
        {
            Ray ray = mainCamera.ScreenPointToRay(Input.mousePosition);
            if (Physics.Raycast(ray, out RaycastHit hit))
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

        Entity prefabEntity = entityManager.GetComponentData<PrefabEntityComponent>(spawnerEntities[currentPrefabIndex]).prefab;
        Entity entity = entityManager.Instantiate(prefabEntity);
        spawnerEntities.Dispose();

        float3 originalScale = entityManager.GetComponentData<LocalTransform>(prefabEntity).Scale;
        quaternion originalRotation = entityManager.GetComponentData<LocalTransform>(prefabEntity).Rotation;
        
        float randomYRotation = UnityEngine.Random.Range(0f, 360f);
        quaternion newRotation = math.mul(originalRotation, quaternion.RotateY(math.radians(randomYRotation)));

        float heightOffset = originalScale.y * 0.5f;
        float3 adjustedPosition = new float3(position.x, math.max(position.y + heightOffset, heightOffset), position.z);

        entityManager.SetComponentData(entity, new LocalTransform
        {
            Position = adjustedPosition,
            Rotation = newRotation,
            Scale = originalScale.x
        });

        Debug.Log("CreatePrefabsOnClick: Entidad " + prefabs[currentPrefabIndex].name + " creada en " + adjustedPosition);
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
    /// Método para resetear la simulación: eliminar todas las entidades existentes
    /// y volver a dejar el sistema listo para crear nuevos prefabs.
    /// </summary>
    public void ResetSimulation()
    {
        // 1) Query: Entidades de SubScene que NO tengan PrefabEntityComponent
        var queryDesc = new EntityQueryDesc
        {
            All = new[] { ComponentType.ReadOnly<SceneSection>() }, // todas las de la subescena
            None = new[] { ComponentType.ReadOnly<PrefabEntityComponent>() } // pero sin spawners
        };

        var subsceneQuery = entityManager.CreateEntityQuery(queryDesc);
        var toDestroy = subsceneQuery.ToEntityArray(Allocator.Temp);

        // 2) Destruir únicamente esas entidades
        entityManager.DestroyEntity(toDestroy);
        toDestroy.Dispose();
        
        Debug.Log("CreatePrefabsOnClick: Se han eliminado todas las entidades de la subescena, excepto los spawners.");

        // 3) Resetear nuestro estado interno
        currentPrefabIndex = 0;
        isWaitingForClick = false;
        messageCanvas.SetActive(true);

        // 4) Volver a solicitar la colocación desde cero
        SolicitarColocacion();
    }

}
