# 发布指南 · 2026-04-01

## 0. 当前发布结论

`No-Go`

当前不得执行正式发布。依据 `.ai/reports/qa-report-20260401.md`，存在以下阻塞项：

1. QA-001：CLI 在输入文件不存在时输出 Python traceback，错误协议失稳
2. QA-002：`config validate` 对非法配置返回成功语义
3. QA-003：非法配置未阻断后续业务命令
4. QA-004：工作单查询缺少租户隔离，存在跨租户数据泄露风险

仅当以上阻塞项修复并完成回归后，才允许进入正式发布步骤。

## 1. 文档范围与发布假设

- 当前项目已从原 Go CLI 模板转为 Python 数字员工控制面 CLI。
- 因此本指南按当前仓库事实编写：
  - 包名：`digital-employee`
  - CLI：`dectl`
  - 构建系统：`setuptools`
  - Python 要求：`>=3.12`
- `.ai/context/release-constraint.md` 仍保留了 Go 模板中的“Go 版本”字段要求。本指南保留该列，但当前项目对应值为 `N/A`。
- 当前仓库缺少正式 `.ai/temp/requirement.md`，因此本指南只覆盖 P6 已实现的 M1 范围，不视为完整产品 GA 发布手册。

## 2. 发布前检查清单

仅在 QA 结论转为 `Go` 后执行：

- [ ] `.ai/reports/qa-report-{version}.md` 结论为 `Go`
- [ ] 所有 P0 缺陷关闭或经书面批准降级
- [ ] `python3 -m unittest discover -s tests -p 'test_*.py'` 通过
- [ ] `dectl --json config show` 输出稳定且可解析
- [ ] `dectl --json config validate` 对坏配置返回失败语义
- [ ] `dectl --json employee test sales-assistant --input "smoke"` 通过
- [ ] 租户隔离回归通过：`tenant-b` 不能读取 `tenant-a` 工单
- [ ] 文件仓储并发写入风险已验证或已替换为正式持久化方案
- [ ] `pyproject.toml` 中版本号与 Git Tag 一致
- [ ] `CHANGELOG` 或发布说明准备完成
- [ ] Release 产物生成后已计算 checksum、checksum 签名、Artifact Attestation
- [ ] 发布包中不包含真实密钥、测试数据或本地状态目录

## 3. 构建矩阵

当前发布约束要求覆盖以下平台：

| OS | ARCH | Python 版本 | Go 版本 | 产物建议 |
|---|---|---|---|---|
| `darwin` | `amd64` | `3.12.x` | `N/A` | `wheel` + `tar.gz` |
| `darwin` | `arm64` | `3.12.x` | `N/A` | `wheel` + `tar.gz` |
| `linux` | `amd64` | `3.12.x` | `N/A` | `wheel` + `tar.gz` |
| `linux` | `arm64` | `3.12.x` | `N/A` | `wheel` + `tar.gz` |

说明：

- 当前仓库没有独立二进制构建链，发布形态应以 `sdist`、`wheel` 和压缩包为主。
- `Scoop` 依赖 Windows 分发链，当前不在已声明构建矩阵内，只保留后续接入方案。

## 4. 打包与校验和策略

### 4.1 产物类型

建议发布以下产物：

- `digital_employee-<version>.tar.gz`
  - Python source distribution
- `digital_employee-<version>-py3-none-any.whl`
  - Python wheel
- `dectl-<version>-<os>-<arch>.tar.gz`
  - 面向人工下载的压缩包，内容包括：
    - `src/`
    - `configs/`
    - `pyproject.toml`
    - `README` / `release-notes`
    - 示例启动脚本

### 4.2 打包步骤

正式发布前在干净环境执行：

```bash
python3 -m pip install --upgrade build
python3 -m build
```

若要生成面向人工分发的压缩包，建议目录结构如下：

```text
dectl-<version>-<os>-<arch>/
├── pyproject.toml
├── src/
├── configs/
└── README.md
```

然后执行：

```bash
tar -czf dectl-<version>-<os>-<arch>.tar.gz dectl-<version>-<os>-<arch>/
```

### 4.3 校验和与可信链

对每个产物生成：

- `sha256sum`
- `sha256sum.sig`
- Artifact Attestation

示例：

```bash
sha256sum dist/* > checksums.txt
sha256sum dectl-<version>-<os>-<arch>.tar.gz >> checksums.txt
```

发布页必须同时附带：

- 产物文件
- `checksums.txt`
- `checksums.txt.sig`
- Attestation 链接或文件

## 5. GitHub Releases / Homebrew / Scoop / 压缩包分发方案

### 5.1 GitHub Releases

当前主发布渠道：

1. 创建 tag：`v<version>`
2. 上传 `sdist`、`wheel`、压缩包、checksum 与签名
3. 发布说明需明确：
  - 当前支持的命令范围
  - 已知限制
  - 配置与凭证要求
  - 回滚方式

### 5.2 压缩包分发

当前推荐的人工分发方式：

- 面向内部环境下载 `dectl-<version>-<os>-<arch>.tar.gz`
- 解压后使用：

```bash
python3 -m pip install .
```

或：

```bash
PYTHONPATH=./src python3 -m digital_employee.api.cli.main version
```

### 5.3 Homebrew

当前状态：`待后续补充`

建议接入条件：

- QA 结论连续两个版本为 `Go`
- 产物结构稳定
- 能提供固定 URL、checksum 与版本化压缩包

建议公式策略：

- 使用 GitHub Release 上的版本化压缩包
- 安装时创建 `dectl` wrapper
- 公式中显式声明 Python 3.12 依赖

### 5.4 Scoop

当前状态：`待后续补充`

当前阻塞：

- 现有构建矩阵未覆盖 Windows
- 尚无 Windows 安装与验证记录

建议后续策略：

- Windows 构建与 smoke 测试补齐后，再维护 `scoop` manifest
- manifest 中固定版本、下载地址和 SHA256

## 6. 配置与凭证说明

发布说明中必须明确以下配置原则：

- 配置优先级：`flag > env > active profile config > tenant config > default`
- 机器可消费配置必须来自结构化文件和环境变量，不得依赖解析 `AGENTS.md`
- 不在仓库、压缩包或发布说明中写入真实密钥

建议说明的关键环境变量：

- `DE_BASE_URL`
- `DE_API_TOKEN`
- `DE_TENANT`
- `DE_PROFILE`
- `DE_TIMEOUT`
- `DE_OUTPUT`
- `DE_NO_INPUT`
- `OPENAI_API_KEY`

当前实现仍使用文件状态目录时，需额外说明：

- 默认状态目录：项目根下 `.de-state/`
- 若使用 `DE_STATE_DIR` 覆盖，必须保证目录权限、备份和租户隔离策略

## 7. 回滚与旧版本兼容策略

回滚原则：

- 始终保留最近一个稳定 tag 与对应产物
- 发布失败时先停止继续分发，再回滚到上一稳定版本
- 配置变更必须在发布说明中写明兼容性影响

推荐回滚步骤：

1. 从 GitHub Releases 撤下有缺陷的最新版本说明入口
2. 将部署环境中的 Python 包回退到上一稳定版本
3. 恢复上一版本配置模板
4. 若使用文件状态目录，先备份 `.de-state/` 或 `DE_STATE_DIR` 指向的数据
5. 执行最小 smoke：
   - `dectl version`
   - `dectl --json config show`
   - `dectl --json employee list`

兼容性提示：

- 当前版本仍处于 M1 骨架期，不承诺状态文件格式长期兼容
- 若后续切换到 PostgreSQL/Redis 正式存储，实现方需提供状态迁移说明

## 8. 发布后验证步骤

仅在完成正式发布后执行：

1. 校验 GitHub Release 附件是否完整：
   - wheel
   - sdist
   - 压缩包
   - checksum
   - checksum 签名
2. 在干净环境安装：

```bash
python3 -m pip install digital_employee-<version>-py3-none-any.whl
```

3. 执行 CLI smoke：

```bash
dectl --json config show
dectl --json employee test sales-assistant --input "release smoke"
```

4. 若启用租户能力，再执行隔离验证：

```bash
dectl --json --tenant tenant-a work-order create --employee sales-assistant --input "tenant a smoke"
dectl --json --tenant tenant-b work-order list
```

判定标准：

- 所有命令退出码符合 CLI 规范
- `stdout` 可稳定解析
- `stderr` 不出现 traceback
- `tenant-b` 不得看到 `tenant-a` 资源

## 9. 当前发布建议

本次版本不应发布。

先完成以下工作，再重新进入 P8/P9：

1. 修复 QA-001 到 QA-004
2. 对修复项补齐自动化测试
3. 重新生成 QA 报告，确认结论从 `No-Go` 变为 `Go`
4. 再执行本指南中的构建、签名和发布步骤
