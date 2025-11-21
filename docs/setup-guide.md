# Developer Setup Guide

This guide will help you configure your local environment to work with this repository.

## Prerequisites

- Git installed on your system
- Python 3.12+ with pip

## Quick Setup

Run the setup script from the project root:

```bash
./scripts/setup_commit_config.sh
```

This script will:

1. Configure the git commit template
2. Install the prepare-commit-msg hook (auto-adds Jira references)
3. Install pre-commit and its hooks

## What Gets Installed

### Git Commit Template

When you run `git commit` (without `-m`), a template will guide you through writing properly formatted commit messages following Conventional Commits.

### Pre-commit Hooks

The following checks run automatically before each commit:

- **Black**: Code formatting
- **isort**: Import sorting
- **Flake8**: Linting
- **mypy**: Type checking
- **commitlint**: Commit message validation

Additionally, branch name validation runs before each push to ensure compliance with EGC Flow.

## Branch Naming Convention

Your branches must follow this format:

- `main` - Production releases only
- `trunk` - Integration branch
- `feature/<task>` - New features (e.g., `feature/SCRUM-123`)
- `bugfix/<task>` - Bug fixes
- `hotfix/<task>` - Urgent production fixes

## Commit Message Format

```
<type>(<scope>): <subject>

[optional body]

Refs: SCRUM-XX
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## Troubleshooting

### pre-commit not found

If you get "command not found" after running the script, ensure pip's bin directory is in your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Hooks not running

Verify hooks are installed:

```bash
pre-commit install --install-hooks
pre-commit install --hook-type commit-msg
pre-commit install --hook-type pre-push
```
