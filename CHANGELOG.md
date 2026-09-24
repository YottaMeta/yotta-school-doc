# 更新日志

## v0.1.2 (2026-09-24)

- 修复技能市场分类：显式声明一级分类 `education`（教育学习）与二级分类 `edu-teaching-aid`（教学辅助），避免被误分到 `IT 运维与安全`。
- 发布链路：分类字段现在进入市场副本契约并在上传 payload 中显式传递；功能与 0.1.1 相同。

## v0.1.1 (2026-09-24)

- 修复：中英 README 页头补挂 `assets/banner.png`，GitHub / 平台首屏可直接看到品牌 banner。
- 测试：新增「README 必须引用 banner」契约测试，测试总数 66 → 67；仍为 Python 3.8+ 零依赖。

## v0.1.0 (2026-09-24)

初始发布：

- 定位：元公 —— 本地、确定性的学校公文可信起草与校验技能（零依赖，Python 3.8+ 标准库）；不联网、不调用模型、不编造事实。
- 输入：文种规则包 JSON（8 个内置文种）+ 结构化事实 JSON（标题 / 单位 / 日期 / 受文对象 / 联系方式 / 正文要点 / 附件）。
- 能力：文书骨架生成（缺失事实统一为 `〔待补〕`）、文稿检查（`field_missing` / `section_missing` / `date_format_invalid` / `date_order_invalid` / `fact_date_mismatch` / `attachment_missing` / `attachment_unknown` / `placeholder_present` / `privacy_risk` / `action_item_incomplete` / `sensitive_term_review` / `overclaim_review`）、规则包 list / show / validate。
- CLI：`draft` / `check` / `types` / `template`；退出码 0 / 1 / 2 / 3 / 4；支持 `--format md|json`、`--out`、`--stdin`、`--gate findings=<n>`。
- 测试：66 项，Python 3.8.20 / 3.11.9 / 3.13.15 全绿；合成样例（完整通知 / 缺口通知 / 缺口会议纪要）端到端通过。
- 文档：SKILL.md + references（types-format / report-format / privacy）+ 中英 README + 四方式安装 + banner。
