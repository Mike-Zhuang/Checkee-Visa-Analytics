# Release Notes v0.5.5

发布日期：2026-03-30

## 重点修复

- 强化 Checkee 详情抓取策略，默认优先保障 `note` 可见性：
  - 新增 `CHECKEE_DETAIL_FETCH_REQUIRE_NOTE=true`（默认开启）。
  - 开启时，只要案例存在 `detail_url`，就会尝试抓取详情页，不再受采样比例限制。
- 采样默认值调整：`CHECKEE_DETAIL_FETCH_SAMPLE_RATIO` 默认从 `0.2` 提升到 `1.0`。
- 优化 403 处理策略：
  - 不再因为单条 403 就中断后续全部详情抓取，避免“整批 note 几乎为空”。
  - 新增 `detail_forbidden_count` 指标，并调整 `detail_blocked` 判定逻辑。

## 测试

- 后端测试通过：
  - `../.venv/bin/python -m pytest tests/test_phase1_discovery.py tests/test_major_classifier.py -q`
- 新增测试覆盖：
  - `DETAIL_FETCH_REQUIRE_NOTE=true` 且采样比为 `0` 时，仍会抓取全部详情。
  - `DETAIL_FETCH_REQUIRE_NOTE=false` 时，恢复按采样策略执行。
