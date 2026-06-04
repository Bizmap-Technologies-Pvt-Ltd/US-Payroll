# Before You Commit — US Payroll

Quick checklist every developer must follow before pushing code. Takes ~1 minute.

## One-time setup

```bash
cd apps/us_payroll
uvx pre-commit install        # auto-runs ruff + eslint on every `git commit`
```
> No `uvx`? Install it: `curl -LsSf https://astral.sh/uv/install.sh | sh`
> Or use pip: `pip install pre-commit ruff==0.8.1 semgrep` and drop the `uvx` prefix below.

## Every commit (must pass)

```bash
cd apps/us_payroll
uvx pre-commit run --all-files
```
This runs ruff (import sort + lint + format), eslint, prettier, and file checks.
Fix anything it reports. Most style issues auto-fix — just re-add and commit.

## Before opening a PR (must pass)

Pre-commit does NOT run semgrep. Run it manually — this catches SQL injection,
missing type hints, manual commits, and missing translations:

```bash
git clone --depth 1 https://github.com/frappe/semgrep-rules.git /tmp/frappe-semgrep-rules
uvx semgrep scan --config /tmp/frappe-semgrep-rules/rules --metrics=off
```

Then run the tests (from the bench root):

```bash
bench --site <test-site> run-tests --app us_payroll
```

## Hard rules (these fail CI — don't introduce them)

- **No f-strings / `.format()` inside `frappe.db.sql()`** — use `%s` / `%(name)s` params. (SQL injection)
- **Every `@frappe.whitelist()` argument needs a type hint** (`doc: str`, `year: int`). Add `methods=["POST"]` to anything that writes.
- **No `frappe.db.commit()`** in controllers or request handlers — Frappe auto-commits.
- **No `frappe.db.set_value`** on status/validated fields — load the doc and `save()`.
- **Wrap all user-facing text** in `_()` (Python) / `__()` (JS).
- **No `cur_frm` / `$c_obj`** or other deprecated globals; declare JS globals you use.
- **No `print()`** in committed code — use `frappe.logger()` if needed.

## Commit message format

Conventional Commits: `feat:`, `fix:`, `refactor:`, `chore:` …
Example: `fix: add missing now_datetime import in payroll_entry`

---
CI (`.github/workflows/linter.yml` + `ci.yml`) runs pre-commit, semgrep, pip-audit,
and the server tests on every PR. Green locally = green in CI.
