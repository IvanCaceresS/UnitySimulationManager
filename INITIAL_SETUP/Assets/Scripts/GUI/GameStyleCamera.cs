using UnityEngine;

public class GameStyleCamera : MonoBehaviour
{
    [Header("Velocidades de Movimiento")]
    public float moveSpeed = 20f;
    public float verticalSpeed = 20f;

    [Header("Rotación de la Cámara")]
    public float rotationSpeed = 200f;

    [Header("Zoom de la Cámara")]
    public float zoomSpeed = 5f;
    public float minZoom = 5f;
    public float maxZoom = 60f;

    [Header("Restricciones de Posición")]
    public float maxDistance = 200f;
    public float minHeight = 0.5f;

    private float currentZoom = 60f;
    private float pitch = 0f;
    private float yaw = 0f;

    private Vector3 freeCameraPosition;
    private Quaternion freeCameraRotation;
    private Vector3 topDownPosition = new Vector3(0, 100, 0);
    private Quaternion topDownRotation = Quaternion.Euler(90, 0, 0);

    private bool isTopDownView = false;
    private bool canMove = false;

    void Start()
    {
        InitializeCamera();
        GameStateManager.OnSetupComplete += EnableMovement;
    }

    void OnDestroy()
    {
        GameStateManager.OnSetupComplete -= EnableMovement; // Limpieza para evitar fugas de memoria
    }

    private void EnableMovement()
    {
        canMove = true;
        Debug.Log("GameStyleCamera: Activando movimiento de cámara.");
    }

    void Update()
    {
        if (!canMove) return;

        if (Input.GetKeyDown(KeyCode.C)) 
        {
            ToggleCameraMode();
            Debug.Log("GameStyleCamera: Cambiando modo de cámara.");
        }

        if (!isTopDownView)
        {
            HandleInput();
        }
    }

    private void InitializeCamera()
    {
        Cursor.visible = true;
        Cursor.lockState = CursorLockMode.None;
        Camera.main.fieldOfView = currentZoom;

        freeCameraPosition = transform.position;
        freeCameraRotation = transform.rotation;
    }

    private void HandleInput()
    {
        HandleRotation();
        HandleMovement();
        HandleZoom();
    }

    private void HandleRotation()
    {
        if (Input.GetMouseButton(1))
        {
            Cursor.lockState = CursorLockMode.Locked;
            Cursor.visible = false;

            float mouseX = Input.GetAxis("Mouse X") * rotationSpeed * Time.deltaTime;
            float mouseY = Input.GetAxis("Mouse Y") * rotationSpeed * Time.deltaTime;

            yaw += mouseX;
            pitch = Mathf.Clamp(pitch - mouseY, -90f, 90f);

            transform.rotation = Quaternion.Euler(pitch, yaw, 0f);
        }
        else
        {
            Cursor.lockState = CursorLockMode.None;
            Cursor.visible = true;
        }
    }

    private void HandleMovement()
    {
        Vector3 moveDirection = Vector3.zero;

        moveDirection += transform.right * Input.GetAxis("Horizontal") * moveSpeed * Time.deltaTime;
        moveDirection += transform.forward * Input.GetAxis("Vertical") * moveSpeed * Time.deltaTime;

        if (Input.GetKey(KeyCode.Space))
        {
            moveDirection += Vector3.up * verticalSpeed * Time.deltaTime;
        }
        if (Input.GetKey(KeyCode.LeftControl))
        {
            moveDirection += Vector3.down * verticalSpeed * Time.deltaTime;
        }

        transform.position += moveDirection;
        RestrictPosition();
    }

    private void HandleZoom()
    {
        float scroll = Input.GetAxis("Mouse ScrollWheel");
        if (scroll != 0)
        {
            currentZoom = Mathf.Clamp(currentZoom - scroll * zoomSpeed, minZoom, maxZoom);
            Camera.main.fieldOfView = currentZoom;
        }
    }

    private void RestrictPosition()
    {
        Vector3 position = transform.position;

        if (Vector3.Distance(position, Vector3.zero) > maxDistance)
        {
            Vector3 direction = (position - Vector3.zero).normalized;
            position = Vector3.zero + direction * maxDistance;
        }

        if (position.y < minHeight)
        {
            position.y = minHeight;
        }

        transform.position = position;
    }

    public void ToggleCameraMode()
    {
        if (isTopDownView)
        {
            transform.position = freeCameraPosition;
            transform.rotation = freeCameraRotation;
        }
        else
        {
            freeCameraPosition = transform.position;
            freeCameraRotation = transform.rotation;

            transform.position = topDownPosition;
            transform.rotation = topDownRotation;
        }

        isTopDownView = !isTopDownView;
    }
}
