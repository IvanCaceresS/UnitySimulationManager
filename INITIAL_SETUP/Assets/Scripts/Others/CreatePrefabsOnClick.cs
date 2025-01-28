using UnityEngine;
using Unity.Entities;
using Unity.Mathematics;
using Unity.Transforms;
using Unity.Rendering;
using Unity.Collections;
using UnityEngine.UI;
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
            Debug.LogError("No se encontró una cámara principal en la escena.");
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

        Debug.Log("Se encontraron " + prefabs.Count + " prefabs.");
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
                    Debug.Log("Todos los prefabs han sido colocados.");
                    messageText.text = "Todos los prefabs han sido colocados.";
                    isWaitingForClick = false;
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
            Debug.LogError("No se encontró un spawner correspondiente al prefab en el índice " + currentPrefabIndex);
            return;
        }

        Entity prefabEntity = entityManager.GetComponentData<PrefabEntityComponent>(spawnerEntities[currentPrefabIndex]).prefab;
        Entity entity = entityManager.Instantiate(prefabEntity);
        spawnerEntities.Dispose();

        float3 originalScale = entityManager.GetComponentData<LocalTransform>(prefabEntity).Scale;
        quaternion originalRotation = entityManager.GetComponentData<LocalTransform>(prefabEntity).Rotation;
        
        float randomYRotation = UnityEngine.Random.Range(0f, 360f);
        quaternion newRotation = math.mul(originalRotation, quaternion.RotateY(math.radians(randomYRotation)));

        entityManager.SetComponentData(entity, new LocalTransform
        {
            Position = position,
            Rotation = newRotation,
            Scale = originalScale.x
        });

        Debug.Log("Entidad " + prefabs[currentPrefabIndex].name + " creada en " + position);
    }

    private void SolicitarColocacion()
    {
        if (currentPrefabIndex >= prefabs.Count)
            return;

        string prefabName = prefabs[currentPrefabIndex].name;
        messageText.text = "Por favor, ahora clickee donde quiere colocar el " + prefabName + ".";
        isWaitingForClick = true;
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

        RectTransform textTransform = messageText.GetComponent<RectTransform>();
        textTransform.sizeDelta = new Vector2(1000, 100);
        textTransform.anchoredPosition = new Vector2(0, 150);
        messageCanvas.SetActive(true);
    }
}
