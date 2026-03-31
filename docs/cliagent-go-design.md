# cliagent Go CLI 开发设计文档

> 日期：2026-03-31
> 状态：v1.0 基线
> 说明：本文件是唯一实现基线。

## 1. 结论与定位

- `cliagent` 的正确定位不是“通用 AI 编码助手”，而是“可审计交付工作流 CLI”。
- 核心价值不是多模型、多 Agent 花活，而是把需求到发布的阶段产物、Gate 审批、状态追踪和证据留存落到仓库内可追踪文件。
- 后续取舍统一按一句话判断：这个能力是否显著提升“交付可审计性、可控性、可恢复性”。若不能，默认延后。

对外主张只保留三点：

1. `Gate-first`：每阶段审批和回退可追溯
2. `Repo-native`：状态、证据、交付物全部落在仓库内
3. `CI-ready`：全链路支持非交互和稳定机读输出

明确不做：

1. 通用聊天助手替代品
2. IDE 全量体验竞争
3. 重型云端协作平台
4. 无人值守软件工厂

## 2. 单一事实源

实现与运行时必须严格区分“人类协议”和“机器配置”：

| 载体 | 角色 | 规则 |
|---|---|---|
| `AGENTS.md` | 人类与 AI 协作协议 | 供人阅读和执行，不作为机器配置源 |
| `docs/cliagent-go-design.md` | 技术实现基线 | 目录、分层、协议、状态模型的唯一标准 |
| `.cliagent/workflow.yaml` | 机器工作流配置 | 定义阶段、角色、输出语言、交付物路径、跳过策略 |
| `.cliagent/config.yaml` | 机器运行配置 | 定义 Provider、模型、超时、CLI 默认行为 |
| `.ai/context/*.md` | 项目上下文 | 供角色输入使用，不承载机器判定逻辑 |
| `.ai/temp/` `.ai/reports/` `.ai/records/` `.ai/state/` | 运行产物 | CLI 唯一写入位置 |

兼容性要求：

- 禁止直接解析自然语言 `AGENTS.md` 判断阶段、角色或路径。
- 禁止解析 `.ai/context/workflow-config.md` 这类 Markdown 文件作为机器执行源。
- 若历史项目存在 `.ai/context/workflow-config.md`，`doctor` 必须提示迁移到 `.cliagent/workflow.yaml`。

## 3. 设计原则

### 3.1 本地优先

- 工作流状态和证据保存在工作区，不依赖数据库才能完成 MVP。
- 没有网络时，`mock` provider 仍可驱动主链路测试。

### 3.2 协议稳定优先

- 优先冻结命令面、错误码和 `--json` schema，再优化交互样式。
- 用户可依赖的输出不能随着版本随意变更；变更必须通过 `schema_version` 演进。

### 3.3 状态一致性优先

- 所有关键写入采用“临时文件 + 原子替换”。
- 所有关键动作采用“当前状态 + 追加账本”双记录模型。

### 3.4 轻依赖与清晰分层

- 优先标准库和轻依赖。
- `cmd/` 只组装命令；业务逻辑进入 `internal/`。
- 默认不暴露 `pkg/` API，除非出现明确的外部复用需求。

### 3.5 可测试与可脚本化

- 所有主命令必须可在非 TTY 环境运行。
- Golden Test 覆盖稳定输出；Mock Provider 覆盖离线和 CI 场景。

### 3.6 安全默认值

- API Key 只从环境变量读取。
- 日志和状态文件默认脱敏，不记录完整密钥和认证头。

## 4. MVP 范围

### 4.1 v1.0 必做

1. `init`
2. `status`
3. `run <role>`
4. `gate approve`
5. `gate return`
6. `gate list`
7. `config show`
8. `config validate`
9. `doctor`
10. `version`
11. Provider：`mock` + `openai`
12. `run --dry-run`
13. 原子写入、Gate 状态、执行账本、并发锁

### 4.2 延后到 v1.1+

1. `chat`
2. `pipeline`
3. `pattern list/show/create`
4. `anthropic` provider
5. `sqlite` 状态存储
6. Bubble Tea TUI
7. MCP 集成

### 4.3 延后理由

- 这些能力不能显著提升首版“可审计交付主链路”的可用性。
- 它们会同时抬高协议复杂度、状态复杂度和测试成本。

## 5. 命令模型与协议

### 5.1 命令树

```text
cliagent
├── init
├── status
├── run <role>
├── gate
│   ├── approve
│   ├── return
│   └── list
├── config
│   ├── show
│   └── validate
├── doctor
└── version
```

### 5.2 关键参数

| 命令 | 关键参数 |
|---|---|
| `init` | `--force` |
| `status` | `--json` |
| `run <role>` | `--phase` `--input` `--input-file` `--dry-run` `--json` `--no-input` |
| `gate approve` | `--phase` |
| `gate return` | `--phase` `--reason` |
| `gate list` | `--json` |
| `config show` | `--json` |
| `doctor` | `--json` |
| `version` | `--json` |

### 5.3 交互规则

1. 非 TTY：严禁交互提问，缺参直接退出 `2`
2. TTY：只允许最小必要确认
3. `--no-input`：强制禁用任何交互

### 5.4 输出规则

- 成功结果写入 `stdout`
- 诊断、警告、调试、Provider 摘要写入 `stderr`
- `--json` 时，`stdout` 只能输出单个 JSON 对象

统一机读包裹：

```json
{
  "schema_version": 1,
  "command": "run",
  "ok": true,
  "data": {},
  "error": null
}
```

错误格式：

```json
{
  "schema_version": 1,
  "command": "run",
  "ok": false,
  "data": null,
  "error": {
    "code": 6,
    "type": "gate_blocked",
    "message": "phase P2 is not approved",
    "hint": "run `cliagent gate approve --phase P2` first"
  }
}
```

### 5.5 Exit Code

| Code | 含义 |
|---|---|
| `0` | 成功 |
| `1` | 未分类错误 |
| `2` | 参数或输入校验失败 |
| `3` | 配置错误 |
| `4` | Provider 鉴权失败 |
| `5` | Provider 调用失败 |
| `6` | Gate 阻塞或阶段非法 |
| `7` | 用户取消 |
| `10` | 内部错误 |

## 6. 目录与分层设计

### 6.1 目录树

```text
cmd/
└── cliagent/
    └── main.go

internal/
├── cli/
├── app/
├── workflow/
├── provider/
│   ├── openai/
│   └── mock/
├── config/
├── workspace/
├── state/
├── output/
└── version/

pkg/                              # 默认空，出现明确复用需求后再引入
testdata/
├── fixtures/
└── golden/

.cliagent/
├── workflow.yaml
└── config.yaml
```

### 6.2 分层职责

| 层 | 职责 | 禁止事项 |
|---|---|---|
| `internal/cli` | 参数解析、帮助文案、TTY 判断、Exit Code 映射 | 不直接写业务文件，不直接拼 Provider 请求 |
| `internal/app` | 单个用例编排、依赖组合、错误包装 | 不直接决定底层存储格式 |
| `internal/workflow` | 阶段、角色、Gate、交付物路径、状态流转 | 不读取命令行 flags |
| `internal/provider` | LLM 调用、超时、重试、脱敏 | 不做工作流判定 |
| `internal/workspace` | 工作区脚手架、文件读写、原子写入 | 不感知 CLI 展示 |
| `internal/state` | Gate 状态、执行账本、并发锁 | 不耦合具体角色语义 |
| `internal/output` | human/json 输出渲染 | 不决定业务流程 |

### 6.3 `internal/` 与 `pkg/` 边界

- 阶段流转、角色注册、状态存储、配置加载、Provider 抽象均放入 `internal/`。
- `pkg/` 只允许放置明确要向外复用且已稳定的公共类型；v1.0 默认不暴露。

## 7. 核心模型与接口

### 7.1 Provider

```go
type Provider interface {
	Name() string
	Chat(ctx context.Context, req ChatRequest) (*ChatResult, error)
}
```

流式接口预留但不强制进入 MVP 主链路：

```go
type StreamingProvider interface {
	Stream(ctx context.Context, req ChatRequest) (<-chan StreamEvent, error)
}
```

### 7.2 Workspace

```go
type Workspace interface {
	ProjectRoot() string
	EnsureScaffold(ctx context.Context) error
	ReadFile(ctx context.Context, path string) ([]byte, error)
	WriteFileAtomic(ctx context.Context, path string, data []byte) error
	FileExists(ctx context.Context, path string) (bool, error)
}
```

### 7.3 StateStore

```go
type StateStore interface {
	LoadGateState(ctx context.Context) (*GateState, error)
	SaveGateState(ctx context.Context, state *GateState) error
	AppendRun(ctx context.Context, record RunRecord) error
	AppendGateAction(ctx context.Context, action GateAction) error
	AcquirePhaseLock(ctx context.Context, phase Phase) (UnlockFunc, error)
}
```

### 7.4 核心状态模型

| 类型 | 说明 |
|---|---|
| `WorkflowConfig` | 阶段与角色映射、交付物路径、输出语言、delivery mode、skip 规则 |
| `RuntimeConfig` | Provider、模型、超时、颜色、默认输出模式 |
| `GateState` | 当前阶段、各阶段审批状态、更新时间 |
| `RunRecord` | 每次执行的输入摘要、输出文件、耗时、结果、是否 dry-run |
| `GateAction` | approve/return 动作流水、原因、时间、操作者 |
| `CommandResponse[T]` | 全命令统一的 JSON 包裹模型 |

## 8. 状态、一致性与并发控制

### 8.1 文件模型

- `.ai/temp/*.md`：阶段产物
- `.ai/reports/**/*.md`：评审、QA、发布报告
- `.ai/records/**/*.md`：开发日志
- `.ai/state/gates.json`：当前 Gate 状态
- `.ai/state/runs.jsonl`：执行账本
- `.ai/state/gate-actions.jsonl`：Gate 动作账本
- `.ai/state/locks/phase.lock`：阶段执行锁

### 8.2 一致性规则

1. 交付物和 `gates.json` 使用原子写入
2. 账本文件使用追加写入，单行单记录
3. `run <role>` 先拿锁，再写开始记录，再执行业务，最后提交状态并释放锁
4. 执行失败时保留失败记录，不回滚已存在的历史账本

### 8.3 恢复策略

- `status` 先读 `gates.json`，再结合交付物存在性做一致性检查。
- `doctor` 检测陈旧锁、缺失文件、账本断裂，并给出可执行修复建议。

## 9. 角色执行主链路

`run <role>` 的最小执行顺序如下：

1. 解析 flags、环境变量和配置文件
2. 加载 `.cliagent/workflow.yaml`
3. 校验工作区脚手架与上游交付物
4. 根据角色映射定位阶段、目标文件和上下游输入
5. 组装 Prompt
6. 若为 `--dry-run`，输出 Prompt 摘要并写入执行账本
7. 调用 Provider
8. 原子写入交付物
9. 更新 `gates.json`
10. 追加 `runs.jsonl`
11. 按需要输出门控卡或 JSON 结果

Prompt 组装规则：

- 角色边界来自内置模板或受控模板文件，不从 `AGENTS.md` 直接抽取
- 项目上下文按需读取，不做全量无上限拼接
- 长文档优先摘要化，避免 token 膨胀和不稳定输出

## 10. 配置与工作区约定

### 10.1 配置优先级

1. flags
2. env
3. 项目级 `.cliagent/config.yaml`
4. 用户级配置文件
5. default

### 10.2 工作流配置示例

```yaml
version: 1
project:
  delivery_mode: standard
  output_language: zh-CN
  current_version: ""
  current_sprint: ""
roles:
  PM:
    phase: P1
    enabled: true
    output: .ai/temp/requirement.md
  Architect:
    phase: P2
    enabled: true
    output: .ai/temp/architect.md
```

### 10.3 运行配置示例

```yaml
provider:
  name: openai
  model: gpt-5.4
  timeout: 60s

cli:
  color: auto
  json_default: false
```

### 10.4 路径规则

- `delivery_mode=standard`：产物路径固定在 `.ai/temp/` 与 `.ai/reports/`
- `delivery_mode=scrum`：产物路径解析为 `.ai/{current_version}/{current_sprint}/...`
- 当 `scrum` 缺少 `current_version` 或 `current_sprint` 时，非 TTY 直接失败，TTY 才允许最小提示

## 11. 安全、测试与发布

### 11.1 安全

1. API Key 仅从环境变量读取
2. 日志、账本、错误输出默认脱敏
3. `doctor` 检查危险权限和配置缺失

### 11.2 测试

1. 单元测试：配置合并、阶段检测、Gate 流转、路径解析、错误映射
2. Golden Test：`status`、`gate list`、帮助文案、`--json` schema
3. 集成测试：`init -> run PM -> gate approve -> status -> doctor`
4. Mock Provider：保证离线稳定和 CI 可重复

### 11.3 发布

1. 使用 `goreleaser` 生成多平台二进制和 checksum
2. v1.0 即纳入 checksum 签名和 GitHub Artifact Attestation
3. 首批支持 `darwin/linux` 的 `amd64/arm64`

## 12. 实施顺序

### 阶段 A：冻结协议与脚手架

1. 固化命令面、错误码和 JSON schema
2. 完成 `init/status/config/version`
3. 建立 `.cliagent/` 与 `.ai/` 脚手架

### 阶段 B：打通工作流主链路

1. 完成 `run/gate/doctor`
2. 落地原子写入、执行账本、阶段锁
3. 完成 Mock Provider、Golden 和最小集成测试

### 阶段 C：接入真实 Provider 与发布链

1. 完成 `openai` provider
2. 补齐错误分类、超时、重试和脱敏
3. 接入 `goreleaser`、签名和 attestation

阶段验收只看三件事：

1. 非交互主链路可稳定执行
2. 输出协议可回归测试
3. 中断和失败后状态可恢复、可审计
