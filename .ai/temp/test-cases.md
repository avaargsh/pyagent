# P8 QA 测试用例

## 1. 测试依据

- 当前仓库缺少正式 `.ai/temp/requirement.md`，本轮验收不按完整产品签收口径执行。
- 本轮测试依据如下：
  - `.ai/temp/cli-spec.md`
  - `.ai/temp/wbs.md`
  - `.ai/temp/architect.md`
- 本轮只覆盖 P6 已交付的 M1 可运行范围：
  - `config show|validate`
  - `employee list|show|test`
  - `work-order create|get|list`
  - `mock provider`
  - 基础 `unittest` 回归

## 2. 测试环境

- 时间：2026-04-01
- 工作目录：`/home/dev/pyagent`
- Python：`3.12.3`
- 当前环境限制：
  - 缺少 `pydantic`
  - 缺少 `fastapi`
  - 缺少 `pytest`
- 运行约定：
  - CLI 通过 `PYTHONPATH=/home/dev/pyagent/src python3 -m digital_employee.api.cli.main` 执行
  - 非法配置场景使用 `/home/dev/pyagent/.qa-invalid-config`
  - 租户隔离场景使用 `/home/dev/pyagent/.qa-state/tenant-20260401-02`

## 3. 测试用例

| ID | 优先级 | 验证点 | 前置条件 | 执行方式 | 预期结果 |
|---|---|---|---|---|---|
| P0-01 | P0 | `config show --json` 输出稳定可解析 | 使用默认配置 | 执行 `config show --json` | 退出码 `0`；`stdout` 为单个 JSON；包含 `system/providers/employees/policies` |
| P0-02 | P0 | `employee test --json` 可完成 dry-run | 默认配置存在 `sales-assistant` | 执行 `employee test sales-assistant --input ... --json` | 退出码 `0`；返回 `employee_id/prompt/summary` |
| P0-03 | P0 | `work-order create/get` 主链路可用 | 默认配置；文件状态目录可写 | 执行 `work-order create --json` 后再 `work-order get --json` | 创建成功；可按返回 ID 读取同一工单 |
| P0-04 | P0 | 输入文件错误时仍遵守 CLI 错误协议 | 指定不存在的输入文件 | 执行 `employee test ... --input-file does-not-exist.txt` | 非零退出；不输出 Python traceback；错误可稳定映射到 `exit code 2/10` 之一；若 `--json` 则返回标准错误包裹 |
| P0-05 | P0 | `config validate` 对非法配置给出失败语义 | 使用 `.qa-invalid-config` | 执行 `config validate --json` | 非法配置时 `ok=false` 或退出码 `3`；结果必须明确表示配置不可用 |
| P0-06 | P0 | 非法配置会阻断后续业务命令 | 使用 `.qa-invalid-config` | 执行 `employee list --json` | 返回配置错误；不得继续列出装配失败的员工 |
| P0-07 | P0 | 工作单查询遵守租户隔离 | 在 `tenant-a` 下创建工单 | 用 `tenant-b` 执行 `work-order list/get --json` | `tenant-b` 不得看到 `tenant-a` 的工单；`get` 应返回不存在或权限错误 |
| P1-01 | P1 | 当前单元与集成回归基线可通过 | 测试目录完整 | 执行 `python3 -m unittest discover -s tests -p 'test_*.py'` | 退出码 `0`；测试全部通过 |

## 4. 本轮不覆盖

- `approval/*`
- `session/*`
- `tool dry-run`
- `replay run`
- `doctor`
- REST 入口联调
- `openai` 真实 provider 联调
- 并发创建、锁和恢复点压力验证
