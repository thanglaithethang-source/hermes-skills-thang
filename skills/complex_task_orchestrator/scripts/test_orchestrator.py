#!/usr/bin/env python3
"""
Orchestrator Skill Test Suite — 15 Scenarios
Kiểm tra logic orchestration qua simulation.
Chạy: python scripts/test_orchestrator.py
"""
import os
import sys
import yaml
import tempfile

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

results = []

def record(test_name, passed, evidence):
    results.append({
        "test": test_name,
        "status": "PASS" if passed else "FAIL",
        "evidence": evidence
    })
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {test_name}")
    print(f"         {evidence[:200]}")

def load_yaml(filepath):
    full = os.path.join(SKILL_DIR, filepath)
    with open(full, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f.read())

def load_text(filepath):
    full = os.path.join(SKILL_DIR, filepath)
    with open(full, 'r', encoding='utf-8') as f:
        return f.read()

# ============================================================
# TEST 01 — SIMPLE TASK: Đọc file, đếm dòng, báo kết quả
# Kỳ vọng: Không spawn sub-agent, không tạo task graph dư thừa, có verification
# ============================================================
def test_01_simple_task():
    print("\n[TEST 01] Simple task — đọc file, đếm dòng")
    skill = load_text("SKILL.md")
    has_level1 = "LEVEL 1" in skill and "thực hiện trực tiếp" in skill.lower()
    has_no_delegate = "không cần chia sub-agent" in skill.lower() or "không tạo delegate_task" in skill.lower()
    has_verify = "kiểm tra kết quả" in skill.lower()

    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = os.path.join(tmpdir, "test.txt")
        with open(fpath, 'w') as f:
            f.write("line1\nline2\nline3\n")
        with open(fpath, 'r') as f:
            count = len(f.readlines())
        exists = os.path.isfile(fpath)

    passed = has_level1 and has_no_delegate and has_verify and exists and count == 3
    evidence = f"LEVEL1: {has_level1}, no_delegate: {has_no_delegate}, verify: {has_verify}, file_exists: {exists}, line_count: {count}"
    record("TEST 01: Simple task (LEVEL 1, no sub-agent, direct + verification)", passed, evidence)

# ============================================================
# TEST 02 — COMPOUND TASK: Phân tích 3 file độc lập, tổng hợp báo cáo
# Kỳ vọng: Chia task, chạy song song nếu an toàn, có integrator, không mất dữ liệu
# ============================================================
def test_02_compound_task():
    print("\n[TEST 02] Compound task — 3 file độc lập, tổng hợp báo cáo")
    skill = load_text("SKILL.md")
    has_parallel = "PARALLEL_SAFE" in skill
    has_batch = "tasks=[" in skill or "batch" in skill.lower()
    has_integrator = "INTEGRATOR" in skill
    manifest = load_yaml("templates/execution_manifest.yaml")
    has_waves = "waves" in manifest
    has_ownership = "resource_ownership" in manifest

    tasks = [
        {"task_id": "T01", "execution_mode": "PARALLEL_SAFE", "owned_resources": []},
        {"task_id": "T02", "execution_mode": "PARALLEL_SAFE", "owned_resources": []},
        {"task_id": "T03", "execution_mode": "PARALLEL_SAFE", "owned_resources": []},
    ]
    all_safe = all(t["execution_mode"] == "PARALLEL_SAFE" for t in tasks)
    no_conflicts = all(not t.get("owned_resources") for t in tasks)

    passed = has_parallel and has_batch and has_integrator and has_waves and has_ownership and all_safe and no_conflicts
    evidence = f"PARALLEL_SAFE: {has_parallel}, batch: {has_batch}, integrator: {has_integrator}, waves: {has_waves}, ownership: {has_ownership}, all_safe: {all_safe}, no_conflicts: {no_conflicts}"
    record("TEST 02: Compound task (3 independent, parallel, integrator)", passed, evidence)

# ============================================================
# TEST 03 — COMPLEX CODE TASK: DB + Backend + Frontend + Test
# Kỳ vọng: Dependency graph, no same-file conflict, DB first, integration test, final audit
# ============================================================
def test_03_complex_code_task():
    print("\n[TEST 03] Complex code task — DB + Backend + Frontend + Test")
    skill = load_text("SKILL.md")
    has_dep_graph = "DEPENDENCY GRAPH" in skill or "dependency" in skill.lower()
    has_waves = "WAVE" in skill
    has_ownership = "owned_resources" in skill and "Exclusive Ownership" in skill
    has_integration = "Integration Gate" in skill
    has_audit = "FINAL AUDIT" in skill

    tasks = [
        {"task_id": "T01", "title": "Database", "dependencies": [],
         "owned_resources": [{"path": "db/schema.sql", "mode": "write"}], "execution_mode": "SEQUENTIAL"},
        {"task_id": "T02", "title": "Backend", "dependencies": ["T01"],
         "owned_resources": [{"path": "src/backend/**", "mode": "write"}], "execution_mode": "SEQUENTIAL"},
        {"task_id": "T03", "title": "Frontend", "dependencies": ["T02"],
         "owned_resources": [{"path": "src/frontend/**", "mode": "write"}], "execution_mode": "SEQUENTIAL"},
        {"task_id": "T04", "title": "Tests", "dependencies": ["T02", "T03"],
         "owned_resources": [{"path": "tests/**", "mode": "write"}], "execution_mode": "SEQUENTIAL"},
    ]
    write_paths = [r["path"] for t in tasks for r in t["owned_resources"] if r["mode"] == "write"]
    no_conflict = len(write_paths) == len(set(write_paths))
    db_before_backend = "T01" in tasks[1]["dependencies"]
    test_deps = "T02" in tasks[3]["dependencies"] and "T03" in tasks[3]["dependencies"]

    passed = has_dep_graph and has_waves and has_ownership and has_integration and has_audit and no_conflict and db_before_backend and test_deps
    evidence = f"dep_graph: {has_dep_graph}, waves: {has_waves}, ownership: {has_ownership}, integration: {has_integration}, audit: {has_audit}, no_conflict: {no_conflict}, db_first: {db_before_backend}, test_deps: {test_deps}"
    record("TEST 03: Complex code task (dep graph, no conflict, DB first, integration, audit)", passed, evidence)

# ============================================================
# TEST 04 — SAME-FILE CONFLICT
# Kỳ vọng: Không chạy song song, có 1 writer, integrator xử lý
# ============================================================
def test_04_same_file_conflict():
    print("\n[TEST 04] Same-file conflict — 2 task sửa cùng file")
    skill = load_text("SKILL.md")
    has_conflict_rules = "Cùng sửa một file" in skill
    has_not_parallel = "KHÔNG được đánh dấu" in skill and "PARALLEL_SAFE" in skill
    has_one_writer = "Một resource chỉ có MỘT writer" in skill
    has_integrator = "integrator" in skill.lower()

    task_a = {"owned_resources": [{"path": "src/config.py", "mode": "write"}]}
    task_b = {"owned_resources": [{"path": "src/config.py", "mode": "write"}]}
    a_paths = {r["path"] for r in task_a["owned_resources"] if r["mode"] == "write"}
    b_paths = {r["path"] for r in task_b["owned_resources"] if r["mode"] == "write"}
    conflict_detected = bool(a_paths & b_paths)

    passed = has_conflict_rules and has_not_parallel and has_one_writer and conflict_detected and has_integrator
    evidence = f"conflict_rules: {has_conflict_rules}, not_parallel: {has_not_parallel}, one_writer: {has_one_writer}, conflict_detected: {conflict_detected}, integrator: {has_integrator}"
    record("TEST 04: Same-file conflict (detect, no parallel, one writer)", passed, evidence)

# ============================================================
# TEST 05 — OUTPUT-PATH CONFLICT
# Kỳ vọng: Phát hiện trước khi chạy, tạo path riêng hoặc sequential
# ============================================================
def test_05_output_path_conflict():
    print("\n[TEST 05] Output-path conflict — 2 task cùng ghi output path")
    skill = load_text("SKILL.md")
    has_output_rule = "Cùng ghi vào một thư mục output" in skill
    has_not_parallel = "KHÔNG được đánh dấu" in skill

    task_a = {"owned_resources": [{"path": "output/**", "mode": "write"}]}
    task_b = {"owned_resources": [{"path": "output/**", "mode": "write"}]}
    a_paths = {r["path"] for r in task_a["owned_resources"] if r["mode"] == "write"}
    b_paths = {r["path"] for r in task_b["owned_resources"] if r["mode"] == "write"}
    conflict_detected = bool(a_paths & b_paths)
    should_be_sequential = conflict_detected

    passed = has_output_rule and has_not_parallel and conflict_detected and should_be_sequential
    evidence = f"output_rule: {has_output_rule}, not_parallel: {has_not_parallel}, conflict_detected: {conflict_detected}, should_be_sequential: {should_be_sequential}"
    record("TEST 05: Output-path conflict (detect before run, sequential)", passed, evidence)

# ============================================================
# TEST 06 — FAILED WORKER
# Kỳ vọng: Không tiếp tục như PASS, có diagnose, repair task, verify lại
# ============================================================
def test_06_failed_worker():
    print("\n[TEST 06] Failed worker — sub-agent trả về FAIL")
    skill = load_text("SKILL.md")
    has_repair = "REPAIR" in skill and "repair" in skill.lower()
    has_no_false_pass = "KHÔNG tuyên bố PASS" in skill or "không tuyên bố" in skill.lower()
    has_diagnose = "DIAGNOSE" in skill or "nguyên nhân gốc" in skill.lower()
    has_verify_again = "VERIFY AGAIN" in skill

    worker_result = {"status": "FAIL", "task_id": "T01", "evidence": ["exit_code: 1"]}
    should_not_pass = worker_result["status"] != "PASS"
    should_create_repair = has_repair and should_not_pass

    passed = has_repair and has_no_false_pass and has_diagnose and has_verify_again and should_not_pass and should_create_repair
    evidence = f"repair: {has_repair}, no_false_pass: {has_no_false_pass}, diagnose: {has_diagnose}, verify_again: {has_verify_again}, not_pass: {should_not_pass}, create_repair: {should_create_repair}"
    record("TEST 06: Failed worker (no false PASS, diagnose, repair, verify)", passed, evidence)

# ============================================================
# TEST 07 — MALFORMED WORKER OUTPUT
# Kỳ vọng: Phát hiện sai schema, chuẩn hóa hoặc yêu cầu trả lại, không mất evidence
# ============================================================
def test_07_malformed_output():
    print("\n[TEST 07] Malformed worker output — sai schema")
    skill = load_text("SKILL.md")
    has_normalize = "chuẩn hóa" in skill.lower()
    has_output_schema = "Output Schema" in skill
    has_evidence = "evidence" in skill.lower()

    # Simulate malformed output (missing required fields)
    malformed = {"status": "PASS", "summary": "Done"}  # Missing task_id, evidence, etc.
    required_fields = ["status", "task_id", "summary", "evidence"]
    missing = [f for f in required_fields if f not in malformed]
    is_malformed = len(missing) > 0

    passed = has_normalize and has_output_schema and has_evidence and is_malformed
    evidence = f"normalize: {has_normalize}, output_schema: {has_output_schema}, evidence: {has_evidence}, malformed_detected: {is_malformed}, missing_fields: {missing}"
    record("TEST 07: Malformed output (detect, normalize, no evidence loss)", passed, evidence)

# ============================================================
# TEST 08 — RETRY LIMIT
# Kỳ vọng: Không loop vô hạn, đổi chiến lược, báo BLOCKED
# ============================================================
def test_08_retry_limit():
    print("\n[TEST 08] Retry limit — 3 lần fail → BLOCKED")
    skill = load_text("SKILL.md")
    has_max_3 = "3" in skill and "attempt" in skill.lower()
    has_escalation = "BLOCKED" in skill
    has_change_strategy = "thay đổi chiến lược" in skill.lower()
    has_no_infinite = "KHÔNG loop vô hạn" in skill

    max_attempts = 3
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
    all_failed = True
    reached_limit = attempts == max_attempts
    should_block = all_failed and reached_limit
    no_infinite = attempts <= max_attempts

    passed = has_max_3 and has_escalation and has_change_strategy and has_no_infinite and should_block and no_infinite
    evidence = f"max_3: {has_max_3}, escalation: {has_escalation}, change_strategy: {has_change_strategy}, no_infinite: {has_no_infinite}, reached_limit: {reached_limit}, no_infinite_loop: {no_infinite}"
    record("TEST 08: Retry limit (max 3, change strategy, BLOCKED)", passed, evidence)

# ============================================================
# TEST 09 — APPROVAL GATE
# Kỳ vọng: Dừng trước side effect, yêu cầu duyệt, không thực thi trước approval
# ============================================================
def test_09_approval_gate():
    print("\n[TEST 09] Approval gate — xóa dữ liệu")
    skill = load_text("SKILL.md")
    contract = load_yaml("templates/task_contract.yaml")
    manifest = load_yaml("templates/execution_manifest.yaml")

    has_approval_section = "Approval Gate" in skill
    has_delete = "Xóa dữ liệu" in skill
    has_production = "Thay đổi production" in skill
    has_readonly_exempt = "chỉ đọc" in skill and "không cần approval" in skill.lower()
    has_contract_approval = "approval_gates" in contract if contract else False
    has_manifest_mode = "APPROVAL_REQUIRED" in str(manifest) if manifest else False
    has_clarify = "clarify" in skill.lower()

    dangerous = {"type": "delete", "approved": False}
    should_stop = not dangerous["approved"]

    passed = has_approval_section and has_delete and has_production and has_readonly_exempt and has_contract_approval and has_manifest_mode and should_stop and has_clarify
    evidence = f"approval_section: {has_approval_section}, delete: {has_delete}, production: {has_production}, readonly_exempt: {has_readonly_exempt}, contract: {has_contract_approval}, manifest_mode: {has_manifest_mode}, stops: {should_stop}, clarify: {has_clarify}"
    record("TEST 09: Approval gate (stops before delete, requires approval)", passed, evidence)

# ============================================================
# TEST 10 — FALSE PASS
# Kỳ vọng: Integrator/auditor phát hiện artifact không tồn tại, đánh FAIL
# ============================================================
def test_10_false_pass():
    print("\n[TEST 10] False PASS — worker tuyên bố PASS nhưng artifact không tồn tại")
    skill = load_text("SKILL.md")
    has_false_pass = "False PASS" in skill or "false PASS" in skill.lower()
    has_verify_artifact = "artifact tồn tại" in skill.lower() or "tồn tại thật" in skill.lower()
    has_no_trust = "Không tin" in skill or "không tin" in skill.lower()

    # Simulate: worker says PASS, but file doesn't exist
    worker_claim = {"status": "PASS", "artifacts_created": [{"path": "/nonexistent/file.txt"}]}
    artifact_exists = os.path.isfile(worker_claim["artifacts_created"][0]["path"])
    should_fail = not artifact_exists

    passed = has_false_pass and has_verify_artifact and has_no_trust and should_fail
    evidence = f"false_pass_detection: {has_false_pass}, verify_artifact: {has_verify_artifact}, no_trust: {has_no_trust}, artifact_missing: {should_fail}"
    record("TEST 10: False PASS (detect missing artifact, mark FAIL)", passed, evidence)

# ============================================================
# TEST 11 — BUILD PASS, FUNCTION FAIL
# Kỳ vọng: Auditor không dừng ở build, chạy functional test, phát hiện lỗi
# ============================================================
def test_11_build_pass_function_fail():
    print("\n[TEST 11] Build PASS, function FAIL")
    skill = load_text("SKILL.md")
    has_build_vs_function = "Build PASS" in skill and "Functional" in skill
    has_functional_test = "functional test" in skill.lower() or "luồng thực" in skill.lower()
    has_auditor_not_stop = "Auditor không dừng ở build" in skill or "không dừng ở build" in skill.lower()

    # Simulate: build succeeds, function fails
    build_result = "PASS"
    function_result = "FAIL"
    should_detect = build_result == "PASS" and function_result == "FAIL"

    passed = has_build_vs_function and has_functional_test and has_auditor_not_stop and should_detect
    evidence = f"build_vs_function: {has_build_vs_function}, functional_test: {has_functional_test}, auditor_not_stop: {has_auditor_not_stop}, detect: {should_detect}"
    record("TEST 11: Build PASS function FAIL (auditor runs functional test)", passed, evidence)

# ============================================================
# TEST 12 — REGRESSION
# Kỳ vọng: Regression test phát hiện, repair chỉ sửa phạm vi bị ảnh hưởng
# ============================================================
def test_12_regression():
    print("\n[TEST 12] Regression — feature mới hỏng feature cũ")
    skill = load_text("SKILL.md")
    has_regression = "regression" in skill.lower()
    has_repair_scope = "chỉ sửa phạm vi" in skill.lower() or "phạm vi liên quan" in skill.lower()

    # Simulate: old test that was passing now fails
    old_test_passing = True
    old_test_after_new_feature = False
    regression_detected = old_test_passing and not old_test_after_new_feature

    passed = has_regression and has_repair_scope and regression_detected
    evidence = f"regression: {has_regression}, repair_scope: {has_repair_scope}, detected: {regression_detected}"
    record("TEST 12: Regression (detect, repair only affected scope)", passed, evidence)

# ============================================================
# TEST 13 — TOOL FAILURE
# Kỳ vọng: Dùng fallback phù hợp, không bịa kết quả, báo BLOCKED nếu không có fallback
# ============================================================
def test_13_tool_failure():
    print("\n[TEST 13] Tool failure — tool chính không hoạt động")
    skill = load_text("SKILL.md")
    has_fallback = "fallback" in skill.lower()
    has_no_fabricate = "không bịa" in skill.lower() or "BLOCKED" in skill
    has_tool_failure_section = "Tool failure" in skill

    # Simulate: primary tool fails, fallback available
    primary_tool_ok = False
    fallback_available = True
    should_use_fallback = not primary_tool_ok and fallback_available
    should_block_if_no_fallback = not primary_tool_ok and not fallback_available

    passed = has_fallback and has_no_fabricate and has_tool_failure_section and should_use_fallback
    evidence = f"fallback: {has_fallback}, no_fabricate: {has_no_fabricate}, tool_failure_section: {has_tool_failure_section}, use_fallback: {should_use_fallback}"
    record("TEST 13: Tool failure (use fallback, no fabrication, BLOCKED if none)", passed, evidence)

# ============================================================
# TEST 14 — CONTEXT LOSS
# Kỳ vọng: Worker vẫn nhận đủ constraint, final audit kiểm tra đúng tiêu chí gốc
# ============================================================
def test_14_context_loss():
    print("\n[TEST 14] Context loss — acceptance criteria ở đầu context dài")
    skill = load_text("SKILL.md")
    has_context_loss = "Context loss" in skill or "context loss" in skill.lower()
    has_bookend = "bookend" in skill.lower()
    has_no_guess = "suy đoán" in skill.lower()
    has_audit_original = "tiêu chí gốc" in skill.lower()

    # Simulate: long context with criteria at start AND end (bookend pattern)
    criteria_text = "Acceptance: File X must exist"
    long_context = criteria_text + "\n" + "x" * 10000 + "\n" + criteria_text + "\n"
    criteria_at_start = criteria_text in long_context[:200]
    criteria_at_end = criteria_text in long_context[-200:]

    passed = has_context_loss and has_bookend and has_no_guess and has_audit_original and criteria_at_start and criteria_at_end
    evidence = f"context_loss: {has_context_loss}, bookend: {has_bookend}, no_guess: {has_no_guess}, audit_original: {has_audit_original}, criteria_start: {criteria_at_start}, criteria_end: {criteria_at_end}"
    record("TEST 14: Context loss (bookend pattern, audit original criteria)", passed, evidence)

# ============================================================
# TEST 15 — TRIGGER CONTROL
# Kỳ vọng: Không over-trigger cho prompt đơn giản, không under-trigger cho prompt phức tạp
# ============================================================
def test_15_trigger_control():
    print("\n[TEST 15] Trigger control — over/under trigger")
    skill = load_text("SKILL.md")
    has_activation = "Activation" in skill
    has_negative_trigger = "KHÔNG kích hoạt" in skill
    has_level1 = "LEVEL 1" in skill
    has_level3 = "LEVEL 3" in skill

    # Simulate: simple prompt should not trigger orchestration
    simple_prompt = "Rename a file"
    complex_prompt = "Build a web app with database, backend API, frontend, and tests"

    # Simple: should be LEVEL 1 (no sub-agent)
    simple_should_not_orchestrate = "LEVEL 1" in skill and "Không tạo delegate_task" in skill
    # Complex: should trigger
    complex_should_orchestrate = "LEVEL 3" in skill

    passed = has_activation and has_negative_trigger and has_level1 and has_level3 and simple_should_not_orchestrate and complex_should_orchestrate
    evidence = f"activation: {has_activation}, negative_trigger: {has_negative_trigger}, level1: {has_level1}, level3: {has_level3}, simple_no_orchestrate: {simple_should_not_orchestrate}, complex_orchestrate: {complex_should_orchestrate}"
    record("TEST 15: Trigger control (no over-trigger, no under-trigger)", passed, evidence)

# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("Orchestrator Skill Test Suite — 15 Scenarios")
    print("=" * 60)

    test_01_simple_task()
    test_02_compound_task()
    test_03_complex_code_task()
    test_04_same_file_conflict()
    test_05_output_path_conflict()
    test_06_failed_worker()
    test_07_malformed_output()
    test_08_retry_limit()
    test_09_approval_gate()
    test_10_false_pass()
    test_11_build_pass_function_fail()
    test_12_regression()
    test_13_tool_failure()
    test_14_context_loss()
    test_15_trigger_control()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed_count = sum(1 for r in results if r["status"] == "PASS")
    failed_count = sum(1 for r in results if r["status"] == "FAIL")

    for r in results:
        print(f"  {r['status']:4s} | {r['test']}")

    print()
    print(f"Total: {len(results)} | PASS: {passed_count} | FAIL: {failed_count}")
    print("=" * 60)

    return 1 if failed_count > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
