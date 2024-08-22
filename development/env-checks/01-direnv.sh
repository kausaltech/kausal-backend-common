# shellcheck shell=bash

direnv_hook_instructions_fail() {
    echo -e "${BLUE}ℹ️ To complete direnv setup, you need to add direnv initialization to your shell.${NC}"
    echo -e "${BLUE}   Please visit the following link for instructions:${NC}"
    echo -e "${GREEN}   https://direnv.net/docs/hook.html ${NC}"
    echo -e "${BLUE}   After adding the hook, restart your shell or source your shell configuration file.${NC}"
    exit 1
}

check_direnv() {
    print_check "Checking for direnv..." "🔄"
    find_direnv="command -v direnv"
    if $find_direnv >/dev/null 2>&1; then
        print_success "direnv found in PATH"
        print_findings "Path" "$($find_direnv)"
        return
    else
        print_error "direnv not found in PATH"
        print "It can be installed with:\n    curl -sfL https://direnv.net/install.sh | bash"
        if prompt_user "Would you like me to install direnv"; then
            echo "Installing direnv..."
            if curl -sfL https://direnv.net/install.sh | bash; then
                print_success "direnv installed successfully"
                hash -r
                if ! $find_direnv >/dev/null 2>&1; then
                    direnv_hook_instructions_fail
                fi
                print_findings "Path" "$($find_direnv)"
            else
                print_error "Failed to install direnv"
                exit 1
            fi
        else
            print_error "direnv is required but not installed"
            exit 1
        fi
    fi
}

DIRENV_UV_LAYOUT="$(cat << 'EOF'
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
)"

check_direnv_lib() {
    print_check "Checking for direnv library file" "⚙️"

    local direnv_lib="$HOME/.config/direnv/lib/python-uv.sh"

    if [[ -f "$direnv_lib" ]]; then
        print_success "$direnv_lib exists"
    else
        print_warning "$direnv_lib does not exist"

        # Prompt user to create the file and add the function
        if prompt_user "Would you like to create $direnv_lib and add the layout_python-uv function?" ; then
            mkdir -p $(dirname "$direnv_lib")
            echo "$DIRENV_UV_LAYOUT" > "$direnv_lib"
            # shellcheck disable=SC2320 disable=SC2181
            if [[ $? -eq 0 ]]; then
                print_success "$direnv_lib created with layout_python-uv function"
            else
                print_error "Failed to create $direnv_lib"
                exit 1
            fi
        else
            print_error "$direnv_lib not created; you'll need to set it up yourself"
            exit 1
        fi
    fi

    return 0
}

check_direnv
check_direnv_lib
