# Release Notes v0.5.4

发布日期：2026-03-30

## 修复

- 修复管理员「专业归类管理」面板中二级分类下拉候选缺失 `Unspecified` 时的显示误导问题。
  - 现已确保每行都保留当前有效值，并始终可选择 `Unspecified`。
  - 避免出现自动归类显示为 `STEM / Unspecified`，但编辑框视觉上误显示 `AI & Data` 的情况。

## 测试

- 前端测试：`pnpm test -- --run src/test/admin-page.test.tsx`（通过）
- 后端测试：`../.venv/bin/python -m pytest tests/test_major_classifier.py -q`（通过）
