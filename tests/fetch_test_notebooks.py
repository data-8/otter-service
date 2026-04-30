#!/usr/bin/env python3
"""
Fetch student and solution notebooks from GitHub (or local PR workspace) for CI testing.

Output structure:
  tests/test_files/{course}/{assignment}/student/{assignment}.ipynb  + data files
  tests/test_files/{course}/{assignment}/solution/{assignment}.ipynb + data files

Usage:
  # Fetch all notebooks for given courses from GitHub
  python tests/fetch_test_notebooks.py --courses "88ex,88bx,88cx,8x"

  # Only lab01 per course (smoke test)
  python tests/fetch_test_notebooks.py --courses "88ex" --smoke

  # xDevs PR: after otter assign has run, read from local workspace
  python tests/fetch_test_notebooks.py \
    --changed-files "88e/raw_notebooks/lab01/lab01.ipynb" \
    --local
"""
import argparse
import base64
import os
import shutil
import sys
import time
from pathlib import Path

import jwt
import nbformat
import requests

COURSE_DIRS = {
    "88ex": "88e",
    "88bx": "88b",
    "88cx": "88c",
    "8x": "8x",
}
STUDENT_REPOS = {
    "88ex": "edx-berkeley/88E-student",
    "88bx": "edx-berkeley/88B-student",
    "88cx": "edx-berkeley/88C-student",
    "8x": "edx-berkeley/8X-student",
}
SOLUTION_REPO = "edx-berkeley/xDevs"
SMOKE_ASSIGNMENT = "lab01"
OUTPUT_DIR = Path("tests/test_files")


# ---------------------------------------------------------------------------
# GitHub auth
# ---------------------------------------------------------------------------

def get_github_token():
    app_id = os.environ.get("GITHUB_APP_ID")
    private_key = os.environ.get("GITHUB_APP_PRIVATE_KEY")
    installation_id = os.environ.get("GITHUB_APP_INSTALLATION_ID")

    if app_id and private_key and installation_id:
        now = int(time.time())
        payload = {"iat": now - 60, "exp": now + 600, "iss": app_id}
        jwt_token = jwt.encode(payload, private_key, algorithm="RS256")
        resp = requests.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        resp.raise_for_status()
        return resp.json()["token"]

    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token

    raise RuntimeError(
        "No GitHub credentials found. Set GITHUB_APP_ID/PRIVATE_KEY/INSTALLATION_ID or GITHUB_TOKEN."
    )


def gh_headers(token):
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}


def gh_get(token, url):
    resp = requests.get(url, headers=gh_headers(token))
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def fetch_dir_files(token, repo, dir_path, ref="main"):
    """Return list of (filename, decoded_bytes) for all files in a repo directory."""
    items = gh_get(token, f"https://api.github.com/repos/{repo}/contents/{dir_path}?ref={ref}")
    if not items:
        return []
    results = []
    for item in items:
        if item["type"] != "file":
            continue
        content_data = gh_get(token, item["url"])
        if content_data is None:
            continue
        decoded = base64.b64decode(content_data["content"])
        results.append((item["name"], decoded))
    return results


def list_tree(token, repo, ref="main"):
    """List all blob paths in repo tree. Returns [] for empty/missing repo."""
    data = gh_get(token, f"https://api.github.com/repos/{repo}/git/trees/{ref}?recursive=1")
    if data is None:
        return []
    return [item["path"] for item in data.get("tree", []) if item["type"] == "blob"]


# ---------------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------------

def save_files(files, dest_dir):
    """Write (filename, bytes) pairs into dest_dir, creating it if needed."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files:
        (dest_dir / name).write_bytes(content)
        print(f"  saved {dest_dir / name}")


# ---------------------------------------------------------------------------
# GitHub fetch path (otter-service, edx-user-image, edx-hub CI)
# ---------------------------------------------------------------------------

def find_assignments_in_student_repo(token, course, smoke=False):
    """
    Return list of (section, assignment) for all notebooks in the student repo.
    Student repo structure: lab/{section}/{assignment}/{assignment}.ipynb
    """
    repo = STUDENT_REPOS.get(course)
    if not repo:
        print(f"  [skip] no student repo configured for {course}")
        return []

    paths = list_tree(token, repo)
    if not paths:
        print(f"  [skip] {repo} is empty or inaccessible")
        return []

    seen = set()
    assignments = []
    for p in paths:
        parts = Path(p).parts
        # expect: lab/{section}/{assignment}/{assignment}.ipynb
        if len(parts) == 4 and parts[0] == "lab" and parts[3].endswith(".ipynb"):
            section, assignment = parts[1], parts[2]
            if smoke and assignment != SMOKE_ASSIGNMENT:
                continue
            if (section, assignment) not in seen:
                seen.add((section, assignment))
                assignments.append((section, assignment))
    return assignments


def fetch_for_course(token, course, smoke=False):
    course_dir = COURSE_DIRS.get(course)
    if not course_dir:
        print(f"  [skip] unknown course {course}")
        return 0

    print(f"\nFetching notebooks for {course}...")
    assignments = find_assignments_in_student_repo(token, course, smoke=smoke)
    if not assignments:
        return 0

    repo_student = STUDENT_REPOS[course]
    count = 0
    for section, assignment in assignments:
        student_dir_path = f"lab/{section}/{assignment}"
        solution_dir_path = f"{course_dir}/solutions/lab/{section}/{assignment}"

        student_files = fetch_dir_files(token, repo_student, student_dir_path)
        if not student_files:
            print(f"  [miss] student {student_dir_path} in {repo_student}")
            continue

        solution_files = fetch_dir_files(token, SOLUTION_REPO, solution_dir_path)
        if not solution_files:
            print(f"  [miss] solution {solution_dir_path} in {SOLUTION_REPO}")
            continue

        # Rename solution notebook from {assignment}-solution.ipynb → {assignment}.ipynb
        # so otter.Notebook("{assignment}.ipynb") finds it when executing
        renamed_solution = []
        for name, content in solution_files:
            if name == f"{assignment}-solution.ipynb":
                name = f"{assignment}.ipynb"
            renamed_solution.append((name, content))

        save_files(student_files, OUTPUT_DIR / course / assignment / "student")
        save_files(renamed_solution, OUTPUT_DIR / course / assignment / "solution")
        count += 1

    return count


# ---------------------------------------------------------------------------
# Local PR path (xDevs CI only)
# ---------------------------------------------------------------------------

def fetch_from_pr(changed_raw_paths):
    """
    After otter assign has run in the xDevs CI workspace, copy the generated
    student/solution files into tests/test_files/.
    """
    count = 0
    for raw_path_str in changed_raw_paths:
        raw_path = Path(raw_path_str)
        if not raw_path.exists():
            print(f"  [skip] {raw_path} not found", file=sys.stderr)
            continue

        nb = nbformat.read(str(raw_path), as_version=4)
        ot = nb.metadata.get("otter_service", {})
        course = str(ot.get("course", "")).strip()
        section = str(ot.get("section", "")).strip()
        assignment = str(ot.get("assignment", "")).strip()

        if not (course and section and assignment):
            print(f"  [skip] {raw_path}: missing otter_service metadata", file=sys.stderr)
            continue

        class_dir = raw_path.parts[0]  # e.g. "88e"
        student_dir = Path(class_dir) / "student" / "lab" / section / assignment
        solution_dir = Path(class_dir) / "solutions" / "lab" / section / assignment

        if not student_dir.exists():
            print(f"  [miss] {student_dir}", file=sys.stderr)
            continue
        if not solution_dir.exists():
            print(f"  [miss] {solution_dir}", file=sys.stderr)
            continue

        out_student = OUTPUT_DIR / course / assignment / "student"
        out_solution = OUTPUT_DIR / course / assignment / "solution"

        if out_student.exists():
            shutil.rmtree(out_student)
        if out_solution.exists():
            shutil.rmtree(out_solution)

        shutil.copytree(student_dir, out_student)

        # Copy solution files, renaming {assignment}-solution.ipynb → {assignment}.ipynb
        out_solution.mkdir(parents=True, exist_ok=True)
        for src in solution_dir.iterdir():
            dest_name = src.name
            if dest_name == f"{assignment}-solution.ipynb":
                dest_name = f"{assignment}.ipynb"
            shutil.copy2(src, out_solution / dest_name)

        print(f"  copied {course}/{assignment} from local workspace")
        count += 1

    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--courses", default="", help="Comma-separated course keys, e.g. 88ex,88bx")
    parser.add_argument("--smoke", action="store_true", help="Only fetch lab01 per course")
    parser.add_argument(
        "--changed-files",
        default="",
        help="Space-separated raw notebook paths (xDevs CI, used with --local)",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Read local workspace files instead of fetching from GitHub (xDevs CI only)",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.local:
        changed = [f for f in args.changed_files.split() if f.endswith(".ipynb")]
        if not changed:
            print("Error: --local requires --changed-files", file=sys.stderr)
            sys.exit(1)
        total = fetch_from_pr(changed)
    else:
        token = get_github_token()
        courses = [c.strip() for c in args.courses.split(",") if c.strip()]
        if not courses:
            print("Error: --courses required unless using --local", file=sys.stderr)
            sys.exit(1)
        total = sum(fetch_for_course(token, c, smoke=args.smoke) for c in courses)

    print(f"\nFetched {total} notebook pair(s) → {OUTPUT_DIR}/")
    if total == 0:
        print("Warning: no notebooks fetched — nothing to test", file=sys.stderr)


if __name__ == "__main__":
    main()
