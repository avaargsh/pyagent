# Python 数字员工平台包结构契约

## 1. 文档范围与输入

- 本文档用于把当前仓库的包结构，对齐到 `.ai/temp/architect-optimized.md` 所定义的新架构。
- 输入优先级：
  - 第一优先：`.ai/temp/architect-optimized.md`
  - 第二优先：`.ai/temp/architect.md`
  - 第三优先：`.ai/temp/cli-spec.md`
  - 第四优先：`.ai/temp/wbs.md`
- 当前仓库仍缺少正式 `.ai/temp/requirement.md`，因此本契约只约束工程边界与迁移方向，不把当前假设提升为最终产品承诺。
- 本契约是“从当前代码演进到新架构”的包结构约束，不是 greenfield 目录想象图。
- 命名规则：
  - Python 模块：`snake_case`
  - 文档 / 配置：`kebab-case`
  - 领域名词优先使用 `work_order / session / approval / artifact / event_ledger / runtime_cell`

## 2. 对齐结论

- 新架构保留 `work-order` 作为一等业务对象，不引入 `workspace` 作为业务核心。
- 新架构把当前项目从“大 `Deps` + 大 `TurnEngine` + 大 `work_order_use_cases`”收敛成三段式：
  - `work-order` 业务模型
  - `RuntimeCell / RuntimeManager` 运行时胶囊
  - `EventLedger` 审计事实源
- 当前包结构需要完成四个关键对齐：
  - `application` 从 `use_cases` 中拆出 `commands` 和 `queries`
  - `runtime` 从单一 `turn_engine.py` 拆成 `turn/` 回合流水线
  - `providers / tools / policy` 成为平级资源服务，不再混在 runtime 和 use case 里
  - `session + events` 从临时对象提升为 `projection + ledger` 双模型
- 兼容策略：
  - 允许 `application/use_cases/`、`runtime/turn_engine.py`、`application/services/request_context.py` 暂时保留
  - 但这些旧入口只能作为 shim，最终要转发到新包边界，不再承载核心逻辑

## 3. 目录树

建议目录树如下：

```text
src/
├── digital_employee/
│   ├── __init__.py
│   ├── api/
│   │   ├── cli/
│   │   ├── rest/
│   │   ├── websocket/
│   │   └── webhook/
│   ├── application/
│   │   ├── dto/
│   │   ├── commands/
│   │   ├── queries/
│   │   └── services/
│   ├── domain/
│   │   └── runtime_constraints.py
│   ├── contracts/
│   ├── runtime/
│   │   ├── manager.py
│   │   ├── cell.py
│   │   ├── coordinator_runtime.py
│   │   ├── task_supervisor.py
│   │   ├── session_runtime.py
│   │   ├── budget.py
│   │   ├── retry.py
│   │   ├── lease.py
│   │   └── turn/
│   │       ├── engine.py
│   │       ├── context_assembler.py
│   │       ├── budget_controller.py
│   │       ├── model_gateway.py
│   │       ├── action_interpreter.py
│   │       ├── session_recorder.py
│   │       └── result_mapper.py
│   ├── agents/
│   ├── skills/
│   ├── memory/
│   ├── tools/
│   │   ├── registry.py
│   │   ├── executor.py
│   │   ├── exposure.py
│   │   ├── schemas.py
│   │   ├── builtins/
│   │   └── handlers/
│   ├── providers/
│   │   ├── catalog.py
│   │   ├── factory.py
│   │   ├── router.py
│   │   ├── models.py
│   │   ├── normalization.py
│   │   └── adapters/
│   ├── policy/
│   │   ├── engine.py
│   │   ├── approvals.py
│   │   ├── redaction.py
│   │   └── rules.py
│   ├── integrations/
│   ├── infra/
│   │   ├── config/
│   │   ├── db/
│   │   ├── repositories/
│   │   ├── queue/
│   │   ├── locks/
│   │   └── storage/
│   ├── observability/
│   │   ├── ledger.py
│   │   ├── projections.py
│   │   ├── replay.py
│   │   ├── streaming.py
│   │   ├── tracing.py
│   │   └── logging.py
│   └── bootstrap/
│       ├── container.py
│       └── factories.py
└── digital_employee_sdk/
```

说明：

- 新增 `bootstrap/` 是本次对齐里唯一值得接受的顶层增量，因为 composition root 不属于 `application service`。
- `application/use_cases/` 不再是目标形态；迁移期允许保留，但其职责只能是兼容转发。
- `runtime/turn_engine.py` 不再是目标形态；迁移期允许保留，但其职责只能是对 `runtime/turn/engine.py` 的兼容包装。

## 4. 分层职责与依赖边界

| 包 | 主要职责 | 允许依赖 | 禁止依赖 |
|---|---|---|---|
| `api.cli` | 参数解析、TTY 行为、JSON/JSONL 输出、exit code 映射 | `application.commands` `application.queries` `application.dto` | 直接访问 repo / provider / tool handler |
| `api.rest` | HTTP 路由、鉴权、请求校验、流式响应 | `application.commands` `application.queries` | 直接拼装 runtime 对象 |
| `application.commands` | 状态变化型业务命令：create/run/cancel/resume/approve | `domain` `contracts` `application.services` | 直接依赖 CLI / REST / infra 具体实现 |
| `application.queries` | 只读查询：get/list/tail/export/doctor view | `domain` `contracts` `application.services` | 直接写库或调用外部动作 |
| `application.services` | orchestration facade、artifact service、approval facade | `runtime` `contracts` `observability` | CLI 表现层 |
| `domain` | 业务实体、状态枚举、领域校验规则 | 无或极少基础库 | `infra` `api` |
| `runtime.cell` | `RuntimeCell` 运行时胶囊 | `providers` `tools` `memory` `policy` `runtime.turn` | 直接依赖业务 repo |
| `runtime.manager` | `RuntimeManager` 懒加载、热重载、生命周期 | `runtime.cell` `infra.config` | 业务用例逻辑 |
| `runtime.turn` | 单回合执行流水线 | `providers` `tools` `memory` `policy` `observability` | CLI/HTTP、数据库方言 |
| `runtime.task_supervisor` | 进程内任务监督、超时、取消 | 基础库 | 直接承载业务状态机 |
| `tools.registry` | 工具定义注册与查询 | `tools.schemas` `domain` | 直接执行业务副作用 |
| `tools.executor` | handler 调度、超时、重试、幂等包装 | `tools.registry` `integrations` `policy` | 业务编排 |
| `providers.catalog` | provider/model 配置目录与槽位信息 | `infra.config` | 直接网络调用 |
| `providers.router` | 回合级 provider/model 选择 | `providers.catalog` | policy / tool / repo |
| `policy.engine` | `allow/ask/deny` 决策 | `domain` `infra.config` | API 展示、网络调用 |
| `memory` | 记忆选择、摘要、预算裁剪、知识注入 | `integrations` `contracts` | 工具副作用 |
| `observability.ledger` | append-only 事件账本写入 | `contracts` `infra.repositories` | 业务决策 |
| `observability.projections` | 从账本投影 `work_order/session` 查询视图 | `contracts` `infra.repositories` | 执行动作 |
| `infra.repositories` | snapshot / projection / ledger / artifact / approval 存储 | `domain` `contracts` | CLI/HTTP、provider |
| `bootstrap` | composition root、工厂、依赖装配 | 全部内部包 | 业务规则 |

硬性约束：

- `application` 不得直接 new `ProviderRouter`、`ToolRegistry`、`TaskSupervisor`。
- `runtime.turn` 不得直接操作 `WorkOrderRepository`。
- `ToolRegistry` 不得再内置具体外部系统副作用实现。
- `PolicyEngine` 必须既参与“工具暴露前过滤”，也参与“执行前最终检查”。
- `execution_mode / dispatch_mode / background_state / coordinator event type / coordination metadata key` 必须统一定义在 `domain/runtime_constraints.py`，不得在多个包重复声明。

## 5. 关键接口与结构体

建议冻结以下关键结构：

### 5.1 Runtime

`RuntimeCellKey`

- `tenant: str | None`
- `employee_id: str`
- `config_version: str`

`RuntimeCell`

- `key: RuntimeCellKey`
- `provider_catalog`
- `provider_router`
- `tool_registry`
- `tool_executor`
- `policy_engine`
- `memory_manager`
- `hook_dispatcher`
- `turn_pipeline`

`RuntimeManager`

- `get_cell(key) -> RuntimeCell`
- `reload_cell(key) -> None`
- `invalidate_by_tenant(tenant) -> None`
- `invalidate_by_employee(employee_id) -> None`

### 5.2 Application

`WorkOrderCommandService`

- `create_work_order()`
- `run_work_order()`
- `cancel_work_order()`
- `resume_work_order()`

`WorkOrderQueryService`

- `get_work_order()`
- `list_work_orders()`
- `list_artifacts()`

`SessionQueryService`

- `get_session()`
- `list_sessions()`
- `tail_session()`
- `export_session()`

### 5.3 Event / Projection

`LedgerEvent`

- `event_id`
- `event_type`
- `tenant`
- `work_order_id`
- `session_id`
- `turn_index`
- `ts`
- `payload`
- `trace_id`
- `request_id`

`WorkOrderSnapshot`

- `work_order_id`
- `tenant`
- `employee_id`
- `status`
- `current_step`
- `last_session_id`
- `output_summary`
- `last_error`
- `config_snapshot_id`

`SessionProjection`

- `session_id`
- `work_order_id`
- `employee_id`
- `status`
- `current_stage`
- `budget_used`
- `budget_remaining`
- `last_event_at`

### 5.4 Provider / Tool / Policy

`ProviderCatalog`

- `list_models()`
- `resolve_slot(slot_name)`

`ProviderRouter`

- `select_for_turn(profile, turn_context) -> ProviderBinding`

`ToolRegistry`

- `register(definition)`
- `require(name)`
- `list_all()`
- `filter_by_capabilities(...)`

`ToolExecutor`

- `execute(tool_call, runtime_context) -> ToolObservation`

`PolicyEngine`

- `check_exposure(...) -> ExposureDecision`
- `check_execution(...) -> ExecutionDecision`

## 6. 配置模型与状态模型

配置模型建议拆成四层：

1. `SystemConfig`
   - runtime defaults
   - queue / lease / timeout
   - observability
2. `TenantConfig`
   - provider policy
   - integration endpoints
   - approval routing
   - redaction policy
3. `EmployeeProfileConfig`
   - provider slot
   - skill packs
   - allowed tools
   - knowledge scopes
   - approval policy
4. `RuntimeOverride`
   - flag
   - env
   - request scoped override

状态模型建议固定成“两类持久化 + 一类运行态”：

- 持久化快照：
  - `work_order_snapshot`
  - `session_projection`
  - `approval_record`
  - `artifact_record`
- 持久化事实源：
  - `event_ledger`
- 运行态：
  - `runtime_cell`
  - `task_handle`
  - `lease_state`

迁移要求：

- 每个 `work_order` 必须记录 `tenant` 与 `config_snapshot_id`
- `session_projection` 必须能在没有完整历史消息的情况下支持 `get/list/tail`
- `event_ledger` 必须是 append-only，不允许原地覆盖

## 7. 测试桩、Mock 与 Golden 放置方式

- `tests/unit/`
  - 领域对象
  - runtime 子组件
  - provider router / policy engine / tool exposure
- `tests/integration/`
  - CLI
  - REST
  - repository + projection
  - background task flow
- `tests/contract/`
  - tool observation shape
  - provider normalization shape
  - event ledger schema
- `tests/golden/cli/`
  - `config show`
  - `session tail --jsonl`
  - `doctor --json`
- `tests/fixtures/`
  - configs
  - work orders
  - sessions
  - ledger events
  - provider responses
- `tests/fakes/`
  - fake provider
  - fake tool executor
  - fake ledger writer
  - fake projection repo

Mock 约束：

- `ProviderRouter` 用 fake catalog + fake provider 验证
- `RuntimeManager` 用 fake config version / fake runtime cell 验证
- `ToolExecutor` 只 mock integration adapter，不 mock registry
- `Command` 与 `Query` 测试优先使用 fake facade，不要再直接 patch 整个 composition root

## 8. 迁移期兼容约束

- `application/use_cases/*.py`
  - 迁移期允许存在，但目标是薄 shim
  - 禁止继续往里加核心逻辑
- `runtime/turn_engine.py`
  - 迁移期允许存在，最终仅保留向 `runtime/turn/engine.py` 的兼容入口
- `application/services/request_context.py`
  - 迁移期允许存在，最终仅保留向 `bootstrap/container.py` 的兼容包装
- `Deps`
  - 迁移期允许存在
  - 但新代码优先依赖 `CommandService / QueryService / RuntimeManager`
- `session + events` 双写期
  - 在 `EventLedger` 落地前允许保留当前 `SessionRecord`
  - 一旦 `EventLedger` 上线，projection 与 ledger 必须双写，直到查询面完全切换

禁止事项：

- 不再新增“第二个大容器对象”
- 不再新增“第二个大 use case 文件”
- 不再把具体 tool handler 塞回 `tools/registry.py`

## 9. 预计新增 / 修改文件列表

优先新增：

- `src/digital_employee/bootstrap/container.py`
- `src/digital_employee/bootstrap/factories.py`
- `src/digital_employee/application/commands/work_order_commands.py`
- `src/digital_employee/application/queries/work_order_queries.py`
- `src/digital_employee/application/queries/session_queries.py`
- `src/digital_employee/runtime/manager.py`
- `src/digital_employee/runtime/cell.py`
- `src/digital_employee/runtime/session_runtime.py`
- `src/digital_employee/runtime/turn/engine.py`
- `src/digital_employee/runtime/turn/context_assembler.py`
- `src/digital_employee/runtime/turn/budget_controller.py`
- `src/digital_employee/runtime/turn/model_gateway.py`
- `src/digital_employee/runtime/turn/action_interpreter.py`
- `src/digital_employee/runtime/turn/session_recorder.py`
- `src/digital_employee/providers/catalog.py`
- `src/digital_employee/providers/factory.py`
- `src/digital_employee/tools/executor.py`
- `src/digital_employee/policy/engine.py`
- `src/digital_employee/observability/ledger.py`
- `src/digital_employee/observability/projections.py`
- `src/digital_employee/observability/replay.py`

优先重构：

- `src/digital_employee/application/use_cases/work_order_use_cases.py`
- `src/digital_employee/application/use_cases/session_use_cases.py`
- `src/digital_employee/application/services/request_context.py`
- `src/digital_employee/application/services/deps.py`
- `src/digital_employee/runtime/turn_engine.py`
- `src/digital_employee/providers/router.py`
- `src/digital_employee/tools/registry.py`
- `src/digital_employee/infra/repositories/work_orders.py`
- `src/digital_employee/infra/repositories/sessions.py`

需要补齐但当前尚未成为主路径：

- `src/digital_employee/policy/approvals.py`
- `src/digital_employee/policy/redaction.py`
- `src/digital_employee/infra/repositories/events.py`
- `src/digital_employee/infra/repositories/approvals.py`
- `src/digital_employee/api/rest/sessions.py`
- `src/digital_employee/api/rest/tools.py`
- `src/digital_employee/api/websocket/session_events.py`

这份文件清单的目标不是“一次性全做完”，而是固定未来几轮重构的落点，避免继续在旧包边界上加功能。
