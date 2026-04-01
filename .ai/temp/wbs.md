# Python 数字员工平台 WBS

## 1. 文档范围与假设

- 本文档用于把 `.ai/temp/architect-optimized.md`、`.ai/temp/package-plan.md` 与 `.ai/temp/plan.md` 转成可开发、可验证的迁移任务。
- 输入优先级：
  - 第一优先：`.ai/temp/architect-optimized.md`
  - 第二优先：`.ai/temp/package-plan.md`
  - 第三优先：`.ai/temp/plan.md`
  - 第四优先：`.ai/temp/cli-spec.md`
- 当前仓库仍缺少正式 `.ai/temp/requirement.md`，因此以下 WBS 只承诺“把现有项目迁移到新架构”，不补充未确认的产品范围。
- 当前代码库已经存在 bootstrap 实现、CLI 协议和一批回归测试，因此任务拆解采用迁移式重构，不采用 greenfield 建设思路。
- 每个任务粒度控制在 `0.5–2 人天`，且必须有可验证交付物。
- 本轮 WBS 的硬约束：
  - 不改变 `work-order` 作为一等业务对象
  - 不把 `workspace` 或聊天 session 提升为业务核心
  - 不继续扩 `application/use_cases/`、`application/services/deps.py`、`runtime/turn_engine.py` 为长期终态
  - 先收紧边界，再扩能力；先兼容迁移，再删除旧入口
  - 所有运行时状态与协调事件约束必须集中在单一结构化模块中，不允许靠分散字符串维护
- MVP 范围限定为：
  - `dectl` 控制面协议保持可用
  - `work-order create|get|list|run|cancel|resume`
  - `RuntimeCell / RuntimeManager`
  - `TurnPipeline`
  - `EventLedger + WorkOrderSnapshot + SessionProjection`
  - `mock` 与 `openai` provider
  - `PolicyEngine` 的 `allow / ask / deny`
  - `watch / tail / replay / doctor` 所需的最小事实源

## 2. 里程碑

| 里程碑 | 目标 | 完成标准 |
|---|---|---|
| M1 | 收紧控制面与应用层边界 | `bootstrap`、`commands / queries`、兼容 shim、CLI/REST facade 就位，旧 `Deps` 不再是唯一入口 |
| M2 | 稳定运行时与审计平面 | `RuntimeCell / RuntimeManager`、`TurnPipeline`、`EventLedger + Projection` 可工作，租户隔离与事件一致性可验证 |
| M3 | 收紧治理边界并预留协调器 | `Provider / Tool / Policy` 三层边界明确，`CoordinatorRuntime` 仅作为可选路径接入，不污染默认主链路 |

## 3. 史诗 / 故事 / 任务拆解

### 史诗 E1：边界收敛与迁移底座

#### 故事 S1：收紧 composition root 与控制面依赖

| 任务 | 预估 | 说明 | 输入 | 输出 | 依赖 | 风险 |
|---|---|---|---|---|---|---|
| T1 | 1 人天 | 新建 `bootstrap/container.py` 与 `bootstrap/factories.py`，把 repo / provider / tool / runtime 的构造逻辑从应用层抽离 | 架构文档第 5、7 节；包结构契约第 3、4 节 | composition root、工厂函数、装配单测 | 无 | 若 container 边界不先冻结，后续 commands / runtime 重构会继续挂回 `Deps` |
| T2 | 1 人天 | 收紧 `request_context.py` 与 `deps.py`，让 CLI / REST 通过 facade 获取能力，而不是直接持有运行时对象 | T1；技术方案 A1 | 兼容层、facade 接口、入口接线修改 | T1 | 兼容入口改动过大容易导致 CLI/REST 全面回归 |
| T3 | 0.5 人天 | 补 `config invalid / input invalid / internal error` 协议回归，确保 container 重构不破坏 CLI 契约 | CLI 规范第 5、6 节；现有集成测试 | Golden / integration tests、错误协议基线 | T1、T2 | 若协议回归未锁住，后续每轮迁移都会扩大排查面 |

#### 故事 S2：拆分 commands / queries 与兼容层

| 任务 | 预估 | 说明 | 输入 | 输出 | 依赖 | 风险 |
|---|---|---|---|---|---|---|
| T4 | 1 人天 | 新建 `application/commands/` 与 `application/queries/`，先拆出 `work_order` 主链路 | 架构文档第 5 节；包结构契约第 4 节；技术方案 A2 | `work_order_commands.py`、`work_order_queries.py`、接口测试 | T1、T2 | 读写拆分不彻底会让旧 `work_order_use_cases.py` 继续膨胀 |
| T5 | 1 人天 | 继续拆出 `session / tool / approval` 的查询与命令面，并更新 CLI/REST 调用路径 | T4；CLI 规范第 2、3 节 | `session_queries.py`、`tool_queries.py`、`approval_commands.py`、命令接线 | T4 | 若 CLI 仍直连旧 use case，后续 runtime 重构收益会被抵消 |
| T6 | 0.5 人天 | 把旧 `application/use_cases/*.py` 降级成 shim，只保留转发和兼容，不再承载核心逻辑 | T4、T5；技术方案 A2 | shim 文件、迁移注释、回归测试 | T4、T5 | 若旧 use case 仍保留写逻辑，最终会形成双入口和行为漂移 |

### 史诗 E2：运行时胶囊与回合流水线

#### 故事 S3：引入 RuntimeCell / RuntimeManager

| 任务 | 预估 | 说明 | 输入 | 输出 | 依赖 | 风险 |
|---|---|---|---|---|---|---|
| T7 | 1 人天 | 定义 `RuntimeCellKey`、`RuntimeCell` 和 cell 内协作者组装契约 | 架构文档第 6、9 节；包结构契约第 5.1 节 | `runtime/cell.py`、协作者协议、单测 | T2、T6 | 若 cell 边界过宽，会把 repo 和业务状态再次塞回 runtime |
| T8 | 1 人天 | 实现 `RuntimeManager` 的 lazy load / invalidate / reload，并补租户隔离与配置失效测试 | T7；技术方案 A3 | `runtime/manager.py`、缓存与失效逻辑、隔离测试 | T7 | key 设计或失效规则错误会造成跨租户污染或热重载失效 |
| T9 | 0.5 人天 | 在 `work-order` 创建与运行路径中记录 `config_snapshot_id` / `profile_version`，把 runtime 查找从“当前配置”改成“配置快照” | 架构文档第 7 节；技术方案 A3 | 领域字段、仓储更新、创建链路测试 | T4、T7 | 若仍依赖可变配置，运行时复现、回放和审计都会不稳定 |

#### 故事 S4：拆分 TurnEngine 为回合流水线

| 任务 | 预估 | 说明 | 输入 | 输出 | 依赖 | 风险 |
|---|---|---|---|---|---|---|
| T10 | 1 人天 | 抽出 `ContextAssembler`、`BudgetController`、`ToolExposurePlanner`，把上下文、预算和工具可见性从单体引擎中拆出 | 架构文档第 3、6、9 节；技术方案 A4 | `runtime/turn/` 子模块、单测 | T8、T9 | 上下文与预算行为若漂移，会直接影响成本和输出稳定性 |
| T11 | 1 人天 | 抽出 `ModelGateway`、`ActionInterpreter`、`SessionRecorder`、`ResultMapper`，形成正式 `TurnPipeline` | T10；包结构契约第 3、5 节 | `runtime/turn/engine.py`、回合集成测试 | T10 | 若 session/event 记录位置不稳定，后续 ledger 接入会出现重复或缺漏 |
| T12 | 1 人天 | 将 `runtime/turn_engine.py` 改成兼容 wrapper，并收紧 `TaskSupervisor` 职责，只负责任务监督、不再承载业务状态机 | T11；技术方案 A4 | 兼容包装器、supervisor 边界调整、回归测试 | T11 | 若 supervisor 继续写业务状态，会破坏 application 与 runtime 的分层 |

### 史诗 E3：事件事实源与查询投影

#### 故事 S5：建立 EventLedger 与 Projection

| 任务 | 预估 | 说明 | 输入 | 输出 | 依赖 | 风险 |
|---|---|---|---|---|---|---|
| T13 | 1 人天 | 定义 `LedgerEvent`、事件仓储与双写入口，把 `run_work_order()` 和回合执行纳入 append-only 事实源 | 架构文档第 8 节；包结构契约第 5.3 节；技术方案 A5 | `observability/ledger.py`、事件 repo、双写测试 | T11、T12 | 若事件类型和字段不冻结，观察、回放和审计都无法稳定实现 |
| T14 | 1 人天 | 建立 `WorkOrderSnapshot` 与 `SessionProjection`，并把 `get/list/tail/export` 切到 projection/ledger 读取 | T13；CLI 规范第 2、5 节 | `observability/projections.py`、查询改造、JSONL 流测试 | T13 | 投影更新若不一致，会出现 snapshot 与 ledger 事实冲突 |
| T15 | 1 人天 | 基于 `EventLedger` 实现 `replay` 与 `doctor` 的最小闭环，支持失败工作单重演和事件缺口检测 | T13、T14；技术方案 A5 | `observability/replay.py`、诊断规则、回放测试 | T14 | 若 replay 不能区分模拟与真实执行，可能产生二次副作用 |

### 史诗 E4：治理边界与协调器增强

#### 故事 S6：收紧 Provider / Tool / Policy 三层边界

| 任务 | 预估 | 说明 | 输入 | 输出 | 依赖 | 风险 |
|---|---|---|---|---|---|---|
| T16 | 1 人天 | 引入 `ProviderCatalog` 与 `factory.py`，让 `ProviderRouter` 只负责选择，不再负责生命周期和配置解析 | 架构文档第 3、9 节；技术方案 A6 | `providers/catalog.py`、`providers/factory.py`、路由重构 | T8、T11 | provider 选择和实例化混在一起会让 runtime cell 失去可缓存边界 |
| T17 | 1 人天 | 拆分 `ToolRegistry` 与 `ToolExecutor`，补充工具暴露前过滤、执行包装和 `dry-run` 稳定协议 | T10、T16；CLI 规范第 2、3 节 | `tools/executor.py`、registry 重构、tool tests | T10、T16 | 若工具定义和执行仍混在一起，policy 无法稳定卡住副作用边界 |
| T18 | 1 人天 | 落地 `PolicyEngine`、`approvals.py`、`redaction.py`，让 `allow / ask / deny` 同时作用于暴露前和执行前两个阶段 | 架构文档第 4、9 节；技术方案 A6 | policy 包、审批/脱敏测试、approval 接线 | T14、T17 | 若审批只在执行前生效，模型仍可能看到不该暴露的工具能力 |

#### 故事 S7：补充 CoordinatorRuntime 可选路径

| 任务 | 预估 | 说明 | 输入 | 输出 | 依赖 | 风险 |
|---|---|---|---|---|---|---|
| T19 | 1 人天 | 新增 `CoordinatorRuntime` 与协调命令入口，但默认仍走单员工主链路，只在显式复杂任务条件下切换 | 架构文档第 4、10 节；技术方案 A7 | `coordinator_runtime.py`、条件切换逻辑、集成测试 | T15、T18 | 若协调器过早入侵默认链路，会把未稳定的主流程再次复杂化 |

## 4. 并行任务与阻塞任务

### 阻塞任务

| 任务 | 原因 | 被阻塞任务 |
|---|---|---|
| T1 | composition root 不收紧，后续所有新包都会重新耦合到旧 `Deps` | T2、T4、T7 |
| T4 | commands / queries 不拆开，应用层无法稳定承接 runtime 和 projection 改造 | T5、T6、T9、T14 |
| T7 | RuntimeCell 未定义，provider/tool/policy 无法作为稳定协作者装配 | T8、T9、T10、T16 |
| T10 | 回合前半段未拆开，预算和工具暴露规则无法独立测试 | T11、T17、T18 |
| T13 | EventLedger 未落地，`tail / replay / doctor` 没有统一事实源 | T14、T15、T19 |
| T16 | provider catalog / factory 未冻结，runtime cell 缓存边界不稳定 | T17、T18 |
| T18 | policy 未统一到暴露前与执行前，协调器与审批都缺统一治理入口 | T19 |

### 可并行任务

| 并行组 | 任务 | 说明 |
|---|---|---|
| G1 | T2 + T3 | entrypoint 收紧与错误协议回归可并行推进 |
| G2 | T5 + T6 | 在 `work_order` 迁移完成后，其他 use case 拆分与 shim 清理可并行推进 |
| G3 | T8 + T9 | `RuntimeManager` 与配置快照传播在 `RuntimeCell` 边界冻结后可并行 |
| G4 | T11 + T16 | 回合后半段拆分与 provider 生命周期收紧可交错推进 |
| G5 | T14 + T17 | projection 查询面和 tool 执行边界在 ledger 与 exposure 稳定后可并行 |

## 5. MVP 首批实现顺序

建议首批实现顺序如下：

1. T1：建立 `bootstrap/container.py` 与 `bootstrap/factories.py`
2. T2：收紧 `request_context.py` / `deps.py` 和入口接线
3. T3：锁定错误协议与配置阻断回归
4. T4：拆出 `work_order commands / queries`
5. T5：拆出 `session / tool / approval` 的命令与查询面
6. T6：把旧 `use_cases/` 降级为 shim
7. T7：定义 `RuntimeCellKey` 与 `RuntimeCell`
8. T8：实现 `RuntimeManager`
9. T9：把配置快照传播到 `work-order` 与 runtime 查找
10. T10：抽出上下文、预算、工具暴露组件
11. T11：补齐模型调用、动作解释、session 记录与结果映射
12. T12：把旧 `turn_engine.py` 改为 wrapper，并收紧 `TaskSupervisor`
13. T13：写入 `EventLedger`
14. T14：切换到 `WorkOrderSnapshot + SessionProjection`
15. T16：完成 provider catalog / factory / router 三段式
16. T17：完成 `ToolRegistry + ToolExecutor`
17. T18：完成 `PolicyEngine + approvals + redaction`
18. T15：补 `replay + doctor`
19. T19：最后接入 `CoordinatorRuntime`

顺序原则：

- 先把边界收紧，再做运行时重排。
- 先稳定单员工主链路，再补治理和协调器。
- 先建立事件事实源，再切观察、回放和诊断。
- 先让旧入口变成 shim，再考虑删除旧代码。

## 6. 验收口径

- M1 验收：
  - CLI / REST 都经由 facade 调用 application 层
  - `application/use_cases/` 只保留兼容转发
  - `Deps` 不再是唯一装配入口
  - `config invalid / input invalid / internal error` 协议不回归
- M2 验收：
  - `RuntimeCell / RuntimeManager` 能按 `tenant + employee + config_version` 复用与失效
  - `TurnPipeline` 可跑通 `create -> run -> tool exposure -> provider call -> session record`
  - `EventLedger + WorkOrderSnapshot + SessionProjection` 一致
  - `session tail --jsonl` 输出稳定
- M3 验收：
  - `Provider / Tool / Policy` 三层不串职责
  - 审批规则能同时影响工具暴露前和执行前
  - `replay / doctor` 可基于 ledger 工作
  - `CoordinatorRuntime` 默认关闭，显式启用时不绕过审批和事件账本
