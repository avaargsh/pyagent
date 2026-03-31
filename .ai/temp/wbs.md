# cliagent WBS

## 1. 文档范围与假设

- 本文档基于 `docs/cliagent-go-design.md` 的 v1.0 基线展开。
- 当前仓库尚未生成 `.ai/temp/requirement.md`、`.ai/temp/architect.md`、`.ai/temp/cli-spec.md`，因此本 WBS 以主设计稿和 `.cliagent/workflow.yaml` 作为暂代上游输入。
- 当前仓库已生成 `.ai/temp/package-plan.md`，任务的目录边界、接口归属和测试放置方式以该文档为准。
- 任务粒度统一控制在 0.5–2 人天，且每项任务都必须以可验证文件、测试或命令输出作为交付物。
- v1.0 只覆盖主链路：`init/status/run/gate/config/doctor/version + mock/openai + dry-run + 状态一致性`。

## 2. 里程碑

| 里程碑 | 目标 | 对应设计稿阶段 | 完成标准 |
|---|---|---|---|
| M1 | 冻结协议与初始化脚手架 | 阶段 A | 命令面、错误码、JSON schema 固化；`init/status/config/version` 可运行 |
| M2 | 打通工作流主链路 | 阶段 B | `run/gate/doctor` 可运行；状态一致性、账本与锁可验证 |
| M3 | 接入真实 Provider 与发布链 | 阶段 C | `openai` provider 可用；构建发布链可产出可校验制品 |

## 3. 史诗 / 故事 / 任务拆解

### 史诗 E1：协议冻结与 CLI 骨架

#### 故事 S1：冻结命令面与输出协议

| 任务 | 预估 | 说明 | 输入 | 输出 | 依赖 | 风险 |
|---|---|---|---|---|---|---|
| T1 | 1 人天 | 定义根命令、子命令树和帮助文案骨架 | 主设计稿第 4–5 节 | `cmd/cliagent/main.go`、`internal/cli/root.go`、各命令骨架文件 | 无 | 命令命名或参数后续变更会引发 Golden 大面积更新 |
| T2 | 1 人天 | 实现统一 `--json` 响应模型、错误码映射和输出接口 | 主设计稿第 5 节 | `internal/output/`、命令响应模型、错误类型 | T1 | 早期抽象不清会导致 CLI 层和应用层相互渗透 |
| T3 | 0.5 人天 | 建立帮助文案、`status --json`、错误输出的 Golden 基线 | T1、T2 产物 | `testdata/golden/`、CLI Golden Test | T1、T2 | 输出格式若未先冻结，会造成测试频繁失效 |

#### 故事 S2：建立配置与工作区脚手架

| 任务 | 预估 | 说明 | 输入 | 输出 | 依赖 | 风险 |
|---|---|---|---|---|---|---|
| T4 | 1 人天 | 实现 `.cliagent/config.yaml` 与 `.cliagent/workflow.yaml` 的模型、加载与校验 | 主设计稿第 2、10 节；现有 `.cliagent/*.yaml` 模板 | `internal/config/`、配置单测 | 无 | 配置优先级或默认值处理错误会影响全部命令 |
| T5 | 1 人天 | 实现 `init` 脚手架和默认目录生成 | T4、现有 `.ai/context/` 模板 | `internal/workspace/scaffold.go`、`init` 命令测试 | T4 | 脚手架与设计基线不一致会制造后续迁移成本 |
| T6 | 1 人天 | 实现阶段检测、状态表渲染和 `status` 主链路 | 主设计稿第 6、8 节；`.cliagent/workflow.yaml` | `internal/workflow/detector.go`、`internal/output/table.go`、`status` 测试 | T1、T2、T4、T5 | 阶段检测若只看文件存在性，容易与 Gate 状态冲突 |

### 史诗 E2：工作流主链路与状态一致性

#### 故事 S3：落地阶段模型、Gate 与账本

| 任务 | 预估 | 说明 | 输入 | 输出 | 依赖 | 风险 |
|---|---|---|---|---|---|---|
| T7 | 1 人天 | 实现阶段、角色注册、路径解析与交付物映射 | 主设计稿第 6、7、10 节；`.cliagent/workflow.yaml` | `internal/workflow/phase.go`、`role/registry` 等价实现、路径解析测试 | T4 | 角色名、阶段号、输出路径若未统一会让 `run` 和 `status` 结果不一致 |
| T8 | 1.5 人天 | 实现 `gates.json`、`runs.jsonl`、`gate-actions.jsonl` 和阶段锁 | 主设计稿第 8 节 | `internal/state/`、状态单测 | T7 | 原子写入与并发锁处理不当会破坏可恢复性 |
| T9 | 1 人天 | 实现 `gate approve`、`gate return`、`gate list` | T7、T8 | `internal/app/gate.go`、`internal/cli/gate_cmd.go`、Gate Golden Test | T7、T8 | 状态流转规则不严会允许非法跳阶段 |

#### 故事 S4：打通 `run` 与 `doctor`

| 任务 | 预估 | 说明 | 输入 | 输出 | 依赖 | 风险 |
|---|---|---|---|---|---|---|
| T10 | 1.5 人天 | 实现 Prompt 输入装配、上游交付物校验和 `run --dry-run` | 主设计稿第 9 节；`.ai/context/*.md` 模板 | `internal/app/run_role.go`、`internal/workflow/context_loader.go`、dry-run 测试 | T4、T7、T8 | 上下文装配如果失控，真实调用会导致 token 和输出不稳定 |
| T11 | 1.5 人天 | 实现 Mock Provider 和 `run <role>` 主链路原子落盘 | 主设计稿第 4、7、8、9 节 | `internal/provider/mock/`、主链路集成测试 | T8、T10 | 失败场景处理不严会出现交付物写入成功但状态未提交 |
| T12 | 1 人天 | 实现 `doctor` 的一致性检查、陈旧锁检查和迁移提示 | 主设计稿第 2、8、10、11 节 | `internal/app/doctor.go`、`doctor` 测试 | T4、T8、T11 | 诊断规则过弱会让损坏状态被静默放过 |

### 史诗 E3：真实 Provider 与发布链

#### 故事 S5：接入 OpenAI Provider

| 任务 | 预估 | 说明 | 输入 | 输出 | 依赖 | 风险 |
|---|---|---|---|---|---|---|
| T13 | 1.5 人天 | 实现 OpenAI Provider 最小 `Chat` 客户端、超时与错误包装 | 主设计稿第 7、11、12 节 | `internal/provider/openai/`、Provider 单测 | T10、T11 | 接口或认证错误会拖慢整体联调 |
| T14 | 1 人天 | 落地日志脱敏、错误提示规范和 Provider 回退策略 | T13；主设计稿安全要求 | `internal/provider/`、`internal/output/`、错误回归测试 | T13 | 脱敏遗漏会造成密钥泄露风险 |

#### 故事 S6：建立发布链

| 任务 | 预估 | 说明 | 输入 | 输出 | 依赖 | 风险 |
|---|---|---|---|---|---|---|
| T15 | 1 人天 | 增加 `goreleaser`、checksum、签名与 attestation 工作流 | 主设计稿第 11 节；发布约束模板 | `.goreleaser.yml`、CI 工作流、发布文档 | T1、T13、T14 | 过早接入发布链会消耗实现节奏，过晚接入会让制品格式返工 |
| T16 | 0.5 人天 | 构建端到端回归矩阵和最小发布验证脚本 | T15、集成测试结果 | 发布验证脚本、发布前检查单 | T15 | 平台矩阵不完整会延迟首次发布 |

## 4. 并行任务与阻塞任务

### 阻塞任务

| 任务 | 原因 | 被阻塞任务 |
|---|---|---|
| T1 | 命令面未冻结前无法稳定写 Golden | T2、T3、T6、T9 |
| T4 | 配置模型决定所有命令的输入来源 | T5、T6、T7、T10、T12 |
| T7 | 阶段与路径映射是 Gate 和 `run` 的基础 | T8、T9、T10、T11 |
| T8 | 状态存储和锁是 `run`、`gate`、`doctor` 的一致性基础 | T9、T11、T12 |
| T10 | `run` 上下文装配未完成前，真实 Provider 无法联调 | T11、T13 |
| T13 | 真实 Provider 未完成前，发布链无法完成真实端到端验证 | T14、T15、T16 |

### 可并行任务

| 并行组 | 任务 | 说明 |
|---|---|---|
| G1 | T2 + T4 | 输出模型和配置模型边界清晰，可并行推进 |
| G2 | T3 + T5 | 一边固化 Golden，一边实现 `init` 脚手架 |
| G3 | T9 + T12 | 在 T8 完成后，Gate 与 `doctor` 可并行开发 |
| G4 | T14 + T15 | 在 T13 可用后，安全收敛和发布链可并行 |

## 5. MVP 首批实现顺序

建议首批实现顺序如下：

1. T1：冻结命令树和帮助文案骨架
2. T4：完成配置模型、加载与校验
3. T2：完成统一输出模型与错误码映射
4. T5：完成 `init` 工作区脚手架
5. T6：完成 `status`
6. T7：完成阶段、角色与路径解析
7. T8：完成状态存储、账本和锁
8. T9：完成 `gate approve|return|list`
9. T10：完成 `run --dry-run` 和上下文装配
10. T11：完成 Mock Provider 驱动的 `run <role>`
11. T12：完成 `doctor`
12. T3：回填并稳定 Golden 基线
13. T13：接入 OpenAI Provider
14. T14：补齐脱敏和 Provider 错误策略
15. T15：接入发布链
16. T16：完成发布回归验证

顺序原则：

- 先冻结协议，再建立脚手架
- 先打通 Mock 主链路，再接入真实 Provider
- 先保证状态一致性，再建设发布链

## 6. 验收口径

- M1 验收：`init/status/config/version` 在非交互模式下可执行，且 `--json` 输出稳定。
- M2 验收：`run/gate/doctor` 可在 Mock Provider 下完整跑通，失败后可通过状态文件和账本追溯。
- M3 验收：OpenAI Provider 可联调，发布产物可生成 checksum 并完成来源证明。
