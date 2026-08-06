import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Ensure we can import from core
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from core.jira_client import JiraClient

def main():
    parser = argparse.ArgumentParser(description="Push generated tests to Jira")
    parser.add_argument('--repo', required=True, help="GitHub repo owner/name (e.g., owner/repo)")
    args = parser.parse_args()

    repo_name = args.repo.split('/')[-1] if '/' in args.repo else args.repo

    load_dotenv()
    
    jira = JiraClient()
    if not jira.is_configured():
        print("Error: Jira is not fully configured in .env")
        print(f"URL: {jira.url}")
        print(f"Email: {jira.email}")
        print(f"Token: {'Set' if jira.token else 'Missing'}")
        print(f"Project Key: {jira.project_key}")
        sys.exit(1)
        
    print(f"[Jira Sync] Connecting to Project: {jira.project_key} at {jira.url}")
    
    target_status = os.getenv("JIRA_FEATURE_STATUS", "In Progress")
    
    # 1. Look for output test plans only for the target repo
    repo_out_dir = Path("output") / repo_name
    plan_file = repo_out_dir / "test_plan.json"
    
    count = 0
    if plan_file.exists():
            print(f"\nProcessing {plan_file}...")
            try:
                with open(plan_file, "r", encoding="utf-8") as f:
                    tasks = json.load(f)
                    
                for t in tasks:
                    cls = t.get("class", "TestClass")
                    func = t.get("func", "testMethod")
                    axis = t.get("axis", "unit")
                    techniques = t.get("techniques", [])
                    
                    summary = f"[{cls}] {func}() - {axis.upper()} Test Suite"
                    desc = f"Class: {cls}\nFunction: {func}\nAxis: {axis}\nTechniques: {', '.join(techniques)}"
                    
                    issue_key = jira.create_issue(summary=summary, description=desc, issue_type="Feature", status=target_status)
                    if not issue_key:
                        issue_key = jira.create_issue(summary=summary, description=desc, issue_type="Story", status=target_status)
                    if not issue_key:
                        issue_key = jira.create_issue(summary=summary, description=desc, issue_type="Task", status=target_status)
                    if issue_key:
                        count += 1
            except Exception as e:
                print(f"Error processing {plan_file}: {e}")
    else:
        # Fallback to test_matrix_summary.csv
        csv_file = repo_out_dir / "test_matrix_summary.csv"
        if csv_file.exists():
            print(f"\nProcessing {csv_file}...")
            try:
                with open(csv_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines[1:]:
                        parts = line.strip().split(",")
                        if len(parts) >= 4:
                            cls, func, axis, tech = parts[:4]
                            summary = f"[{cls}] {func} - {tech}"
                            desc = f"Class: {cls}\nFunction: {func}\nAxis: {axis}\nTechnique: {tech}"
                            issue_key = jira.create_issue(summary=summary, description=desc, issue_type="Feature", status=target_status)
                            if not issue_key:
                                issue_key = jira.create_issue(summary=summary, description=desc, issue_type="Story", status=target_status)
                            if not issue_key:
                                issue_key = jira.create_issue(summary=summary, description=desc, issue_type="Task", status=target_status)
                            if issue_key:
                                count += 1
            except Exception as e:
                print(f"Error processing {csv_file}: {e}")

    print(f"\n[Jira Sync] Successfully pushed {count} test issues to Jira Project {jira.project_key}!")

if __name__ == "__main__":
    main()
