# Release Notes v0.5.7

发布日期：2026-03-30

## 新增功能

- 首页筛选器新增「仅看有 Note 的案例」开关。
  - 勾选后，只显示 `detail_note` 非空的案例。
  - 该条件会同步作用于案例明细、统计接口和导出接口，保证口径一致。

## 前后端改动

- 后端：
  - `filter_rows` 新增 `has_note` 条件过滤。
  - `/cases`、`/stats/*`、`/export/*` 路由新增 `has_note` 查询参数并接入过滤。
- 前端：
  - `Filters` 新增 `has_note` 布尔字段。
  - 筛选栏新增复选框「仅看有 Note 的案例」。
  - URL 参数组装新增 `has_note=true`。
  - 已选筛选 chip 新增「仅有Note」。
  - 中英文文案同步更新。

## 测试

- 后端：`pytest backend/tests -q`（通过）
- 前端：`pnpm test -- --run src/test/api.test.ts src/test/filter-bar.test.tsx`（通过）
- 前端构建：`pnpm run build`（通过）
