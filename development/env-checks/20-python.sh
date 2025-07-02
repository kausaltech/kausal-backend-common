# shellcheck shell=bash

ensure_python_available() {
    local REQUIRED_PYTHON_VERSION="$1"
    local available_versions

    echo "🔍 Checking for Python $REQUIRED_PYTHON_VERSION availability..."

    # Get the list of installed Python versions
    available_versions=$(uv python list --only-installed | grep '^cpython-' | awk '{print $1}' | cut -d'-' -f2)

    # Check if the required version is available
    if echo "$available_versions" | grep -q "^$REQUIRED_PYTHON_VERSION"; then
        print_success "Python $REQUIRED_PYTHON_VERSION is available"
        return 0
    fi

    # If not found, try to find a compatible version
    for version in $available_versions; do
        if [[ "$version" == "$REQUIRED_PYTHON_VERSION"* ]]; then
            print_success "Compatible Python version $version is available"
            return 0
        fi
    done

    print_warning "Python $REQUIRED_PYTHON_VERSION is not available"

    # Prompt user to install the required version
    read -p "Would you like to install Python $REQUIRED_PYTHON_VERSION now? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "Installing Python $REQUIRED_PYTHON_VERSION..."
        if uv python install "$REQUIRED_PYTHON_VERSION"; then
            print_success "Python $REQUIRED_PYTHON_VERSION installed successfully"
            return 0
        else
            print_error "Failed to install Python $REQUIRED_PYTHON_VERSION"
            return 1
        fi
    else
        print_warning "Python $REQUIRED_PYTHON_VERSION not installed"
        return 1
    fi
}

read_python_version() {
    print_check "Checking Python version requirement" "📊"

    # Check if pyproject.toml exists
    if [ ! -f "pyproject.toml" ]; then
        print_error "pyproject.toml not found"
        exit 1
    fi

    # Extract the Python version requirement from pyproject.toml
    REQUIRED_PYTHON_VERSION=$(grep "requires-python" pyproject.toml | sed -E 's/.*>= *([0-9]+\.[0-9]+).*/\1/')
    if [ -z "$REQUIRED_PYTHON_VERSION" ]; then
        print_error "Could not find or parse 'requires-python' in pyproject.toml"
        exit 1
    fi
    echo "  🏷️  Required Python version: >=${REQUIRED_PYTHON_VERSION}"
}

check_python_version() {
    # Get the current Python version
    CURRENT_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "  🐍 Current Python version: ${CURRENT_VERSION}"

    # Compare versions
    if [ "$(printf '%s\n' "$REQUIRED_PYTHON_VERSION" "$CURRENT_VERSION" | sort -V | head -n1)" = "$REQUIRED_PYTHON_VERSION" ]; then
        if [ "$REQUIRED_PYTHON_VERSION" = "$CURRENT_VERSION" ]; then
            print_success "Python version matches the requirement"
        else
            print_success "Python version exceeds the minimum requirement"
        fi
    else
        print_error "Python version does not meet the minimum requirement"
        if ensure_python_available ${REQUIRED_PYTHON_VERSION}; then
            read -p "Would you like to create a new virtual environment with Python ${REQUIRED_PYTHON_VERSION}? (Y/n) " -n 1 -r
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
        eval "$(direnv export bash)"
    else
        print_warning "Changes not applied to .envrc"
    fi
}

check_venv() {
    print_check "Checking for Python virtual env" "🏠"
    # Check if running in a virtual environment
    if [ -n "$VIRTUAL_ENV" ]; then
        print_success "🐍 Virtual environment is active"
        print_findings "Virtual environment path" "$VIRTUAL_ENV"

        # Check if $VIRTUAL_ENV is under the current directory
        if [[ "$VIRTUAL_ENV" != "$(pwd)"/.venv ]]; then
            print_error "Virtual environment must be in '$(pwd)/.venv'"
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
        echo "  🏷️ Python version: $(python --version)"

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
    print_check "Checking installed package versions..." "📦"

    if [ ! -f "uv.lock" ]; then
      # Extract requirements files from pyproject.toml
      REQ_FILES=$(sed -n '/^dependencies\|^optional-dependencies\.dev/,/}/p' pyproject.toml | grep -o '".*"' | tr -d '"' | grep -v '^$' | tr '\n' ' ')
      if [ -z "$REQ_FILES" ]; then
          print_error "No requirements files found in pyproject.toml"
          return 1
      fi
      if [ -f "requirements-local.txt" ]; then
          REQ_FILES="$REQ_FILES requirements-local.txt"
      fi

      echo -e "  📄 Requirements files: ${DIM}$(echo $REQ_FILES | xargs echo)${NC}"
    fi
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

    if [ -f "uv.lock" ]; then
      set -e
      echo "🔄 Syncing virtual environment with uv.lock..."
      uv sync --all-groups
      return 0
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
            if uv pip sync $REQ_FILES; then
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

check_other_venvs() {
    print_check "Checking for other Python virtual environments..." "🔍"

    local current_venv="${VIRTUAL_ENV##*/}"
    local ignore_marker=".kausal_ignore"
    local venvs_found=0
    local venvs_removed=0
    local venv_dirs=()

    # Find all directories containing pyvenv.cfg and store them in an array
    while IFS= read -r venv_dir; do
        venv_name="${venv_dir##*/}"
        if [[ "$venv_name" != "$current_venv" ]]; then
            venv_dirs+=("$venv_dir")
            ((venvs_found++))
        fi
    done < <(find . -type f -name pyvenv.cfg -print0 | xargs -0 -n1 dirname | sort -u)

    for venv_dir in "${venv_dirs[@]}"; do
        venv_name="${venv_dir##*/}"

        # Check if the ignore marker exists
        if [[ -f "$venv_dir/$ignore_marker" ]]; then
            print_warning "Ignored virtual environment found: $venv_name"
            continue
        fi

        print_findings "Found non-standard virtual environment" "$venv_dir"

        if ! prompt_user "Do you want to remove this virtual environment?"; then
            if prompt_user "Do you want to ignore this virtual environment in future checks?"; then
                touch "$venv_dir/$ignore_marker"
                print_success "Marked $venv_name to be ignored in future checks"
            else
                print_warning "Virtual environment $venv_name left unchanged"
            fi
            continue
        fi

        if rm -rf "$venv_dir"; then
            print_success "Removed virtual environment: $venv_name"
            ((venvs_removed++))
        else
            print_error "Failed to remove virtual environment: $venv_name"
        fi
    done

    if [[ $venvs_found -eq 0 ]]; then
        print_success "No other virtual environments found"
    fi
}

read_python_version
check_venv
check_python_version
check_package_versions
check_other_venvs
