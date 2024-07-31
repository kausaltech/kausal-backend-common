check_direnvrc() {
    echo "🔍 Checking for direnv configuration..."

    local direnvrc="$HOME/.direnvrc"
    local function_name="layout_python-uv"

    local function_content=$(cat << 'EOF'
layout_python-uv() {
    local python=${1:-python3}
    [[ $# -gt 0 ]] && shift
    unset PYTHONHOME
    if [[ -n $VIRTUAL_ENV ]]; then
        VIRTUAL_ENV=$(realpath "${VIRTUAL_ENV}")
    else
        local python_version
        python_version=$("$python" -c "import platform; print(platform.python_version())")
        if [[ -z $python_version ]]; then
            log_error "Could not detect Python version"
            return 1
        fi
        VIRTUAL_ENV=$PWD/.direnv/python-venv-$python_version
    fi
    export VIRTUAL_ENV
    if [[ ! -d $VIRTUAL_ENV ]]; then
        log_status "no venv found; creating $VIRTUAL_ENV"
        uv venv "$VIRTUAL_ENV"
        echo '!*' > "$VIRTUAL_ENV"/lib/python*/site-packages/.rgignore
    fi
    PATH="${VIRTUAL_ENV}/bin:${PATH}"
    export PATH
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

check_direnvrc

