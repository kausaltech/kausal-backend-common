# shellcheck shell=bash

check_uv() {
    print_check "Checking for uv..." "📦"
    local find_uv="command -v uv"
    if $find_uv >/dev/null 2>&1; then
        print_success "uv found in PATH"
        print_findings "Path" "$(find_uv)"
        return
    fi

    print_error "uv not found in PATH"
    echo "It can be installed with running:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo
    if ! prompt_user "Would you like me to install uv?"; then
        print_error "uv is required but not installed"
        exit 1
    fi

    echo "Installing uv..."
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        print_success "uv installed successfully"
        hash -r 2>/dev/null
        if ! $find_uv >/dev/null 2>&1; then
            print_error "uv installed, but not found in PATH. Please configure your shell according to the instructions above, and restart your terminal."
            exit 1
        fi
        echo "  📍 Path: $find_uv"
    else
        print_error "Failed to install uv"
        exit 1
    fi
}

check_uv
