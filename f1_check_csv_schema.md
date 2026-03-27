# f1_check_cleaned.csv 字段定义

- raw: 原始记录文本（单条，去掉结尾 detail）。
- nickname: 昵称（从 Update 后到 F1 类型前）。
- visa_type: 签证类型（F1Renewal 或 F1New）。
- location: 领馆/地区（BeiJing, GuangZhou, ShangHai, ShenYang, WuHan, HongKong, Others, Europe, Vancouver）。
- major: 专业字段（原始文本截取，未做语义纠错）。
- status: 状态（Clear, Reject, Pending）。
- submit_date: 提交日期（YYYY-MM-DD）。
- complete_date: 结案日期（YYYY-MM-DD；Pending 通常为 0000-00-00）。
- reported_days: 原始文本中的处理天数（字符串）。
- calc_days: 按 submit_date 与 complete_date 计算得到的处理天数（仅结案样本）。
- observed_days: 截至观察日 2026-03-27 的已观察天数（仅 Pending 样本）。
- parse_ok: 解析是否成功（1/0）。
- parse_issue: 解析问题标签（如 unknown_location、missing_status 等；为空表示无问题）。
- key: 去重键（nickname|visa_type|submit_date）。

# f1_check_monthly_stats.csv 字段定义

- submit_month: 提交月份（YYYY-MM）。
- total_cases: 该月总样本数（去重后）。
- clear_cases: Clear 数量。
- reject_cases: Reject 数量。
- pending_cases: Pending 数量。
- pending_ratio: Pending 占比。
- finalized_count: 结案样本数（Clear+Reject 且日期可计算）。
- finalized_mean_days: 结案样本平均处理天数。
- finalized_median_days: 结案样本中位处理天数。
- finalized_p90_days: 结案样本 P90 处理天数。
- finalized_max_days: 结案样本最大处理天数。
- long_tail_90plus_count: 结案样本中处理时长 >=90 天数量。
- long_tail_90plus_ratio: 结案样本中 >=90 天占比。
