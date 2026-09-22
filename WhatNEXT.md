现在最重要的不是立刻安装 ROS 2/Gazebo，而是把当前“能运行的仿真核心”升级成“定义清楚、可以公平比较的 benchmark”。

当前项目状态是：

```text
M0 方案设计             已完成
M1 Python 最小闭环       已完成
M1.5 协议与语义冻结       下一步
M2 完整 benchmark         尚未完成
M3 物理校准与真实数据     尚未完成
M4 ROS 2/Gazebo 集成      尚未开始
M5 论文与公开发布         尚未开始
```

目前已经通过 `9 passed`，包含场景解析、辐射衰减、材料遮挡、随机探测器、机器人闭环、基线和结果输出。当前实现记录在 [IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md)。

**一、下一步先冻结五个关键决策**

这五个决策不冻结，后面写得越多，返工越大。

1. **源强单位**

当前使用：

```yaml
reference_cps_at_1m: 160.0
```

它代表“距离 1 m 处的参考计数率”，不是 Bq、Gy/h 或 Sv/h。

我的建议是：

```yaml
strength:
  unit: "reference_count_rate_cps_at_1m"
  value: 160.0
  semantics: "synthetic benchmark unit"
```

v0.1 明确使用合成计数率，不声称真实剂量。之后通过 OpenMC 和实验数据建立校准层，而不是现在就伪装成物理剂量。

2. **机器人位姿是否完美**

当前机器人可以直接看到自己的真实位姿。对于 source localization 这会过于理想。

建议提供两个模式：

```text
oracle_pose       真实位姿，仅用于算法调试
noisy_odometry    带漂移和噪声的里程计，用于正式 benchmark
```

正式结果必须使用 `noisy_odometry`，否则无法评估感知、定位和辐射估计之间的耦合。

3. **剂量预算是否为硬约束**

建议明确：

> 找到源但超过剂量预算，仍然算任务失败。

刚才 Bayesian baseline 已经暴露了这个问题：它定位误差很小，但暴露超过预算，所以总体任务必须失败。这个语义现在已经修正。

4. **v0.1 是否支持多源**

我的建议：

```text
T3-single-source       v0.1 必须完成
T3-two-source          v0.1 必须包含
T3-many-source         v0.2
```

算法接口从第一天支持 source list，但首版不要求解决任意数量的复杂多源问题。

5. **主运行环境**

当前 Windows 环境适合 Python core 开发，但不适合作为 ROS 2/Gazebo 主环境。

建议：

```text
Windows：Python core、数据处理、文档
Ubuntu/WSL2：ROS 2、Gazebo、OpenMC、后续集成
```

不要先在 Windows 上强行安装整套 ROS/Gazebo。那会把时间消耗在环境问题上。

**二、下一阶段 M1.5：协议冻结**

这一阶段的目标是把接口写清楚，而不是增加很多功能。

需要补齐四份规范：

```text
spec/
├── scenario.schema.md
├── observation.schema.md
├── action.schema.md
├── result.schema.md
└── metrics.md
```

当前已经有场景和结果说明，但还需要明确：

### Observation

正式观测应该区分：

```text
pose_estimate
odometry_covariance
detector_counts
detector_count_rate
timestamp
remaining_budget
```

并明确哪些字段对 agent 可见，哪些只对 evaluator 可见。

例如：

```json
{
  "time_s": 12.5,
  "pose_estimate": {
    "x": 2.1,
    "y": 1.8,
    "yaw": 0.42
  },
  "count_rate_cps": 37.0,
  "integration_time_s": 0.5,
  "remaining_exposure_budget": 618.2
}
```

不能把下面这些内容放进 observation：

```text
source position
source strength
true radiation field
material attenuation map
```

### Action

需要固定动作接口：

```json
{
  "linear_velocity_mps": 0.4,
  "angular_velocity_rps": 0.2
}
```

并定义：

- 速度是否自动裁剪；
- 碰撞后是否停止；
- 是否允许倒车；
- 每个动作持续多久；
- 仿真是否固定步长；
- 终止后是否允许继续调用 `step()`。

### Metrics

需要将以下三种量严格分开：

```text
true field rate
expected detector rate
measured detector rate
```

当前代码已经有前两层和测量值，但命名和文档还要统一，否则以后很容易把“传感器计数”误称为“剂量”。

**三、然后补齐任务套件**

当前代码已经能运行 source localization 和 safe exploration 的雏形，但还不是完整任务套件。

建议按以下顺序实现。

### T0：Detector Sanity Check

目标是验证仿真模型，不测试智能算法。

需要测试：

- 距离变为两倍，期望计数率是否约降为四分之一；
- 增加遮挡材料后，计数率是否下降；
- 增加背景后，计数率均值是否上升；
- 计数窗口变化后，方差是否符合 Poisson 直觉；
- 饱和和 dead-time 是否行为稳定；
- 固定随机种子是否完全复现。

### T1：Anomaly Detection

输入：

```text
背景观测序列 + 当前计数
```

输出：

```text
alarm: true/false
confidence
alarm_time
```

指标：

- detection rate；
- false alarm rate；
- detection delay；
- 不同背景强度下的鲁棒性。

### T2：Radiation Field Mapping

这是当前还没有实现的核心任务。

最小版本不需要一开始上复杂深度模型，可以先实现：

- nearest-neighbor map；
- inverse-distance weighted map；
- Gaussian Process map；
- known-map 与 unknown-map 两种设置。

输出：

```text
每个网格单元：
  estimated_count_rate
  uncertainty
```

指标：

- MAE；
- RMSE；
- 高风险区域 IoU；
- 不确定性校准；
- 采样数量与误差的关系。

### T3：Source Localization

当前已有 maximum-observed 和 Bayesian grid baseline，但需要改进：

- single-source；
- two-source；
- 源数量估计；
- 源位置；
- 源强度；
- 置信度；
- 不同噪声和遮挡条件下的表现。

对多源任务不能只取每个真源最近的预测点，否则一个预测点可能被重复匹配。应实现一对一匹配，并报告：

```text
source count precision / recall / F1
location error
strength error
```

### T4：Dose-Constrained Exploration

这是项目最有辨识度的任务。

任务不是单纯“找到最高辐射点”，而是：

> 在不超过暴露预算的条件下，最大化信息获取或完成区域探索。

指标至少包括：

```text
mission success
cumulative exposure
peak exposure
time
coverage
collision count
budget violation
```

**四、建立真正的场景矩阵**

当前只有三个手写场景，下一步需要至少形成 12 个场景。

建议第一批场景矩阵如下：

| 变量 | 设置 |
|---|---|
| 几何 | open room、corridor、warehouse、partitioned room |
| 源数量 | 1、2 |
| 遮挡 | none、concrete、steel、mixed |
| 本底 | low、medium、spatially varying |
| 探测器 | isotropic、directional、high-noise |
| 地图 | known、partial、unknown |
| 任务 | localization、mapping、safe exploration |

不要手工复制 12 份 YAML。应增加 scenario generator：

```text
scenario template
    -> parameter grid
    -> fixed seed
    -> scenario_id
    -> train/validation/test split
```

建议命名：

```text
train_open_room_single_001
train_shielded_two_source_001
validation_corridor_single_001
test_ood_material_mix_001
test_ood_source_count_001
```

测试集可以先在仓库里只放 manifest，不公开源参数；真正的隐藏测试服务以后再做。

**五、建立 baseline report**

下一步不能只跑单个场景。需要一次性运行：

```text
所有场景
× 所有 baseline
× 多个 seeds
```

输出一个表格：

| Scenario | Baseline | Success | Mean error | Exposure | Time | Collision |
|---|---|---:|---:|---:|---:|---:|

首批 baseline 建议为：

1. random walk；
2. lawnmower；
3. Bayesian grid；
4. oracle planner，作为上限参考。

`oracle planner` 很重要：它可以看到真实辐射场，只用于估计“任务本身的可行上限”，不能作为普通算法参与排行榜。

还需要加一个：

```text
no-radiation baseline
```

它可以证明辐射感知是否真的降低了暴露，而不是单纯改变轨迹。

**六、做第一次物理校准**

这一步要在 ROS/Gazebo 之前做。

建议使用一个最小校准案例：

```text
点源
空气
单块混凝土板
固定探测器
多个距离点
```

比较三种结果：

```text
实时解析模型
OpenMC 参考结果
真实/公开实验数据
```

第一阶段不要追求绝对剂量一致，先比较：

- 距离趋势；
- 遮挡前后比值；
- 不同材料相对衰减；
- 传感器计数统计分布。

OpenMC 比 Geant4 更适合作为第一个适配器，因为当前 benchmark 主要需要光子场分布和材料遮挡参考，不需要立刻建立复杂探测器几何。

这一步需要 Ubuntu/WSL2 或 Docker 环境。当前 Windows 环境没有 OpenMC 和 Geant4，因此这里是目前真正的外部环境依赖。

**七、再做 ROS 2/Gazebo 适配**

顺序应该是：

```text
Python core contract
    -> ROS 2 message/service contract
    -> Gazebo world/plugin
    -> ROS 2 replay
    -> same baseline runs in Gazebo
```

而不是重新在 Gazebo 里定义一套不同的物理和任务语义。

ROS 2 适配至少需要：

```text
/radfield/detector/counts
/radfield/detector/count_rate
/radfield/pose_estimate
/radfield/exposure
/radfield/reset
/radfield/episode_status
```

机器人控制可以先使用：

```text
/cmd_vel
/odom
/tf
```

Gazebo 插件只负责：

- 读取机器人真实位姿；
- 调用或复现辐射场模型；
- 发布探测器观测；
- 发布 ground truth 到 debug-only namespace；
- 接受 reset 和 scenario config。

正式评测时，ground truth topic 必须关闭或隔离，避免算法偷看真值。

**八、当前暂时不要做的事**

至少在 M2 之前，不建议：

- 加 neutron；
- 加 alpha/beta contamination；
- 做核素识别；
- 做 UAV；
- 做多机器人协同；
- 做精美 Web UI；
- 做复杂的 Unreal 场景；
- 做真实核设施数字孪生；
- 直接声称结果是 Sv/h、Gy/h；
- 直接训练强化学习模型。

这些内容不是没有价值，而是会掩盖 benchmark 最核心的协议和验证问题。

**九、我建议的近期执行顺序**

下一轮应按这个顺序实施：

1. 冻结 observation/action/result/metrics 协议。
2. 加入 noisy odometry 和 oracle pose 两种模式。
3. 明确 exposure 的三层语义和硬预算规则。
4. 实现 T0 detector sanity tests。
5. 实现 T2 radiation field mapping。
6. 完善 T3 single/two-source localization。
7. 增加 scenario generator 和 12 个场景。
8. 增加 batch runner 和 baseline report。
9. 增加 oracle/no-radiation 对照组。
10. 在 Ubuntu/WSL2 上接 OpenMC 做第一个校准案例。
11. 再决定 ROS 2/Gazebo 的具体落地方式。

换句话说，下一阶段的目标不是“让机器人看起来更真实”，而是：

> 让任何研究者拿到一个场景、一个 agent 和一个结果文件，都能知道它做了什么、看到了什么、为什么成功或失败，以及这个分数是否可信。

目前最适合直接进入实现的是第 1 到第 8 项。需要你确认的只有五个默认决策：

```text
gamma-only v0.1
synthetic count-rate unit
noisy odometry as formal track
dose budget as hard constraint
Python core first, ROS 2/Gazebo later
```

这五项如果没有异议，下一轮就应继续实现协议冻结、位姿噪声、field mapping 和 batch evaluator。