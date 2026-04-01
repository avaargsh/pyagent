# Python 数字员工平台技术方案

## 1. 文档范围与输入

- 本文档用于把 `.ai/temp/architect-optimized.md` 与新版 `.ai/temp/package-plan.md` 映射为可执行的迁移路径。
- 输入优先级：
  - 第一优先：`.ai/temp/architect-optimized.md`
  - 第二优先：`.ai/temp/package-plan.md`
  - 第三优先：`.ai/temp/cli-spec.md`
  - 第四优先：`.ai/temp/wbs.md`
- 当前仓库仍缺少正式 `.ai/temp/requirement.md`，因此本文只定义“如何从当前代码演进到目标结构”，不补充未确认的产品能力。
- 当前仓库已经存在一批 bootstrap 实现，所以本方案按“迁移式重构”制定，而不是按 greenfield 建设制定。

## 2. 实施总原则

- 先收紧边界，再扩能力。
- 先改 composition root，再改应用层，再改 runtime。
- 先双写和兼容，再删除旧入口。
- 先打通单员工主链路，再引入协调器。
- 所有结构性重构都要配套 integration tests，不能只依赖单测。
- 所有运行时状态名和协调事件名都要先进入统一约束模块，再允许被 application/runtime/observability 引用。

固定实施顺序：

1. 收紧 `Deps` 与 composition root
2. 拆分 `commands / queries`
3. 引入 `RuntimeCell / RuntimeManager`
4. 拆 `TurnEngine` 为回合流水线
5. 落 `EventLedger + Projection`
6. 收紧 `Provider / Tool / Policy`
7. 最后补 `CoordinatorRuntime`

## 3. 迁移阶段与文件清单

### A1：收紧 composition root 与依赖装配

目标：

- 让 `build_deps()` 不再直接成为所有业务代码的唯一入口
- 把当前“读取配置 + 校验 + repo/provider/tool/runtime 装配”收进真正的 composition root

新增文件：

- `src/digital_employee/bootstrap/container.py`
- `src/digital_employee/bootstrap/factories.py`

修改文件：

- `src/digital_employee/application/services/request_context.py`
- `src/digital_employee/application/services/deps.py`
- `src/digital_employee/api/cli/main.py`
- `src/digital_employee/api/rest/deps.py`

关键步骤：

1. 在 `bootstrap/container.py` 中定义 `build_control_plane_container()`
2. 把 repo / provider / tool / runtime 的构造函数下沉到 `bootstrap/factories.py`
3. 让 CLI / REST 只拿 `CommandFacade` 与 `QueryFacade`
4. 保留 `Deps` 作为兼容对象，但新代码不再直接依赖它

验证重点：

- CLI 主链路无行为回归
- 配置错误、租户隔离、exit code 规则保持一致

### A2：拆分 application 为 commands / queries

目标：

- 把当前 `use_cases/*.py` 里的读写逻辑分离
- 避免 `work_order_use_cases.py` 继续增长为协调器、artifact、background runner 的杂糅文件

新增文件：

- `src/digital_employee/application/commands/work_order_commands.py`
- `src/digital_employee/application/commands/approval_commands.py`
- `src/digital_employee/application/queries/work_order_queries.py`
- `src/digital_employee/application/queries/session_queries.py`
- `src/digital_employee/application/queries/tool_queries.py`

修改文件：

- `src/digital_employee/application/use_cases/work_order_use_cases.py`
- `src/digital_employee/application/use_cases/session_use_cases.py`
- `src/digital_employee/application/use_cases/tool_use_cases.py`
- `src/digital_employee/api/cli/work_order_cmd.py`
- `src/digital_employee/api/cli/session_cmd.py`
- `src/digital_employee/api/cli/tool_cmd.py`

关键步骤：

1. 把 `create/run/cancel/resume` 移到 `commands/`
2. 把 `get/list/tail/export` 移到 `queries/`
3. 旧 `use_cases/` 文件只保留向新服务的转发
4. 统一由 `application/services/` 暴露 facade

验证重点：

- `work-order create|get|list|run`
- `session get|list|tail`
- CLI / REST 都不再直接依赖旧 `use_cases` 细节

### A3：引入 RuntimeCell / RuntimeManager

目标：

- 把“租户 + 员工画像 + 配置快照”级别的执行环境做成可缓存、可失效、可热重载的运行时胶囊

新增文件：

- `src/digital_employee/runtime/cell.py`
- `src/digital_employee/runtime/manager.py`
- `src/digital_employee/runtime/session_runtime.py`

修改文件：

- `src/digital_employee/application/services/deps.py`
- `src/digital_employee/application/services/request_context.py`
- `src/digital_employee/agents/assembler.py`
- `src/digital_employee/providers/router.py`
- `src/digital_employee/tools/registry.py`

关键步骤：

1. 定义 `RuntimeCellKey(tenant, employee_id, config_version)`
2. 在 `RuntimeCell` 中组装 provider/tool/policy/memory/hook/turn pipeline
3. 用 `RuntimeManager.get_cell()` 取代“每个请求都重新拼一次 runtime”
4. 为配置更新预留 `reload_cell()` 和失效钩子

验证重点：

- 同一租户和员工重复请求复用 cell
- 不同租户不共享 runtime state
- 配置版本变化会触发 cell 失效

### A4：拆 TurnEngine 为回合流水线

目标：

- 把当前过重的 `runtime/turn_engine.py` 拆成可替换的回合组件

新增文件：

- `src/digital_employee/runtime/turn/engine.py`
- `src/digital_employee/runtime/turn/context_assembler.py`
- `src/digital_employee/runtime/turn/budget_controller.py`
- `src/digital_employee/runtime/turn/model_gateway.py`
- `src/digital_employee/runtime/turn/action_interpreter.py`
- `src/digital_employee/runtime/turn/session_recorder.py`
- `src/digital_employee/runtime/turn/result_mapper.py`

修改文件：

- `src/digital_employee/runtime/turn_engine.py`
- `src/digital_employee/memory/context_compactor.py`
- `src/digital_employee/tools/exposure.py`
- `src/digital_employee/runtime/budget.py`

关键步骤：

1. 保留现有 `TurnEngine.run()` 签名
2. 把上下文准备、预算检查、工具暴露、模型调用、tool 解释、session/event 记录逐步抽离
3. 让 `runtime/turn_engine.py` 最终仅转发到 `runtime/turn/engine.py`
4. 把 `TaskSupervisor` 留在回合外，不继续侵入业务状态流转

验证重点：

- `tests/unit/runtime/test_turn_engine.py`
- 工具调用回合
- budget warning
- context compaction

### A5：落 EventLedger 与 Projection

目标：

- 把当前 `SessionRecord(session + events)` 升级为正式事实源和查询视图

新增文件：

- `src/digital_employee/observability/ledger.py`
- `src/digital_employee/observability/projections.py`
- `src/digital_employee/observability/replay.py`
- `src/digital_employee/infra/repositories/events.py`
- `src/digital_employee/infra/repositories/projections.py`

修改文件：

- `src/digital_employee/domain/events.py`
- `src/digital_employee/domain/session.py`
- `src/digital_employee/application/queries/session_queries.py`
- `src/digital_employee/application/commands/work_order_commands.py`
- `src/digital_employee/infra/repositories/work_orders.py`
- `src/digital_employee/infra/repositories/sessions.py`

关键步骤：

1. 定义统一 `LedgerEvent`
2. `run_work_order()` 和 `TurnPipeline` 改成先写 ledger，再更新 projection
3. 双写 `SessionRecord` 与 `EventLedger`，直到查询面迁移完成
4. `session get/list/tail/export` 全部从 projection/ledger 读取
5. 把 `coordination` 作为 `SessionProjection` 的正式字段，而不是只停留在 `session.metadata`

验证重点：

- 事件顺序稳定
- session tail 能稳定输出 JSONL
- 回放输入可从 ledger 还原

### A6：收紧 Provider / Tool / Policy 三层边界

目标：

- 避免 provider、tool、policy 继续相互吞职责

新增文件：

- `src/digital_employee/providers/catalog.py`
- `src/digital_employee/providers/factory.py`
- `src/digital_employee/tools/executor.py`
- `src/digital_employee/policy/engine.py`
- `src/digital_employee/policy/approvals.py`
- `src/digital_employee/policy/redaction.py`

修改文件：

- `src/digital_employee/providers/router.py`
- `src/digital_employee/tools/registry.py`
- `src/digital_employee/tools/handlers/*.py`
- `src/digital_employee/runtime/turn/model_gateway.py`
- `src/digital_employee/runtime/turn/action_interpreter.py`

关键步骤：

1. `ProviderCatalog` 只管理 provider/model 槽位元数据
2. `ProviderRouter` 只负责选择，不负责实例生命周期
3. `ToolRegistry` 只存定义，执行逻辑下沉到 `ToolExecutor`
4. `PolicyEngine` 同时参与“工具暴露前过滤”和“执行前最终检查”

验证重点：

- deny 规则能在 tool exposure 前生效
- approval_required 工具不会绕过 `PolicyEngine`
- provider 切换不会影响 tool registry

### A7：补 CoordinatorRuntime

目标：

- 为复杂工作单预留多员工协作能力，但不影响默认单员工主链路

新增文件：

- `src/digital_employee/runtime/coordinator_runtime.py`
- `src/digital_employee/application/commands/coordinated_work_order_commands.py`

修改文件：

- `src/digital_employee/application/commands/work_order_commands.py`
- `src/digital_employee/runtime/manager.py`
- `src/digital_employee/agents/prompts.py`

关键步骤：

1. 默认仍走单员工路径
2. 只有显式匹配复杂任务条件时才切到协调器
3. 协调器只做任务拆分、员工选择、预算与聚合
4. 工具执行仍由 worker employee runtime 完成
5. `CoordinatorPlan`、`execution_mode`、`dispatch_mode`、`coordinator.*` 事件名全部引用统一约束模块

验证重点：

- 协调器不绕过审批
- 子任务事件能回流到主工单账本
- 失败回滚只影响对应子任务

## 4. 依赖顺序

必须按以下顺序推进：

1. `A1 composition root`
2. `A2 commands / queries`
3. `A3 RuntimeCell / RuntimeManager`
4. `A4 TurnPipeline`
5. `A5 EventLedger / Projection`
6. `A6 Provider / Tool / Policy`
7. `A7 CoordinatorRuntime`

原因：

- 没有 `A1`，后续所有边界都会继续耦合在 `Deps` 上
- 没有 `A2`，应用层依旧会把读写和执行混在一起
- 没有 `A3`，运行时就无法以“租户 + 员工 + 快照”作为稳定装配单位
- 没有 `A5`，观察、回放、诊断永远没有统一事实源
- `A7` 必须最后做，否则会在未稳定的单员工主链路上叠加复杂性

## 5. 风险点与回退方案

### 风险 1：composition root 重构导致 CLI / REST 全面回归

- 回退方式：
  - 保留旧 `build_deps()` 包装器
  - 新旧 facade 并存一轮

### 风险 2：TurnEngine 拆分过程中出现行为漂移

- 回退方式：
  - 保留 `runtime/turn_engine.py` 作为 golden wrapper
  - 让新 `runtime/turn/engine.py` 在行为稳定前只作为内部实现

### 风险 3：EventLedger 上线后查询结果不一致

- 回退方式：
  - 维持 `session projection + SessionRecord` 双写
  - `session get/list` 在一轮版本内保留旧 projection 读取路径

### 风险 4：RuntimeCell 缓存导致租户隔离或配置刷新失效

- 回退方式：
  - 先把 `RuntimeManager` 放在内存实现
  - 只在 cell key 和失效逻辑验证通过后再引入更复杂缓存策略

### 风险 5：PolicyEngine 过晚落地导致工具边界再次变脏

- 回退方式：
  - 即使审批流未完成，也先把 `allow / ask / deny` 接口冻结
  - 工具暴露和执行前检查统一走同一入口

## 6. 需要优先补充的测试

- `tests/integration/cli/test_error_handling.py`
  - 配置错误、输入错误、未知错误协议
- `tests/integration/cli/test_work_order_commands.py`
  - create/get/list/run/cancel/resume
- `tests/unit/runtime/test_turn_engine.py`
  - 重构前作为行为基线
- `tests/unit/runtime/test_runtime_manager.py`
  - lazy load / invalidate / reload
- `tests/unit/tools/test_exposure.py`
  - deny-before-exposure
- `tests/unit/policy/test_engine.py`
  - allow/ask/deny
- `tests/integration/session/test_tail_jsonl.py`
  - projection + ledger
- `tests/integration/work_orders/test_event_consistency.py`
  - `work_order snapshot` 与 `event ledger` 一致性
- `tests/integration/work_orders/test_tenant_runtime_isolation.py`
  - RuntimeCell 租户隔离

测试优先级：

1. 协议不回归
2. 租户和审批不越界
3. 回合执行不漂移
4. 事件事实源可回放

## 7. 最终落地建议

- 这次“对齐新架构”不建议一次性大改代码。
- 最合理的落地方式是先完成 `A1 + A2 + A3`，把边界收紧；然后再做 `A4 + A5`，把执行平面和审计事实源稳定下来；最后才引入 `A6 + A7` 的治理和协调器增强。
- 如果只能做最小闭环，优先做这三件事：
  1. composition root 收敛
  2. `work_order` 命令 / 查询拆分
  3. `RuntimeCell` 引入

完成这三步之后，当前项目就会从“bootstrap 代码堆叠”进入“可持续演进的执行平台”状态。
