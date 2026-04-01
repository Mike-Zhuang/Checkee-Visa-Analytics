# v0.1.0 - First Public Release

首次公开发布版本，完成了从一次性分析脚本到可维护全栈应用的重构。

## Highlights

- 全签证类型可视化分析平台（FastAPI + React + TypeScript）
- 支持多维筛选：月份、签证类型、领馆、状态、New/Renewal
- 提供实时刷新、统计面板、趋势图、明细表、导出能力
- 完成项目开源化整理：License、.gitignore、专业 README、调试配置

## Added

### Backend

- 新增 API 路由层：健康检查、刷新任务、筛选项、统计、导出
- 新增抓取服务：公开页面数据抓取与基础容错
- 新增分析服务：
  - 概览统计（总量、成熟度、中位数、P90、长尾）
  - 月度统计（Pending 比率、成熟度、分位）
  - 敏感性分析（Conservative / Neutral / Aggressive）
- 新增存储服务：本地 CSV/JSON 缓存

### Frontend

- 新增 React + TypeScript + Vite 前端工程
- 新增核心页面与组件：
  - FilterBar
  - StatCards
  - MonthlyChart
  - SensitivityTable
  - CaseTable
- 新增 API 客户端封装与导出链接能力

### Engineering

- 新增 VS Code 调试与任务配置
- 新增 MIT License
- 新增开源标准 README
- 新增发布指南与首发 Release Notes 模板

## Fixed

- 修复概览统计在空数据场景返回 NaN 导致接口 500 的问题
- 修复 event 字段类型差异（int/string）导致 finalized 统计异常的问题

## Breaking Changes

- 移除了早期一次性脚本与历史产物（图表、临时 CSV、旧报告）
- 仓库结构切换为 backend/frontend 双目录工程

## Known Issues

- 当前版本尚未集成自动化测试流水线
- Debug 模式下若使用 uvicorn --reload 与部分调试器组合，可能出现进程退出码异常；建议调试时关闭 --reload

## Upgrade Notes

首次公开版本，无需升级迁移。建议按照 README 的快速开始章节进行环境初始化。

## Contributors

- Zhuang Chengbo (庄程博)
