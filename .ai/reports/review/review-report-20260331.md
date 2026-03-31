# cliagent 方案审计报告

> 日期：2026-03-31
> 范围：`AGENTS.md`、`docs/cliagent-go-design.md` 与当时存在的旧版设计稿

## 结论

当前方案已经按“最优路线”完成一次必要收敛：主基线已统一到 `docs/cliagent-go-design.md`，`AGENTS.md` 与机器配置源已对齐，旧版设计稿已退出主线。

审计后结论：

- 未发现继续推进实现的阻塞级架构矛盾
- 仍有 1 个实现前建议项，需要在进入编码前补齐

## 已修复的阻塞项

### 1. 基线分叉导致实现标准不唯一

原问题：

- `AGENTS.md:5` 要求实现以 `docs/cliagent-go-design.md` 为基线。
- 但真正的定位收敛、MVP 减法和状态增强一度只存在于旧版优化稿中。
- 这会导致后续实现时同时引用 v1 和 v3，产生命令面、状态模型和范围判断分裂。

处理结果：

- `docs/cliagent-go-design.md:3-5` 明确为唯一实现基线。
- 旧版设计稿已从主线剥离，不再作为实现基线。

### 2. 机器配置源与人类协议源冲突

原问题：

- `AGENTS.md:39-55` 与 `AGENTS.md:68-81` 原先要求从 Markdown 路径读取工作流配置。
- 这与全局约束“机器可消费配置必须落到结构化文件”冲突，也与设计稿“不得解析自由文本 Markdown”冲突。

处理结果：

- `AGENTS.md:39-55` 已改为 `.cliagent/workflow.yaml` 和 `.cliagent/config.yaml`。
- `AGENTS.md:68-81` 与 `AGENTS.md:150-156` 已统一使用 `.cliagent/workflow.yaml`。
- `docs/cliagent-go-design.md:30-43` 明确区分 `AGENTS.md`、`.cliagent/*.yaml`、`.ai/context/*.md` 的职责边界。

### 3. MVP 范围膨胀，偏离主链路

原问题：

- 旧版扩张稿曾将 `chat`、`pipeline`、`anthropic`、Pattern 管理、流式输出同时塞入 MVP。
- 这与“先打通主链路，再补增强能力”的工程约束不一致。

处理结果：

- `docs/cliagent-go-design.md:80-109` 已将 v1.0 收敛到 `init/status/run/gate/config/doctor/version + mock/openai + dry-run + 状态一致性`。
- `docs/cliagent-go-design.md:96-109` 明确将增强能力延后到 v1.1+。

### 4. 协议与状态模型不完整，无法支撑审计与恢复

原问题：

- 旧基线只有基础命令和简单状态设想，缺少统一 JSON 包裹、执行账本、Gate 动作账本和阶段锁。
- 这会使 CI 集成、失败恢复、并发保护和审计留痕都不稳定。

处理结果：

- `docs/cliagent-go-design.md:151-198` 固化了统一 JSON 协议和错误码。
- `docs/cliagent-go-design.md:303-325` 增加了 `runs.jsonl`、`gate-actions.jsonl` 和 `locks/phase.lock`。
- `docs/cliagent-go-design.md:327-347` 明确了 `run <role>` 的最小执行顺序。

### 5. 缺少默认配置与上下文模板，工作流无法直接起步

原问题：

- 仓库中原先没有 `.cliagent/` 配置模板，也没有 `.ai/context/` 约束模板。
- 即使方案正确，进入实现或演示时仍会卡在“默认配置从哪里来”的问题上。

处理结果：

- 已新增 `.cliagent/workflow.yaml` 与 `.cliagent/config.yaml` 作为默认结构化配置。
- 已新增 `.ai/context/product-constraint.md`、`.ai/context/architect-constraint.md`、`.ai/context/release-constraint.md` 作为工作流输入模板。

## 建议项

### 1. 将实施顺序转成可执行 WBS 与 Plan

技术基线已经有实现顺序，但还没有转成 `.ai/temp/wbs.md` 和 `.ai/temp/plan.md` 这类可执行交付物。若下一步进入实现，建议先把 `docs` 中的阶段 A/B/C 映射为任务级文件清单与测试清单。

参考：

- `docs/cliagent-go-design.md:421-443`
- `AGENTS.md:266-362`

## 简短结论

当前路线已经从“分叉设计稿”收敛为“单一基线 + 结构化配置 + 主链路优先”。下一步只需把实施顺序展开为 WBS 与 Plan，即可进入实现阶段。
