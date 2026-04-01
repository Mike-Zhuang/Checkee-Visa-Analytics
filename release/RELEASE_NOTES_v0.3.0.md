# Release Notes v0.3.0

发布日期：2026-03-28

## 亮点

- 新增多来源刷新能力，支持 `monthly_track` 与 `latest_snapshot` 两种公开数据来源。
- 新增四类深度分析 API：cohorts、distribution、comparison、anomalies。
- 前端新增深度分析模块与来源选择器，支持在页面直接观察分群、分布、对比和异常长尾案例。
- 提供单机 VPS 生产化部署资产（Nginx + systemd + env 模板 + 一键部署脚本）。

## 后端变更

- `POST /api/v1/tasks/refresh` 支持 `sources` 参数。
- `GET /api/v1/meta/options` 返回 `fetch_sources`。
- 新增统计接口：
  - `GET /api/v1/stats/cohorts`
  - `GET /api/v1/stats/distribution`
  - `GET /api/v1/stats/comparison`
  - `GET /api/v1/stats/anomalies`
- 扩展 meta 状态字段：`requested_sources`、`selected_sources`、`supported_sources`。

## 前端变更

- 筛选栏新增“刷新数据来源”多选。
- 新增组件：
  - `CohortTable`
  - `DistributionPanel`
  - `ComparisonPanel`
  - `AnomalyTable`
- 新增中英文文案覆盖深度分析与来源说明。
- 修复刷新后趋势图口径偏移：默认来源保持 `monthly_track`。

## 部署与运维

新增目录 `deploy/`：

- `deploy/nginx/checkee.conf`
- `deploy/systemd/checkee-backend.service`
- `deploy/env/backend.env.example`
- `deploy/scripts/deploy-backend.sh`

新增文档：

- `DEPLOY_VPS.md`

## 质量验证

- 后端测试：`19 passed`
- 前端测试：`6 passed`
- 前端构建：通过

## 版本信息

- 前端 `package.json` 版本更新至 `0.3.0`
- 后端默认 `CHECKEE_APP_VERSION` 更新至 `0.3.0`
