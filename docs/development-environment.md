# Development environment

Kausal Watch and Kausal Paths use [mise](https://mise.jdx.dev/) to select development tools,
assemble product-specific configuration, and prepare project dependencies. The configuration shared
by both backends lives in the `kausal_common` submodule; each product repository supplies the values
and integrations that differ between Watch and Paths.

This is the supported mise-based setup, not a requirement that every developer structure their shell
the same way. An editor, container, or other environment may activate the project's virtual
environment by different means.

## Running Python

From the repository root, prefer the ordinary command:

```shell
python manage.py check
```

`python` should resolve to the interpreter in the repository's `.venv`:

```shell
command -v python
python -c 'import sys; print(sys.executable)'
```

If it does not, let uv select and maintain the project environment for the command:

```shell
uv run python manage.py check
```

Do not use `mise exec -- python` as the Python fallback. mise manages the base Python installation,
while uv manages the project's packages in `.venv`; invoking Python through mise directly can select
the base interpreter rather than the virtual environment.

## Installing with mise

Initialize the shared submodule before loading the mise configuration, because the product
repository links its common configuration from that submodule:

```shell
git submodule update --init kausal_common
```

Install mise using its [installation instructions](https://mise.jdx.dev/installing-mise.html). On
Linux and macOS, the upstream installer is:

```shell
curl https://mise.run | sh
```

Activate mise using the instructions for your shell. For example:

```shell
eval "$(mise activate zsh)"
```

Then install the configured tools and project dependencies from the product repository root:

```shell
mise install
mise deps
```

`mise install` installs the tool versions selected by the configuration and lockfiles. `mise deps`
runs the declared dependency providers; for the backend this includes `uv sync --all-groups
--all-extras`, and it also prepares any available extension assets.

## How the configuration is assembled

mise discovers several configuration files in the product repository and merges them. Run
`mise config ls` from the repository root to see the files active in the current shell.

| Path | Responsibility |
| --- | --- |
| `.miserc.toml` | Selects the `dev` environment by default and enables environment-aware `conf.d` fragments. |
| `mise.toml` | Product repository's base entry point. Shared backend settings are deliberately kept elsewhere. |
| `mise.dev.toml` | Product-specific development values, such as the product name, backend name, port, and GraphQL schema. |
| `mise.local.toml` | Optional, gitignored overrides for one developer or machine. |
| `mise/config.toml` | Symlink to `kausal_common/mise/backend.toml`, the shared base tool configuration. |
| `mise/config.dev.toml` | Symlink to `kausal_common/mise/backend.dev.toml`, the shared development environment, tools, tasks, and dependency providers. |
| `mise/config.prod.toml` | Symlink to `kausal_common/mise/backend.prod.toml`, the shared production tool overrides. |
| `mise/conf.d/*.toml` | Additional composable configuration. The extensions submodule is connected here when available. |
| `mise/mise*.lock` | Resolved tool versions and checksums for the base, development, and production environments. |

The shared files under `kausal_common/mise/` have these roles:

- `backend.toml` declares the common Python and uv tools and general mise settings.
- `backend.dev.toml` activates or creates `.venv`, adds development tools, defines shared tasks, and
  declares dependency providers. Product-specific values referenced by this file come from the
  product's `mise.dev.toml`.
- `backend.prod.toml` pins production-only tool versions. Container builds select it with
  `MISE_ENV=prod`.

The product repository owns the symlinks rather than copying the common files. Consequently, a
change in `kausal_common/mise/` applies to both Watch and Paths after each repository updates its
submodule revision.

The product's `package.json` may also contribute Node.js and pnpm versions through mise's idiomatic
version-file support. Optional private extensions contribute their build and translation providers
through the symlink in `mise/conf.d/`; a missing optional submodule leaves those providers inactive.

## Diagnosing configuration

These commands show the effective setup without changing project configuration:

```shell
mise config ls
mise ls --current
mise env
mise tasks ls
mise deps --list
```

If mise itself is not behaving as expected, run `mise doctor`. If mise looks correct but Python does
not come from `.venv`, use `uv run python` and inspect the two Python-resolution commands above before
recreating the environment.
