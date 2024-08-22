#!/bin/sh
branch="$(git rev-parse --abbrev-ref HEAD)"
valid_branches="^((feature|fix|wip|chore)\/)?[a-z0-9._-]+$"
if [[ ! $branch =~ $valid_branches ]]
then
    echo "The name of this branch ($branch) is invalid. Pattern for allowed names: $valid_branches." >&2
    exit 1
fi
