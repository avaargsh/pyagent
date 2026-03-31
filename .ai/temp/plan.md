# cliagent 技术方案

## 1. 文档范围与假设

- 本文档用于把 `docs/cliagent-go-design.md` 中的实施顺序映射为可直接执行的文件级实现计划。
- 当前已存在 `.ai/temp/package-plan.md`，本文的目录边界、接口归属和文件映射以该契约为准。
- 任务编号与 `.ai/temp/wbs.md` 保持一致；若后续 WBS 变更，Plan 必须同步刷新。
- 文件清单以“首版建议新增文件”为主，后续允许按实现需要微调，但不得偏离主设计稿的分层边界。

## 2. 任务到文件清单映射

### T1：根命令与子命令骨架

新增 / 修改文件：

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

### T2：统一输出模型与错误码

新增 / 修改文件：

- `internal/app/types.go`
- `internal/output/printer.go`
- `internal/output/model.go`
- `internal/output/json.go`
- `internal/output/table.go`
- `internal/output/errors.go`

### T3：Golden 基线

新增 / 修改文件：

- `testdata/golden/help-root.txt`
- `testdata/golden/status-human.txt`
- `testdata/golden/status-json.json`
- `testdata/golden/gate-list-json.json`
- `internal/cli/root_test.go`
- `internal/cli/status_cmd_test.go`
- `internal/cli/gate_cmd_test.go`

### T4：配置模型、加载与校验

新增 / 修改文件：

- `internal/config/model.go`
- `internal/config/loader.go`
- `internal/config/validate.go`
- `internal/app/config.go`
- `internal/config/loader_test.go`
- `internal/config/validate_test.go`

### T5：工作区脚手架与 `init`

新增 / 修改文件：

- `internal/workspace/paths.go`
- `internal/workspace/scaffold.go`
- `internal/workspace/files.go`
- `internal/app/init.go`
- `internal/cli/init_cmd_test.go`
- `testdata/fixtures/init/`

### T6：`status` 主链路

新增 / 修改文件：

- `internal/workflow/detector.go`
- `internal/app/status.go`
- `internal/output/table.go`
- `internal/cli/status_cmd_test.go`

### T7：阶段、角色与路径解析

新增 / 修改文件：

- `internal/workflow/phase.go`
- `internal/workflow/role.go`
- `internal/workflow/registry.go`
- `internal/workflow/resolver.go`
- `internal/workflow/phase_test.go`
- `internal/workflow/registry_test.go`

### T8：状态存储、账本与锁

新增 / 修改文件：

- `internal/state/model.go`
- `internal/state/store.go`
- `internal/state/file_store.go`
- `internal/state/lock.go`
- `internal/state/file_store_test.go`
- `internal/state/lock_test.go`

### T9：`gate approve|return|list`

新增 / 修改文件：

- `internal/app/gate.go`
- `internal/cli/gate_cmd.go`
- `internal/workflow/gatekeeper.go`
- `internal/workflow/gatekeeper_test.go`
- `internal/cli/gate_cmd_test.go`

### T10：上下文装配与 `run --dry-run`

新增 / 修改文件：

- `internal/app/run_role.go`
- `internal/app/context_loader.go`
- `internal/app/prompt_builder.go`
- `internal/app/run_role_test.go`
- `testdata/fixtures/run-dry-run/`

### T11：Mock Provider 与 `run <role>`

新增 / 修改文件：

- `internal/provider/provider.go`
- `internal/provider/message.go`
- `internal/provider/factory.go`
- `internal/provider/mock/mock.go`
- `internal/provider/mock/mock_test.go`
- `internal/app/run_role.go`
- `internal/cli/run_cmd_test.go`
- `testdata/fixtures/run-mock/`

### T12：`doctor`

新增 / 修改文件：

- `internal/app/doctor.go`
- `internal/cli/doctor_cmd.go`
- `internal/app/doctor_test.go`
- `testdata/fixtures/doctor/`

### T13：OpenAI Provider

新增 / 修改文件：

- `internal/provider/openai/client.go`
- `internal/provider/openai/client_test.go`
- `internal/provider/openai/request.go`
- `internal/provider/openai/response.go`

### T14：脱敏、超时、错误策略

新增 / 修改文件：

- `internal/provider/redact.go`
- `internal/provider/errors.go`
- `internal/provider/timeout.go`
- `internal/output/errors.go`
- `internal/provider/redact_test.go`

### T15：发布链

新增 / 修改文件：

- `.goreleaser.yml`
- `.github/workflows/release.yml`
- `.github/workflows/test.yml`
- `docs/release.md`

### T16：发布回归验证

新增 / 修改文件：

- `scripts/verify-release.sh`
- `testdata/fixtures/release/`
- `.ai/reports/release/release-guide-template.md`

## 3. 关键实现步骤

### 阶段 A：冻结协议与脚手架

1. 先完成 T1，固化命令树与参数面，避免后续测试和实现基线漂移。
2. 并行推进 T4 和 T2，分别稳定配置来源和输出协议。
3. 在 T4 完成后实现 T5，确保 `init` 生成的脚手架与配置模型一致。
4. 基于 T1/T2/T4/T5 交付 T6，完成可机读的 `status`。
5. 在命令面与输出协议稳定后完成 T3，固化 Golden 基线。

### 阶段 B：打通工作流主链路

1. 先做 T7，统一阶段、角色、交付物路径和角色别名映射。
2. 再做 T8，保证状态、账本和阶段锁具备最小可恢复性。
3. 基于 T7/T8 完成 T9，冻结 Gate 状态流转规则。
4. 在状态模型稳定后做 T10，实现 `run --dry-run`、输入校验与上下文装配。
5. 然后做 T11，用 Mock Provider 打通 `run <role>` 到交付物落盘的主链路。
6. 最后完成 T12，让 `doctor` 负责一致性检查、迁移提示和损坏状态诊断。

### 阶段 C：接入真实 Provider 与发布链

1. 在 Mock 主链路稳定后接入 T13，只实现最小 `Chat` 能力，不提前做流式能力。
2. 通过 T14 收敛超时、错误包装和脱敏逻辑，确保真实调用安全可观测。
3. 完成 T15，把构建、checksum、签名和 attestation 纳入 CI。
4. 最后用 T16 建立发布前验证脚本和人工执行手册。

## 4. 依赖顺序

```text
T1 -> T2 -> T3
T4 -> T5 -> T6
T4 -> T7 -> T8 -> T9
T4 + T7 + T8 -> T10 -> T11 -> T12
T11 -> T13 -> T14 -> T15 -> T16
```

关键依赖说明：

- `T4` 是全局输入源依赖，没有配置模型就没有稳定的命令行为。
- `T8` 是主链路的一致性依赖，`run/gate/doctor` 都不能绕过它。
- `T11` 是真实 Provider 联调前的质量闸门，未通过不进入 `T13`。

## 5. 风险点与回退方案

| 风险点 | 影响 | 触发信号 | 回退方案 |
|---|---|---|---|
| 命令面过早变更 | Golden、大量测试和文档同步返工 | 子命令或 flags 高频改名 | 在 T1 完成后冻结命令面；新增命令一律延后到 v1.1+ |
| 配置模型与脚手架不一致 | `init` 生成的工程无法被 `status/run` 正确解析 | 初始化后首次执行即报配置错误 | 以 `.cliagent/*.yaml` 模板为基线重放 `init`；禁止多套模板并存 |
| 阶段检测和 Gate 状态冲突 | `status` 结果不可信 | 文件存在但 Gate 状态缺失或相反 | `status` 以 `gates.json` 为主，文件存在性作为一致性检查，不作为唯一事实源 |
| 原子写入或锁实现不稳 | 交付物损坏、账本断裂、并发覆盖 | 中断后出现半写文件或陈旧锁 | 先用文件锁和临时文件实现最小正确性，不在 v1.0 引入 SQLite |
| Prompt 装配失控 | token 成本和输出稳定性失控 | dry-run 输出过长或输入重复 | 优先路径引用和摘要，限制读取范围；超长输入直接报错 |
| OpenAI Provider 联调不稳定 | 延迟 M3 | 认证失败、超时、响应解析错误频发 | 保持 Mock 为默认 provider；真实 provider 问题不阻塞主链路可发布性 |
| 发布链接入过晚 | 首次发布手工步骤过多，可信链缺失 | 构建可跑但无 checksum/签名/attestation | 在 T15 前不宣布可发布版本；先补齐 CI 后再做版本打包 |

## 6. 优先测试清单

### P0：必须先补

1. 配置优先级测试：flag > env > project config > user config > default
2. `status --json` schema 测试：字段名、布尔值和错误包裹稳定
3. Gate 流转测试：approve/return/list 的合法与非法路径
4. 原子写入测试：交付物和 `gates.json` 失败时不产生半写状态
5. 阶段锁测试：重复执行同一阶段时能拒绝并给出可操作提示
6. `run --dry-run` 测试：不调用 provider，但仍产生稳定摘要和账本记录
7. Mock Provider 集成测试：`init -> status -> run PM -> gate approve -> doctor`

### P1：进入真实 Provider 前补齐

1. OpenAI 认证失败与超时测试
2. Provider 错误脱敏测试
3. `doctor` 的陈旧锁、缺失账本、配置冲突诊断测试
4. `gate list --json` 排序和时间戳稳定性测试

### P2：发布前补齐

1. `goreleaser` 配置 smoke test
2. checksum 生成与校验脚本测试
3. 发布工作流 dry-run
