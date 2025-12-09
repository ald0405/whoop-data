#!/bin/bash
# Helper script to create a PR with proper formatting

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 PR Creation Helper${NC}"
echo "================================"

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI (gh) is not installed${NC}"
    echo "Install it with: brew install gh"
    exit 1
fi

# Check if user is authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not authenticated with GitHub${NC}"
    echo "Run: gh auth login"
    exit 1
fi

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${GREEN}✓${NC} Current branch: ${CURRENT_BRANCH}"

# Check if there are uncommitted changes
if [[ -n $(git status --porcelain) ]]; then
    echo -e "${YELLOW}⚠️  You have uncommitted changes:${NC}"
    git status --short
    echo ""
    read -p "Do you want to commit these changes? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Show commit message template
        echo -e "${BLUE}📝 Creating commit...${NC}"
        git add -A
        
        # Prompt for commit type
        echo ""
        echo "Select commit type:"
        echo "  1) feat     - New feature"
        echo "  2) fix      - Bug fix"
        echo "  3) docs     - Documentation"
        echo "  4) test     - Testing"
        echo "  5) refactor - Code refactoring"
        echo "  6) chore    - Maintenance"
        echo "  7) ci       - CI/CD changes"
        read -p "Enter number (1-7): " commit_type
        
        case $commit_type in
            1) TYPE="feat" EMOJI="✨";;
            2) TYPE="fix" EMOJI="🐛";;
            3) TYPE="docs" EMOJI="📚";;
            4) TYPE="test" EMOJI="🧪";;
            5) TYPE="refactor" EMOJI="🧹";;
            6) TYPE="chore" EMOJI="🔧";;
            7) TYPE="ci" EMOJI="💚";;
            *) TYPE="chore" EMOJI="🔧";;
        esac
        
        read -p "Enter commit subject: " subject
        read -p "Enter commit body (optional, press Enter to skip): " body
        
        # Create commit message
        COMMIT_MSG="${EMOJI} ${TYPE}: ${subject}"
        if [[ -n "$body" ]]; then
            COMMIT_MSG="${COMMIT_MSG}\n\n${body}"
        fi
        
        echo -e "$COMMIT_MSG" | git commit -F -
        echo -e "${GREEN}✓${NC} Changes committed"
    else
        echo "Exiting..."
        exit 1
    fi
fi

# Push current branch
echo -e "${BLUE}⬆️  Pushing to remote...${NC}"
git push -u origin "$CURRENT_BRANCH"
echo -e "${GREEN}✓${NC} Pushed to origin/${CURRENT_BRANCH}"

# Create PR
echo ""
echo -e "${BLUE}📋 Creating Pull Request${NC}"
echo "================================"

read -p "PR title (press Enter to use last commit message): " pr_title
if [[ -z "$pr_title" ]]; then
    pr_title=$(git log -1 --pretty=%s)
fi

read -p "Target branch (default: main): " base_branch
base_branch=${base_branch:-main}

echo ""
echo "PR Preview:"
echo "  Title: $pr_title"
echo "  From: $CURRENT_BRANCH"
echo "  To: $base_branch"
echo ""

read -p "Create this PR? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Generate PR body from commits
    PR_BODY="## Changes\n\n"
    PR_BODY+="### Commits in this PR:\n"
    PR_BODY+=$(git log origin/${base_branch}..HEAD --oneline | sed 's/^/- /')
    PR_BODY+="\n\n---\n"
    PR_BODY+="**Testing:**\n"
    PR_BODY+="- [ ] Tested locally\n"
    PR_BODY+="- [ ] Verified API endpoints work\n"
    PR_BODY+="- [ ] Verified chat interface works\n"
    PR_BODY+="- [ ] Verified ETL pipeline works\n"
    
    # Create PR
    PR_URL=$(gh pr create \
        --title "$pr_title" \
        --body "$PR_BODY" \
        --base "$base_branch" \
        --head "$CURRENT_BRANCH")
    
    echo -e "${GREEN}✓${NC} Pull Request created!"
    echo -e "${BLUE}🔗 ${PR_URL}${NC}"
    
    # Open in browser
    read -p "Open PR in browser? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open "$PR_URL" 2>/dev/null || xdg-open "$PR_URL" 2>/dev/null || echo "URL: $PR_URL"
    fi
else
    echo "PR creation cancelled"
    exit 0
fi

echo ""
echo -e "${GREEN}✅ All done!${NC}"
