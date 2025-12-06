# Continuous Integration

This document describes the Continuous Integration (CI) pipeline for Track Hub 1, covering both local validation with pre-commit hooks and remote validation with GitHub Actions workflows.

## Table of Contents

- [Local Validation (Pre-commit)](#local-validation-pre-commit)
- [Remote Validation (GitHub Actions)](#remote-validation-github-actions)
- [CI Gate](#ci-gate)
- [Configuration Files](#configuration-files)

---

## Local Validation (Pre-commit)

Pre-commit hooks run automatically before each commit and push, ensuring code quality before it reaches the remote repository.

### Installation

Pre-commit hooks are installed automatically during initial setup. See [Developer Setup Guide](setup-guide.md#initial-setup) for installation instructions.

### Hook Stages

#### Pre-commit Stage (Before Commit)

Runs before every `git commit`:

1. **Trailing Whitespace Removal**
   - Removes trailing whitespace at end of lines

2. **End of File Fixer**
   - Ensures files end with a newline

3. **YAML Validation**
   - Validates syntax of YAML files

4. **Large File Check**
   - Prevents files larger than 500KB from being committed

5. **Merge Conflict Check**
   - Detects unresolved merge conflict markers

6. **Branch Protection**
   - Prevents direct commits to `main` and `trunk` branches

7. **Black Formatter**
   - Formats Python code (line length: 120 characters)
   - Applies to `app/` and `rosemary/` directories

8. **isort Import Sorter**
   - Sorts Python imports alphabetically
   - Profile: black-compatible

9. **Flake8 Linter**
   - Validates PEP8 compliance
   - Max line length: 120
   - Ignores: E203, W503

10. **mypy Type Checker**
    - Performs static type checking on Python code

#### Commit-msg Stage (After Commit Message)

Runs after the commit message is written:

1. **Commitlint**
   - Validates commit messages follow Conventional Commits format
   - Ensures proper structure: `<type>(<scope>): <subject>`
   - Configuration: `.commitlintrc.yaml`

#### Pre-push Stage (Before Push)

Runs before `git push`:

1. **Branch Name Validation**
   - Ensures branch follows EGC Flow naming convention
   - Valid patterns:
     - `main`
     - `trunk`
     - `feature/<task>`
     - `bugfix/<task>`
     - `hotfix/<task>`

### Bypassing Hooks (Not Recommended)

While hooks can be bypassed with `--no-verify`, this is strongly discouraged as it defeats the purpose of automated quality checks and may cause CI failures.

---

## Remote Validation (GitHub Actions)

GitHub Actions workflows provide automated validation on every push to any branch. The pipeline consists of multiple stages that run in parallel.

### Stage 1: Commit Validation

**Workflow**: `CI_commits.yml`

**Purpose**: Validates commit messages and branch names

**Checks**:
- Branch name follows EGC Flow convention
- Commit messages follow Conventional Commits specification

**Configuration**:
- `.commitlintrc.yaml` (commit message rules)

### Stage 2: Code Quality

**Workflow**: `CI_lint.yml`

**Purpose**: Ensures code formatting and style compliance

**Checks**:
1. **Black**: Code formatting verification (line length: 120)
2. **isort**: Import order verification (black profile)
3. **Flake8**: PEP8 linting (max line length: 120, ignores E203/W503)

**Target directories**: `app/`, `rosemary/`

### Stage 3: Testing

**Workflow**: `CI_pytest.yml`

**Purpose**: Runs automated tests with coverage analysis

**Feature Branches**:
- Runs all pytest tests (excluding Selenium)
- No coverage requirements

**Trunk/Main Branches**:
- Runs tests with coverage analysis
- Minimum coverage: 50%
- Generates coverage reports (XML, HTML, terminal)
- Uploads coverage to Codecov
- Publishes test results summary

**Artifacts** (trunk/main only):
- `coverage.xml`
- `htmlcov/` (HTML coverage report)
- `pytest-report.xml`
- Retention: 30 days

### Stage 4: Security

**Workflow**: `CI_security.yml`

**Purpose**: Scans for security vulnerabilities

**Jobs**:

1. **Dependency Vulnerability Scan** (all branches)
   - Tool: pip-audit
   - Scans Python dependencies for known vulnerabilities
   - Reports findings but does not block pipeline
   - Uploads JSON report as artifact

2. **SAST Security Scan** (all branches)
   - Tool: Bandit
   - Static Application Security Testing
   - Scans `app/`, `rosemary/`, `core/` directories
   - Uploads findings to GitHub Security tab (SARIF format)
   - Reports findings but does not block pipeline

3. **OWASP Dependency Check** (trunk/main only)
   - Comprehensive dependency vulnerability analysis
   - Uploads reports as artifacts
   - Reports findings but does not block pipeline

4. **Secret Scanning** (trunk/main only)
   - Tool: TruffleHog
   - Scans for exposed secrets in code
   - Only reports verified secrets

### SonarCloud Analysis

**Workflow**: `CI_sonar.yml`

**Purpose**: Performs static code analysis and quality metrics

**Trigger**:
- Runs after Stage 3 (Testing) completes successfully
- Only on `main` branch
- Triggered by workflow completion event

**Functionality**:
- Downloads coverage artifacts from testing workflow
- Performs SonarCloud static analysis
- Uses coverage data from pytest

> **Note**: Sonar and Codecov coverage may vary due to different analysis methods

### CI Gate

**Workflow**: `CI_gate.yml`

**Purpose**: Single required status check for branch protection

**Functionality**:
- Waits for all CI stages to complete
- Requires all checks to pass:
  - Commit validation
  - Code quality
  - Testing
  - Dependency vulnerability scan
- Provides single approval point for merges

**Note**: This is the only workflow configured as a required status check in GitHub branch protection rules.

---

## Configuration Files

The CI pipeline relies on the following configuration files:

| File | Purpose |
|------|---------|
| `.pre-commit-config.yaml` | Pre-commit hooks configuration |
| `.commitlintrc.yaml` | Commit message validation rules |
| `pyproject.toml` | Python tooling configuration (Black, isort, Flake8) |
| `.github/workflows/CI_*.yml` | GitHub Actions CI workflows |
| `.github/workflows/CI_gate.yml` | CI gate workflow (required check) |

---

## Workflow Summary

```
Local Development
├── git commit
│   ├── Pre-commit hooks (formatting, linting, type checking)
│   └── Commit-msg hook (message validation)
└── git push
    └── Pre-push hook (branch name validation)

Remote CI (GitHub Actions)
├── Stage 1: Commit Validation (branch names, commit messages)
├── Stage 2: Code Quality (Black, isort, Flake8)
├── Stage 3: Testing (pytest with coverage)
├── Stage 4: Security (pip-audit, Bandit, OWASP, TruffleHog)
├── CI Gate (waits for all stages, required check)
└── SonarCloud Analysis (after tests on main branch)
```

---

## Best Practices

1. **Always run pre-commit hooks**: They catch issues early and prevent CI failures
2. **Monitor security reports**: Review artifact reports from security scans
3. **Follow naming conventions**: Use proper branch names and commit message formats
4. **Review CI failures promptly**: Fix issues immediately to unblock merges
