# shellcheck shell=bash

check_reviewdog() {
    print_check "Checking for reviewdog..." "🐶"

    # Check if reviewdog exists in ./bin
    if [ -x "./bin/reviewdog" ]; then
        print_success "reviewdog found in ./bin"
        print_findings "Path" "./bin/reviewdog"
        return 0
    fi

    # Check if reviewdog exists in PATH
    if command -v reviewdog >/dev/null 2>&1; then
        print_success "reviewdog found in PATH"
        print_findings "Path" "$(command -v reviewdog)"
        return 0
    fi

    # If we get here, reviewdog was not found
    print_error "reviewdog not found in ./bin or in PATH"

    # Prompt user to install reviewdog, defaulting to yes
    if prompt_user "Would you like to install reviewdog?" ; then
        echo "Installing reviewdog..."
        if curl -sfL https://raw.githubusercontent.com/reviewdog/reviewdog/master/install.sh | sh -s; then
            print_success "reviewdog installed successfully"
            echo "  📍 Path: $(command -v reviewdog)"
            return 0
        else
            print_error "Failed to install reviewdog"
            return 1
        fi
    else
        print_error "reviewdog is required but not installed"
        return 1
    fi
}

check_git_hooks() {
    echo "🔗 Checking git hooks..."

    # Check if pre-commit is available
    if ! command -v pre-commit >/dev/null 2>&1; then
        print_error "pre-commit is not installed"
        return 1
    fi

    # Check if .git directory exists (we're in a git repository)
    if [ ! -d ".git" ]; then
        print_error "Not in a git repository"
        return 1
    fi

    # Check if pre-commit hooks are installed
    if pre-commit install --install-hooks >/dev/null; then
        print_success "Git hooks are properly installed"
    else
        print_error "Error running pre-commit"
        return 1
    fi

    return 0
}

check_reviewdog
check_git_hooks
