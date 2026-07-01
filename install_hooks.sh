#!/bin/bash
# Install the kit's pre-commit hook into .git/hooks/ and the Claude Code
# hooks into .claude/settings.json.
# Run this once per cloned project.

set -e

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

if [ ! -d ".git" ]; then
    echo "Not a git repo. Run 'git init' first."
    exit 1
fi

cp .git-hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

echo "Pre-commit hook installed."
echo "Now every 'git commit' will run preflight, tests, and coverage check."
echo "To bypass for a single commit (use sparingly): git commit --no-verify"

# v3.3: install the Claude Code hooks (SessionStart compliance block,
# PreToolUse accepted-ADR guard). Never overwrite an existing settings.json
# -- the user may have project-specific hooks already; merge by hand then.
if [ -f "claude-settings.template.json" ]; then
    if [ -f ".claude/settings.json" ]; then
        echo ""
        echo ".claude/settings.json already exists -- NOT overwritten."
        echo "Merge the hooks from claude-settings.template.json by hand."
    else
        mkdir -p .claude
        cp claude-settings.template.json .claude/settings.json
        echo ""
        echo "Claude Code hooks installed to .claude/settings.json:"
        echo "  SessionStart -> python preflight.py --compliance"
        echo "  PreToolUse   -> python scripts/hooks/protect_adrs.py (accepted-ADR guard)"
    fi

    # v3.3: the hook commands default to 'python'. On Windows installs where
    # 'python' is the Microsoft Store stub and only 'py' works (the same
    # friction the pre-commit hook handles), patch the commands to the
    # detected interpreter.
    PYTHON_CMD=""
    for candidate in python3 python py; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" --version >/dev/null 2>&1; then
                PYTHON_CMD="$candidate"
                break
            fi
        fi
    done
    if [ -n "$PYTHON_CMD" ] && [ "$PYTHON_CMD" != "python" ] && [ -f ".claude/settings.json" ]; then
        sed -i.bak "s/\"python /\"$PYTHON_CMD /g" .claude/settings.json
        rm -f .claude/settings.json.bak
        echo "Claude Code hook commands patched to use '$PYTHON_CMD'."
    fi
fi
