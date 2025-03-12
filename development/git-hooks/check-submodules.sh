#!/bin/bash
# shellcheck disable=SC2086

set -euo pipefail

### ----------------------------------------------------------------------
txtred='\033[0;31m'       # red
bldred='\033[1;31m'       # red bold
txtgrn='\033[0;32m'       # green
bldgrn='\033[1;32m'       # green bold
txtyel='\033[0;33m'       # yellow
bldyel='\033[1;33m'       # yellow bold
txtrst='\033[0m'          # Text reset

# ------------------------------
# regex
SUBMODULE_REGEX_STATUS="([\+-uU[:space:]])([^[:space:]]*) ([^[:space:]]*)( ([^[:space:]]*))?"
SUBMODULE_REGEX_MODULE="path = (.*)"

# ------------------------------
print_error() {
  echo -e "${bldred}$1${txtrst}" 2>/dev/stderr
}

# ------------------------------
print_success() {
  echo -e "${bldgrn}$1${txtrst}"
}

# ------------------------------
print_warning() {
  echo -e "${bldyel}$1${txtrst}"
}

# ------------------------------
print_warning_with_title() {
  echo -e "${txtyel}$1: ${bldyel}$2${txtrst}"
}

# ------------------------------
parse_git_branch() {
  git branch --no-color 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/\1/'
}

# ------------------------------
find_submodule_remote_ref() {
  local l_remote_ref
  #if git fetch origin main ; then
  #  print_error "unable to fetch"
  #fi
  l_remote_ref=$(git ls-remote --exit-code --ref -b origin main | cut -f 1)
  echo ${l_remote_ref}
  return 0
}

# ------------------------------
# $1 = path
# $2 = the local revision that is being pushed to the remote
find_submodule_commit_hash() {
  local rev=$2
  if [ -z "$rev" ]; then
    rev=HEAD
  fi
  local l_br
  l_br=$(git ls-tree --object-only ${rev} -- $1)
  echo $l_br
  return 0
}

# ------------------------------
# $1 = hash
# $2 = path
#
check_submodule_is_pushed() {
  # need to find the path for this module
  local l_hash=$1
  local l_path=$2

  while read -r line ; do
    if [[ ! "$line" =~ $SUBMODULE_REGEX_MODULE ]]; then
      continue
    fi
    if [[ ! ${BASH_REMATCH[1]} == "${l_path}" ]]; then
      continue
    fi
    local target_commit
    target_commit=$(find_submodule_commit_hash ${l_path} ${PRE_COMMIT_TO_REF})

    pushd . > /dev/null
    cd ${BASH_REMATCH[1]} || exit 1
    local l_remote_ref
    l_remote_ref=$(find_submodule_remote_ref)
    if git merge-base --is-ancestor "$target_commit" "$l_remote_ref" ; then
      print_success "  All is good with this submodule..."
      return 0
    else
      print_error "Stop! Pre-commit condition failed."
      echo "Did you forget to push submodule [$l_path] to remote?"
      echo "Cannot proceed until you do so."

      print_warning_with_title "Checking" "${PRE_COMMIT_FROM_REF}..${PRE_COMMIT_TO_REF}"
      print_warning_with_title "  Submodule remote ref" ${l_remote_ref}
      print_warning_with_title "  Submodule local ref" ${l_hash}
      return 1
    fi
  done < "${SUBMODULE_CONFIG_FILE}"
}

### ----------------------------------------------------------------------
### MAIN
### ----------------------------------------------------------------------

PROJECT_ROOT=$(realpath "$(git rev-parse --git-dir)"/..)

# ------------------------------
# exit if nothing to do here...
SUBMODULE_CONFIG_FILE=${PROJECT_ROOT}/.gitmodules
if [[ ! -f ${SUBMODULE_CONFIG_FILE} ]]; then
  echo "No submodules found in .gitmodules"
  exit 0
fi

echo "Checking submodules..."

# ------------------------------
IFS=$'\x0A'$'\x0D'
#save initial dir
pushd . > /dev/null
cd ${PROJECT_ROOT} || exit

FAILED=0

# loop through all submodules
git_submodules=$(git submodule)
for l in $git_submodules ; do
  if [[ ! "$l" =~ $SUBMODULE_REGEX_STATUS ]]; then
    continue
  fi
  status=${BASH_REMATCH[1]}
  hash=${BASH_REMATCH[2]}
  path=${BASH_REMATCH[3]}
  branch=${BASH_REMATCH[5]}

  echo "[$path]"
  if [[ $status == "-" ]]; then
    print_error "  Submodule [$path] not initialized"
    exit 1
  else
    if check_submodule_is_pushed ${hash} ${path}; then
      print_success "  Submodule [$path] OK"
    else
      IFS=$''
      print_error "  Submodule [$path] FAILED"
      FAILED=1
    fi
  fi
done

# go back to original folder
popd > /dev/null || exit

exit $FAILED
