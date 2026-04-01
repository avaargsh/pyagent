# 评审报告 · 20260401

## 1. 正确性问题

### 阻塞项 1：CLI 只捕获 `CommandFailure`，遇到 YAML 解析、文件读取或仓储损坏时会直接抛 traceback，破坏既定输出协议

- 位置：
  - `src/digital_employee/api/cli/main.py:59-74`
  - `src/digital_employee/api/cli/common.py:77-92`
  - `src/digital_employee/infra/config/loader.py:22-28`
  - `src/digital_employee/infra/repositories/work_orders.py:36-42`
- 问题：
  - `main()` 只捕获 `CommandFailure`。
  - 但 `resolve_text_input()` 读取不存在的 `--input-file` 会抛 `FileNotFoundError`。
  - `_read_yaml()` 会抛 `ValueError`。
  - `FileWorkOrderRepository._load()` 在 JSON 损坏时会抛 `JSONDecodeError`。
- 影响：
  - CLI 无法稳定返回约定的 JSON 错误包裹和 exit code。
  - 非交互脚本会拿到 traceback，而不是机读错误对象。
- 结论：
  - 这是控制面协议层的阻塞问题，必须在进入 QA 前修复。

### 阻塞项 2：租户边界没有真正落到存储和查询路径，`work-order get/list` 可以跨租户读到同一状态文件

- 位置：
  - `src/digital_employee/application/services/request_context.py:41-49`
  - `src/digital_employee/infra/repositories/work_orders.py:13-16`
  - `src/digital_employee/application/use_cases/work_order_use_cases.py:40-72`
- 问题：
  - `AppContext` 只把 `tenant` 保存在配置对象里，但仓储实例没有按租户分区。
  - `FileWorkOrderRepository` 固定读写单个 `work_orders.json`。
  - `get_work_order()` 和 `list_work_orders()` 也没有按 `tenant` 过滤。
- 影响：
  - 多租户场景下，租户 A 可以读到租户 B 的工作单。
  - 这直接违反已批准架构中的“租户间数据强隔离”目标。
- 结论：
  - 这是正确性和安全性双重阻塞项。

### 阻塞项 3：配置校验只收集问题但不阻断命令执行，`config validate` 发现非法配置时也返回成功流程

- 位置：
  - `src/digital_employee/application/services/request_context.py:41-49`
  - `src/digital_employee/infra/config/validate.py:6-22`
  - `src/digital_employee/application/use_cases/config_use_cases.py:31-38`
  - `src/digital_employee/api/cli/main.py:69-71`
- 问题：
  - `build_app_context()` 会计算 `validation_issues`，但不会阻止其它命令继续运行。
  - `validate_config()` 只把 `valid: false` 放进 `data`，没有抛出错误。
  - `main()` 对这种情况仍返回 `0`。
- 影响：
  - 明显非法的 provider/employee 配置仍可能进入后续执行路径。
  - 自动化系统无法依赖 exit code 判定配置是否可用。
- 结论：
  - 这是和 CLI 规范直接冲突的阻塞问题。

## 2. 分层与依赖问题

### 建议项 1：`application.use_cases` 直接 new `MockProvider` / `TurnEngine` 并调用 `asyncio.run()`，破坏用例层边界

- 位置：
  - `src/digital_employee/application/use_cases/employee_use_cases.py:53-72`
- 问题：
  - `test_employee()` 在应用层内部直接依赖具体 provider 和 runtime 实现。
  - 同时它用 `asyncio.run()` 驱动异步调用。
- 影响：
  - 如果未来 REST 层复用这个 use case，在已有事件循环中会直接抛 `RuntimeError`。
  - 应用层被迫了解具体 provider 选择逻辑，违背 P5a 冻结的包边界。
- 建议：
  - 把 provider 选择和 turn 执行交给 runtime/service 层注入。
  - 应用层只处理 DTO 与 orchestration 调用。

### 建议项 2：`employee test` 无视员工配置的 `default_provider`，当前实现永远走 `MockProvider`

- 位置：
  - `src/digital_employee/application/use_cases/employee_use_cases.py:58-72`
- 问题：
  - 即使员工配置未来切到 `openai`，`employee test` 仍固定实例化 `MockProvider`。
- 影响：
  - 该命令无法真实验证“员工装配 + provider 路由”的结果。
  - 它更像“固定 mock 的 prompt smoke test”，而不是 CLI 规范定义的 dry-run 验证。
- 建议：
  - 通过 `ProviderRouter` 选择 provider，并显式增加 `--provider` 或 `--mock` 覆盖开关。

## 3. 并发 / 取消 / 超时风险

### 阻塞项 4：文件版工作单仓储采用无锁的读改写流程，并发创建时会丢记录

- 位置：
  - `src/digital_employee/infra/repositories/work_orders.py:18-47`
- 问题：
  - `create()` 先 `_load()`，再在内存修改，最后 `_save()`。
  - 整个过程没有文件锁、目录锁或 compare-and-swap。
- 影响：
  - 两个并发 CLI/API 请求可相互覆盖，后写请求会吞掉先写请求的数据。
  - 这与前序文档中的“状态一致性优先”要求冲突。
- 结论：
  - 即使当前是 bootstrap 仓储，也至少需要最小串行化保护，否则无法安全进入 QA。

## 4. 配置与密钥泄露风险

### 建议项 3：未发现直接密钥泄露，但 `profile/tenant` 目前只记录在配置对象里，没有真正参与配置分层与权限边界

- 位置：
  - `src/digital_employee/infra/config/loader.py:38-118`
- 问题：
  - `profile` / `tenant` 当前只被保存到 `LoadedConfig`，没有加载 profile-specific 或 tenant-specific 配置源。
- 影响：
  - 命令行上的 `--profile` / `--tenant` 会给人一种“配置已切换”的错误预期。
  - 这会放大租户隔离和审批策略错配风险。
- 建议：
  - 在未实现分层配置前，显式禁止这些参数，或在输出中标注“仅记录，不生效”。

## 5. 输出协议与 CLI 规范偏差

### 建议项 4：`--jsonl` 被全局接受，但当前没有任何真实命令实现流式 JSONL 协议

- 位置：
  - `src/digital_employee/api/cli/main.py:28-29`
  - `src/digital_employee/api/cli/session_cmd.py:8-19`
- 问题：
  - CLI 入口接受 `--jsonl`，但所有相关命令仍是 `not implemented`。
  - 非流式命令也不会拒绝这个 flag。
- 影响：
  - 调用方会误以为 JSONL 已被支持。
  - 这和已批准 CLI 规范中的“仅流式命令允许 `--jsonl`”不一致。
- 建议：
  - 在流式命令未落地前，对非支持命令显式报错。

## 6. 缺失测试与回归风险

### 建议项 5：测试基本覆盖了 happy path，但没有覆盖当前最危险的失败路径

- 位置：
  - `tests/integration/cli/test_config_commands.py:15-23`
  - `tests/integration/cli/test_work_order_commands.py:18-44`
- 缺失项：
  - 非法 YAML / 缺失配置文件的 exit code 与 JSON 错误包裹
  - `--input-file` 不存在时的错误输出
  - 非法配置下 `config validate` 的非零退出
  - 多租户隔离
  - 并发写入丢数据
  - 损坏 `work_orders.json` 后的恢复或报错行为
- 影响：
  - 当前测试通过不能证明控制面协议稳定，只能证明 happy path 可跑。

## 7. 阻塞项与建议项分离

### 阻塞项

1. CLI 未统一捕获非 `CommandFailure` 异常，错误协议不稳定。
2. 工作单存储与查询没有租户隔离。
3. 配置校验不会阻断后续命令，`config validate` 也不会通过 exit code 失败。
4. 文件版仓储无锁，存在并发覆盖风险。

### 建议项

1. 把 `employee test` 的 provider / runtime 依赖移出应用层，并移除 `asyncio.run()`。
2. 让 `employee test` 通过 `ProviderRouter` 工作，而不是硬编码 `MockProvider`。
3. 在真正支持前，禁用或收窄 `--profile` / `--tenant` / `--jsonl` 的语义承诺。
4. 补齐失败路径、隔离和并发相关测试。

## 结论

- 发现 4 个阻塞项，不建议直接进入 QA。
- 当前实现更适合作为 M1 bootstrap 原型，而不是可验收的控制面基线。
- 建议先回到 P6 修复阻塞项，再重新进入评审。
