# Release Notes v0.5.3

发布日期：2026-03-30

## 亮点

- 管理端刷新记录支持区分触发方式：`手动`、`定时`、`自动兜底`，不再全部显示为 `manual`。
- 学科自动归类规则升级，补齐高频缩写与常见学科映射，显著减少待人工处理量。
- Checkee 详情页 `Note` 解析修复并增强，前端案例表新增“原文 + 时间线”双视图展示。

## 后端变更

- 刷新链路新增 `triggered_by` 贯穿参数：
  - `/tasks/refresh`：管理员会话触发记为 `manual`，API Key 调用记为 `scheduled`。
  - `/admin/refresh/stale-trigger`：兜底刷新记为 `auto_fallback`。
  - 刷新成功/失败/冷却/鉴权拒绝日志统一写入对应触发方式。
- 学科归类增强：
  - 新增“仅一级学科输入”自动归类（如 `STEM` -> `STEM / Unspecified`）。
  - 新增常见精确映射（如 `Architecture`、`Biotech`、`Biochem`、`Astronomy` 及高频缩写）。
  - 扩充 `Natural Science` 关键词覆盖（biochemistry/biotech/astronomy/neuroscience 等）。
- 详情页字段抽取增强：
  - 支持单格 `Label: Value`（含 `Note:<br>...`）结构。
  - 雇主等字段忽略 `N/A` 占位值，避免污染筛选项。

## 前端变更

- 管理端刷新历史：
  - `triggered_by` 显示映射为本地化文案（手动/定时/自动兜底）。
- 案例表 `Note` 列：
  - 保留原始备注摘要。
  - 自动提取日期节点并展示时间线标签，提升可读性和排障效率。

## 测试与验证

- 后端：`pytest` 全量通过（42/42）。
- 前端：`vitest` 全量通过（26/26）。
- 前端构建：`pnpm run build` 通过。

## 版本信息

- 后端默认版本：`0.5.3`。
- 前端版本：`0.5.3`。
