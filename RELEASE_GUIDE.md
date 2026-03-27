# 首次发布指南（v0.1.0）

本指南用于 Checkee Visa Analytics 的第一次开源发布，目标是完成：

- 本地版本冻结
- Git 标签发布
- GitHub Release 页面发布

## 1. 版本与命名约定

建议首发版本号：v0.1.0

命名约定：

- Tag: v0.1.0
- Release Title: v0.1.0 - First Public Release

## 2. 发布前检查清单

请在项目根目录执行以下检查。

### 2.1 工作区状态

```bash
git status --short
```

要求：确认本次希望发布的变更都在列表中，且没有误删误加。

### 2.2 后端可运行

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

浏览器访问：

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/docs

### 2.3 前端可运行

```bash
cd frontend
pnpm install
pnpm run dev
```

如需使用 npm：

```bash
cd frontend
npm ci
npm run dev
```

浏览器访问：

- http://127.0.0.1:5173

### 2.4 关键 API 烟测

```bash
curl -sS http://127.0.0.1:8000/api/v1/health
curl -sS http://127.0.0.1:8000/api/v1/meta/options
curl -sS http://127.0.0.1:8000/api/v1/stats/overview
```

要求：HTTP 正常返回 JSON。

### 2.5 自动化测试与覆盖率门禁

后端：

```bash
cd backend
../.venv/bin/python -m pytest
```

前端单测：

```bash
cd frontend
pnpm run test
```

如需使用 npm：

```bash
cd frontend
npm run test
```

前端覆盖率（必须通过阈值）：

```bash
cd frontend
pnpm run test:coverage
```

如需使用 npm：

```bash
cd frontend
npm run test:coverage
```

前端构建：

```bash
cd frontend
pnpm run build
```

如需使用 npm：

```bash
cd frontend
npm run build
```

要求：以上命令全部通过。

### 2.6 GitHub Actions 状态

在发版前确认最新 commit 的 CI 通过：

- backend-tests
- frontend-tests-build
- frontend-npm-compat

## 3. 生成首发提交

在根目录执行：

```bash
git add -A
git commit -m "chore: prepare first open-source release with clean repo and professional docs"
```

## 4. 打标签并推送

```bash
git tag -a v0.1.0 -m "v0.1.0 first public release"
git push origin main
git push origin v0.1.0
```

## 5. 在 GitHub 创建 Release

进入仓库 Releases 页面，点击 Draft a new release：

- Choose a tag: v0.1.0
- Release title: v0.1.0 - First Public Release
- Description: 使用 RELEASE_NOTES_v0.1.0.md 内容
- 勾选 Set as the latest release
- Publish release

## 6. 发布后验证

- 检查 README 首页展示是否正常
- 检查 License 链接是否有效
- 检查 Release 页中的链接是否可点击
- 本地重新 clone 并按 README 快速启动一次

## 7. 回滚策略（如发现严重问题）

如果发布后立刻发现重大问题：

1. 在 GitHub 将该 Release 标记为 pre-release 或删除
2. 修复后打补丁版本：v0.1.1
3. 重新执行本流程
