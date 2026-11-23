# Set up Beads in a new project

Initialize Beads from the **root of the new project's existing Git repository**. Do not run this from the Beads source checkout. First make sure the directory is the intended repository and the CLI is the pinned version:

```bash
cd /path/to/your-project
git rev-parse --show-toplevel
bd version
```

Choose how the project will use Beads before initialization:

- **Personal/local tracking:** use `--stealth`. Beads state stays out of normal repository tracking and is intended for private use on this clone; collaborators will not automatically share your issues.
- **Shared project tracking:** omit `--stealth`. Review the files created by `bd init`, then commit the Beads metadata/configuration that the team intends to share. Agree with collaborators on a consistent `bd` version and issue prefix.

Initialize SQLite (the explicit backend avoids ambiguity) and optionally set a short, stable prefix that identifies this project in issue IDs:

```bash
# Personal/local setup:
bd init --backend sqlite --stealth --prefix myproj

# OR shared setup:
bd init --backend sqlite --prefix myproj
```

Replace `myproj` with a short prefix appropriate for the project. Omit `--prefix` to use the current directory name. Do not run both initialization commands; choose one. SQLite is the default in v0.49.6, while Dolt is also an optional backend. For the SQLite setup, the database is normally `.beads/beads.db`.

Validate the setup and inspect what Beads created:

```bash
bd doctor
git status --short
```

For shared setup, review `git status` and commit the intended Beads configuration/metadata with the project's normal workflow. Do not commit local databases, secrets, or other machine-specific data unless the team explicitly chooses that policy. For stealth setup, Beads configures Git ignore behavior to keep its files out of normal tracking; verify no Beads files are unexpectedly staged.
