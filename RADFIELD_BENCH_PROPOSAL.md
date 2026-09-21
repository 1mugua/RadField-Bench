# RadField-Bench 项目方案（评审稿）

> 状态：方案评审，尚未进入实现阶段
>
> 项目代号：`RadField-Bench`
>
> 建议全称：Radiation Field Benchmark for Safe Robot Exploration

## 1. 核心定位

RadField-Bench 不是“再写一个辐射传感器插件”，也不是完整的核工程 Monte Carlo 软件。它应被定义为：

> 面向辐射不确定、遮挡和安全约束环境的机器人感知、定位、建图与行动评测基准。

项目交付物由七部分组成：

1. 可版本化的场景与任务规范；
2. 可实时运行的 gamma 辐射场和探测器模型；
3. ROS 2 / Python 统一接口；
4. 标准化仿真轨迹与真实数据适配格式；
5. 可复现的基线算法；
6. 统一评测器和隐藏测试集；
7. 物理校准、真实数据验证和适用边界说明。

## 2. 为什么现在做

已有成果分散在四条链路中：

- EEE Manchester 的 Gazebo 辐射插件已经展示了点源、材料衰减、方向响应和核设施场景仿真；
- RCI_radiation 提供了较新的 ROS 2/Gazebo、Nav2、costmap 和剂量日志工程实现；
- Manchester 已有仿真探索数据和真实反应堆机器人辐射采样数据；
- OpenMC、Geant4 和 NIST XCOM 可作为离线高保真物理与材料参数参考。

但目前缺少一个统一回答以下问题的项目：

> 不同机器人算法在相同辐射场、相同传感器不确定性和相同剂量预算下，谁更安全、更准确、更具泛化能力？

因此，项目的创新重点应是“协议化和可比较性”，而不是单纯增加物理模型复杂度。

## 3. 研究目标

### 3.1 总目标

建立一个开放、可复现、可扩展的核辐射机器人 benchmark，使研究者能够比较：

- 辐射异常检测；
- 辐射场建图；
- 单源与多源定位；
- 剂量约束主动探索；
- 辐射感知导航与巡检。

### 3.2 核心研究问题

**RQ：** 在存在材料遮挡、空间/时间背景变化、探测器噪声和累计剂量约束的条件下，机器人如何利用主动观测完成辐射场估计、源定位和安全行动？

子问题：

1. 轻量实时辐射模型与 OpenMC/Geant4 高保真结果之间的误差是否足以支持机器人算法比较？
2. 哪些主动探索策略能在定位精度、任务时间和累计剂量之间取得更优折中？
3. 在未见过的建筑布局、材料组合、源数量和传感器噪声下，算法是否仍然有效？

## 4. v0.1 的边界

### 纳入范围

- gamma 辐射；
- 2D 室内地面机器人；
- 单源和少量多源；
- 点源及有限近似分布源；
- 空间遮挡、材料衰减和方向响应；
- 稳定或缓慢变化的本底；
- 未知地图或部分已知地图；
- 计数噪声、采样窗、效率、饱和和报警阈值；
- 累计剂量、峰值剂量、时间和能耗约束。

### 明确不纳入 v0.1

- alpha、beta、中子和复杂核素谱识别；
- 每个仿真步执行 Monte Carlo 输运；
- 真实敏感核设施 CAD 和部署细节；
- UAV、空地协同和大规模多机器人；
- 去污、处置和操作机械臂；
- 机器人电子元件的详细辐照失效模型。

这些可以作为 v0.2/v0.3 的扩展，而不是首发承诺。

## 5. 设计原则

1. **算法看不到真值。** 源位置、场真值和真实材料参数只能由评测器使用。
2. **在线与离线分层。** 在线模型保证实时性，OpenMC/Geant4 用于校准和验证。
3. **安全不是附加指标。** 剂量、峰值暴露、越界和碰撞必须进入主评测。
4. **场景泛化优先于场景记忆。** 测试集要按布局、材料、源数量和噪声做 OOD 切分。
5. **基线要跨范式。** 同时提供规则、概率、空间统计和学习方法。
6. **失败必须可解释。** 每次评测需要输出暴露曲线、观测轨迹、失败原因和不确定性。

## 6. 系统架构

### 6.1 场景规范层

使用版本化的 `scenario.yaml` 描述：

- 世界几何和坐标系；
- 可通行区域；
- 材料与衰减参数来源；
- 辐射源、背景和时间行为；
- 机器人和传感器配置；
- 任务、预算、终止条件；
- 随机种子、数据 split 和版本。

场景规范应独立于具体仿真器，使未来可以从 Gazebo 迁移到其他后端。

### 6.2 辐射场层

v0.1 的实时模型由以下组件构成：

- 点源距离衰减；
- 多源叠加；
- 通过材料的射线遮挡与衰减；
- 探测器方向响应；
- 空间/时间背景；
- 可配置的场更新频率。

典型场景使用 OpenMC 或 Geant4 生成离线参考切片，比较实时模型的距离、遮挡和相对强度误差。

### 6.3 探测器层

探测器不直接输出“真实剂量”，而是输出带噪观测：

- 计数率或计数窗口；
- 采样周期；
- 本底率；
- 探测效率；
- 方向响应/准直；
- 延迟；
- 饱和；
- 漏报、误报和报警阈值。

传感器 profile 可参考 IAEA 对 PRD、手持 gamma/neutron 探测器、RID、背包式和车载探测器的分类，但 v0.1 先实现一个 gamma 计数器和一个方向敏感探测器。

### 6.4 机器人与任务层

提供两种接口：

- ROS 2 topic/service/action，用于真实机器人软件栈；
- Gymnasium 风格 `reset()` / `step()` / `observation` / `action` 接口，用于学习和快速实验。

每个任务必须声明：观测空间、动作空间、成功条件、失败条件、episode horizon 和评测字段。

### 6.5 数据和评测层

评测器独立于训练代码，接收 episode 记录，输出标准 JSON 和图表：

- 源定位误差；
- 场建图误差与不确定性校准；
- 任务成功率；
- 累计剂量和峰值剂量；
- 任务时间；
- 能耗；
- 碰撞、禁区进入、失联和超预算次数；
- 推理频率和资源使用。

不建议压成一个不可解释的总分，而应报告 Pareto 前沿：准确度、剂量、时间和能耗之间的折中。

## 7. 任务套件

### T0：Detector Sanity Check

用于验证传感器和物理实现：单源、无遮挡、固定探测器。检查距离衰减、采样噪声、饱和和单位。

### T1：Radiation Anomaly Detection

机器人或固定传感器判断当前观测是否偏离背景。

指标：检出率、误报率、报警延迟、不同本底下的鲁棒性。

### T2：Radiation Field Mapping

机器人根据轨迹和计数观测估计空间辐射场，并输出均值与不确定性。

指标：MAE/RMSE、危险区域 IoU、校准误差、采样预算下的误差下降曲线。

### T3：Source Localization

估计源的数量、位置、强度和置信度。

指标：位置误差、源数识别 F1、强度误差、收敛时间和置信度校准。

### T4：Dose-Constrained Exploration

在累计剂量预算内主动探索并完成定位或覆盖。

指标：成功率、累计剂量、峰值剂量、完成时间、覆盖率、碰撞和超预算率。

### T5：Radiation-Aware Inspection

在已知检查点和未知高风险区域之间规划巡检顺序。

指标：有效覆盖率、漏检率、剂量、总路程、能耗和任务完成时间。

## 8. 场景矩阵和数据切分

不要只随机化源位置，应沿以下轴构造场景：

- 几何：空房间、走廊、仓储区、复杂房间；
- 源：单源、双源、三源、强弱源混合；
- 材料：无遮挡、混凝土、钢、水、多层遮挡；
- 本底：稳定、空间变化、时间波动；
- 传感器：低噪、中噪、方向性、延迟、饱和；
- 地图：已知、部分已知、未知；
- 机器人：速度、定位误差、动作噪声、通信延迟。

建议 split：

- `train`：公开场景和真值；
- `val`：公开场景、隐藏部分参数；
- `test-iid`：同分布但隐藏 seed；
- `test-ood`：新布局、新材料、新源数量或新噪声；
- `test-sim2real`：使用真实数据统计校准的传感器分布。

## 9. 数据格式

一个 episode 至少包含：

```text
scenario.yaml
world.sdf / mesh
robot_pose.parquet
detector_counts.parquet
actions.parquet
map_or_lidar/
exposure.parquet
ground_truth/            # 仅训练或评测端可见
evaluation_manifest.json
```

ROS 2 bag 用于回放；Parquet/NPZ 用于离线学习和统计；所有记录必须带仿真时间、传感器时间、坐标系和版本信息。

## 10. 首发基线

至少提供四类基线：

1. 随机游走和固定栅格扫描；
2. Frontier exploration / radiation-aware frontier；
3. 粒子滤波或贝叶斯源定位；
4. Gaussian Process 建图 + 信息增益规划。

后续再加入深度强化学习、模型预测控制和多机器人策略。这样 benchmark 不会被某一种学习范式垄断。

## 11. 物理和真实数据验证

验证分为三层：

### L1：数学单元验证

验证距离衰减、多源叠加、材料衰减、方向响应和 Poisson 计数统计。

### L2：高保真仿真交叉验证

选择有限的几何、材料和源配置，用 OpenMC/Geant4 生成参考结果，比较实时模型的空间相对误差和遮挡误差。

### L3：实验/真实机器人验证

使用安全、合规的实验室标定数据及 Manchester 机器人辐射数据，比较：

- 距离-计数曲线；
- 遮挡前后相对变化；
- 探测器方向响应；
- 机器人运动造成的采样分布；
- 建图误差和不确定性。

项目必须公开适用边界，不能把“与真实数据有相似趋势”包装成核工程级准确性。

## 12. 推荐技术路线

### v0.1

- ROS 2 + 新版 Gazebo；
- 2D UGV；
- gamma 计数器；
- 单源/少量多源；
- 射线遮挡和材料衰减；
- 五个任务；
- 四个基线；
- CLI 评测器；
- Docker 复现实验。

### v0.2

- 多种 detector profile；
- 动态背景和移动障碍；
- 真实数据统计校准；
- 更复杂的 3D 场和多楼层；
- 中子或简化谱信息的实验性支持。

### v0.3

- UAV/UGV；
- 多机器人和通信受限；
- 机器人感知退化与健康状态；
- 真实机器人闭环验证；
- 社区排行榜和挑战赛。

## 13. 里程碑和阶段门

### M0：规范冻结

产出：项目章程、术语表、场景 schema、任务协议、指标定义、非目标清单。

通过条件：另一个研究者能仅凭文档写出一个兼容场景。

### M1：物理最小闭环

产出：单源、单机器人、单探测器、单场景、可回放数据。

通过条件：T0 单元测试和固定 seed 回放完全一致。

### M2：Benchmark 闭环

产出：T1-T5、四类基线、训练/验证/测试 split、统一评测器。

通过条件：同一提交在干净环境中可重复运行并输出标准结果。

### M3：校准与论文

产出：OpenMC/Geant4 对照、真实数据对照、误差和适用边界报告。

通过条件：能够区分“算法差异”和“仿真模型误差”。

### M4：公开发布

产出：文档、容器、示例、数据集、基线结果、贡献规范和版本策略。

## 14. 主要风险

| 风险 | 后果 | 对策 |
|---|---|---|
| 范围过大 | 永远无法完成首版 | 锁定 gamma + 2D UGV + 5 个任务 |
| 物理过于理想 | 算法结果虚高 | 引入噪声、遮挡、延迟、背景和 OOD split |
| 物理过于复杂 | 无法实时运行 | 在线近似，离线高保真校准 |
| 只有仿真没有现实证据 | 社区信任不足 | 引入实验标定和 Manchester 数据 |
| 只做插件没有 benchmark | 难以形成论文和社区影响 | 优先冻结任务、指标和评测器 |
| 真实设施信息敏感 | 合规与安全风险 | 使用虚构/匿名化场景和公开参数范围 |
| 总分过度简化 | 掩盖剂量与安全问题 | 发布多指标和 Pareto 前沿 |

## 15. v0.1 验收标准

首版不追求“大”，而应满足：

- 12 个版本化场景；
- 5 个任务；
- 4 类基线；
- 1 个 ROS 2 接口和 1 个 Python 接口；
- 1 个统一评测器；
- 公开训练集、验证集和隐藏测试集；
- 固定 seed 可复现；
- 至少一个 OpenMC/Geant4 校准案例；
- 至少一个真实机器人数据对照案例；
- 文档明确列出物理假设与不适用范围。

## 16. 建议的仓库结构

```text
radfield-bench/
├── spec/          # 场景、任务、指标和数据格式
├── worlds/        # 地图、材质、机器人和传感器配置
├── field_models/  # 在线辐射场与离线参考适配
├── sensors/       # 探测器模型
├── tasks/         # T0-T5
├── datasets/      # 生成、转换和回放工具
├── baselines/     # 规则、概率、GP 和学习基线
├── evaluator/     # 评测器与结果 schema
├── calibration/   # OpenMC/Geant4/实验校准
├── containers/    # Docker/CI
└── docs/          # 教程、设计和复现实验
```

## 17. 待确认的关键决策

在进入实现前，需要由项目发起人确认：

1. v0.1 是否严格限定为 gamma，不加入中子或谱识别？
2. 主仿真后端是否采用 ROS 2 + Gazebo Harmonic？
3. 第一优先任务是 source localization，还是 dose-constrained exploration？
4. 是否愿意把真实实验标定作为 v0.1 的必要门槛？
5. 项目首要受众是算法研究者、核工业研发人员，还是机器人软件开发者？
6. 数据集是否采用“公开训练 + 隐藏测试”模式？

我的建议是：全部选择较保守的 v0.1 方案，即 gamma、2D UGV、source localization + safe exploration、ROS 2/Gazebo、OpenMC 校准、Manchester 数据对照、隐藏测试集。

## 参考资料

- [Wright et al., Simulating Ionising Radiation in Gazebo for Robotic Nuclear Inspection Challenges](https://www.mdpi.com/2218-6581/10/3/86)
- [EEEManchester gazebo_radiation_plugin](https://github.com/EEEManchester/gazebo_radiation_plugin)
- [EEEManchester gazebosim_world_generator](https://github.com/EEEManchester/gazebosim_world_generator)
- [RCI_radiation](https://github.com/RCILab/RCI_radiation)
- [Radiation Exposure Reduction During Autonomous Exploration](https://figshare.manchester.ac.uk/articles/dataset/Radiation_Exposure_Reduction_During_Autonomous_Exploration/18782165)
- [3D radiation data gathered robotically at a nuclear test reactor](https://research.manchester.ac.uk/en/datasets/gaussian-process-regression-of-3d-radiation-data-gathered-robotic/)
- [Geant4 overview](https://www.geant4.org/about/)
- [OpenMC documentation](https://docs.openmc.org/en/stable/)
- [NIST XCOM photon cross sections](https://www.nist.gov/pml/xcom-photon-cross-sections-database)
- [Physics-informed radiation multi-source localization](https://link.springer.com/article/10.1007/s41315-025-00461-3)
- [IAEA Nuclear Security Series No. 6](https://www-pub.iaea.org/MTCD/publications/PDF/pub1309_web.pdf)
