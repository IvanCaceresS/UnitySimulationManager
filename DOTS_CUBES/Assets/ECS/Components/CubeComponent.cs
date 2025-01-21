using Unity.Entities;
using Unity.Mathematics;

namespace ECS
{
    public struct CubeComponent : IComponentData
    {
        public float3 moveDirection;
        public float moveSpeed;
    }
}