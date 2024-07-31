ensure_python_available() {
    local required_version="$1"
    local available_versions

    echo "🔍 Checking for Python $required_version availability..."

    # Get the list of installed Python versions
    available_versions=$(uv python list --only-installed | grep '^cpython-' | awk '{print $1}' | cut -d'-' -f2)

    # Check if the required version is available
    if echo "$available_versions" | grep -q "^$required_version"; then
        print_success "Python $required_version is available"
        return 0
    fi

    # If not found, try to find a compatible version
    for version in $available_versions; do
        if [[ "$version" == "$required_version"* ]]; then
            print_success "Compatible Python version $version is available"
            return 0
        fi
    done

    print_warning "Python $required_version is not available"

    # Prompt user to install the required version
    read -p "Would you like to install Python $required_version now? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "Installing Python $required_version..."
        if uv python install "$required_version"; then
            print_success "Python $required_version installed successfully"
            return 0
        else
            print_error "Failed to install Python $required_version"
            return 1
        fi
    else
        print_warning "Python $required_version not installed"
        return 1
    fi
}

check_python_version() {
    echo "📊 Checking Python version requirement..."

    # Check if pyproject.toml exists
    if [ ! -f "pyproject.toml" ]; then
        print_error "pyproject.toml not found"
        return
    fi

    # Extract the Python version requirement from pyproject.toml
    REQUIRED_VERSION=$(grep "requires-python" pyproject.toml | sed -E 's/.*>= *([0-9]+\.[0-9]+).*/\1/')
    if [ -z "$REQUIRED_VERSION" ]; then
        print_error "Could not find or parse 'requires-python' in pyproject.toml"
        return
    fi

    # Get the current Python version
    CURRENT_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

    echo "  🏷️  Required Python version: >=${REQUIRED_VERSION}"
    echo "  🐍 Current Python version: ${CURRENT_VERSION}"

    # Compare versions
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$CURRENT_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
        if [ "$REQUIRED_VERSION" = "$CURRENT_VERSION" ]; then
            print_success "Python version matches the requirement"
        else
            print_success "Python version exceeds the minimum requirement"
        fi
    else
        print_error "Python version does not meet the minimum requirement"
        if ensure_python_available ${REQUIRED_VERSION}; then
            read -p "Would you like to create a new virtual environment with Python ${REQUIRED_VERSION}? (Y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                echo "Creating new virtual environment..."
                if uv venv .venv; then
                    print_success "Virtual environment created successfully"
                    source .venv/bin/activate
                else
                    print_error "Failed to create virtual environment"
                fi
            else
                print_warning "Virtual environment not created"
            fi
        else
            print_error "Unable to ensure required Python version is available"
        fi
    fi
}

check_envrc() {
    echo "🔍 Checking .envrc file..."

    local envrc="./.envrc"
    local required_layout="layout python-uv"

    # Check if .envrc exists
    if [[ ! -f "$envrc" ]]; then
        print_warning ".envrc file not found"
        read -p "Would you like to create .envrc with '$required_layout'? (Y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            echo "$required_layout" > "$envrc"
            print_success ".envrc file created with '$required_layout'"
            direnv allow
        else
            print_warning ".envrc file not created"
        fi
        return
    fi

    # Check if the first line is correct and no other layout lines exist
    local first_line=$(head -n 1 "$envrc")
    local other_layouts=$(grep -n "^layout" "$envrc" | grep -v "^1:")

    if [[ "$first_line" == "$required_layout" && -z "$other_layouts" ]]; then
        print_success ".envrc file is correctly configured"
        return
    fi

    # Prepare the new content
    local new_content="$required_layout"$'\n'
    while IFS= read -r line; do
        if [[ "$line" != "layout "* ]]; then
            new_content+="$line"$'\n'
        fi
    done < "$envrc"

    # Create a unified diff
    diff=$(diff -u "$envrc" <(echo -n "$new_content"))

    # Show the diff and ask for confirmation
    echo "Proposed changes to .envrc:"
    echo "$diff"
    read -p "Would you like to apply these changes? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo -n "$new_content" > "$envrc"
        print_success ".envrc file updated"
        direnv allow
    else
        print_warning "Changes not applied to .envrc"
    fi
}

check_venv() {
    # Check if running in a virtual environment
    if [ -n "$VIRTUAL_ENV" ]; then
        print_success "🐍 Virtual environment is active"
        echo "  🏠 Virtual environment path: $VIRTUAL_ENV"

        # Check if $VIRTUAL_ENV is under the current directory
        if [[ ! "$VIRTUAL_ENV" == "$(pwd)"/* ]]; then
            print_error "Virtual environment is not located under the current directory"
            exit 1
        fi
    else
        print_error "No virtual environment is active"
        exit 1
    fi

    # Check Python interpreter
    PYTHON_PATH=$(which python)
    if [ -n "$PYTHON_PATH" ]; then
        print_success "🐍 Python interpreter found"
        echo "  📍 Python path: $PYTHON_PATH"
        echo "  🏷️  Python version: $(python --version)"

        # Check if the Python interpreter is from the virtual environment
        if [[ "$PYTHON_PATH" == "$VIRTUAL_ENV"/* ]]; then
            print_success "Python interpreter is from the active virtual environment"
        else
            print_error "Python interpreter is not from the active virtual environment"
            exit 1
        fi
    else
        print_error "Python interpreter not found in PATH"
        exit 1
    fi
}

check_package_versions() {
    echo "📦 Checking installed package versions..."

    # Extract requirements files from pyproject.toml
    REQ_FILES=$(grep -E "^(dependencies|optional-dependencies\.dev)" pyproject.toml | sed -n 's/.*\[\([^]]*\)\].*/\1/p' | tr -d '"' | tr ',' ' ')
    if [ -z "$REQ_FILES" ]; then
        print_error "No requirements files found in pyproject.toml"
        return 1
    fi

    echo "  📄 Requirements files: $(echo $REQ_FILES | xargs echo)"

    # Check if `uv` command (a new Python package manager) is available in path
    echo "📦 Checking for uv..."

    if command -v uv >/dev/null 2>&1; then
        print_success "uv found in PATH"
        echo "  📍 Path: $(command -v uv)"
    else
        # If `uv` is not found, install it with pip
        print_error "uv not found in PATH"
        echo "Installing uv with pip..."
        pip install uv
        if command -v uv >/dev/null 2>&1; then
            print_success "Successfully installed uv"
            echo "  📍 Path: $(command -v uv)"
        else
            print_error "Failed to install uv"
            return 1
        fi
    fi

    # Executing pip-sync with dry run option
    echo "🔄 Running 'uv pip sync' with dry run option..."
    OUTPUT=$(uv pip sync --dry-run $REQ_FILES 2>&1)
    EXIT_CODE=$?
    if [ $EXIT_CODE -gt 1 ]; then
        print_error "Error running uv pip sync"
        echo "$OUTPUT"
        return 1
    fi

    if ! echo "$OUTPUT" | grep -q "Would make no changes"; then
        print_warning "Package version mismatches detected"
        echo "$OUTPUT"
        read -p "Would you like to fix these mismatches? (Y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            echo "Fixing package mismatches..."
            uv pip sync $REQ_FILES
            if [ $? -eq 0 ]; then
                print_success "Package mismatches resolved"
            else
                print_error "Failed to resolve package mismatches"
                return 1
            fi
        else
            print_error "Package mismatches not resolved"
            return 1
        fi
    else
        print_success "All package versions match requirements"
    fi
}

check_python_version
check_envrc
check_venv
check_package_versions
