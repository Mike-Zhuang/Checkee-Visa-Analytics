# RELEASE NOTES v0.6.0

发布日期：2026-04-01

## 本版本摘要

v0.6.0 完成了三批核心升级，目标是从“看数据”升级为“可执行建议 + 主动提醒 + 用户工作流闭环”，并保证现有看板能力不回退。

## 重点能力

### 1. 用户体系与服务端筛选保存

- 新增普通用户注册/登录/会话管理。
- 新增服务端筛选保存（创建、更新、删除、加载）。
- 用户相关数据首版使用 SQLite 持久化。

### 2. 建议引擎最小闭环

- 新增 `GET /api/v1/stats/recommendation`。
- 输出建议概率区间、档位、方向与依据链。
- 前端新增建议面板，支持依据展开/收起。

### 3. 站内主动提醒最小闭环

- 新增用户订阅接口（基于已保存筛选）：
  - `GET /api/v1/user/subscriptions`
  - `POST /api/v1/user/subscriptions`
  - `PUT /api/v1/user/subscriptions/{subscription_id}`
  - `DELETE /api/v1/user/subscriptions/{subscription_id}`
- 新增站内通知接口：
  - `GET /api/v1/user/notifications`
  - `POST /api/v1/user/notifications/{notification_id}/read`
  - `POST /api/v1/user/notifications/read-all`
- 刷新流程已接入订阅评估：刷新后自动比对指标变化，满足规则时生成站内通知（含去重与冷却）。
- 前端新增通知中心与订阅管理 UI。

## 文档与工程整理

- 所有 release 相关 Markdown 已统一迁移至 `release/` 目录，便于后续版本维护。

## 兼容性说明

- 旧接口语义保持兼容；新增功能以新增端点和新增 UI 为主。
- 管理端刷新、导出、既有统计与筛选路径保持可用。

## 验证结果

- 后端全量测试：通过（71 passed）。
- 前端全量测试：通过（42 passed）。
- 前端构建：通过。

## 已知说明

- 前端构建存在 chunk size 提示（非阻塞告警），可在后续版本通过按需拆包优化。
