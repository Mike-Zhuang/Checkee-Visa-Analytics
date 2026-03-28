# Checkee Visa Analytics

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-success)
[![Stars](https://img.shields.io/github/stars/Mike-Zhuang/Checkee-Visa-Analytics?style=social)](https://github.com/Mike-Zhuang/Checkee-Visa-Analytics/stargazers)

全签证类型实时抓取与可视化分析平台（FastAPI + React + TypeScript）

</div>

## 目录

- [项目亮点](#项目亮点)
- [近期更新（v0.5.0）](#近期更新v050)
- [功能清单](#功能清单)
- [技术架构](#技术架构)
- [快速开始](#快速开始)
- [环境变量配置](#环境变量配置)
- [本地调试](#本地调试)
- [管理端入口](#管理端入口)
- [测试与质量门禁](#测试与质量门禁)
- [国际化与可访问性](#国际化与可访问性)
- [API 概览](#api-概览)
- [项目结构](#项目结构)
- [数据与合规说明](#数据与合规说明)
- [路线图](#路线图)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

## 项目亮点

Checkee Visa Analytics 是一个面向签证申请数据分析的全栈项目，提供：

- 跨签证类型聚合分析（F1/H1/B1/J1/O1/L1 等）
- 右删失场景下的稳健统计（中位数、P90、敏感性区间）
- 可交互筛选与月度趋势分析（核心筛选 + 详情筛选）
- 专业自动归类与人工覆盖（L1/L2）
- 一键刷新抓取、导出报告与 CSV
- 本地开发友好（VS Code 任务 + 调试配置）

## 近期更新（v0.5.0）

- 新增专业归类系统：`manual` / `auto` / `unknown` / `not_applicable`。
- 新增管理员专业归类面板：支持分组查看、单行覆盖保存、删除覆盖。
- 公共分析链路新增专业一级/二级筛选，支持端到端查询与导出。
- 筛选区交互统一升级为胶囊/分组式选择器，并统一控件颗粒度与间距。
- 公共页面空态文案与权限语义优化：无权限场景不再提示普通用户执行刷新操作。

## 功能清单

- 数据抓取
  - 从公开页面抓取月度案例数据
  - 支持指定起始月份抓取历史数据（from_month）
  - 支持抓取月份安全上限保护与截断标识
  - 内置重试机制与基础容错逻辑
- 数据分析
  - 概览统计：样本量、成熟度、中位数、P90、长尾占比
  - 月度统计：Pending 比率、成熟度、分布指标
  - 敏感性分析：Conservative / Neutral / Aggressive 三口径
- 前端交互
  - 多维筛选（月份、签证类型、领馆、状态、New/Renewal、专业 L1/L2）
  - 详情筛选（专业、雇主、城市、州）统一胶囊式交互
  - 领馆按国家/地区分组筛选（后端统一分组配置）
  - 筛选条件标签可视化、最近 N 月快捷选择
  - 案例明细分页与空态提示
  - 局部容错加载（单接口失败不拖垮整页）
  - 趋势图 + 明细表联动
  - 一键导出 Markdown 报告与 CSV
  - 管理端专业归类运营面板（按来源分组 + 人工覆盖）
- 工程化能力
  - 前后端环境变量配置化（默认值可覆盖）
  - 管理员登录会话与后端刷新权限控制
  - 前端中英双语切换（i18n）与功能开关
  - 关键页面 a11y 语义增强（aria/label/caption/focus-visible）
  - 后端 pytest 基线 + 前端 Vitest/RTL 基线
  - GitHub Actions CI（后端测试 + 前端覆盖率门禁 + 构建）

## 技术架构

- 后端：FastAPI
  - 模块化分层：api / services / core
  - 主要能力：抓取、清洗、统计、导出
- 前端：React + TypeScript + Recharts + Vite
  - 组件化页面组织
  - 轻量可维护的接口封装
- 数据存储：本地 CSV / JSON（用于离线缓存与快速读取）

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- npm 9+（兼容）
- pnpm 9+（推荐）

### 包管理器说明

- 推荐使用 pnpm（CI 主链路也使用 pnpm）。
- 保留 npm 兼容链路，便于已有环境平滑迁移。
- 首次使用建议启用 Corepack：

```bash
corepack enable
corepack prepare pnpm@10.12.4 --activate
```

若本机没有 `corepack` 命令，可使用：

```bash
npm install -g pnpm@10
```

### 1. 安装后端依赖

```bash
.venv/bin/python -m pip install -r backend/requirements.txt
```

### 2. 安装前端依赖

```bash
cd frontend
pnpm install
```

如需使用 npm：

```bash
cd frontend
npm ci
```

### 3. 启动后端

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 4. 启动前端

```bash
cd frontend
pnpm run dev
```

如需使用 npm：

```bash
cd frontend
npm run dev
```

访问地址：

- 前端：http://127.0.0.1:5173
- 后端：http://127.0.0.1:8000
- OpenAPI 文档：http://127.0.0.1:8000/docs

## 环境变量配置

### 后端配置

```bash
cd backend
cp .env.example .env
```

常用变量：

- `CHECKEE_DATA_DIR`：数据目录（CSV/JSON）
- `CHECKEE_MAX_FETCH_MONTHS`：抓取月份上限
- `CHECKEE_API_DEFAULT_REFRESH_MONTHS`：默认刷新月份
- `CHECKEE_API_MAX_CASES_LIMIT`：明细接口最大分页大小
- `CHECKEE_CORS_ALLOW_ORIGINS`：允许的跨域来源

### 前端配置

```bash
cd frontend
cp .env.example .env
```

常用变量：

- `VITE_API_BASE_URL`：后端 API 基地址
- `VITE_DEFAULT_PAGE_SIZE`：明细默认分页大小
- `VITE_DEFAULT_REFRESH_MONTHS`：刷新按钮默认月份
- `VITE_PAGE_SIZE_OPTIONS`：分页候选值（逗号分隔）
- `VITE_ENABLE_LANGUAGE_SWITCH`：是否显示语言切换
- `VITE_ENABLE_SENSITIVITY`：是否显示敏感性分析模块
- `VITE_ENABLE_CONSULATE_GROUPS`：是否显示领馆分组筛选
- `VITE_ENABLE_PUBLIC_REFRESH`：公开页是否允许手动刷新
- `VITE_ENABLE_ADMIN_PAGE`：是否启用管理端页面
- `VITE_ADMIN_ROUTE_PATH`：管理端路由路径（默认 `/admin-ops`）
- `VITE_ADMIN_REQUIRE_ACCESS_CODE`：是否要求前端访问码
- `VITE_ADMIN_ACCESS_CODE`：前端访问码（可选）

## 本地调试

项目已包含 VS Code 调试配置，可直接使用：

- 任务
  - `Dev: Full Stack`：并行启动前后端
  - `Backend: Run API`
  - `Frontend: Run H5`
- 调试
  - `Backend (Uvicorn Debug)`
  - `Frontend (Vite)`
  - `Full Stack Debug`

相关文件：

- `.vscode/tasks.json`
- `.vscode/launch.json`
- `.vscode/settings.json`

## 管理端入口

- 默认管理端地址：`/admin-ops`（可由 `VITE_ADMIN_ROUTE_PATH` 调整）。
- 管理端主要能力：
  - 登录后触发手动刷新
  - 查看刷新历史
  - 维护专业归类人工覆盖（L1/L2）
- 生产环境建议：
  - 开启后端刷新鉴权（`CHECKEE_REFRESH_REQUIRE_ADMIN_KEY=true`）
  - 配置强密码 `CHECKEE_ADMIN_REFRESH_KEY`

## 测试与质量门禁

### 后端测试

```bash
cd backend
../.venv/bin/python -m pytest
```

### 前端测试

```bash
cd frontend
pnpm run test
```

如需使用 npm：

```bash
cd frontend
npm run test
```

### 前端覆盖率（含阈值门禁）

```bash
cd frontend
pnpm run test:coverage
```

如需使用 npm：

```bash
cd frontend
npm run test:coverage
```

当前阈值（Vitest）：

- statements >= 25
- lines >= 25
- functions >= 20
- branches >= 40

### 前端构建检查

```bash
cd frontend
pnpm run build
```

如需使用 npm：

```bash
cd frontend
npm run build
```

### CI

GitHub Actions 工作流位于 `.github/workflows/ci.yml`，在 `push`/`pull_request` 时执行：

- backend: `pytest`
- frontend（pnpm 主门禁）: `pnpm run test:coverage` + `pnpm run build`
- frontend（npm 兼容 smoke）: `npm run build`

## 国际化与可访问性

- i18n：基于 i18next + react-i18next，内置 `zh`/`en` 资源。
- 语言切换：通过页头下拉选择器切换，默认根据本地存储与浏览器语言检测。
- a11y：
  - 表单控件关联 `label` / `htmlFor`
  - 错误与加载状态使用 `role=alert/status` 与 `aria-live`
  - 数据表增加 `caption` 与表头语义
  - 全局 `:focus-visible` 焦点样式

## API 概览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/admin/login` | 管理员登录，获取会话 token |
| GET | `/api/v1/admin/session` | 校验管理员会话状态 |
| POST | `/api/v1/admin/logout` | 注销管理员会话 |
| GET | `/api/v1/admin/major-classifications` | 获取专业归类列表（支持搜索） |
| PUT | `/api/v1/admin/major-classifications` | 批量写入专业人工覆盖 |
| DELETE | `/api/v1/admin/major-classifications` | 删除单个专业人工覆盖 |
| GET | `/api/v1/health` | 健康检查 |
| POST | `/api/v1/tasks/refresh` | 触发抓取刷新（支持 from_month，生产建议鉴权） |
| GET | `/api/v1/meta/options` | 获取筛选项 |
| GET | `/api/v1/meta/consulate-groups` | 获取领馆国家/地区分组 |
| GET | `/api/v1/meta/state` | 获取刷新状态 |
| GET | `/api/v1/cases` | 获取案例明细（支持筛选/分页） |
| GET | `/api/v1/stats/overview` | 获取总体统计 |
| GET | `/api/v1/stats/monthly` | 获取月度统计 |
| GET | `/api/v1/stats/sensitivity` | 获取敏感性分析 |
| GET | `/api/v1/stats/cohorts` | 获取分群统计（按签证类型） |
| GET | `/api/v1/stats/distribution` | 获取结案时长分布桶 |
| GET | `/api/v1/stats/comparison` | 获取最新月 vs 基线月对比 |
| GET | `/api/v1/stats/anomalies` | 获取异常长尾案例 |
| GET | `/api/v1/export/report` | 导出 Markdown 报告 |
| GET | `/api/v1/export/cases.csv` | 导出案例 CSV |

## 项目结构

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml
├── backend/
│   ├── app/
│   │   └── services/
│   │       └── major_classifier.py
│   ├── data/
│   │   ├── api/
│   │   ├── core/
│   ├── tests/
│   └── .env.example
│   └── data/
├── frontend/
│   ├── src/
│   │   ├── api.ts
│   │   ├── App.tsx
│   │   └── AdminPage.tsx
│   │   └── test/
│   │   ├── api.ts
│   │   └── App.tsx
│   ├── .env.example
│   └── package.json
├── deploy/
│   ├── env/
│   ├── nginx/
│   ├── scripts/
│   └── systemd/
├── DEPLOY_VPS.md
├── .vscode/
├── LICENSE
└── README.md
```

## 数据与合规说明

- 数据来源于公开页面，仅用于学习与研究。
- 请遵守目标站点的服务条款与访问策略。
- 不建议将含敏感信息的原始数据直接公开提交到仓库。

## 刷新参数说明

调用 POST /api/v1/tasks/refresh 时可使用：

- all_months: 是否抓取全部可见月份
- months: 最近 N 月抓取窗口（默认 6）
- from_month: 指定起始月份（格式 YYYY-MM），例如 2025-01
- sources: 抓取来源列表（可选值：`monthly_track`、`latest_snapshot`）

说明：

- from_month 优先于 months。
- 后端会应用月份安全上限保护，并在响应中返回 truncated_by_limit 与 month_limit。
- 当 `CHECKEE_REFRESH_REQUIRE_ADMIN_KEY=true` 时，刷新接口需要管理员权限。

## 公网部署（VPS）

项目已提供单机 VPS 部署资产：

- Nginx 反向代理与限流模板：`deploy/nginx/checkee.conf`
- systemd 服务模板：`deploy/systemd/checkee-backend.service`
- 生产环境变量模板：`deploy/env/backend.env.example`
- 一键部署脚本：`deploy/scripts/deploy-backend.sh`
- 部署说明文档：`DEPLOY_VPS.md`

## 路线图

- [ ] 增加定时刷新任务（6h / 12h / 24h）
- [x] 增加测试体系（后端 pytest + 前端 Vitest/RTL）
- [x] 增加部署模板（VPS: Nginx + systemd）
- [x] 增加权限与配置管理（环境变量化）
- [x] 增加专业归类自动化与人工覆盖运营能力
- [x] 统一筛选区交互（胶囊/分组式）与视觉颗粒度
- [ ] 增加更高覆盖率目标与回归集扩展

## 贡献指南

欢迎 Issue 与 PR。

建议流程：

1. Fork 仓库并创建特性分支
2. 提交改动并补充必要说明
3. 发起 PR，描述问题背景与验证方式

## 许可证

本项目采用 MIT 协议，详见 [LICENSE](LICENSE)。

---

维护者：Zhuang Chengbo (庄程博)
