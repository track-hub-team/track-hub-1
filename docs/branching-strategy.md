# Branching and Commit Strategy

This document describes the Git workflow and commit conventions used in the Track Hub project.

## Git Workflow: EGC Flow

We follow **EGC Flow**, an adapted version of Git Flow taught in the EGC (Evolución y Gestión de la Configuración) course.

### Branch Structure

```
main (production)
  └── trunk (integration)
       ├── feature/SCRUM-XX (new features)
       ├── bugfix/SCRUM-XX (bug fixes)
       └── hotfix/SCRUM-XX (urgent fixes)
```

### Branch Types

| Branch Type | Naming Pattern | Purpose | Base Branch | Merge To |
|-------------|---------------|---------|-------------|----------|
| `main` | `main` | Production releases only | - | - |
| `trunk` | `trunk` | Integration branch | `main` | `main` |
| `feature/<task>` | `feature/SCRUM-123` | New features and enhancements | `trunk` | `trunk` |
| `bugfix/<task>` | `bugfix/SCRUM-45` | Bug fixes identified during development | `trunk` | `trunk` |
| `hotfix/<task>` | `hotfix/SCRUM-99` | Urgent production fixes | `main` | `main` + `trunk` |

### Branch Creation from Jira

**Recommended Process**:
1. Open the Jira task/subtask
2. Click "Create Branch" in Jira
3. Add one of the approved prefixes: `feature/`, `bugfix/`, or `hotfix/`
4. Jira automatically appends the task ID

**Example**:
- Jira task: `SCRUM-44`
- Branch created: `feature/SCRUM-44-Revision-general-de-la-funcionalidad`

---

## Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/) with a required footer reference.

### Structure

```
<type>(<scope>): <subject>

[optional body]

Refs: SCRUM-XX
```

### Components

#### 1. Type (Required)

| Type | Usage | Example |
|------|-------|---------|
| `feat` | New feature | `feat(community): add curator management` |
| `fix` | Bug fix | `fix(auth): resolve login redirect issue` |
| `docs` | Documentation | `docs: update community features guide` |
| `style` | Code style (formatting, missing semicolons) | `style(routes): format with black` |
| `refactor` | Code refactoring | `refactor(services): extract validation logic` |
| `test` | Adding or updating tests | `test(community): add selenium curator test` |
| `chore` | Maintenance tasks | `chore: update dependencies` |

#### 2. Scope (Optional)

The scope indicates which module or component is affected:
- `community`, `auth`, `dataset`, `profile`
- Can be omitted for cross-cutting changes

#### 3. Subject (Required)

**Rules**:
- Must be **lowercase**
- No period at the end
- Max **100 characters** for the entire header
- Use imperative mood

#### 4. Body (Optional)

- Separated from subject by a blank line
- Explain **what** and **why**, not **how**
- Wrap at 72 characters

#### 5. Footer (Required)

- **Must** include task reference: `Refs: SCRUM-XX`
- Auto-populated by commit template (see below)

### Complete Example

```
feat(community): add curator search functionality

Implement real-time user search for adding curators to communities.
Includes autocomplete with name and email filtering.

Refs: SCRUM-44
```

---

## Commit Template & Automation

### Initial Setup

Initial setup instructions are detailed in the [Developer Guide](../README.md#initial-setup).

### How the Template Works

When you create a commit:

1. **Git opens your editor** with the template:
   ```
   <type>(<scope>): <subject>

   [optional body]

   Refs: SCRUM-XX
   ```

2. **The hook auto-fills** the footer based on your branch:
   - Branch: `feature/SCRUM-44-communities`
   - Auto-filled: `Refs: SCRUM-44`

3. **You only replace** the `<type>(<scope>): <subject>` line and the optional body

### Example Workflow

```bash
# 1. Create branch from Jira
git checkout -b feature/SCRUM-44-add-communities

# 2. Make changes
# ... edit files ...

# 3. Stage changes
git add app/modules/community/

# 4. Commit (template opens)
git commit

# 5. Replace the template line:
#    FROM: <type>(<scope>): <subject>
#    TO:   feat(community): add community creation endpoint

# 6. Footer is already filled:
#    Refs: SCRUM-44
```

---

## Pull Requests

Our team does **not use pull requests for development**. This tool is only used to integrate changes with the track-hub-2 team. If a pull request is opened and cannot be merged due to synchronization or other issues, the pull request must be marked as [DEPRECATED].

---

## Best Practices

### ✅ Do

- **Commit often** with focused changes
- **Rebase before merging** to keep history clean if necessary
- **Reference the Jira task** in every commit footer
- **Run tests** before pushing
- **Keep branches short-lived**

### ❌ Don't

- **Don't commit directly to `trunk` or `main`** (although it shouldn't work)
- **Don't use `git commit -m`** (bypasses the template)
- **Don't mix multiple features** in one commit
