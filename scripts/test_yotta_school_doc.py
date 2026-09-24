#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""元公 yotta-school-doc 内核契约测试（TDD：先红后绿）。"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import yotta_school_doc as yd  # noqa: E402

NOW = "2026-09-24T00:00:00Z"


def facts_notice_complete():
    return {
        "schema_version": yd.SCHEMA_VERSION,
        "doc_type": "notice",
        "visibility": "public",
        "title": "关于开展秋季运动会的通知",
        "issuer": "示例中学",
        "published_date": "2026-09-24",
        "audience": "各年级组、各班级",
        "action_deadline": "2026-09-30",
        "contact": "教务处（010-00000000）",
        "body_points": ["运动会时间与地点", "报名办法", "安全工作要求"],
        "attachments": ["报名表.xlsx"],
        "approval": {"reviewer": "校务会", "approved_date": "2026-09-23"},
    }


OK_NOTICE = (
    "# 关于开展秋季运动会的通知\n"
    "\n"
    "各年级组、各班级：\n"
    "\n"
    "为做好秋季运动会组织工作，现将有关事项通知如下。\n"
    "\n"
    "一、时间与地点\n"
    "2026年10月15日 在学校操场举行。\n"
    "\n"
    "二、报名办法\n"
    "请各班于 2026-09-30 前将报名表交教务处。\n"
    "\n"
    "三、联系方式\n"
    "联系人：教务处（010-00000000）。\n"
    "\n"
    "附件：报名表.xlsx\n"
    "\n"
    "示例中学\n"
    "2026-09-24\n"
)

GAP_NOTICE = (
    "# 秋季运动会\n"
    "\n"
    "各班级：\n"
    "\n"
    "请尽快报名。\n"
)


class TypesTest(unittest.TestCase):
    def test_default_types_have_eight_kinds(self):
        types = yd.load_types(None)
        self.assertGreaterEqual(len(types["types"]), 8)
        self.assertIn("notice", types["by_id"])
        self.assertIn("minutes", types["by_id"])

    def test_type_has_required_fields_and_sections(self):
        types = yd.load_types(None)
        notice = yd.get_type(types, "notice")
        self.assertIn("contact", notice["required_fields"])
        self.assertTrue(notice["required_sections"])

    def test_schema_version_mismatch_rejected(self):
        payload = {"schema_version": "9.9", "types": [dict(yd.DEFAULT_TYPES["types"][0])]}
        with self.assertRaises(yd.ConfigError):
            yd.load_types(payload, "types")

    def test_duplicate_type_rejected(self):
        first = dict(yd.DEFAULT_TYPES["types"][0])
        payload = {"schema_version": yd.SCHEMA_VERSION, "types": [first, dict(first)]}
        with self.assertRaises(yd.ConfigError):
            yd.load_types(payload, "types")

    def test_unknown_required_field_rejected(self):
        item = dict(yd.DEFAULT_TYPES["types"][0])
        item["required_fields"] = ["title", "no_such_field"]
        payload = {"schema_version": yd.SCHEMA_VERSION, "types": [item]}
        with self.assertRaises(yd.ConfigError):
            yd.load_types(payload, "types")

    def test_duplicate_section_rejected(self):
        item = dict(yd.DEFAULT_TYPES["types"][0])
        item["required_sections"] = [
            {"id": "body", "name": "正文", "min_lines": 2},
            {"id": "body", "name": "正文副本", "min_lines": 2},
        ]
        payload = {"schema_version": yd.SCHEMA_VERSION, "types": [item]}
        with self.assertRaises(yd.ConfigError):
            yd.load_types(payload, "types")

    def test_bad_min_lines_rejected(self):
        item = dict(yd.DEFAULT_TYPES["types"][0])
        item["required_sections"] = [{"id": "body", "name": "正文", "min_lines": 0}]
        payload = {"schema_version": yd.SCHEMA_VERSION, "types": [item]}
        with self.assertRaises(yd.ConfigError):
            yd.load_types(payload, "types")

    def test_missing_types_file_is_config_error(self):
        with self.assertRaises(yd.ConfigError):
            yd.load_types("no-such-types.json", "types")

    def test_unknown_type_is_config_error(self):
        types = yd.load_types(None)
        with self.assertRaises(yd.ConfigError):
            yd.get_type(types, "no_such_type")


class FactsTest(unittest.TestCase):
    def test_load_valid_facts(self):
        facts = yd.load_facts(facts_notice_complete())
        self.assertEqual(facts["doc_type"], "notice")
        self.assertEqual(facts["title"], "关于开展秋季运动会的通知")

    def test_facts_schema_mismatch_rejected(self):
        payload = facts_notice_complete()
        payload["schema_version"] = "9.9"
        with self.assertRaises(yd.ConfigError):
            yd.load_facts(payload)

    def test_facts_requires_doc_type(self):
        payload = facts_notice_complete()
        del payload["doc_type"]
        with self.assertRaises(yd.ConfigError):
            yd.load_facts(payload)

    def test_list_fields_must_be_string_arrays(self):
        payload = facts_notice_complete()
        payload["body_points"] = ["ok", 3]
        with self.assertRaises(yd.ConfigError):
            yd.load_facts(payload)

    def test_unknown_visibility_rejected(self):
        payload = facts_notice_complete()
        payload["visibility"] = "secret"
        with self.assertRaises(yd.ConfigError):
            yd.load_facts(payload)

    def test_date_helpers_parse_iso_and_chinese(self):
        self.assertEqual(yd.normalize_date("2026-09-24"), "2026-09-24")
        self.assertEqual(yd.normalize_date("2026年9月24日"), "2026-09-24")
        self.assertIsNone(yd.normalize_date("2026/09/24"))


class DraftTest(unittest.TestCase):
    def setUp(self):
        self.types = yd.load_types(None)
        self.facts = yd.load_facts(facts_notice_complete())

    def test_complete_skeleton_has_no_findings(self):
        skeleton = yd.build_skeleton(self.facts, self.types, now=NOW)
        self.assertEqual(skeleton["findings"], [])

    def test_missing_field_becomes_placeholder_and_finding(self):
        facts = facts_notice_complete()
        del facts["contact"]
        skeleton = yd.build_skeleton(yd.load_facts(facts), self.types, now=NOW)
        self.assertTrue(any(f["kind"] == "field_missing" and f["field"] == "contact"
                            for f in skeleton["findings"]))
        self.assertIn(yd.PLACEHOLDER, yd.render_skeleton_markdown(skeleton))

    def test_body_points_keep_order(self):
        skeleton = yd.build_skeleton(self.facts, self.types, now=NOW)
        self.assertEqual(skeleton["body_points"],
                         ["运动会时间与地点", "报名办法", "安全工作要求"])

    def test_attachments_are_listed(self):
        skeleton = yd.build_skeleton(self.facts, self.types, now=NOW)
        markdown = yd.render_skeleton_markdown(skeleton)
        self.assertIn("报名表.xlsx", markdown)

    def test_skeleton_is_deterministic_except_timestamp(self):
        first = yd.build_skeleton(self.facts, self.types, now=NOW)
        second = yd.build_skeleton(self.facts, self.types, now=NOW)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_json_contract_keys(self):
        skeleton = yd.build_skeleton(self.facts, self.types, now=NOW)
        for key in ("schema_version", "tool", "tool_version", "generated_at", "document",
                    "facts", "fields", "body_points", "attachments", "findings", "sources",
                    "disclaimer"):
            self.assertIn(key, skeleton)

    def test_markdown_has_expected_sections(self):
        markdown = yd.render_skeleton_markdown(yd.build_skeleton(self.facts, self.types, now=NOW))
        for marker in ("学校公文骨架", "受文对象", "正文要点", "办理要求", "附件", "来源与免责"):
            self.assertIn(marker, markdown)

    def test_missing_published_date_flagged(self):
        facts = facts_notice_complete()
        del facts["published_date"]
        skeleton = yd.build_skeleton(yd.load_facts(facts), self.types, now=NOW)
        self.assertTrue(any(f["field"] == "published_date" for f in skeleton["findings"]))


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.types = yd.load_types(None)
        self.facts = yd.load_facts(facts_notice_complete())
        self.notice = yd.get_type(self.types, "notice")

    def test_complete_notice_has_no_findings(self):
        result = yd.check_document(OK_NOTICE, self.notice, facts=self.facts, now=NOW)
        self.assertEqual(result["findings"], [])

    def test_missing_contact_detected(self):
        text = OK_NOTICE.replace("联系人：教务处（010-00000000）。\n", "")
        result = yd.check_document(text, self.notice, facts=self.facts, now=NOW)
        self.assertTrue(any(f["kind"] == "field_missing" and f["field"] == "contact"
                            for f in result["findings"]))

    def test_missing_deadline_detected(self):
        text = OK_NOTICE.replace("请各班于 2026-09-30 前将报名表交教务处。", "请各班报名。")
        result = yd.check_document(text, self.notice, facts=self.facts, now=NOW)
        self.assertTrue(any(f["kind"] == "field_missing"
                            and f["field"] == "action_deadline" for f in result["findings"]))

    def test_missing_audience_detected(self):
        text = OK_NOTICE.replace("各年级组、各班级：\n", "")
        result = yd.check_document(text, self.notice, facts=self.facts, now=NOW)
        self.assertTrue(any(f["field"] == "audience" for f in result["findings"]))

    def test_placeholder_detected(self):
        text = OK_NOTICE.replace("示例中学\n2026-09-24\n", "〔待补〕\n2026-09-24\n")
        result = yd.check_document(text, self.notice, facts=self.facts, now=NOW)
        self.assertTrue(any(f["kind"] == "placeholder_present" for f in result["findings"]))

    def test_privacy_id_card_detected(self):
        text = OK_NOTICE + "\n学生身份证号：110101200001010011\n"
        result = yd.check_document(text, self.notice, facts=self.facts, now=NOW)
        self.assertTrue(any(f["kind"] == "privacy_risk" for f in result["findings"]))

    def test_privacy_mobile_detected(self):
        text = OK_NOTICE + "\n家长手机号：13800138000\n"
        result = yd.check_document(text, self.notice, facts=self.facts, now=NOW)
        self.assertTrue(any(f["kind"] == "privacy_risk" for f in result["findings"]))

    def test_privacy_address_detected(self):
        text = OK_NOTICE + "\n家庭住址：示例路 1 号\n"
        result = yd.check_document(text, self.notice, facts=self.facts, now=NOW)
        self.assertTrue(any(f["kind"] == "privacy_risk" for f in result["findings"]))

    def test_overclaim_detected(self):
        text = OK_NOTICE + "\n请确保全部工作彻底完成。\n"
        result = yd.check_document(text, self.notice, facts=self.facts, now=NOW)
        self.assertTrue(any(f["kind"] == "overclaim_review" for f in result["findings"]))

    def test_sensitive_term_detected(self):
        text = OK_NOTICE + "\n对违纪学生给予开除处分。\n"
        result = yd.check_document(text, self.notice, facts=self.facts, now=NOW)
        self.assertTrue(any(f["kind"] == "sensitive_term_review" for f in result["findings"]))

    def test_date_order_invalid_detected(self):
        facts = facts_notice_complete()
        facts["published_date"] = "2026-10-01"
        facts["action_deadline"] = "2026-09-30"
        result = yd.check_document(OK_NOTICE, self.notice, facts=yd.load_facts(facts), now=NOW)
        self.assertTrue(any(f["kind"] == "date_order_invalid" for f in result["findings"]))

    def test_fact_date_mismatch_detected(self):
        facts = facts_notice_complete()
        facts["published_date"] = "2026-09-25"
        result = yd.check_document(OK_NOTICE, self.notice, facts=yd.load_facts(facts), now=NOW)
        self.assertTrue(any(f["kind"] == "fact_date_mismatch"
                            and f["field"] == "published_date" for f in result["findings"]))

    def test_date_format_invalid_detected(self):
        text = OK_NOTICE.replace("2026-09-24", "2026/9/24")
        result = yd.check_document(text, self.notice, facts=self.facts, now=NOW)
        self.assertTrue(any(f["kind"] == "date_format_invalid" for f in result["findings"]))

    def test_attachment_missing_detected(self):
        text = OK_NOTICE.replace("附件：报名表.xlsx\n", "")
        result = yd.check_document(text, self.notice, facts=self.facts, now=NOW)
        self.assertTrue(any(f["kind"] == "attachment_missing" for f in result["findings"]))

    def test_attachment_unknown_detected(self):
        facts = facts_notice_complete()
        facts["attachments"] = []
        result = yd.check_document(OK_NOTICE, self.notice, facts=yd.load_facts(facts), now=NOW)
        self.assertTrue(any(f["kind"] == "attachment_unknown" for f in result["findings"]))

    def test_minutes_action_item_incomplete_detected(self):
        minutes = yd.get_type(self.types, "minutes")
        text = (
            "# 教学工作会议纪要\n\n"
            "参会人员：语文组、数学组。\n\n"
            "一、议定事项\n"
            "决定推进作业分层设计。\n\n"
            "二、待办\n"
            "整理分层作业材料。\n\n"
            "示例中学\n"
            "2026-09-24\n"
        )
        result = yd.check_document(text, minutes, now=NOW)
        self.assertTrue(any(f["kind"] == "action_item_incomplete" for f in result["findings"]))

    def test_findings_are_sorted_and_have_evidence(self):
        result = yd.check_document(GAP_NOTICE, self.notice, facts=self.facts, now=NOW)
        keys = [(f["kind"], f.get("field") or "", f["detail"]) for f in result["findings"]]
        self.assertEqual(keys, sorted(keys))
        self.assertTrue(all("evidence" in f for f in result["findings"]))

    def test_markdown_lists_findings(self):
        result = yd.check_document(GAP_NOTICE, self.notice, facts=self.facts, now=NOW)
        markdown = yd.render_check_markdown(result)
        self.assertIn("缺口清单", markdown)
        self.assertIn("field_missing", markdown)

    def test_check_without_facts_still_runs(self):
        result = yd.check_document(OK_NOTICE, self.notice, facts=None, now=NOW)
        self.assertIn("summary", result)


class SecurityTest(unittest.TestCase):
    def test_engine_has_no_network_imports(self):
        source = (SCRIPTS_DIR / "yotta_school_doc.py").read_text(encoding="utf-8")
        for marker in ("import urllib", "import socket", "import requests", "http.client"):
            self.assertNotIn(marker, source)

    def test_engine_has_no_author_machine_paths(self):
        source = (SCRIPTS_DIR / "yotta_school_doc.py").read_text(encoding="utf-8")
        self.assertNotIn("D:\\AI_WorkDir", source)
        self.assertNotIn("C:\\Users", source)

    def test_output_directory_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(yd.InputError):
                yd.resolve_output_path(td)

    def test_output_escape_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(yd.InputError):
                yd.resolve_output_path(os.path.join(td, "..", "x.md"))


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.facts = self.dir / "facts.json"
        self.facts.write_text(
            json.dumps(facts_notice_complete(), ensure_ascii=False), encoding="utf-8")
        self.doc = self.dir / "notice.md"
        self.doc.write_text(OK_NOTICE, encoding="utf-8")
        self.gap = self.dir / "gap.md"
        self.gap.write_text(GAP_NOTICE, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_cli_version(self):
        self.assertEqual(yd.main(["--version"]), 0)

    def test_cli_draft_to_file(self):
        out = self.dir / "draft.md"
        code = yd.main(["draft", "--type", "notice", "--facts", str(self.facts),
                        "--out", str(out)])
        self.assertEqual(code, 0)
        self.assertIn("学校公文骨架", out.read_text(encoding="utf-8"))

    def test_cli_draft_json(self):
        out = self.dir / "draft.json"
        yd.main(["draft", "--type", "notice", "--facts", str(self.facts),
                 "--format", "json", "--out", str(out)])
        payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(payload["tool"], "yotta-school-doc")

    def test_cli_check_clean_and_gate(self):
        self.assertEqual(yd.main(["check", "--doc", str(self.doc), "--type", "notice",
                                  "--facts", str(self.facts), "--gate", "findings=1"]), 0)

    def test_cli_check_gap_triggers_gate(self):
        code = yd.main(["check", "--doc", str(self.gap), "--type", "notice",
                        "--facts", str(self.facts), "--gate", "findings=1"])
        self.assertEqual(code, 1)

    def test_cli_check_stdin(self):
        out = self.dir / "stdin.json"
        code = yd.main(["check", "--stdin", "--type", "notice",
                        "--format", "json", "--out", str(out)],
                       stdin_text=OK_NOTICE)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["summary"]["findings"], 0)

    def test_cli_types_list_show_validate(self):
        self.assertEqual(yd.main(["types", "list"]), 0)
        self.assertEqual(yd.main(["types", "show", "--type", "notice"]), 0)
        self.assertEqual(yd.main(["types", "validate"]), 0)

    def test_cli_unknown_type_exit_three(self):
        self.assertEqual(yd.main(["draft", "--type", "no_such_type",
                                  "--facts", str(self.facts)]), 3)

    def test_cli_missing_doc_exit_two(self):
        self.assertEqual(yd.main(["check", "--doc", str(self.dir / "nope.md"),
                                  "--type", "notice"]), 2)

    def test_cli_unknown_command_exit_two(self):
        self.assertEqual(yd.main(["nope"]), 2)

    def test_cli_template_writes_files(self):
        out_dir = self.dir / "tpl"
        self.assertEqual(yd.main(["template", "--output-dir", str(out_dir)]), 0)
        names = sorted(p.name for p in out_dir.iterdir())
        self.assertEqual(names, ["document.md", "facts.json", "types.json"])
        yd.load_types(json.loads((out_dir / "types.json").read_text(encoding="utf-8")), "tpl")
        yd.load_facts(json.loads((out_dir / "facts.json").read_text(encoding="utf-8")))


class DocContractTest(unittest.TestCase):
    root = SCRIPTS_DIR.parent

    def _read(self, *parts):
        return self.root.joinpath(*parts).read_text(encoding="utf-8")

    def test_skill_frontmatter_matches_engine(self):
        front = self._read("SKILL.md").split("---", 2)[1]
        self.assertIn("name: yotta-school-doc", front)
        self.assertIn("version: %s" % yd.VERSION, front)
        self.assertIn("license: MIT", front)
        self.assertIn("触发", front)
        self.assertIn("边界", front)

    def test_references_are_complete(self):
        for name in ("types-format.md", "report-format.md", "privacy.md"):
            text = self._read("references", name)
            self.assertGreater(len(text), 700, name)

    def test_readme_four_ways(self):
        readme = self._read("README.md")
        self.assertIn("npx -y @yottameta/yotta-school-doc", readme)
        self.assertIn("git clone https://github.com/YottaMeta/yotta-school-doc", readme)
        self.assertIn("Download ZIP", readme)
        self.assertIn("install.sh --agent", readme)
        self.assertNotIn("npx skills", readme)

    def test_chinese_readme_four_ways(self):
        readme = self._read("README.zh-CN.md")
        self.assertIn("方式一", readme)
        self.assertIn("方式四", readme)
        self.assertIn("install.sh --agent", readme)

    def test_disclaimer_documented(self):
        for name in ("SKILL.md", "README.zh-CN.md", "references/privacy.md"):
            self.assertIn("最终签发", self._read(*name.split("/")), name)

    def test_report_format_doc_covers_json_keys(self):
        facts = yd.load_facts(facts_notice_complete())
        result = yd.check_document(OK_NOTICE, yd.get_type(yd.load_types(None), "notice"),
                                   facts=facts, now=NOW)
        doc = self._read("references", "report-format.md")
        for key in result:
            self.assertIn("`%s`" % key, doc, key)

    def test_finding_kinds_documented(self):
        doc = self._read("references", "report-format.md")
        for kind in ("field_missing", "section_missing", "date_format_invalid",
                     "date_order_invalid", "fact_date_mismatch", "attachment_missing",
                     "attachment_unknown", "placeholder_present", "privacy_risk",
                     "action_item_incomplete", "sensitive_term_review", "overclaim_review"):
            self.assertIn(kind, doc)


class FixtureTest(unittest.TestCase):
    fixtures = SCRIPTS_DIR / "fixtures" / "samples"

    def test_fixture_types_and_documents(self):
        types = yd.load_types(self.fixtures / "types.json", "fixture")
        facts = yd.load_facts(self.fixtures / "facts-complete.json")
        notice = yd.get_type(types, "notice")
        clean = (self.fixtures / "notice-complete.md").read_text(encoding="utf-8")
        gap = (self.fixtures / "notice-gap.md").read_text(encoding="utf-8")
        self.assertEqual(yd.check_document(clean, notice, facts=facts)["findings"], [])
        self.assertGreaterEqual(len(yd.check_document(gap, notice, facts=facts)["findings"]), 3)

    def test_fixture_minutes_has_action_gap(self):
        types = yd.load_types(self.fixtures / "types.json", "fixture")
        minutes = yd.get_type(types, "minutes")
        text = (self.fixtures / "minutes-gap.md").read_text(encoding="utf-8")
        result = yd.check_document(text, minutes)
        self.assertTrue(any(f["kind"] == "action_item_incomplete"
                            for f in result["findings"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
