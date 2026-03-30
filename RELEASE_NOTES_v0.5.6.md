# Release Notes v0.5.6

发布日期：2026-03-30

## 修复摘要

- 修复刷新记录触发方式判定：当请求同时携带 `X-Admin-Key` 和 Bearer 时，优先标记为 `scheduled`，避免自动任务误显示为“手动”。
- 修复首页专业筛选器：
  - `major_categories_l2` 选项现在会合并 taxonomy 全量二级分类。
  - 每个一级分类的映射中都会补齐 `Unspecified`，与管理员面板行为一致。
- 修复手动刷新 504：
  - 刷新主流程改为“先完成案例刷新并快速返回”，详情 note 改为后台异步补全，避免前台请求超时。
  - 增加 `detail_enrichment` 运行状态写入 `meta`，可用于观察后台补全进度。

## 新增配置

- `CHECKEE_DETAIL_FETCH_SYNC_ON_REFRESH=false`（默认）
  - `false`：刷新请求不阻塞等待 note 抓取（推荐，避免 504）。
  - `true`：保持同步抓取（可能较慢）。

## 测试

- `../.venv/bin/python -m pytest tests/test_refresh_validation.py tests/test_meta.py tests/test_phase1_discovery.py tests/test_major_classifier.py -q`（通过）
