check_direnv() {
    echo "🔍 Checking for direnv..."

    if command -v direnv >/dev/null 2>&1; then
        print_success "direnv found in PATH"
        echo "  📍 Path: $(command -v direnv)"
        return
    else
        print_error "direnv not found in PATH"
        read -p "Would you like to install direnv? (Y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            echo "Installing direnv..."
            if curl -sfL https://direnv.net/install.sh | bash; then
                print_success "direnv installed successfully"
                echo "  📍 Path: $(command -v direnv)"
            else
                print_error "Failed to install direnv"
                exit 1
            fi
        else
            print_warning "direnv is required but not installed"
            exit 1
        fi
    fi

    echo -e "${BLUE}ℹ️ To complete direnv setup, you need to add a hook to your shell.${NC}"
    echo -e "${BLUE}   Please visit the following link for instructions:${NC}"
    echo -e "${GREEN}   https://direnv.net/docs/hook.html${NC}"
    echo -e "${BLUE}   After adding the hook, restart your shell or source your shell configuration file.${NC}"

    read -p "Have you installed the direnv hook? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "direnv hook not installed. Please install it and run this script again."
        exit 1
    fi
}

check_direnvrc() {
    echo "🔍 Checking for direnv configuration..."

    local direnvrc="$HOME/.direnvrc"
    local function_name="layout_python-uv"

    local function_content=$(cat << 'EOF'
layout_python-uv() {
    [[ $# -gt 0 ]] && shift

    VIRTUAL_ENV=$PWD/.venv
    if [[ ! -d $VIRTUAL_ENV ]]; then
        log_status "no venv found; creating $VIRTUAL_ENV"
        uv venv "$VIRTUAL_ENV"
    fi

    SPS="$VIRTUAL_ENV"/lib/python*/site-packages
    for SP in $SPS; do
        if [ -d "$SP" ]; then
            RGIGNORE_FILE="$SP/.rgignore"
            if [ ! -f "$RGIGNORE_FILE" ]; then
                log_status "Creating .rgignore file in $SP"
                echo '!*' > "$RGIGNORE_FILE"
            fi
        fi
    done

    source "${VIRTUAL_ENV}/bin/activate"
}
EOF
    )

    # Check if $HOME/.direnvrc exists
    if [[ -f "$direnvrc" ]]; then
        print_success "$direnvrc exists"

        # Check if layout_python-uv function is present
        if grep -q "$function_name" "$direnvrc"; then
            print_success "layout_python-uv function found in $direnvrc"
        else
            print_warning "layout_python-uv function not found in $direnvrc"

            # Prompt user to add the function
            read -p "Would you like to add the layout_python-uv function to $direnvrc? (Y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                echo "$function_content" >> "$direnvrc"
                if [[ $? -eq 0 ]]; then
                    print_success "layout_python-uv function added to $direnvrc"
                else
                    print_error "Failed to add layout_python-uv function to $direnvrc"
                    return 1
                fi
            else
                print_warning "layout_python-uv function not added to $direnvrc"
            fi
        fi
    else
        print_warning "$direnvrc does not exist"

        # Prompt user to create the file and add the function
        read -p "Would you like to create $direnvrc and add the layout_python-uv function? (Y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            echo "$function_content" > "$direnvrc"
            if [[ $? -eq 0 ]]; then
                print_success "$direnvrc created with layout_python-uv function"
            else
                print_error "Failed to create $direnvrc"
                return 1
            fi
        else
            print_warning "$direnvrc not created"
        fi
    fi

    return 0
}

check_direnv
check_direnvrc
