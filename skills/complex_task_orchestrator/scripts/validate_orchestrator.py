#!/usr/bin/env python3
"""
Orchestrator Skill Validator
Kiểm tra cấu trúc skill complex_task_orchestrator.
Chạy: python scripts/validate_orchestrator.py
"""
import os
import sys
import re
import yaml

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXPECTED_FILES = [
    "SKILL.md",
    "README.md",
    "templates/task_contract.yaml",
    "templates/execution_manifest.yaml",
    "templates/subagent_assignment.yaml",
    "templates/final_audit.yaml",
    "templates/final_report.md",
    "references/delegate_task_api.md",
    "references/tool_routing_guide.md",
    "scripts/validate_orchestrator.py",
    "scripts/test_orchestrator.py",
]

REQUIRED_FRONTMATTER_KEYS = ["name", "description", "version"]

VALID_EXECUTION_MODES = {"SEQUENTIAL", "PARALLEL_SAFE", "APPROVAL_REQUIRED"}
VALID_ROLES = {"PLANNER", "RESEARCHER", "EXECUTOR", "TESTER", "INTEGRATOR", "AUDITOR", "REPAIRER"}
VALID_COMPLEXITY_LEVELS = {"LEVEL_1", "LEVEL_2", "LEVEL_3"}
VALID_STATUSES = {"PENDING", "RUNNING", "PASS", "FAIL", "BLOCKED", "CANCELLED"}


def check_file_exists(filepath):
    """Check if a file exists."""
    full = os.path.join(SKILL_DIR, filepath)
    exists = os.path.isfile(full)
    return exists, full


def parse_frontmatter(content):
    """Parse YAML frontmatter from markdown."""
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None
    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None


def validate_frontmatter(content):
    """Validate SKILL.md frontmatter."""
    errors = []
    fm = parse_frontmatter(content)
    if fm is None:
        errors.append("SKILL.md: Missing or invalid YAML frontmatter")
        return errors
    for key in REQUIRED_FRONTMATTER_KEYS:
        if key not in fm:
            errors.append(f"SKILL.md: Missing required frontmatter key: {key}")
    if fm.get("name") != "complex_task_orchestrator":
        errors.append(f"SKILL.md: name must be 'complex_task_orchestrator', got '{fm.get('name')}'")
    return errors


def validate_yaml_file(filepath):
    """Validate a YAML file parses correctly."""
    full = os.path.join(SKILL_DIR, filepath)
    errors = []
    try:
        with open(full, 'r', encoding='utf-8') as f:
            content = f.read()
        # Skip comment-only lines for validation
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        errors.append(f"{filepath}: YAML parse error: {e}")
    except FileNotFoundError:
        errors.append(f"{filepath}: File not found")
    return errors


def validate_execution_manifest():
    """Validate execution_manifest.yaml has required fields."""
    filepath = "templates/execution_manifest.yaml"
    full = os.path.join(SKILL_DIR, filepath)
    errors = []
    try:
        with open(full, 'r', encoding='utf-8') as f:
            content = f.read()
        data = yaml.safe_load(content)
        if not data:
            errors.append(f"{filepath}: Empty or invalid YAML")
            return errors
        # Check required top-level keys
        required_keys = ["tasks", "waves", "resource_ownership", "integration", "audit"]
        for key in required_keys:
            if key not in data:
                errors.append(f"{filepath}: Missing required key: {key}")
        # Check task schema if tasks exist
        if data.get("tasks"):
            for i, task in enumerate(data["tasks"]):
                if "execution_mode" in task and task["execution_mode"] not in VALID_EXECUTION_MODES:
                    errors.append(f"{filepath}: task[{i}].execution_mode invalid: {task['execution_mode']}")
                if "assigned_role" in task and task["assigned_role"] not in VALID_ROLES:
                    errors.append(f"{filepath}: task[{i}].assigned_role invalid: {task['assigned_role']}")
                if "status" in task and task["status"] not in VALID_STATUSES:
                    errors.append(f"{filepath}: task[{i}].status invalid: {task['status']}")
        # Check complexity level
        if "complexity_level" in data and data["complexity_level"] not in VALID_COMPLEXITY_LEVELS:
            errors.append(f"{filepath}: complexity_level invalid: {data['complexity_level']}")
    except Exception as e:
        errors.append(f"{filepath}: Error: {e}")
    return errors


def validate_task_contract():
    """Validate task_contract.yaml has required fields."""
    filepath = "templates/task_contract.yaml"
    full = os.path.join(SKILL_DIR, filepath)
    errors = []
    try:
        with open(full, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f.read())
        if not data:
            errors.append(f"{filepath}: Empty or invalid YAML")
            return errors
        required_keys = ["objective", "deliverables", "acceptance_criteria", "constraints",
                        "allowed_actions", "forbidden_actions", "dependencies", "risks",
                        "approval_gates", "stop_conditions"]
        for key in required_keys:
            if key not in data:
                errors.append(f"{filepath}: Missing required key: {key}")
    except Exception as e:
        errors.append(f"{filepath}: Error: {e}")
    return errors


def validate_subagent_assignment():
    """Validate subagent_assignment.yaml."""
    filepath = "templates/subagent_assignment.yaml"
    errors = validate_yaml_file(filepath)
    full = os.path.join(SKILL_DIR, filepath)
    try:
        with open(full, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f.read())
        if data:
            if "goal" not in data:
                errors.append(f"{filepath}: Missing 'goal' field")
            if "context" not in data:
                errors.append(f"{filepath}: Missing 'context' field")
            if "role" in data and data["role"] not in {"leaf", "orchestrator"}:
                errors.append(f"{filepath}: Invalid role: {data['role']}")
    except Exception as e:
        errors.append(f"{filepath}: Error: {e}")
    return errors


def validate_final_audit():
    """Validate final_audit.yaml."""
    filepath = "templates/final_audit.yaml"
    errors = validate_yaml_file(filepath)
    full = os.path.join(SKILL_DIR, filepath)
    try:
        with open(full, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f.read())
        if data:
            required_keys = ["overall_status", "criteria", "fail_list", "frozen"]
            for key in required_keys:
                if key not in data:
                    errors.append(f"{filepath}: Missing required key: {key}")
    except Exception as e:
        errors.append(f"{filepath}: Error: {e}")
    return errors


def main():
    print("=" * 60)
    print("Orchestrator Skill Validator")
    print("=" * 60)
    print()

    all_errors = []
    all_warnings = []

    # 1. Check all expected files exist
    print("[1] Checking file existence...")
    for f in EXPECTED_FILES:
        exists, full = check_file_exists(f)
        if exists:
            print(f"  OK  {f}")
        else:
            all_errors.append(f"Missing file: {f}")
            print(f"  FAIL {f}")
    print()

    # 2. Validate SKILL.md frontmatter
    print("[2] Validating SKILL.md frontmatter...")
    skill_md = os.path.join(SKILL_DIR, "SKILL.md")
    if os.path.isfile(skill_md):
        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()
        errors = validate_frontmatter(content)
        if errors:
            all_errors.extend(errors)
            for e in errors:
                print(f"  FAIL {e}")
        else:
            print("  OK  Frontmatter valid")
            fm = parse_frontmatter(content)
            print(f"  name: {fm.get('name')}")
            print(f"  version: {fm.get('version')}")
    else:
        all_errors.append("SKILL.md not found")
    print()

    # 3. Validate YAML templates
    print("[3] Validating YAML templates...")
    yaml_errors = validate_execution_manifest()
    yaml_errors += validate_task_contract()
    yaml_errors += validate_subagent_assignment()
    yaml_errors += validate_final_audit()
    if yaml_errors:
        all_errors.extend(yaml_errors)
        for e in yaml_errors:
            print(f"  FAIL {e}")
    else:
        print("  OK  All YAML templates valid")
    print()

    # 4. Check SKILL.md content for required sections
    print("[4] Checking SKILL.md required sections...")
    required_sections = [
        "Activation",
        "Phân loại độ phức tạp",
        "LEVEL 1",
        "LEVEL 2",
        "LEVEL 3",
        "delegate_task",
 "PARALLEL_SAFE",
        "Approval Gate",
        "Context Management",
        "Output Schema",
        "Completion Criteria",
        "Pitfalls",
    ]
    with open(skill_md, 'r', encoding='utf-8') as f:
        skill_content = f.read()
    for section in required_sections:
        if section.lower() in skill_content.lower():
            print(f"  OK  Section: {section}")
        else:
            all_warnings.append(f"SKILL.md: Section not found: {section}")
            print(f"  WARN Section not found: {section}")
    print()

    # 5. Summary
    print("=" * 60)
    if all_errors:
        print(f"RESULT: FAIL ({len(all_errors)} errors, {len(all_warnings)} warnings)")
        print()
        print("Errors:")
        for e in all_errors:
            print(f"  - {e}")
    else:
        print(f"RESULT: PASS (0 errors, {len(all_warnings)} warnings)")
        if all_warnings:
            print()
            print("Warnings:")
            for w in all_warnings:
                print(f"  - {w}")
    print("=" * 60)
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
