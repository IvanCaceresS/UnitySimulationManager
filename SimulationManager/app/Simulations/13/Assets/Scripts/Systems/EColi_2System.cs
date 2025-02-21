using Unity.Burst;
using Unity.Collections;
using Unity.Entities;
using Unity.Jobs;
using Unity.Mathematics;
using Unity.Physics;
using Unity.Physics.Extensions;
using Unity.Transforms;
using UnityEngine;

[BurstCompile]
[UpdateInGroup(typeof(SimulationSystemGroup))]
public partial class EColi_2System : SystemBase
{
    protected override void OnUpdate()
    {
        // Comprobamos el estado global
        if (!GameStateManager.IsSetupComplete || GameStateManager.IsPaused)
            return;

        float deltaTime = GameStateManager.DeltaTime;

        // ---------------------------------------------------------------------
        // PASO 1: Construir el NativeParallelHashMap de ParentData a partir de
        // LocalTransform.
        // ---------------------------------------------------------------------
        EntityQuery query = GetEntityQuery(typeof(LocalTransform));
        int capacity = math.max(1024, query.CalculateEntityCount() * 2);
        NativeParallelHashMap<Entity, ParentData> parentMap =
            new NativeParallelHashMap<Entity, ParentData>(capacity, Allocator.TempJob);
        var parentMapWriter = parentMap.AsParallelWriter();
        Dependency = Entities.ForEach((Entity e, in LocalTransform transform) =>
        {
            parentMapWriter.TryAdd(e, new ParentData
            {
                Position = transform.Position,
                Rotation = transform.Rotation,
                Scale    = transform.Scale
            });
        }).ScheduleParallel(Dependency);

        // ---------------------------------------------------------------------
        // PASO 2: Obtener el EntityCommandBuffer para postergar cambios.
        // ---------------------------------------------------------------------
        EndSimulationEntityCommandBufferSystem ecbSystem =
            World.GetOrCreateSystemManaged<EndSimulationEntityCommandBufferSystem>();
        var ecb = ecbSystem.CreateCommandBuffer().AsParallelWriter();
        Dependency=Entities.WithReadOnly(parentMap).ForEach((Entity entity,int entityInQueryIndex,ref LocalTransform transform,ref EColi_2Component organism)=>
        {   
            // Inicializar TimeReference solo una vez.
            if (!organism.TimeReferenceInitialized)
            {
                // Creamos un generador de números aleatorios usando el índice (puedes ajustar el seed según necesites)
                Unity.Mathematics.Random rng = new Unity.Mathematics.Random((uint)(entityInQueryIndex + 1) * 99999);
                float randomMultiplier = rng.NextFloat(0.9f, 1.1f);
                organism.TimeReference *= randomMultiplier;
                organism.TimeReferenceInitialized = true;
            }
            float maxScale=organism.MaxScale;
            organism.GrowthDuration=organism.DivisionInterval=organism.TimeReference*organism.SeparationThreshold;
            if(transform.Scale<maxScale)
            {
                organism.GrowthTime+=deltaTime;
                float t=math.clamp(organism.GrowthTime/organism.GrowthDuration,0f,1f);
                float initialScale=organism.IsInitialCell?maxScale:0.01f;
                transform.Scale=math.lerp(initialScale,maxScale,t);}
if(transform.Scale>=maxScale)
{
    organism.TimeSinceLastDivision+=deltaTime;
    if(organism.TimeSinceLastDivision>=organism.DivisionInterval)
    {
        Unity.Mathematics.Random rng=new Unity.Mathematics.Random((uint)(entityInQueryIndex+1)*99999);
        int s=rng.NextFloat()<0.5f?1:-1;
        Entity c=ecb.Instantiate(entityInQueryIndex,entity);
        LocalTransform ct=transform;
        ct.Scale=0.01f;
        EColi_2Component cd=organism;
        cd.TimeReferenceInitialized = false;
        cd.GrowthTime=0f;
        cd.TimeSinceLastDivision=0f;
        cd.HasGeneratedChild=false;
        cd.Parent=entity;
        cd.IsInitialCell=false;
        cd.SeparationSign=s;
        float3 u=math.mul(transform.Rotation,new float3(0,s,0));
        ct.Position=transform.Position+u*(transform.Scale*0.25f);
        ecb.SetComponent(entityInQueryIndex,c,ct);
        ecb.SetComponent(entityInQueryIndex,c,cd);
        organism.TimeSinceLastDivision=0f;
    }
}
if(!organism.IsInitialCell&&organism.Parent!=Entity.Null&&parentMap.TryGetValue(organism.Parent,out ParentData pd))
{
    if(transform.Scale<organism.SeparationThreshold*maxScale)
    {
        float off=math.lerp(0f,pd.Scale*4.9f,transform.Scale/maxScale);
        float3 u=math.mul(pd.Rotation,new float3(0,organism.SeparationSign,0));
        transform.Position=pd.Position+u*off;
        transform.Rotation=pd.Rotation;
    }
    else organism.Parent=Entity.Null;
}



            // Actualizar componentes mediante el ECB.
            ecb.SetComponent(entityInQueryIndex, entity, transform);
            ecb.SetComponent(entityInQueryIndex, entity, organism);
        }).ScheduleParallel(Dependency);
        ecbSystem.AddJobHandleForProducer(Dependency);

        // ---------------------------------------------------------------------
        // PASO FINAL: Liberar el NativeParallelHashMap.
        // ---------------------------------------------------------------------
        Dependency = parentMap.Dispose(Dependency);
    }
}
