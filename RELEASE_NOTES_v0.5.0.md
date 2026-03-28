# Release Notes v0.5.0

发布日期：2026-03-28

## 亮点

- 新增专业归类体系：自动分类 + 人工覆盖 + N/A 只读保护。
- 新增管理员专业归类面板，支持按来源分组查看、逐行编辑、保存与删除覆盖。
- 公共分析链路全面支持专业一级/二级分类筛选。
- 筛选区交互统一升级：核心筛选与详情筛选改为胶囊/分组式交互，旧风格选择框完成统一。
- 筛选版式做了颗粒度对齐：长宽、行距、头部与帮助文案高度统一，桌面与移动端都更稳定。

## 后端变更

- 新增专业归类管理接口：
  - GET /api/v1/admin/major-classifications
  - PUT /api/v1/admin/major-classifications
  - DELETE /api/v1/admin/major-classifications
- 全部分析与导出链路支持新筛选参数：
  - major_categories_l1
  - major_categories_l2
- options 接口新增专业分类元数据：
  - major_categories_l1
  - major_categories_l2
  - major_category_mapping
- 新增 major_classifier 服务：
  - 自动规则归类
  - manual/auto/unknown/not_applicable 来源标记
  - N/A 类值归类只读保护
- 存储层新增专业分类规则与覆盖项读写能力。

## 前端变更

- 管理页新增专业归类管理面板：
  - 支持按 unknown/manual/auto/not_applicable 分区展示
  - 支持 L1/L2 联动编辑与单行保存
  - N/A 行禁止编辑与删除
- 筛选栏升级：
  - 专业一级/二级、专业、雇主、城市、州统一为胶囊式多选
  - 月份筛选升级为胶囊式多选并保留最近 3/6/12 月快捷操作
  - 滚轮链路优化，避免内部滚动带动整页
- 空态与引导文案优化：公开页不再提示普通用户执行无权限刷新操作。
- 页面标题微调：
  - 中文副标题由“签证进度数据看板（新手友好版）”更新为“签证进度数据看板”。

## 交互与视觉微调

- 统一筛选控件颗粒度：
  - 同列卡片最小高度
  - 头部区域最小高度
  - 主内容区最小高度
  - 帮助文案区域最小高度
- 统一下拉框视觉风格（语言切换、分页、管理页分类选择）。

## 质量验证

- 后端测试：35 passed。
- 前端测试：通过（18 passed）。
- 前端构建：通过。

## 版本信息

- 前端 package.json 版本更新至 0.5.0。
- 后端默认 CHECKEE_APP_VERSION 更新至 0.5.0。

## 升级提示

- 生产环境部署前，请同步更新后端环境变量中的 CHECKEE_APP_VERSION=0.5.0。
- 建议部署后先执行一次管理员登录与专业归类面板冒烟检查，再对外开放页面访问。
