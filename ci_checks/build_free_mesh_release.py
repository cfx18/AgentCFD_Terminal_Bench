"""Build a NEW versioned task directory; no API, solver or registration overwrite.

All ten IDs stay in the manifest. Only implemented tasks can be loaded; missing
physics/GT/acceptance remains explicit review status, never a smaller denominator.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tomllib

from agentcfd_bench.geometry_assets import candidate
from agentcfd_bench.task_package import PROJECT, load_task, task_digest
from agentcfd_bench.free_mesh_couette import SCHEMA, GROUPS
from agentcfd_bench.public_task import SCHEMA as PUBLIC_SCHEMA, public_text, render

VERSION='free-mesh-v1'

PROTOCOL='''# 公共操作协议

初始文件只有下方列出的只读几何；工作目录为 /work。可查阅提供的通用工具文档，不可获取参考解或历史成绩。
本题提供 blockMesh 网格生成工具；分块、单元数、疏密和数值方法由你决定。几何表面标签用于对应物理边界，不是网格编号要求。
在 0/、constant/、system/ 下创建算例输入。几何会由服务原样放入 constant/triSurface/，不要提交或覆盖该目录。
提交输入只能包含自包含 ASCII 字典和场，支持局部字典值引用；不执行任意脚本、动态代码、外部包含或自带库。
不提交已有体网格、旧时间目录、独立初始通量、附加体积力或运行时函数对象。你可以在输入目录外编写自己的后处理程序。

运行时，将 system/science-action.json 写成 {"action":"run","solver":"icoFoam"}，结束当前回复。
独立服务会执行网格生成、网格质量检查、求解和单元坐标/体积导出；求解器不在 Agent 工作区内。
服务返回真实日志及只读 /artifacts/<run_id>/ 输出，包括最终的速度、压力、单元中心 C 和单元体积 V。
出现错误可以修改后再次提交；同一任务的历史及累计模型调用预算不重置，没有固定失败次数上限。

报告时，将同一提交文件替换为 {"action":"report","run_id":"返回的运行编号","measurements":{...}}。
measurements 的每项为 {"unit":"规定单位","value":数值或向量}，具体字段见下方观测要求。
这些是提交接口示意，不是 OpenFOAM 配置示例。不要将文字说明、Markdown 围栏或 NaN 写进 JSON。
验收器会独立读取实际输出，不能用手填数据或解析解代替仿真结果；错误反馈来自本次提交。
'''

OBSERVATIONS='''# 定量观测要求

取实际计算至 2 s 的最终场。对单元量 q，体积平均为 sum(V_i*q_i)/sum(V_i)，不是单元数平均。

|字段|单位|定义|
|---|---|---|
|final_time|s|实际最终物理时刻|
|cell_count|1|实际单元数，仅统计，不要求等于某个参考数量|
|volume|m3|实际单元体积之和|
|U_volume_mean|m/s|速度三分量的体积平均，三元素数组|
|Ux_volume_rms|m/s|sqrt(sum(V_i*Ux_i^2)/sum(V_i))|
|transverse_velocity_rms|m/s|sqrt(sum(V_i*(Uy_i^2+Uz_i^2))/sum(V_i))|
|p_volume_mean|m2/s2|实际运动学压力的体积平均|
|ux_final_initial_residual|1|最终时间步最后一次 Ux 方程求解日志的 Initial residual|

残差仅报告，不等于物理正确。报告数值允许 1e-6 绝对误差加 1e-5 相对误差。
物理验收在实际单元坐标比较速度与独立解析基准，并采用体积权重；不按参考单元顺序或网格相似度评分。
速度的体积加权均方根误差和最大绝对误差均须不超过 0.005 m/s；横向速度均方根须不超过 1e-6 m/s。
只有物理条件、真实执行、物理精度和报告真实性全部满足才算通过。
'''


def write(root, name, text):
    path=root/name
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as handle: handle.write(text)


def instruction(project, task_id):
    old=project/'task-drafts/geometry-only-free-mesh-v1'/task_id/'instruction.md'
    lines=[line for line in old.read_text().splitlines() if '【作者审阅' not in line]
    text='\n'.join(lines).replace('提交接口与观测格式见独立运行协议。','')
    text=text.replace('按独立运行协议输出指定物理观测。','')
    if task_id=='s-202':
        text+='''

水从下部水域左侧流入，速度 (0.001,0,0) m/s，入口温度 300 K；初始水流速度也为 (0.001,0,0) m/s。
空气从上部空气域左侧流入，速度 (0.1,0,0) m/s，入口温度 300 K；初始空气速度也为 (0.1,0,0) m/s。
两股流体均从各自右侧流出；正常流出时速度和温度法向零梯度，回流速度为零、回流温度为 300 K。
所有流体接触的实体壁面静止无滑移；除指定加热面和流体进出口外，外表面均绝热。
除已指定接触热阻的加热体—左固体接触外，其他流固及固固接触均保持温度与法向热通量连续。
'''
    if task_id=='s-204':
        text+='''

初始空气绝对压力为 100000 Pa；腔体密闭，无质量进出。初始湍动能为 3.75×10⁻⁴ m²/s²，比耗散率为 0.12 s⁻¹，湍流普朗特数为 0.85。
绝对压力与温度共同确定初始空气质量；不能把压力的数值基准当成允许任意改变气体质量的自由度。
'''
    return public_text(text.strip()+'\n')


def build(project, output):
    project,output=Path(project),Path(output)
    registered=tomllib.loads((project/'tasks/dataset.toml').read_text())['tasks']
    # Validate sources before creating anything.
    rows=[(row['id'],load_task(row['id'])) for row in registered]
    values={name:(candidate(task),instruction(project,name)) for name,task in rows}
    output.mkdir(parents=True,exist_ok=False)
    registry=['[dataset]','name = "science-free-mesh-v1"','']
    review={'version':VERSION,'registered':len(rows),'paid_ready':False,'tasks':{}}
    for name,task in rows:
        root=output/name
        geometry,text=values[name]
        write(root,'instruction.md',text)
        for path,value in geometry['public_files'].items(): write(root,path,value)
        status='implemented' if name=='s-001' else 'review'
        review['tasks'][name]={'status':status,'source_task':task.binding,
                              'native_qualified':False,'geometry':geometry['review'],
                              'blockers':([] if name=='s-001' else ['cross_mesh_acceptance_and_reference_controls'])}
        if name=='s-202': review['tasks'][name]['blockers']+=['pressure_convention_and_initialization_review']
        if name=='s-204': review['tasks'][name]['blockers']+=['old_1000_iteration_reference_not_steady_ground_truth']
        if name=='s-001':
            write(root,'protocol.md',PROTOCOL)
            write(root,'observations.md',OBSERVATIONS)
            public={'schema':PUBLIC_SCHEMA,'texts':['instruction.md','protocol.md','observations.md'],
                    'assets':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in geometry['public_files'].items()}}
            write(root,'public-task.json',json.dumps(public,indent=2)+'\n')
            write(root,'environment/report-schema.json',json.dumps(SCHEMA,indent=2)+'\n')
            write(root,'tests/acceptance.py','from agentcfd_bench.free_mesh_couette import *\n')
            write(root,'solution/reference.py','from agentcfd_bench.free_mesh_reference import *\n')
            write(root,'README.md','# Free mesh Couette\n\nImplementation candidate; native qualification and paid launch are separate.\n')
            commands=[['mesh','blockMesh'],['mesh_check','checkMesh'],['solver','icoFoam'],
                      ['centres','postProcess','-func','writeCellCentres','-latestTime'],
                      ['volumes','postProcess','-func','writeCellVolumes','-latestTime']]
            config=f'''schema_version = "1.4"
[metadata]
version = "{VERSION}"
runtime = "{task.identity['runtime']}"
native_commands = {json.dumps(commands)}
artifact_fields = ["U", "p", "C", "V"]
qualification_seconds = 300
[metadata.native_completion]
kind = "transient"
end = 2.0
tolerance = 1e-8
early_convergence = false
[metadata.acceptance_groups]
report = {json.dumps(GROUPS['report'])}
physical = {json.dumps(GROUPS['physical'])}
[verifier]
environment_mode = "separate"
[verifier.environment]
network_mode = "no-network"
'''
            write(root,'task.toml',config)
            render(root)  # The exact renderer used for the actual model prompt.
        registry+=['[[tasks]]',f'id = "{name}"',f'status = "{status}"',
                   'digest = "'+task_digest(root)+'"','']
    write(output,'dataset.toml','\n'.join(registry))
    write(output,'author-review.json',json.dumps(review,ensure_ascii=False,indent=2)+'\n')
    return {'output':str(output),'registered':len(rows),'implemented':['s-001'],
            'review':[name for name,_ in rows if name!='s-001'],'paid_ready':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(build(PROJECT,args.output),ensure_ascii=False,indent=2))
