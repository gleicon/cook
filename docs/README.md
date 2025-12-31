# Cook Documentation

This directory contains the MkDocs documentation for Cook.

## Building Documentation

### Install Dependencies

```bash
uv pip install -e ".[docs]"
```

Or with pip:

```bash
pip install -e ".[docs]"
```

### Serve Locally

```bash
mkdocs serve
```

View at: http://127.0.0.1:8000

### Build Static Site

```bash
mkdocs build
```

Output in `site/` directory.

## Publishing

### GitHub Pages

```bash
mkdocs gh-deploy
```

### Manual Deployment

```bash
mkdocs build
rsync -av site/ user@server:/var/www/docs/
```

## Documentation Structure

```
docs/
├── index.md                    # Home page
├── getting-started/
│   ├── installation.md        # Installation guide
│   ├── quickstart.md          # Quick start tutorial
│   └── concepts.md            # Core concepts
├── resources/
│   ├── index.md               # Resources overview
│   ├── file.md                # File resource
│   ├── package.md             # Package resource
│   ├── repository.md          # Repository resource
│   ├── service.md             # Service resource
│   └── exec.md                # Exec resource
├── guides/
│   ├── multi-environment.md   # Multi-env deployments
│   ├── ssh.md                 # SSH remote execution
│   ├── state.md               # State management
│   ├── drift.md               # Drift detection
│   └── recording.md           # Recording mode
├── examples/
│   ├── lemp.md                # LEMP stack
│   ├── minimidia.md           # Minimidia SaaS
│   └── wordpress.md           # WordPress
├── api/
│   ├── core.md                # Core API
│   ├── resources.md           # Resources API
│   └── transport.md           # Transport API
└── development/
    ├── contributing.md        # Contributing guide
    ├── testing.md             # Testing guide
    └── architecture.md        # Architecture docs
```

## Writing Guidelines

### Style

- Use present tense
- Be concise and factual
- Avoid superlatives and emojis
- Provide working code examples
- Include error handling examples

### Code Blocks

Use language-specific syntax highlighting:

    ```python
    from cook import Package
    Package("nginx")
    ```

### Admonitions

Use for warnings and notes:

    !!! note
        This is a note.

    !!! warning
        This is a warning.

### API Documentation

Use mkdocstrings for API reference:

    ::: cook.resources.repository.Repository
        options:
          show_source: false

## Dependencies

- mkdocs: Static site generator
- mkdocs-material: Material theme
- mkdocstrings: API documentation from docstrings
