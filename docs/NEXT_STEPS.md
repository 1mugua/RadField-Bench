# RadField-Bench 下一步工作计划

状态：执行计划 v0.1

本文档把当前方案转化为可执行的工程、实验和验证任务。完成一项后应更新复选框、产出物和验证结果，不通过阶段门时不进入下一阶段。

## 1. 已确认的 v0.1 决策

- [x] 只做 gamma 辐射，不加入中子、alpha、beta 或核素识别。
- [x] 首版采用 2D 室内 UGV，不先做 UAV 和多机器人。
- [x] 源强使用合成 benchmark 单位：`reference_count_rate_cps_at_1m`。
- [x] 正式 track 使用带噪位姿/里程计；真实位姿只用于 oracle 调试和评测器。
- [x] 累计暴露预算是硬约束；定位准确但超预算仍算失败。
- [x] 先冻结 Python core 和 benchmark 协议，再接 ROS 2/Gazebo。
- [x] OpenMC/Geant4 只作为离线校准和交叉验证工具，不进入每个仿真 tick。

## 2. 当前完成状态

已完成：

- Python editable package 和 CLI；
- scenario schema v0.1 及校验；
- gamma 点源、反平方衰减、材料遮挡和计数噪声；
- 2D 机器人闭环环境；
- random walk、lawnmower、Bayesian grid 三个基线；
- JSON/CSV 结果产物和评测器；
- 三个参考场景；
- 9 个自动化测试；
- Python 3.10/3.12 CI 配置。

当前环境尚未提供：

- ROS 2；
- Gazebo；
- OpenMC；
- Geant4；
- 真实探测器标定数据；
- 隐藏测试服务和排行榜。

## 3. 阶段 M1.5：冻结接口与语义

目标：让不同算法在不阅读内部实现的情况下，也能使用同一个环境和评测器。

### 3.1 Observation contract

- [ ] 新增 `spec/observation.schema.md`。
- [ ] 区分 `pose_estimate`、真实 pose、detector raw counts、count rate 和 exposure cost。
- [ ] 明确 agent 可见字段与 evaluator-only 字段。
- [ ] 明确时间戳、坐标系、采样窗口和单位。
- [ ] 为 observation 增加版本号。

正式 observation 至少包含：

```json
{
  "time_s": 12.5,
  "pose_estimate": {"x": 2.1, "y": 1.8, "yaw": 0.42},
  "count_rate_cps": 37.0,
  "integration_time_s": 0.5,
  "cumulative_exposure": 112.0,
  "remaining_exposure_budget": 618.2
}
```

禁止向 agent 暴露：

- source position；
- source strength；
- true radiation field；
- material attenuation map；
- evaluator hidden labels。

### 3.2 Action contract

- [ ] 新增 `spec/action.schema.md`。
- [ ] 固定 action 为 linear/angular velocity。
- [ ] 明确 action clipping、固定时间步长和倒车行为。
- [ ] 明确碰撞后的机器人状态。
- [ ] episode 终止后再次调用 `step()` 必须产生一致错误。

### 3.3 Metrics contract

- [ ] 新增 `spec/metrics.md`。
- [ ] 严格区分 true field rate、expected detector rate 和 measured count rate。
- [ ] 明确 `success`、`terminated`、`truncated` 和 `failure_reason` 的优先级。
- [ ] 明确“超暴露预算必败”的规则。
- [ ] 增加版本化结果 schema。

### 3.4 M1.5 阶段门

通过条件：

- 一个外部 agent 只依赖文档即可实现 `reset/step`；
- 相同 scenario、seed 和 action 序列得到完全一致的观测；
- 真值不会出现在 agent observation；
- 超预算、碰撞、超时和到达目标的优先级有自动化测试覆盖。

## 4. 阶段 M1.6：完善传感器和运动不确定性

目标：避免当前完美位姿和理想运动让算法结果虚高。

### 4.1 Pose modes

- [ ] `oracle_pose`：真实位姿，仅用于调试和上限实验。
- [ ] `noisy_odometry`：平移噪声、角度噪声和随时间累积的漂移。
- [ ] 在 scenario 中加入 pose noise profile 和随机种子。
- [ ] 输出估计位姿协方差或等价的不确定性描述。

### 4.2 Detector profiles

- [ ] `isotropic_gamma_counter`。
- [ ] `directional_gamma_counter`。
- [ ] low-count/high-noise profile。
- [ ] background-only profile。
- [ ] 统一 detector profile schema。

### 4.3 阶段门

- [ ] 轨迹在 oracle 与 noisy pose 下可分别回放。
- [ ] 传感器 noise seed 与环境 seed 解耦。
- [ ] 不同 integration window 的均值和方差行为有测试。
- [ ] 观测日志包含传感器时间和环境时间。

## 5. 阶段 M2：任务套件

目标：从“能跑仿真”升级为“能公平比较算法”。

### T0 Detector Sanity Check

- [ ] 单源无遮挡距离曲线。
- [ ] 反平方衰减测试。
- [ ] 材料遮挡相对衰减测试。
- [ ] Poisson 计数统计测试。
- [ ] dead-time 和 saturation 测试。

### T1 Radiation Anomaly Detection

- [ ] 背景序列生成器。
- [ ] alarm interface。
- [ ] detection rate、false alarm rate、detection delay 指标。
- [ ] 稳定背景和空间/时间变化背景场景。

### T2 Radiation Field Mapping

- [ ] 统一二维 grid 输出格式。
- [ ] nearest-neighbor baseline。
- [ ] inverse-distance weighted baseline。
- [ ] Gaussian Process baseline。
- [ ] MAE、RMSE、高风险区域 IoU 和 uncertainty calibration 指标。

### T3 Source Localization

- [ ] single-source protocol。
- [ ] two-source protocol。
- [ ] source count precision/recall/F1。
- [ ] 一对一 source matching。
- [ ] location error、strength error 和 confidence 指标。

### T4 Dose-Constrained Exploration

- [ ] 覆盖目标定义。
- [ ] exposure budget hard constraint。
- [ ] no-radiation baseline。
- [ ] oracle-field upper-bound baseline。
- [ ] success、coverage、time、exposure、collision 的 Pareto 输出。

### T5 Radiation-Aware Inspection

- [ ] inspection waypoint schema。
- [ ] 高风险区域优先/规避策略。
- [ ] 漏检率和有效覆盖率。
- [ ] 任务顺序、能耗和累计暴露指标。

## 6. 阶段 M2.1：场景生成与数据切分

目标：让测试结果反映泛化能力，而不是记忆手写地图。

### 6.1 场景生成轴

- [ ] 几何：open room、corridor、warehouse、partitioned room。
- [ ] 源：single、two-source、weak/strong mixed source。
- [ ] 材料：none、concrete、steel、mixed shielding。
- [ ] 背景：low、medium、spatially varying、temporally varying。
- [ ] 传感器：isotropic、directional、high-noise、delayed。
- [ ] 地图：known、partial、unknown。
- [ ] 运动：oracle、noisy odometry、action noise。

### 6.2 Split

- [ ] `train`：公开场景和真值。
- [ ] `validation`：公开场景，部分参数隐藏。
- [ ] `test-iid`：同分布隐藏 seed。
- [ ] `test-ood`：新布局、材料、源数量或噪声。
- [ ] `test-sim2real`：由真实数据统计校准的传感器分布。

### 6.3 目标规模

首批至少 12 个版本化场景：

- 6 个 train；
- 3 个 validation；
- 2 个 test-iid manifest；
- 1 个 test-ood manifest。

- [ ] 新增 scenario template generator。
- [ ] 新增 fixed-seed registry。
- [ ] 新增场景清单和 hash。
- [ ] 禁止通过文件名泄露测试源参数。

## 7. 阶段 M2.2：批量评测和基线报告

目标：一次运行所有场景、基线和 seeds，并生成可读报告。

- [ ] 新增 batch runner。
- [ ] 新增 baseline/scenario/seed 矩阵配置。
- [ ] 新增 `results.csv` 和 `results.json`。
- [ ] 新增均值、标准差、置信区间。
- [ ] 新增按任务、场景族和 split 的聚合。
- [ ] 输出 Pareto 图数据：accuracy、exposure、time、energy。
- [ ] 输出失败案例索引。
- [ ] 加入 random、lawnmower、Bayesian grid、no-radiation 和 oracle 对照。

阶段门：

- [ ] 同一配置重复运行结果一致。
- [ ] 所有 baseline 都只消费 agent observation。
- [ ] 报告能区分“定位成功”和“安全任务成功”。
- [ ] 至少生成一张可用于论文的 baseline table。

## 8. 阶段 M3：高保真物理校准

目标：确认算法差异没有被过大的仿真模型误差掩盖。

### 8.1 首个校准几何

```text
单点 gamma 源
空气环境
单块混凝土板
固定探测器
多个距离与遮挡位置
```

### 8.2 三路比较

- [ ] 当前实时解析模型。
- [ ] OpenMC 离线参考结果。
- [ ] 合规的公开/实验室标定数据。

比较指标：

- 距离趋势；
- 遮挡前后比值；
- 材料相对衰减；
- 计数分布和不确定性；
- 计算时间和可扩展性。

### 8.3 注意事项

- [ ] 不把 count-equivalent cost 写成 Sv/h 或 Gy/h。
- [ ] 记录 OpenMC、材料库和版本。
- [ ] 发布模型适用边界和残差。
- [ ] 不将真实敏感设施 CAD 纳入公开仓库。

阶段门：能够区分算法误差与场模型误差，并且报告中明确两者的来源。

## 9. 阶段 M4：ROS 2/Gazebo 适配

前置条件：M1.5、M1.6、M2 协议已经冻结，并准备好 Ubuntu/WSL2 或 Docker 环境。

### 9.1 ROS 2 接口

- [ ] `/radfield/detector/counts`。
- [ ] `/radfield/detector/count_rate`。
- [ ] `/radfield/pose_estimate`。
- [ ] `/radfield/exposure`。
- [ ] `/radfield/reset`。
- [ ] `/radfield/episode_status`。
- [ ] debug-only ground-truth namespace。

### 9.2 Gazebo 适配原则

- [ ] Gazebo 只负责机器人动力学、碰撞和普通传感器。
- [ ] 辐射场语义与 Python core 共用同一份 scenario contract。
- [ ] 固定步长和同步传感器时间。
- [ ] debug ground truth 默认关闭。
- [ ] ROS 2 结果与 Python core 回放结果可对照。

### 9.3 阶段门

- [ ] 同一场景在 Python core 和 Gazebo 得到一致的场语义。
- [ ] 同一 baseline 可以通过 ROS 2 运行。
- [ ] ROS bag 能转成统一 trajectory.csv。
- [ ] 仿真时间、传感器时间和评测时间不混淆。

## 10. 阶段 M5：真实数据与公开发布

- [ ] 接入 Manchester 仿真探索数据做格式适配。
- [ ] 接入 Manchester 真实机器人辐射采样数据做统计对照。
- [ ] 增加安全实验室标定记录（如具备合规条件）。
- [ ] 检查每份数据、地图、模型和纹理的许可证。
- [ ] 生成数据卡、模型卡和适用边界说明。
- [ ] 建立 hidden test service 或离线受控评测包。
- [ ] 发布 baseline report 和版本化 leaderboard。
- [ ] 撰写 benchmark paper。

## 11. 暂缓事项

在 M2 通过前暂不做：

- [ ] neutron、alpha、beta；
- [ ] radionuclide identification；
- [ ] UAV、空地协同、多机器人；
- [ ] 机器人电子学辐照失效；
- [ ] 真实核设施数字孪生；
- [ ] 复杂 Web UI；
- [ ] 强化学习大规模训练。

这些功能可能进入 v0.2/v0.3，但不应阻塞 v0.1 benchmark。

## 12. 当前执行顺序

接下来按以下顺序实施：

1. 冻结 observation/action/result/metrics 文档。
2. 增加 noisy odometry 和 oracle pose 两种模式。
3. 完成 T0 detector sanity tests。
4. 实现 T2 field mapping 和 GP baseline。
5. 完善 T3 single/two-source localization。
6. 增加 scenario generator 和 12 个场景。
7. 增加 batch evaluator、统计汇总和 baseline report。
8. 增加 no-radiation 与 oracle-field 对照。
9. 在 Ubuntu/WSL2/Docker 中接入 OpenMC 校准案例。
10. 再开始 ROS 2/Gazebo 适配。

## 13. 每周工作节奏建议

每个迭代周期只承诺一个可验证目标：

- 先写 schema 和测试；
- 再写实现；
- 运行固定 seed 回放；
- 更新示例结果；
- 记录已知限制；
- 通过阶段门后再扩展下一层。

不要以“新增代码行数”作为进度标准，应以“新增任务是否可复现、指标是否可解释、失败是否可定位”为标准。

