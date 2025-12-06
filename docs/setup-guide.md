# Developer Setup Guide

This guide will help you configure your local environment to work with this repository.

## Prerequisites

- Git installed on your system
- Python 3.12+ with pip

## Initial Setup

Run the setup script from the project root:

```bash
./scripts/setup_commit_config.sh
```

This script installs:
1. Git commit template
2. Prepare-commit-msg hook (auto-adds Jira references)
3. Pre-commit hooks for code quality validation

## Next Steps

After running the setup script, familiarize yourself with:

- **[Branching and Commit Strategy](branching-strategy.md)**: Branch naming conventions, commit message format, and template usage
- **[Continuous Integration](ci.md)**: Local pre-commit hooks and remote CI workflows

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
