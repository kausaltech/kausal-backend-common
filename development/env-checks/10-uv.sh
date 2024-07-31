check_uv() {
    echo "📦 Checking for uv..."

    if command -v uv >/dev/null 2>&1; then
        print_success "uv found in PATH"
        echo "  📍 Path: $(command -v uv)"
    else
        print_error "uv not found in PATH"
        echo "It can be installed with running:"
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        read -p "Would you like me to install uv? (Y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            echo "Installing uv..."
            if curl -LsSf https://astral.sh/uv/install.sh | sh; then
                print_success "uv installed successfully"
                echo "  📍 Path: $(command -v uv)"
                # Ensure the current shell can find uv
                export PATH="$HOME/.cargo/bin:$PATH"
            else
                print_error "Failed to install uv"
                return 1
            fi
        else
            print_warning "uv is required but not installed"
            exit 1
        fi
    fi
}

check_uv
