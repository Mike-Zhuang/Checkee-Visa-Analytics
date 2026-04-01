# Release Notes v0.5.1

发布日期：2026-03-28

## 亮点

- 页面底部新增开源项目风格 Footer，统一展示版本号、GitHub 仓库、维护者信息与赞助入口。
- 前端版本号与构建注入版本打通，支持与 GitHub Release 标签保持同步。
- 新增可配置项，支持通过环境变量自定义仓库链接、维护者信息与 Buy Me a Coffee 链接。

## 前端变更

- 新增 Footer 区块：
  - 版本号显示（自动补全 `v` 前缀）
  - GitHub 仓库链接
  - 维护者主页链接
  - Buy Me a Coffee 按钮
- 新增配置项：
  - `VITE_APP_VERSION`
  - `VITE_GITHUB_REPO_URL`
  - `VITE_MAINTAINER_NAME`
  - `VITE_MAINTAINER_URL`
  - `VITE_BUY_ME_COFFEE_URL`
- 新增中英文文案：
  - `footer.version`
  - `footer.githubRepo`
  - `footer.maintainedBy`
  - `footer.buyMeCoffee`

## 后端与版本同步

- 后端默认 `CHECKEE_APP_VERSION` 更新为 `0.5.1`。
- 前端 `package.json` 版本更新为 `0.5.1`。

## 质量验证

- 前端构建：通过。

## 升级提示

- 生产环境建议同步更新后端环境变量：`CHECKEE_APP_VERSION=0.5.1`。
- 如需个性化 Footer 信息，可在前端 `.env` 中配置上述 `VITE_*` 变量后重新构建发布。
