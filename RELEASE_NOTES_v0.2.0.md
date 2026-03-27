# v0.2.0 - Tooling & Package Manager Upgrade

本版本聚焦工程化升级：新增 pnpm 主链路并保留 npm 兼容，补齐 CI 与文档同步，提升本地开发与发布一致性。

## Highlights

- 新增 pnpm 工作区与锁文件（根目录）
- CI 前端主链路切换为 pnpm（含 frozen-lockfile）
- 保留 npm 兼容 smoke 构建检查
- README 与发布指南完成双包管理器说明
- 本地任务与版本约束统一（Node 22 + packageManager + engines）

## Added

- 新增 `.nvmrc`（Node 22）
- 新增 `pnpm-workspace.yaml`
- 新增根目录 `pnpm-lock.yaml`
- 新增 `frontend/.npmrc` 与 `frontend/.pnpmrc`
- 新增 CI job：`frontend-npm-compat`

## Changed

- `.github/workflows/ci.yml`
  - 前端主 job 改用 pnpm：
    - setup-node cache: pnpm
    - `pnpm/action-setup`
    - `pnpm install --frozen-lockfile`
    - `pnpm run test:coverage` + `pnpm run build`
  - 新增 npm 兼容 smoke：`npm ci` + `npm run build`
- `.vscode/tasks.json`
  - 前端开发任务默认改为 `pnpm run dev`
- `frontend/package.json`
  - 增加 `packageManager` 与 `engines`
  - 版本升级到 `0.2.0`
- `backend/app/core/config.py`
  - 默认 `APP_VERSION` 升级到 `0.2.0`
- 文档更新：`README.md`、`RELEASE_GUIDE.md`

## Fixed

- 修复本地缺少前端依赖时 `vite` 启动失败导致“前端无法连接服务器”的问题（根因是 `frontend/node_modules` 缺失，而非后端 API 不可用）
- 完善 `.gitignore`，避免误提交根目录依赖目录与本地环境文件

## Known Issues

- `pnpm install` 可能提示 `Ignored build scripts: esbuild`（安全提示）；当前不阻塞开发与构建。
- 前端生产包仍有单 chunk > 500k 的提示，后续可评估代码分割优化。

## Contributors

- Zhuang Chengbo (庄程博)
