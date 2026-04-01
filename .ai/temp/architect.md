# Python 人工智能数字员工 Agent 架构

## 1. 文档范围与参考基线

- 本文档把 `/home/dev/claude-code-source-code` 中可迁移的 agent 架构模式，重构为适用于 Python 的“人工智能数字员工”平台。
- 参考的核心模式来自以下源码事实：
  - `README_CN.md` 中的最小代理循环与“生产级线束”说明
  - `src/QueryEngine.ts` 的查询生命周期与会话持久化入口
  - `src/tools.ts` 与 `src/Tool.ts` 的工具注册、能力裁剪、权限上下文
  - `src/Task.ts` 的统一任务状态模型
  - `src/memdir/memdir.ts` 的分层记忆与加载上限
  - `src/remote/RemoteSessionManager.ts` 的远程会话、权限请求与观察者模式
  - `src/coordinator/coordinatorMode.ts` 的协调器/执行者分工
- 不直接继承的部分：
  - 不复用 REPL/UI 形态
  - 不依赖 Bun/TypeScript 构建体系
  - 不引入隐式 feature gate、远程静默开关、不可审计的行为覆盖
- 本设计面向企业内部数字员工场景：客服、销售助理、运营执行、财务助理、HR 助理、流程专员。核心目标是把“聊天代理”升级为“可审计的业务执行单元”。

## 2. 架构结论

- 系统不应以“消息对话”作为一等核心对象，而应以 `work-order` 作为一等核心对象。聊天只是入口，真正被调度和审计的是工作单、步骤、审批、工具动作和交付物。
- 运行时采用“协调器 + 专业数字员工 + 工具执行器 + 人工审批节点”的四层模型，而不是让单一大模型直接驱动所有外部系统。
- Python 技术路线建议：
  - 运行时：`Python 3.12+` + `asyncio`
  - API 层：`FastAPI`
  - 数据模型：`Pydantic v2`
  - 持久化：`PostgreSQL`
  - 短期状态与队列：`Redis`
  - HTTP 集成：`httpx`
  - ORM：`SQLAlchemy 2.x`
  - 可观测性：`OpenTelemetry` + `structlog` 或标准 `logging`
- MVP 不引入 Temporal、Airflow、Ray 这类重编排平台；先以“持久化状态机 + 事件账本 + 异步 worker”打通主链路。业务复杂度明显上升后，再评估引入 Temporal。
- 机器配置必须全部落到结构化文件和数据库模型中。`AGENTS.md`、SOP Markdown、FAQ 文档只供人和模型阅读，不允许作为机器配置源解析。

建议的顶层目录：

```text
pyproject.toml
src/
├── digital_employee/
│   ├── api/
│   ├── application/
│   ├── domain/
│   ├── runtime/
│   ├── agents/
│   ├── skills/
│   ├── tools/
│   ├── memory/
│   ├── providers/
│   ├── policy/
│   ├── integrations/
│   ├── infra/
│   └── observability/
└── digital_employee_sdk/        # 默认可为空，只暴露稳定外部接口
configs/
├── system.yaml
├── providers/
├── agents/
├── skills/
└── policies/
playbooks/
knowledge/
tests/
```

## 3. 架构目标与约束

### 3.1 架构目标

1. 让每个数字员工都具备明确的角色、权限、知识域、工具域、审批策略和 SLA。
2. 支持同步对话、异步任务、计划任务、Webhook 触发四类入口。
3. 支持长流程恢复、失败重试、人工接管、回放审计。
4. 支持多租户隔离，避免模型、记忆、日志和集成凭证交叉污染。
5. 保证“先计划，后执行；先授权，后落地；先记账，后提交”。

### 3.2 设计约束

- 异步优先：所有跨层 I/O 必须可取消、可超时、可重试。
- 模型不可直接访问数据库、外部系统和密钥；一切副作用必须经 `tool` 或 `integration adapter`。
- 高风险动作必须走策略引擎：
  - 发信
  - 发起审批
  - 更新 CRM/ERP
  - 写入财务、人事、客户主数据
  - 调用桌面自动化/RPA
- 明确禁止直接解析自然语言 `AGENTS.md`、SOP Markdown、聊天记录来决定阶段、权限、路径、模型或租户配置。
- 默认优先轻依赖和标准协议，避免过早引入复杂分布式编排框架。

### 3.3 产品边界

范围内：

- 数字员工画像与角色装配
- 任务分解、工具调度、审批流与交付物生成
- 多 Provider 模型适配
- 短期记忆、长期记忆、组织知识检索
- 远程观察、人工干预、事件审计

范围外：

- 通用聊天机器人平台
- 重型 RPA 录制平台
- 无约束自动执行的“黑盒全自动员工”
- 依赖自由文本配置的 agent 市场

## 4. 模块划分与职责边界

### 4.1 分层目录

```text
src/digital_employee/
├── api/                 # REST/WebSocket/Webhook/CLI 入口
├── application/         # 用例编排，事务边界，状态流转
├── domain/              # 业务实体与规则，不依赖基础设施
├── runtime/             # TurnEngine、TaskSupervisor、SessionManager
├── agents/              # 数字员工角色、装配器、能力画像
├── skills/              # SOP、模板、任务协议、提示片段
├── tools/               # 工具协议、注册表、执行器、结果规范化
├── memory/              # 记忆模型、检索、裁剪、摘要
├── providers/           # LLM 抽象与 OpenAI/Anthropic/内部模型适配
├── policy/              # 权限、审批、脱敏、租户隔离、资源访问控制
├── integrations/        # Slack/Email/CRM/ERP/OA/知识库等适配器
├── infra/               # DB/Redis/对象存储/队列/锁/配置装载
└── observability/       # tracing、audit、metrics、replay
```

### 4.2 关键模块职责

| 模块 | 主要职责 | 允许依赖 | 禁止依赖 |
|---|---|---|---|
| `api` | 鉴权、反序列化、请求校验、流式输出、回调入口 | `application` | 直接依赖 `providers`、`integrations` |
| `application` | 工作单创建、运行、恢复、审批、关闭等用例 | `domain` `runtime` `policy` `infra` | 直接拼接模型 prompt 细节 |
| `domain` | `WorkOrder`、`TaskStep`、`Approval`、`Artifact`、`EmployeeProfile` 等实体 | 无或极少工具库 | `api` `providers` `infra` |
| `runtime` | 代理循环、任务监督、执行预算、取消、重试、并发控制 | `agents` `tools` `memory` `providers` `policy` | HTTP 展示、数据库方言细节 |
| `agents` | 角色定义、能力矩阵、目标拆解策略、角色级系统提示 | `skills` `policy` | 直接调用数据库或第三方系统 |
| `skills` | 标准作业包、行业 SOP、模板参数、输入输出契约 | `domain` | 直接访问网络和密钥 |
| `tools` | 工具 schema、执行包装、幂等键、结果标准化 | `integrations` `policy` | 工作流判定与租户业务状态机 |
| `memory` | 会话记忆、案例记忆、组织知识、摘要与裁剪规则 | `infra` | 直接发起外部动作 |
| `providers` | 多模型适配、响应归一化、成本与超时控制 | `infra` | 业务规则、审批流 |
| `policy` | allow/ask/deny、审批路由、敏感信息脱敏、租户边界 | `domain` `infra` | UI 交互 |
| `integrations` | 企业系统 API 封装、速率限制、签名、重试 | `infra` | 直接依赖 `api` |
| `infra` | 配置、数据库、缓存、锁、队列、对象存储、事件总线 | 基础库 | 业务规则 |
| `observability` | 审计账本、运行指标、链路追踪、回放 | `infra` | 业务编排 |

### 4.3 运行时内核

从参考仓库迁移出的核心模式如下：

1. `TurnEngine`
   - 对应参考中的 `QueryEngine`
   - 负责单次推理回合：装配上下文、调用 Provider、解析模型输出、分派工具、写回观察结果
   - 内部必须拆分出三个可替换子层：
     - `ContextCompactor`：在上下文接近预算上限时进行 `snip -> microcompact -> autocompact`
     - `ToolExposurePlanner`：只向模型暴露当前回合真正可见的工具 schema
     - `TaskSupervisor`：把长时间任务和后台任务从同步回合中解耦
2. `ToolRegistry`
   - 对应参考中的 `tools.ts` + `Tool.ts`
   - 统一维护工具定义、输入 schema、权限要求、输出标准
3. `TaskSupervisor`
   - 对应参考中的 `Task.ts`
   - 统一管理同步任务、异步任务、远程任务、计划任务和人工接管任务
4. `MemoryManager`
   - 对应参考中的 `memdir`
   - 管理会话记忆、员工记忆、组织知识的边界、大小上限与检索策略
   - 其中会话记忆必须具备三层压缩协议：
     - `snip`：去掉空消息、陈旧工具进度和重复系统噪声
     - `microcompact`：保留事实摘要，不保留逐字历史
     - `autocompact`：超过阈值时自动把旧消息折叠成摘要边界
5. `RemoteControlGateway`
   - 对应参考中的 `RemoteSessionManager`
   - 支持管理员观察、审批介入、人工继续执行、远程终止
6. `CoordinatorRuntime`
   - 对应参考中的 `coordinatorMode`
   - 协调器只做计划、授权和任务分派；专业员工或工具执行器负责落地

### 4.4 `internal` 与公共 SDK 边界

- `src/digital_employee/` 默认视为内部实现，不承诺外部稳定性。
- 只有在确有对外集成需求时，才在 `src/digital_employee_sdk/` 暴露稳定接口：
  - `AgentRequest`
  - `AgentResult`
  - `ToolSpec`
  - `ApprovalDecision`
  - `WebhookClient`
- 角色装配、运行时状态机、权限规则、内部事件模型不对外暴露，避免早期锁死演进空间。

## 5. 分层数据流

### 5.1 总体流程

```text
用户/系统入口
  -> API/Webhook/Scheduler/CLI
  -> Application Use Case
  -> WorkOrder + Session 初始化
  -> CoordinatorRuntime
  -> TurnEngine
  -> Provider 生成计划/动作
  -> ToolRegistry + PolicyEngine 校验
  -> Integration Adapter 执行动作
  -> Event/Audit/Artifact 落盘
  -> Application 汇总结果
  -> API/消息通道返回结果或进入异步观察
```

### 5.2 命令层、应用层、基础设施层的数据流

#### 命令层 / 接入层

- 接收来源：
  - Web 控制台
  - 企业 IM
  - 邮件入口
  - Webhook
  - 定时触发器
  - 运维 CLI
- 职责：
  - 鉴权和租户识别
  - 请求标准化
  - 幂等键生成
  - 流式响应或任务受理回执

#### 应用层

- 将请求映射为 `CreateWorkOrder`、`RunStep`、`ApproveAction`、`ResumeRun` 等用例。
- 根据租户、部门、员工角色加载：
  - `EmployeeProfile`
  - `SkillPack`
  - `KnowledgeScope`
  - `PolicyProfile`
- 决定当前工作单是：
  - 即时完成
  - 异步排队
  - 进入审批等待
  - 进入人工接管

#### 基础设施层

- Provider adapter 负责模型请求
- Integration adapter 负责外部系统写入
- Repository 负责状态持久化
- Redis/Queue 负责运行中的 lease、事件推送和后台重试
- Object storage 保存附件、报告、导出文件

### 5.3 单次执行回合

1. `TurnEngine` 从工作单当前步骤读取目标、上下文、已完成动作和剩余预算。
2. `MemoryManager` 注入四类上下文：
   - 当前会话短期记忆
   - 当前工作单中间产物
   - 员工长期偏好与经验
   - 组织知识与 SOP 片段
3. `ProviderRouter` 为本回合选择模型：
   - 规划模型
   - 执行模型
   - 审核模型
4. `ToolExposurePlanner` 基于当前任务、员工和权限模式裁剪工具清单，只把当回合允许感知的工具 schema 发送给模型。
5. 模型输出若为工具动作，则进入 `ToolRegistry`。
6. `PolicyEngine` 根据员工、工具、资源、租户和风险级别执行 `allow/ask/deny`。
7. 若需审批，则生成 `ApprovalRequest` 并暂停工作单。
8. 若允许执行，则由 `ToolExecutor` 调用具体集成并产出 `ToolObservation`。
9. `TaskSupervisor` 根据观察结果决定继续下一回合、重试、升级人工或结束；超过交互阈值的任务切到后台监督，而不是占住同步会话。

### 5.4 为什么采用工作单中心而不是纯会话中心

- 数字员工的核心不是“回答得像不像人”，而是“任务是否正确完成、可追溯、可恢复”。
- 工作单天然适合挂载 SLA、审批链、附件、交付物、失败原因和责任归属。
- 这比参考仓库的纯交互式 REPL 更适合企业流程场景。

## 6. 配置、状态、会话与 Provider 适配策略

### 6.1 配置策略

机器可消费配置必须进入结构化文件或数据库，不读取自由文本 Markdown：

```text
configs/
├── system.yaml
├── providers/openai.yaml
├── agents/sales-assistant.yaml
├── agents/hr-assistant.yaml
├── skills/customer-followup.yaml
└── policies/high-risk-actions.yaml
```

配置优先级固定为：

`runtime override > env > tenant config > project config > default`

规则：

- 密钥只从环境变量或密钥管理器读取
- `AGENTS.md`、SOP Markdown、FAQ 文档只作为提示输入，不作为配置源
- 租户级模型、工具、审批策略必须可版本化

### 6.2 状态模型

建议采用“快照 + 事件账本”双轨模型：

- 快照表：
  - `work_orders`
  - `sessions`
  - `task_steps`
  - `approvals`
  - `artifacts`
  - `employee_profiles`
- 事件表：
  - `run_events`
  - `tool_events`
  - `approval_events`
  - `memory_events`
  - `handoff_events`

状态机最少需要覆盖：

- `pending`
- `running`
- `waiting_approval`
- `waiting_human`
- `retrying`
- `completed`
- `failed`
- `cancelled`

### 6.3 会话模型

区分四种会话，避免把所有运行时状态都塞进聊天消息：

1. `conversation_session`
   - 面向用户交互界面
2. `work_order_session`
   - 面向具体业务目标
3. `background_run`
   - 面向异步执行、计划任务、批处理
4. `remote_watch_session`
   - 面向管理员观察、审批和远程干预

每个会话必须携带：

- `tenant_id`
- `employee_id`
- `actor_id`
- `correlation_id`
- `risk_level`
- `budget_policy`
- `knowledge_scope_id`

### 6.4 Provider 适配策略

参考 `Tool.ts` 的统一协议思想，Python 侧统一抽象为：

```python
class LLMProvider(Protocol):
    async def complete(self, request: CompletionRequest) -> CompletionResult: ...
    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamEvent]: ...
```

Provider 适配层必须承担：

- 消息格式归一化
- tool call 归一化
- JSON schema 约束
- 超时与重试
- 成本统计
- 模型能力矩阵

`ProviderRouter` 的职责：

- 按任务类型路由模型
- 按租户策略做白名单限制
- 按预算做降级
- 当主 Provider 不可用时切换到备用 Provider 或 `mock`

### 6.5 记忆策略

参考 `memdir` 的边界控制，但改成适合企业数字员工的五层记忆：

1. `scratchpad`
   - 当前回合临时推理草稿，不落长期存储
2. `session-memory`
   - 当前会话短期上下文
3. `work-order-memory`
   - 当前工作单中间事实、附件摘要、决策记录
4. `employee-memory`
   - 角色偏好、常用模板、历史成功案例
5. `organization-knowledge`
   - SOP、制度、产品资料、客户策略

记忆必须有封闭分类，避免无限堆积：

- `policy`
- `process`
- `customer`
- `case`
- `reference`

并强制：

- 单条大小上限
- 总注入预算
- 过期策略
- 删除与纠错机制

### 6.6 权限与审批策略

沿用参考仓库“工具权限上下文”的思想，但做企业化增强：

- 权限判断维度：
  - 员工角色
  - 技能包
  - 工具名
  - 资源类型
  - 租户策略
  - 当前风险级别
- 权限结果固定为：
  - `allow`
  - `ask`
  - `deny`
- `ask` 必须生成可审计审批记录，审批通过后才能恢复执行。

### 6.7 远程观察与人工接管

借鉴 `RemoteSessionManager`，但严格限制能力：

- 管理端可以：
  - 观察当前步骤
  - 批准或驳回风险动作
  - 中断运行
  - 注入补充指令
  - 切换为人工接管
- 管理端不可以：
  - 静默改写模型系统提示
  - 静默打开高危工具权限
  - 通过隐藏远程开关改变租户行为

这类控制必须写入审计账本，且默认对租户管理员可见。

## 7. 非功能目标

| 目标 | 指标 |
|---|---|
| 启动速度 | API 冷启动 `< 10s`，worker 进程冷启动 `< 15s` |
| 交互延迟 | P95 任务受理时间 `< 300ms`，P95 首 token 时间 `< 2.5s` |
| 可恢复性 | 单节点异常后，运行中工作单可在 `5min` 内恢复调度 |
| 一致性 | 所有工具动作、审批动作、状态迁移均有事件账本 |
| 可测试性 | 核心状态机、策略引擎、工具协议、Provider 归一化必须有自动化测试 |
| 跨平台 | 开发环境支持 Linux/macOS，生产环境优先 Linux |
| 可观测性 | 100% 工作单带 `trace_id/correlation_id/tenant_id` |
| 安全性 | 密钥不落日志；默认脱敏；租户间数据强隔离 |
| 成本控制 | 每个工作单必须带预算上限、模型路由和超时策略 |

补充要求：

- 所有重要外部调用都要支持幂等键
- 失败重试必须区分：
  - 可重试网络错误
  - 不可重试业务错误
  - 需人工处理的策略错误
- 输出结果必须稳定，可被 API、消息系统和审计系统复用
- 任何后台自动执行都必须能被暂停、取消和回放

## 8. 风险与替代方案

### 8.1 多 Agent 过度设计

风险：

- 一开始就做大量“数字员工互相分工”会迅速放大 token 成本、调试成本和一致性问题。

结论：

- MVP 只保留一个 `CoordinatorRuntime` 和少量专业员工模板。
- 真正并发的部分放在工具执行层和后台任务层，而不是先做复杂 agent swarm。

替代方案：

- 如果业务早期较简单，可退化为“单协调器 + 技能包 + 工具策略”。

### 8.2 工作流引擎选择

风险：

- 直接引入 Temporal 虽然强大，但会显著提高部署、运维和开发门槛。

结论：

- 先用 PostgreSQL + Redis + 持久化状态机。

替代方案：

- 当出现大量跨天流程、补偿事务和高并发后台编排时，再迁移到 Temporal。

### 8.3 记忆污染

风险：

- 如果长期记忆没有分类和上限，数字员工会逐步失真，甚至把错误案例当成组织事实。

结论：

- 记忆必须分类、限额、可纠错、可删除，并区分“事实”和“偏好”。

替代方案：

- 在早期只保留 `session-memory + organization-knowledge` 两层，延后员工长期记忆。

### 8.4 模型直接执行高风险动作

风险：

- 模型若直接调用外部系统写操作，会带来误操作、越权和审计缺口。

结论：

- 所有副作用必须经过 `ToolRegistry + PolicyEngine + IntegrationAdapter`。
- 高风险动作一律审批或双重校验。

替代方案：

- 在高监管行业可采取“模型只建议，人工点击提交”的保守模式。

### 8.5 远程控制滥用

风险：

- 参考仓库暴露出的远程控制和 killswitch 模式，不适合企业内部数字员工平台直接照搬。

结论：

- 不允许隐藏远程开关、不可见行为覆盖或静默模型切换。
- 远程控制只用于观察、审批、接管和中止，且必须完整审计。

### 8.6 推荐实施顺序

1. 先实现单工作单主链路：创建、运行、审批、完成
2. 再实现统一工具协议与 ProviderRouter
3. 再实现组织知识检索与短期记忆
4. 再实现远程观察与人工接管
5. 最后再引入多专业员工、计划任务和复杂后台编排
