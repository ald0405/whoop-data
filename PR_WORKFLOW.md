# Pull Request Workflow Guide

## 🚀 Quick Start

### Option 1: Automated PR Creation (Recommended)
```bash
# Run the automated PR helper script
./scripts/create_pr.sh
```

This script will:
1. Detect uncommitted changes
2. Help you create a proper commit message
3. Push to remote
4. Create a PR with automated changelog
5. Open the PR in your browser

### Option 2: Manual Process

#### Step 1: Commit Your Changes

```bash
# Stage your changes
git add .

# Create a commit (will open template)
git commit

# Or use the quick format
git commit -m "✨ feat: Add new feature description"
```

#### Step 2: Push to Remote

```bash
git push -u origin your-branch-name
```

#### Step 3: Create PR Using GitHub CLI

```bash
# Basic PR
gh pr create --title "Your PR Title" --body "Description"

# Or interactive mode
gh pr create
```

## 📝 Commit Message Format

We follow **Conventional Commits** with emojis:

```
<emoji> <type>: <subject>

<optional body>

<optional footer>
```

### Types & Emojis

| Type | Emoji | Description | Example |
|------|-------|-------------|---------|
| `feat` | ✨ | New feature | `✨ feat: Add weight trend visualization` |
| `fix` | 🐛 | Bug fix | `🐛 fix: Resolve API authentication error` |
| `docs` | 📚 | Documentation | `📚 docs: Update API endpoint documentation` |
| `test` | 🧪 | Testing | `🧪 test: Add unit tests for workout API` |
| `refactor` | 🧹 | Refactoring | `🧹 refactor: Clean up database queries` |
| `chore` | 🔧 | Maintenance | `🔧 chore: Update dependencies` |
| `ci` | 💚 | CI/CD | `💚 ci: Add automated release notes workflow` |
| `perf` | ⚡ | Performance | `⚡ perf: Optimize database queries` |
| `style` | 💄 | Code style | `💄 style: Format code with black` |
| `revert` | ⏪ | Revert | `⏪ revert: Undo breaking changes` |

### Commit Examples

**Good commits:**
```bash
✨ feat: Add automated system verification script

Added verify_system.py to test all components (imports, database, API, agent)
- Tests database connectivity and data presence
- Validates environment variables
- Verifies agent functionality
- Checks API route definitions

Helps users quickly verify their setup after installation or changes.
```

```bash
🐛 fix: Resolve WHOOP 2025 data query issue

Fixed date filtering and ordering in workout CRUD queries.
The agent was unable to access 2025 workout data due to missing
ORDER BY clause and date filter support.
```

**Bad commits:**
```bash
update stuff
fixed bug
changes
wip
```

## 🔄 Automated Release Notes

When you create a PR to `main`, the GitHub Action will automatically:

1. **Scan your commits** and categorize them:
   - ✨ Features
   - 🐛 Bug Fixes
   - 📚 Documentation
   - 🧹 Refactoring
   - 🧪 Testing
   - 🔧 Maintenance

2. **Post a comment** on your PR with the changelog

3. **Update the comment** when you push more commits

### Example Generated Changelog

```markdown
## 📝 Changes in this PR

### ✨ Features
- ✨ feat: Add automated system verification script
- ✨ feat: Add comprehensive testing guide

### 🐛 Bug Fixes
- 🐛 fix: Resolve WHOOP 2025 data query issue

### 📚 Documentation
- 📚 docs: Update README with new verification steps

### 📦 All Commits
- ✨ feat: Add automated system verification script
- 📚 docs: Create comprehensive testing guide
- 🐛 fix: Resolve WHOOP 2025 data query issue
- 📚 docs: Update README with verification steps
```

## 🔍 PR Review Checklist

Before submitting your PR, ensure:

- [ ] **Code Quality**
  - [ ] Follows existing code style
  - [ ] No unnecessary commented code
  - [ ] Complex logic is commented
  
- [ ] **Testing**
  - [ ] Ran `python verify_system.py`
  - [ ] Tested locally with real data
  - [ ] Verified API endpoints work
  - [ ] Verified chat interface works
  - [ ] Verified ETL pipeline works

- [ ] **Documentation**
  - [ ] Updated README if needed
  - [ ] Updated API docs if endpoints changed
  - [ ] Updated TESTING_GUIDE if test procedures changed
  
- [ ] **Git**
  - [ ] Meaningful commit messages
  - [ ] Branch name describes the change
  - [ ] No merge conflicts

## 🌿 Branch Naming

Use descriptive branch names:

```bash
feat/add-weight-visualization
fix/whoop-auth-error
docs/update-api-guide
refactor/clean-database-layer
test/add-integration-tests
chore/update-dependencies
```

## 📦 Creating a Release

When you're ready to create a release:

```bash
# Tag your release
git tag -a v1.0.0 -m "Release v1.0.0: Initial public release"

# Push the tag
git push origin v1.0.0

# Create GitHub release
gh release create v1.0.0 --title "v1.0.0" --generate-notes
```

The release notes workflow will automatically generate changelog from commits between tags.

## 🛠️ GitHub CLI Setup

If you don't have GitHub CLI installed:

```bash
# macOS
brew install gh

# Authenticate
gh auth login

# Verify
gh auth status
```

## 💡 Tips

1. **Commit often**: Small, focused commits are better than large ones
2. **Be descriptive**: Write commit messages for your future self
3. **Use the template**: Run `git commit` (no `-m`) to use the full template
4. **Test before pushing**: Run `verify_system.py` to catch issues early
5. **Use the script**: `./scripts/create_pr.sh` automates the tedious parts

## 🚨 Common Issues

### "gh: command not found"
Install GitHub CLI: `brew install gh`

### "Failed to authenticate"
Run: `gh auth login` and follow prompts

### "Your branch is behind 'origin/main'"
```bash
git fetch origin
git rebase origin/main
```

### "merge conflicts"
```bash
git fetch origin
git rebase origin/main
# Resolve conflicts
git rebase --continue
```

## 📚 Resources

- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub CLI Documentation](https://cli.github.com/manual/)
- [Git Branching Best Practices](https://git-scm.com/book/en/v2/Git-Branching-Branching-Workflows)
