#!/bin/bash
#
# Create and remove git worktrees of a Kausal backend, each with the state a checkout does not
# carry: submodules, a virtualenv, its own database and its own Redis database.
#
#   worktree.sh new <name> [options]   create <root>/<repo>/<name>
#   worktree.sh rm <name> [options]    remove it, its database and its Redis keys
#   worktree.sh list                   list this repo's worktrees and their databases
#
# <root> is `../worktrees` next to the main checkout, or $KAUSAL_WORKTREES_ROOT. <repo> is the
# main checkout's directory name, so Paths and Watch worktrees live side by side. The script
# can be run from the main checkout or from any of its worktrees.
#
# Options for `new`:
#   --branch <branch>      branch to check out; created from --base if it does not exist
#                          (default: <name>)
#   --base <ref>           start point of a new branch (default: HEAD)
#   --db-template <db>     database to clone (default: the one in the main checkout's .env.db).
#                          `createdb -T` refuses while anything is connected to the template.
#   --no-db                do not create a database or write .env.db
#   --no-setup             skip `uv sync` and `mise deps`
#
# Options for `rm`:
#   --force                remove even with uncommitted changes
#   --keep-db              keep the database
#   --delete-branch        also delete the branch, if it is merged (`git branch -d`)
#
# Why each worktree gets its own database: branches with different migrations cannot share one,
# and pytest-django names the test database `test_<dbname>`, so two worktrees on one
# DATABASE_URL running `--reuse-db` concurrently would destroy each other's test database.
#
# Local files: `.env`, `.secrets/` and `mise.local.toml` are copied, not linked, so a worktree
# can change its own without affecting the others. DATABASE_URL and REDIS_URL are removed
# from the copied `.env` and written to `.env.db` and `.env.redis` instead. They must not
# remain in `.env`: settings.py reads `.env` first and `read_env` never overwrites a variable
# that is already set, so a value left there would win over the per-worktree file.
#
# Redis databases 1..15 are handed out across all repos under <root>; 0 is left to the main
# checkouts.

set -euo pipefail

die() { echo "worktree.sh: $*" >&2; exit 1; }
info() { echo "==> $*" >&2; }

common_dir=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) \
  || die "not inside a git repository"
main=$(dirname "$common_dir")
repo=$(basename "$main")
root=${KAUSAL_WORKTREES_ROOT:-$(dirname "$main")/worktrees}

# Print the value of variable $2 in env file $1, if the file sets it.
env_value() {
  [ -f "$1" ] || return 0
  sed -nE "s/^[[:space:]]*(export[[:space:]]+)?$2=//p" "$1" | tail -n1 | sed -E "s/^[\"'](.*)[\"']$/\1/"
}

# Print the database name in a postgres URL.
db_name() {
  local path=${1#*://}
  path=${path#*/}
  echo "${path%%\?*}"
}

check_name() {
  [[ $1 =~ ^[a-z0-9][a-z0-9_-]*$ ]] || die "name must match [a-z0-9][a-z0-9_-]*: $1"
}

# Print the lowest Redis database number in 1..15 that no worktree under $root uses.
free_redis_db() {
  local used n f
  used=$(for f in "$root"/*/*/.env.redis; do
    [ -f "$f" ] && env_value "$f" REDIS_URL | sed -nE 's|.*/([0-9]+)$|\1|p'
  done)
  for n in $(seq 1 15); do
    grep -qx "$n" <<<"$used" || { echo "$n"; return; }
  done
  die "all Redis databases 1..15 are taken under $root"
}

# Initialize submodule $1 in the new worktree, borrowing objects from the main checkout's copy
# so that commits not yet pushed are available too.
init_submodule() {
  local path=$1 dir=$2
  shift 2
  if [ ! -e "$main/$path/.git" ]; then
    info "Skipping submodule $path: not checked out in the main checkout"
    return
  fi
  info "Initializing submodule $path"
  git -C "$dir" submodule update --init --reference "$main/$path" "$@" -- "$path"
}

cmd_new() {
  local name=${1:-}
  [ -n "$name" ] || die "usage: worktree.sh new <name> [options]"
  shift
  check_name "$name"
  local branch=$name base=HEAD template="" no_db=0 no_setup=0
  while [ $# -gt 0 ]; do
    case $1 in
      --branch) branch=$2; shift 2 ;;
      --base) base=$2; shift 2 ;;
      --db-template) template=$2; shift 2 ;;
      --no-db) no_db=1; shift ;;
      --no-setup) no_setup=1; shift ;;
      *) die "unknown option: $1" ;;
    esac
  done

  local dir=$root/$repo/$name
  [ -e "$dir" ] && die "$dir already exists"

  local main_db_url db_url="" db=""
  main_db_url=$(env_value "$main/.env.db" DATABASE_URL)
  if [ $no_db = 0 ]; then
    if [ -z "$template" ]; then
      [ -n "$main_db_url" ] || die "no DATABASE_URL in $main/.env.db; pass --db-template or --no-db"
      template=$(db_name "$main_db_url")
    fi
    db="wt-$repo-$name"
    db_url="${main_db_url:-postgresql:///x}"
    db_url="${db_url%/*}/$db"
  fi

  mkdir -p "$root/$repo"
  # Serialize allocation of Redis databases between concurrent runs.
  exec 9>"$root/.lock"
  flock 9

  info "Creating worktree $dir on branch $branch"
  if git -C "$main" show-ref --verify --quiet "refs/heads/$branch"; then
    git -C "$main" worktree add "$dir" "$branch"
  else
    git -C "$main" worktree add -b "$branch" "$dir" "$base"
  fi

  init_submodule kausal_common "$dir"
  init_submodule private/extensions "$dir" --checkout

  info "Copying local files"
  if [ -f "$main/.env" ]; then
    grep -vE '^[[:space:]]*(export[[:space:]]+)?(DATABASE_URL|REDIS_URL)=' "$main/.env" >"$dir/.env" || true
  fi
  [ -d "$main/.secrets" ] && cp -a "$main/.secrets" "$dir/.secrets"
  [ -f "$main/mise.local.toml" ] && cp -a "$main/mise.local.toml" "$dir/mise.local.toml"

  local redis_url redis_db
  redis_url=$(env_value "$main/.env" REDIS_URL)
  if [ -n "$redis_url" ]; then
    redis_db=$(free_redis_db)
    redis_url=$(sed -E 's|/[0-9]*$||' <<<"$redis_url")
    echo "REDIS_URL=$redis_url/$redis_db" >"$dir/.env.redis"
    info "Redis: $redis_url/$redis_db"
  fi
  flock -u 9

  if [ $no_db = 0 ]; then
    info "Cloning database $template into $db"
    createdb -T "$template" "$db" \
      || die "createdb failed; is something connected to $template? The worktree exists; retry with: createdb -T $template $db && echo DATABASE_URL=$db_url > $dir/.env.db"
    echo "DATABASE_URL=$db_url" >"$dir/.env.db"
  fi

  if [ $no_setup = 0 ]; then
    info "Setting up the environment"
    (
      cd "$dir"
      mise trust --quiet
      uv sync --all-groups --all-extras
      mise deps
    )
  fi

  info "Done: $dir"
}

cmd_rm() {
  local name=${1:-}
  [ -n "$name" ] || die "usage: worktree.sh rm <name> [options]"
  shift
  check_name "$name"
  local force=() keep_db=0 delete_branch=0
  while [ $# -gt 0 ]; do
    case $1 in
      --force) force=(--force); shift ;;
      --keep-db) keep_db=1; shift ;;
      --delete-branch) delete_branch=1; shift ;;
      *) die "unknown option: $1" ;;
    esac
  done

  local dir=$root/$repo/$name
  [ -d "$dir" ] || die "no worktree at $dir"
  local branch db_url redis_url
  branch=$(git -C "$dir" symbolic-ref --quiet --short HEAD || true)
  db_url=$(env_value "$dir/.env.db" DATABASE_URL)
  redis_url=$(env_value "$dir/.env.redis" REDIS_URL)

  # Submodules make `git worktree remove` refuse even when clean, so check cleanliness here
  # and force the removal itself.
  if [ ${#force[@]} = 0 ] && [ -n "$(git -C "$dir" status --porcelain --ignore-submodules=none)" ]; then
    die "$dir has uncommitted changes; commit them or pass --force"
  fi
  info "Removing worktree $dir"
  git -C "$main" worktree remove --force "$dir"

  if [ -n "$db_url" ] && [ $keep_db = 0 ]; then
    local db
    db=$(db_name "$db_url")
    info "Dropping databases $db and test_$db"
    dropdb --if-exists "$db"
    dropdb --if-exists "test_$db"
  fi
  if [ -n "$redis_url" ] && command -v redis-cli >/dev/null; then
    info "Flushing Redis $redis_url"
    redis-cli -u "$redis_url" FLUSHDB >/dev/null || true
  fi
  if [ $delete_branch = 1 ] && [ -n "$branch" ]; then
    git -C "$main" branch -d "$branch"
  fi
}

cmd_list() {
  local dir
  for dir in "$root/$repo"/*/; do
    [ -d "$dir" ] || continue
    dir=${dir%/}
    printf '%-24s %-40s %-36s %s\n' "$(basename "$dir")" \
      "$(git -C "$dir" symbolic-ref --quiet --short HEAD 2>/dev/null || echo '(detached)')" \
      "$(db_name "$(env_value "$dir/.env.db" DATABASE_URL)")" \
      "$(env_value "$dir/.env.redis" REDIS_URL)"
  done
}

case ${1:-} in
  new) shift; cmd_new "$@" ;;
  rm) shift; cmd_rm "$@" ;;
  list) shift; cmd_list "$@" ;;
  *) sed -n '3,20p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
