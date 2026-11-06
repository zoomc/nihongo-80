# Day 1–3 端到端真实演练记录

生成时间：2026-11-07 00:50:07 +0800

复现命令：`python3 tests/test_all.py`

说明：演练在独立临时目录 `/tmp/nh80-test-*` 执行，会真实建库、生成 80 天课程与网页、
启动 Day 1–3 会话、作答批改、写错题库、排 FSRS、导入网页回传码（含复习三档自评）、生成周报，
**不污染真实项目的学习档案**。测试结束自动清理临时目录。

## 原始输出

```
test_01_db_and_fts (__main__.TestAStatic.test_01_db_and_fts) ... ok
test_01b_framework_delivery (__main__.TestAStatic.test_01b_framework_delivery)
v2 框架：分级兑现与去模板化必须被强校验，而不是只查覆盖率。 ... ok
test_02_keyword_relation_semantic (__main__.TestAStatic.test_02_keyword_relation_semantic) ... ok
test_03_80_days_complete (__main__.TestAStatic.test_03_80_days_complete) ... ok
test_04_prerequisites_and_no_spoilers (__main__.TestAStatic.test_04_prerequisites_and_no_spoilers) ... ok
test_05_external_materials_have_no_body (__main__.TestAStatic.test_05_external_materials_have_no_body) ... ok
test_01_fsrs_official_and_deterministic (__main__.TestBEngine.test_01_fsrs_official_and_deterministic) ... ok
test_02_one_correct_is_not_mastered (__main__.TestBEngine.test_02_one_correct_is_not_mastered) ... ok
test_03_error_remedy_mapping (__main__.TestBEngine.test_03_error_remedy_mapping) ... ok
test_01_start_day1 (__main__.TestCFlow.test_01_start_day1) ... ok
test_02_answer_and_grade (__main__.TestCFlow.test_02_answer_and_grade) ... ok
test_03_finish_day1_and_persist (__main__.TestCFlow.test_03_finish_day1_and_persist) ... ok
test_04_day2_reads_previous_summary (__main__.TestCFlow.test_04_day2_reads_previous_summary) ... ok
test_05_fsrs_due_and_remedy_tasks (__main__.TestCFlow.test_05_fsrs_due_and_remedy_tasks) ... ok
test_06_web_result_import_idempotent (__main__.TestCFlow.test_06_web_result_import_idempotent) ... ok
test_06b_review_ratings_drive_fsrs (__main__.TestCFlow.test_06b_review_ratings_drive_fsrs)
v3：网页「今日复习」三档自评必须真正写回 FSRS，且不得判定掌握。 ... ok
test_07_day3_and_adjust (__main__.TestCFlow.test_07_day3_and_adjust) ... ok
test_08_weekly_report_real_data (__main__.TestCFlow.test_08_weekly_report_real_data) ... ok
test_09_backup_restore_audit (__main__.TestCFlow.test_09_backup_restore_audit) ... ok
test_10_new_session_prompt_reads_real_state (__main__.TestCFlow.test_10_new_session_prompt_reads_real_state) ... ok

----------------------------------------------------------------------
Ran 20 tests in 6.696s

OK
测试根目录: /var/folders/y5/s3nn1c7x6wg6vnnll6cxvq2w0000gn/T/nh80-test-ofezwxt0
```
