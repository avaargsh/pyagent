# 发布约束

## 发布渠道

- GitHub Releases
- 压缩包分发
- Homebrew / Scoop 待后续补充

## 构建矩阵

- `darwin/amd64`
- `darwin/arm64`
- `linux/amd64`
- `linux/arm64`

## 可信链要求

- 产物 checksum
- checksum 签名
- Artifact Attestation

## 回滚要求

- 保留最近稳定版本
- 发布说明必须包含回滚步骤
- 配置变更必须注明兼容性影响
