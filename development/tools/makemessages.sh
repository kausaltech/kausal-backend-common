#!/bin/bash
#
# Update the gettext catalogues of a Kausal backend without touching the ones it does not own.
#
#   makemessages.sh host            the host project's own `locale/`, including the pybabel
#                                   `notifications` domain if the host has one (run from the
#                                   host root)
#   makemessages.sh package <dir>   a self-contained package with its own `locale/`, such as
#                                   `kausal_common` or an extension package
#
# A bare `manage.py makemessages` from the host root is not safe: Django walks every directory
# below the cwd, so it also rewrites the catalogues of `kausal_common` and the extensions
# submodule, and sends strings from directories without a `locale/` of their own (such as the
# shared extension modules) to the host catalogue.
#
# Packages are extracted from inside their own directory, without Django settings. The
# output then depends only on the package's own files, so every host produces the same
# catalogue for a shared package. Only languages that already have a catalogue for the domain
# are updated; add a new language by running `makemessages -l <lang>` by hand once.
#
# A catalogue whose only change is the `POT-Creation-Date` header is restored from git, so
# rerunning with no source changes leaves the working tree clean.

set -euo pipefail

COMMON_ARGS=(--add-location=file --no-wrap)

# Print `-l <lang>` for every language in locale dir $1 that has a catalogue for domain $2.
locale_args() {
  local locale_dir=$1 domain=$2 po
  for po in "$locale_dir"/*/LC_MESSAGES/"$domain".po; do
    [ -e "$po" ] || continue
    po=${po#"$locale_dir"/}
    printf -- '-l\n%s\n' "${po%%/*}"
  done
}

# Restore catalogues in locale dir $1 whose only change is a generated header.
restore_header_only_changes() {
  local locale_dir=$1 file files
  # Read the whole list before checking anything out: a diff still running would hold the
  # index lock that the checkout needs.
  files=$(git -C "$locale_dir" --no-optional-locks diff --name-only --relative -- .)
  for file in $files; do
    case "$file" in
      *.po | *.pot) ;;
      *) continue ;;
    esac
    if git -C "$locale_dir" --no-optional-locks diff --quiet \
      -I '^"POT-Creation-Date: ' -I '^"Generated-By: ' -- "$file"; then
      git -C "$locale_dir" checkout --quiet -- "$file"
    fi
  done
}

# Run makemessages for each domain that has catalogues in locale dir $1, using the command in
# the RUNNER array and adding the arguments in the EXTRA_ARGS array.
run_domains() {
  local locale_dir=$1 domain langs domain_args
  for domain in django djangojs; do
    mapfile -t langs < <(locale_args "$locale_dir" "$domain")
    [ ${#langs[@]} -gt 0 ] || continue
    domain_args=()
    # Keep the template only where the repo tracks one, as a source for translation services.
    [ -e "$locale_dir/$domain.pot" ] && domain_args+=(--keep-pot)
    [ "$domain" = djangojs ] && domain_args+=(--ignore '*.min.js')
    "${RUNNER[@]}" makemessages -d "$domain" "${langs[@]}" "${COMMON_ARGS[@]}" \
      "${EXTRA_ARGS[@]}" "${domain_args[@]}"
  done
}

# Notification e-mail templates are Jinja2, which makemessages cannot parse, so their
# `notifications` domain is extracted with pybabel as configured in `babel.cfg`.
run_notifications() {
  [ -f babel.cfg ] && [ -f locale/notifications.pot ] || return 0
  pybabel -q extract -F babel.cfg --input-dirs=. -o locale/notifications.pot \
    --ignore-dirs='.* _* private kausal_common node_modules e2e-tests' \
    --add-location=file --no-wrap
  pybabel -q update -D notifications -i locale/notifications.pot -d locale --no-wrap
}

# makemessages deletes the template of every directory in LOCALE_PATHS before extracting,
# including the ones of shared packages it is told to ignore. Run the command in "$@" and put
# those templates back as they were.
preserving_package_templates() {
  local backup pot
  backup=$(mktemp -d)
  for pot in kausal_common/locale/*.pot; do
    if [ -e "$pot" ]; then cp -p "$pot" "$backup/"; fi
  done
  "$@"
  for pot in "$backup"/*.pot; do
    if [ -e "$pot" ]; then cp -p "$pot" kausal_common/locale/; fi
  done
  rm -r "$backup"
}

cmd_host() {
  [ -f manage.py ] || { echo "Run this from the host project root" >&2; exit 1; }
  RUNNER=(python manage.py)
  EXTRA_ARGS=(--ignore private --ignore kausal_common --ignore node_modules --ignore e2e-tests)
  preserving_package_templates run_domains locale
  run_notifications
  restore_header_only_changes locale
}

cmd_package() {
  local dir=${1:?Usage: $0 package <dir>}
  [ -d "$dir/locale" ] || { echo "$dir has no locale directory" >&2; exit 1; }
  cd "$dir"
  # -P keeps the package directory off sys.path, so its subpackages (such as `logging`)
  # cannot shadow the standard library. --symlinks picks up modules that are shared into the
  # package through symlinks.
  RUNNER=(env -u DJANGO_SETTINGS_MODULE python -P -m django)
  EXTRA_ARGS=(--symlinks --ignore node_modules)
  run_domains locale
  restore_header_only_changes locale
}

case "${1:-}" in
  host) cmd_host ;;
  package) shift; cmd_package "$@" ;;
  *) echo "Usage: $0 host | package <dir>" >&2; exit 1 ;;
esac
