# Python 数字员工平台运行时约束

## 1. 目的

- 本文档用于统一当前仓库中与执行模式、后台状态、协调事件和协调快照相关的硬约束。
- 代码单一事实源：
  - `src/digital_employee/domain/runtime_constraints.py`
  - `src/digital_employee/domain/work_order.py`
  - `src/digital_employee/domain/session.py`
- 本文档是人类可读版约束说明；代码实现必须以结构化模块为准，不能靠分散字符串常量维持一致性。

## 2. 执行与调度模式

### 2.1 ExecutionMode

- `single`
- `coordinated`

规则：

- `work-order` 默认是 `single`
- 只有显式协调路径才允许 `coordinated`
- 新代码禁止直接硬编码 `"single"` / `"coordinated"`

### 2.2 DispatchMode

- `foreground`
- `background`

规则：

- `execution_mode` 表示“单员工 / 协调执行”
- `dispatch_mode` 表示“前台 / 后台调度”
- 两者不能混用

## 3. 后台状态

固定状态：

- `queued`
- `running`
- `waiting_approval`
- `completed`
- `failed`
- `cancelled`

终态集合：

- `completed`
- `failed`
- `waiting_approval`
- `cancelled`

规则：

- doctor、session observability、后台心跳和 reclaim/cancel 必须共享这套状态定义
- 新代码禁止在多个模块分别维护“后台终态集合”

## 4. Work-Order 与 CoordinatorPlan

### 4.1 CoordinatorPlan

字段：

- `worker_employee_id`
- `selection_reason`
- `required_tools`
- `matched_terms`

规则：

- `worker_employee_id` 必填
- `selection_reason` 必填，允许降级为 `unknown`
- `required_tools` / `matched_terms` 会做去重和空值清理

### 4.2 WorkOrder

规则：

- `single` 模式下，`coordinator_participants` 必须为空，`coordinator_plan` 必须为空
- `coordinated` 模式下，`coordinator_participants` 至少一个
- 如果存在 `coordinator_plan`，其 `worker_employee_id` 必须属于 `coordinator_participants`
- CLI `work-order create --coordinated` 且未显式传 `--participant` 时，默认使用协调者自己作为唯一参与者

含义：

- `CoordinatorPlan` 是工单快照事实，不是临时推断结果
- `run / resume / replay / doctor` 应优先使用工单里的计划，而不是重新选 worker

## 5. Coordination 事实源

协调信息优先级：

1. `WorkOrder.coordinator_plan`
2. `SessionProjection.coordination`
3. `session.metadata + coordinator ledger events`

规则：

- `work-order create` 负责生成并持久化 `CoordinatorPlan`
- session projection 必须显式持久化 `coordination`
- 只有在 projection/metadata 缺失时，才允许从 ledger 事件重建协调快照

## 6. Event 与 Projection 约束

协调相关事件固定为：

- `coordinator.started`
- `coordinator.worker_selected`

`SessionProjection.coordination` 固定字段：

- `execution_mode`
- `dispatch_mode`
- `coordinator_employee_id`
- `worker_employee_id`
- `participant_ids`
- `selection_reason`
- `required_tools`
- `matched_terms`

规则：

- `session list/get/export` 直接返回这份快照
- 查询层不应再拼装新的协调协议
- projection 构建允许从 `session.metadata` 和协调事件做容错重建，但输出字段必须稳定

## 7. 工程规则

- 所有新的执行模式、后台状态、协调事件、metadata key，都必须先进入 `runtime_constraints.py`
- 禁止在 `application`、`runtime`、`observability`、`tests` 中各自维护一套相同语义的字符串
- 文档更新时，优先更新本文件，再同步 `.ai/temp/architect-optimized.md`、`.ai/temp/package-plan.md`、`.ai/temp/plan.md`
