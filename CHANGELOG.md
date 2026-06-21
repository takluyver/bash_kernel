# Unreleased

- Add `BASH_KERNEL_CMD` environment variable to override the command used to
  launch bash. Its value allows a wrapper command with arguments, e.g.
  `export BASH_KERNEL_CMD="apptainer exec --nv container.sif bash"`. When a
  wrapper is used, the `--rcfile` bash startup file is copied into the shared
  temp directory (`$TMPDIR`/`/tmp`) so it is readable from inside the wrapper
  (e.g. a container), and the kernel banner no longer fails if the wrapper's
  `--version` output is unavailable or unexpected.

# Version 0.10.0 (2024-01-05)

- Support for Python 3.13, by replacing the removed imghdr standard library module
  with `filetype` from PyPI. Thnks to @jans-code (https://github.com/takluyver/bash_kernel/pull/148)

# Version 0.9.0 (2022-12-17)

- Support for progress bars, and display and updating of HTML/JS content. Thanks to @janpfeifer (https://github.com/takluyver/bash_kernel/pull/122)
- Add a Binder template/config (thanks @mwouts)

# Version 0.8.0 (2022-08-22)

- Fixes for modern GNU readline. Solves longstanding bug rendering bash_kernel inoperable (@kdm9 https://github.com/takluyver/bash_kernel/pull/120).
