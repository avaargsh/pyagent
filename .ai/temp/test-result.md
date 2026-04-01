# P8 QA 测试结果

## 1. 执行概览

- 执行日期：2026-04-01
- 执行人：QA 工程师阶段
- 结论：当前交付物不满足发布条件

## 2. 用例结果

| ID | 结果 | 退出码 | 实际结果摘要 |
|---|---|---|---|
| P0-01 | 通过 | `0` | `config show --json` 返回单个 JSON 对象，含 `system/providers/employees/policies`，结构稳定 |
| P0-02 | 通过 | `0` | `employee test sales-assistant --input "Generate a follow-up draft" --json` 返回 dry-run 摘要，`summary` 明确引用 `customer-followup` 和允许工具 |
| P0-03 | 通过 | `0` | 在 `tenant-a` 下创建工单 `wo_20260401061826_4dca20`，随后 `work-order get` 成功返回同一工单详情 |
| P0-04 | 失败 | `1` | `employee test --input-file /home/dev/pyagent/does-not-exist.txt` 直接打印 Python traceback，错误未按 CLI 协议封装 |
| P0-05 | 失败 | `0` | 在非法配置目录执行 `config validate --json` 时，`data.valid=false`，但顶层仍为 `ok=true` 且退出码 `0` |
| P0-06 | 失败 | `0` | 在非法配置目录执行 `employee list --json` 仍返回 `broken-assistant`，未被配置错误阻断 |
| P0-07 | 失败 | `0` | `tenant-b` 执行 `work-order list/get --json` 能看到 `tenant-a` 创建的 `wo_20260401061826_4dca20` |
| P1-01 | 通过 | `0` | `python3 -m unittest discover -s tests -p 'test_*.py'` 输出 `Ran 13 tests`，`OK` |

## 3. 关键执行记录

### 3.1 通过项

`config show --json`

- 结果：返回稳定 JSON 包裹
- 关键字段：`schema_version=1`、`command=config show`、`ok=true`

`employee test sales-assistant --input "Generate a follow-up draft" --json`

- 结果：dry-run 成功
- 关键摘要：
  - `employee_id=sales-assistant`
  - `summary=Mock plan for sales-assistant: handle 'Generate a follow-up draft' using customer-followup; allowed tools: knowledge-search, send-email.`

`work-order create/get --json`

- 创建命令在 `tenant-a` 下返回：
  - `work_order_id=wo_20260401061826_4dca20`
  - `tenant=tenant-a`
  - `status=pending`
- 随后 `work-order get` 可成功读取相同工单

### 3.2 失败项

`employee test sales-assistant --input-file /home/dev/pyagent/does-not-exist.txt`

- 实际：输出完整 Python traceback
- 末尾错误：`FileNotFoundError: [Errno 2] No such file or directory`
- 偏差：不符合 CLI 规范中的稳定错误包裹和 exit code 约定

`config validate --json` in `/home/dev/pyagent/.qa-invalid-config`

- 实际：
  - `ok=true`
  - `data.valid=false`
  - `issues` 包含：
    - `at least one provider must be configured`
    - `employee broken-assistant references unknown provider missing-provider`
- 偏差：非法配置没有映射为失败语义

`employee list --json` in `/home/dev/pyagent/.qa-invalid-config`

- 实际：仍返回
  - `employee_id=broken-assistant`
  - `default_provider=missing-provider`
- 偏差：非法配置未阻断业务命令

`work-order list/get --json` with `tenant-b`

- 前置：`tenant-a` 已创建 `wo_20260401061826_4dca20`
- 实际：
  - `tenant-b work-order list` 返回该工单
  - `tenant-b work-order get wo_20260401061826_4dca20` 同样成功
- 偏差：租户边界失效

## 4. 备注

- 本轮未复现并发写入丢记录问题；该项仍是代码评审阶段已标出的高风险，需要后续专项验证。
- 由于环境缺少 `fastapi` 和 `pytest`，REST 联调与 `pytest` 体系未纳入本轮结果。
