# cliagent 包结构契约

## 1. 文档范围与假设

- 本文档基于 `docs/cliagent-go-design.md`、`.ai/temp/wbs.md` 与 `.ai/temp/plan.md` 编写，是当前仓库的 P5a 包结构契约。
- 当前仓库尚未生成正式的 `.ai/temp/requirement.md`、`.ai/temp/architect.md`、`.ai/temp/cli-spec.md`，因此命令边界、非功能目标和输出约定暂以主设计稿为准。
- v1.0 只覆盖主链路：`init/status/run/gate/config/doctor/version + mock/openai + dry-run + 状态一致性`。
- `chat`、`pipeline`、`pattern` 管理、`anthropic`、`sqlite`、TUI、MCP 均不进入本包结构契约。
- 默认不创建 `pkg/` 公共 API；若未来需要对外暴露稳定类型，再单独评估。

## 2. 推荐目录树

```text
cmd/
└── cliagent/
    └── main.go

internal/
├── cli/
│   ├── root.go
│   ├── common.go
│   ├── init_cmd.go
│   ├── status_cmd.go
│   ├── run_cmd.go
│   ├── gate_cmd.go
│   ├── config_cmd.go
│   ├── doctor_cmd.go
│   └── version_cmd.go
├── app/
│   ├── bootstrap.go
│   ├── types.go
│   ├── init.go
│   ├── status.go
│   ├── run_role.go
│   ├── gate.go
│   ├── config.go
│   ├── doctor.go
│   ├── context_loader.go
│   └── prompt_builder.go
├── config/
│   ├── model.go
│   ├── loader.go
│   └── validate.go
├── workflow/
│   ├── phase.go
│   ├── role.go
│   ├── registry.go
│   ├── resolver.go
│   ├── detector.go
│   └── gatekeeper.go
├── provider/
│   ├── provider.go
│   ├── message.go
│   ├── factory.go
│   ├── errors.go
│   ├── redact.go
│   ├── timeout.go
│   ├── mock/
│   │   └── mock.go
│   └── openai/
│       ├── client.go
│       ├── request.go
│       └── response.go
├── workspace/
│   ├── paths.go
│   ├── scaffold.go
│   └── files.go
├── state/
│   ├── model.go
│   ├── store.go
│   ├── file_store.go
│   └── lock.go
├── output/
│   ├── model.go
│   ├── printer.go
│   ├── json.go
│   ├── table.go
│   └── errors.go
└── version/
    └── version.go

testdata/
├── fixtures/
│   ├── init/
│   ├── status/
│   ├── run-dry-run/
│   ├── run-mock/
│   ├── doctor/
│   └── release/
└── golden/
    ├── help-root.txt
    ├── status-human.txt
    ├── status-json.json
    └── gate-list-json.json
```

补充约束：

- 不新增 `internal/role/` 独立包，角色定义并入 `internal/workflow/`。
- 不新增 `internal/pattern/`；角色模板能力延后到 v1.1+。
- `internal/workflow/` 只保留规则与映射，不承担文件 I/O。

## 3. 每个包的职责

| 包 | 主要职责 | 允许依赖 | 禁止依赖 |
|---|---|---|---|
| `cmd/cliagent` | 进程入口、依赖组装、调用 `cli.Execute()` | `internal/cli` | 其他业务包 |
| `internal/cli` | Cobra 命令定义、flags 解析、TTY 判断、Exit Code 映射、调用 `app` 与 `output` | `internal/app` `internal/output` `internal/version` | `provider` `workspace` `state` 的底层细节 |
| `internal/app` | 单个用例编排；组合配置、工作流、Provider、状态、工作区；返回纯结果结构体 | `config` `workflow` `provider` `workspace` `state` | `cli`、直接终端渲染 |
| `internal/config` | 运行配置与工作流配置模型、加载、合并、校验 | 标准库、YAML 解析 | `cli` `app` `state` |
| `internal/workflow` | 阶段枚举、角色注册、交付物解析、Gate 规则、检测输入模型 | `config` 或纯内部类型 | `workspace` `state` `provider` |
| `internal/provider` | 统一消息模型、Provider 接口、工厂、超时、脱敏、错误包装与具体实现 | 标准库 | `cli` `app` `workflow` |
| `internal/workspace` | 路径解析、脚手架生成、文件读写、原子写入 | `config` | `cli` `output` `provider` |
| `internal/state` | Gate 状态、执行账本、锁文件、状态持久化接口与文件实现 | `workflow` | `cli` `output` `provider` |
| `internal/output` | human/json 渲染、稳定错误包裹、表格输出 | 标准库 | `app` 以外的业务依赖 |
| `internal/version` | 版本信息、构建元数据 | 标准库 | 其他业务包 |

依赖方向必须保持为：

```text
cmd -> cli -> app
cli -> output, version
app -> config, workflow, provider, workspace, state
state -> workflow
workflow/config/provider/workspace/output/version 彼此尽量平行，不反向依赖 app/cli
```

硬约束：

1. `cli` 只能做参数解析和结果展示，不能直接操作 `.ai/` 文件。
2. `app` 是唯一允许同时依赖 `workflow + provider + workspace + state` 的层。
3. `workflow` 只处理规则、阶段和角色映射；任何文件读取都在 `workspace` 或 `app` 完成。
4. `provider` 通过接口隔离，`app` 只能依赖 `provider.Provider`，不能依赖具体实现包。
5. `pkg/` 默认空置，避免为了未来扩展预埋公共 API。

## 4. 关键接口与结构体

### 4.1 关键接口归属

`internal/provider/provider.go`

```go
type Provider interface {
	Name() string
	Chat(ctx context.Context, req ChatRequest) (*ChatResult, error)
}
```

说明：

- `StreamingProvider` 仅预留，不进入 v1.0 主链路。
- `provider.Factory` 负责根据 `RuntimeConfig.Provider.Name` 返回 `mock` 或 `openai` 实例。

`internal/workspace/files.go`

```go
type Workspace interface {
	ProjectRoot() string
	EnsureScaffold(ctx context.Context) error
	ReadFile(ctx context.Context, path string) ([]byte, error)
	WriteFileAtomic(ctx context.Context, path string, data []byte) error
	FileExists(ctx context.Context, path string) (bool, error)
}
```

说明：

- `WriteFileAtomic` 是必须能力，不能下沉到调用方自己拼装临时文件逻辑。

`internal/state/store.go`

```go
type StateStore interface {
	LoadGateState(ctx context.Context) (*GateState, error)
	SaveGateState(ctx context.Context, state *GateState) error
	AppendRun(ctx context.Context, record RunRecord) error
	AppendGateAction(ctx context.Context, action GateAction) error
	AcquirePhaseLock(ctx context.Context, phase workflow.Phase) (UnlockFunc, error)
}
```

说明：

- v1.0 只实现文件版 `StateStore`。
- `AcquirePhaseLock` 返回释放函数，避免调用方直接操作锁文件。

### 4.2 关键结构体归属

| 包 | 结构体 / 类型 | 用途 |
|---|---|---|
| `config` | `RuntimeConfig` | Provider、CLI、日志、超时等运行配置 |
| `config` | `WorkflowConfig` | 角色到阶段映射、交付物路径、output language、delivery mode |
| `config` | `RoleConfig` `ProjectConfig` `GateConfig` | 工作流细分模型 |
| `workflow` | `Phase` | P1~P9 的强类型枚举 |
| `workflow` | `RoleID` `RoleSpec` | 角色标识、别名、输出路径、启用状态 |
| `workflow` | `Deliverable` `StatusSnapshot` | 阶段检测与状态表渲染所需的中间模型 |
| `app` | `RunRoleRequest` `RunRoleResult` | `run` 用例的输入输出 |
| `app` | `StatusResult` | `status` 用例返回的阶段、Gate、交付物摘要 |
| `app` | `GateResult` | `gate approve|return|list` 返回结果 |
| `app` | `DoctorResult` | `doctor` 的诊断结果、告警与建议 |
| `provider` | `Message` `ChatRequest` `ChatResult` | Provider 无关的统一消息协议 |
| `state` | `GateState` | 当前阶段、阶段审批状态、更新时间 |
| `state` | `PhaseState` | 单阶段审批状态 |
| `state` | `RunRecord` | 每次执行的账本记录 |
| `state` | `GateAction` | `approve/return` 动作流水 |
| `output` | `CommandResponse[T]` | 统一 JSON 包裹模型 |
| `version` | `Info` | 版本、commit、build time 等元数据 |

### 4.3 包边界上的实现约束

- `StatusResult`、`GateResult`、`DoctorResult` 由 `app` 输出纯数据结构，渲染由 `output` 完成。
- `context_loader.go` 与 `prompt_builder.go` 归属 `internal/app`，因为它们既需要读取文件，又需要拼接业务上下文，不应放进 `workflow`。
- `detector.go` 在 `workflow` 中只接收“已观测到的交付物状态”，不直接读文件系统。

## 5. 配置模型与状态模型

### 5.1 配置模型

`RuntimeConfig` 建议字段：

```yaml
provider:
  name: mock
  model: mock-default
  timeout: 60s

cli:
  color: auto
  json_default: false
  no_input: false

logging:
  level: info
  redact_secrets: true
```

`WorkflowConfig` 建议字段：

```yaml
version: 1
project:
  delivery_mode: standard
  output_language: zh-CN
  current_version: ""
  current_sprint: ""
gate:
  require_approval: true
roles:
  PM:
    phase: P1
    enabled: true
    output: .ai/temp/requirement.md
```

模型归属规则：

1. 配置文件序列化模型只放在 `internal/config`。
2. `.ai/context/*.md` 是角色上下文输入，不进入配置模型。
3. 配置优先级固定为 `flag > env > project config > user config > default`。

### 5.2 状态模型

`GateState` 建议结构：

```json
{
  "current_phase": "P2",
  "last_action": "approve",
  "updated_at": "2026-03-31T21:00:00+08:00",
  "phases": {
    "P1": "approved",
    "P2": "pending"
  }
}
```

`RunRecord` 必须至少包含：

- `run_id`
- `role`
- `phase`
- `dry_run`
- `input_summary`
- `output_files`
- `provider`
- `model`
- `started_at`
- `ended_at`
- `status`
- `error_code`

`GateAction` 必须至少包含：

- `phase`
- `action`
- `reason`
- `actor`
- `created_at`

状态模型归属规则：

1. `gates.json` 存“当前事实”。
2. `runs.jsonl` 与 `gate-actions.jsonl` 存“追加账本”。
3. 锁状态只通过 `state` 包管理，调用方不能自行写 `.ai/state/locks/`。

## 6. 测试桩、Mock、Golden 文件放置方式

| 类型 | 放置位置 | 规则 |
|---|---|---|
| 单元测试 | 各包同目录 `*_test.go` | 优先测试包边界、错误路径、序列化与状态流转 |
| 集成 Fixture | `testdata/fixtures/` | 每个子目录对应一个最小工作区场景，如 `init/`、`run-mock/`、`doctor/` |
| Golden 文件 | `testdata/golden/` | 只存 CLI 可见稳定输出，如帮助文案、`status`、`gate list --json` |
| 生产可用 Mock Provider | `internal/provider/mock/` | 既用于测试，也作为 v1.0 默认 provider |
| 测试专用 Fake | 各包 `*_test.go` 内或同包测试辅助文件 | 不进入生产编译路径 |

具体约束：

1. Golden 只覆盖 `stdout` 稳定输出，不覆盖日志时间戳等不稳定字段。
2. `Mock Provider` 是正式实现，不放在 `testdata/`。
3. `StateStore`、`Workspace`、`Provider` 的临时 Fake 优先写在测试文件内，避免污染生产包接口。
4. 集成测试最小链路固定为：`init -> status -> run PM -> gate approve -> doctor`。

## 7. 预计新增 / 修改文件列表

### A. 命令与应用层

- `cmd/cliagent/main.go`
- `internal/cli/root.go`
- `internal/cli/common.go`
- `internal/cli/init_cmd.go`
- `internal/cli/status_cmd.go`
- `internal/cli/run_cmd.go`
- `internal/cli/gate_cmd.go`
- `internal/cli/config_cmd.go`
- `internal/cli/doctor_cmd.go`
- `internal/cli/version_cmd.go`
- `internal/app/bootstrap.go`
- `internal/app/types.go`
- `internal/app/init.go`
- `internal/app/status.go`
- `internal/app/run_role.go`
- `internal/app/gate.go`
- `internal/app/config.go`
- `internal/app/doctor.go`
- `internal/app/context_loader.go`
- `internal/app/prompt_builder.go`

### B. 配置、工作流、状态

- `internal/config/model.go`
- `internal/config/loader.go`
- `internal/config/validate.go`
- `internal/workflow/phase.go`
- `internal/workflow/role.go`
- `internal/workflow/registry.go`
- `internal/workflow/resolver.go`
- `internal/workflow/detector.go`
- `internal/workflow/gatekeeper.go`
- `internal/workspace/paths.go`
- `internal/workspace/scaffold.go`
- `internal/workspace/files.go`
- `internal/state/model.go`
- `internal/state/store.go`
- `internal/state/file_store.go`
- `internal/state/lock.go`

### C. Provider、输出与版本

- `internal/provider/provider.go`
- `internal/provider/message.go`
- `internal/provider/factory.go`
- `internal/provider/errors.go`
- `internal/provider/redact.go`
- `internal/provider/timeout.go`
- `internal/provider/mock/mock.go`
- `internal/provider/openai/client.go`
- `internal/provider/openai/request.go`
- `internal/provider/openai/response.go`
- `internal/output/model.go`
- `internal/output/printer.go`
- `internal/output/json.go`
- `internal/output/table.go`
- `internal/output/errors.go`
- `internal/version/version.go`

### D. 测试与发布辅助

- `testdata/fixtures/init/`
- `testdata/fixtures/status/`
- `testdata/fixtures/run-dry-run/`
- `testdata/fixtures/run-mock/`
- `testdata/fixtures/doctor/`
- `testdata/fixtures/release/`
- `testdata/golden/help-root.txt`
- `testdata/golden/status-human.txt`
- `testdata/golden/status-json.json`
- `testdata/golden/gate-list-json.json`
- `.goreleaser.yml`
- `.github/workflows/test.yml`
- `.github/workflows/release.yml`
- `scripts/verify-release.sh`

说明：

- `internal/output/model.go` 用于承载 `CommandResponse[T]`，不再在 `app` 层维护响应包裹结构。
- `internal/app/context_loader.go` 与 `internal/app/prompt_builder.go` 取代先前放在 `workflow` 的草案位置，以保持领域层纯净。
