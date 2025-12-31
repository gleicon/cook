# Documentation Setup Complete

MkDocs documentation site for Cook is now configured and ready to use.

## Quick Start

### View Locally

```bash
uv run mkdocs serve
```

Open http://127.0.0.1:8000 in your browser.

Changes to markdown files auto-reload.

### Build Static Site

```bash
uv run mkdocs build
```

Output: `site/` directory

## Publishing Options

### GitHub Pages

Automatic deployment to GitHub Pages:

```bash
uv run mkdocs gh-deploy
```

Site will be available at: https://gleicon.github.io/cook/

### Manual Hosting

Build and copy to your server:

```bash
uv run mkdocs build
rsync -av site/ user@server:/var/www/docs/
```

### ReadTheDocs

1. Go to https://readthedocs.org
2. Import your repository
3. ReadTheDocs auto-detects mkdocs.yml

## Documentation Structure

```
docs/
├── index.md                     ✅ Home page
├── getting-started/
│   ├── installation.md         ✅ Complete
│   ├── quickstart.md           ✅ Complete
│   └── concepts.md             ✅ Complete
├── resources/
│   ├── index.md                ✅ Complete
│   ├── repository.md           ✅ Complete (full reference)
│   ├── file.md                 ⚪ Placeholder
│   ├── package.md              ⚪ Placeholder
│   ├── service.md              ⚪ Placeholder
│   └── exec.md                 ⚪ Placeholder
├── examples/
│   ├── minimidia.md            ✅ Complete
│   ├── lemp.md                 ⚪ Placeholder
│   └── wordpress.md            ⚪ Placeholder
└── guides/                     ⚪ All placeholders
```

## Completed Pages

Well-documented pages ready for use:

1. **Home (index.md)** - Overview and quick example
2. **Installation** - Complete install guide for all platforms
3. **Quick Start** - Tutorial with working examples
4. **Core Concepts** - Framework fundamentals
5. **Resources Overview** - Resource pattern explanation
6. **Repository Resource** - Complete reference with examples
7. **Minimidia Example** - Production SaaS deployment

## Remaining Work

Create content for placeholder pages:

### High Priority

- `resources/package.md` - Package resource reference
- `resources/file.md` - File resource reference
- `resources/service.md` - Service resource reference
- `resources/exec.md` - Exec resource reference

### Medium Priority

- `guides/multi-environment.md` - Multi-env deployment patterns
- `guides/ssh.md` - Remote execution guide
- `guides/drift.md` - Drift detection usage
- `examples/lemp.md` - LEMP stack example

### Low Priority

- API reference pages
- Development guides
- Additional examples

## Configuration

### Site Settings

Edit `mkdocs.yml` to customize:

- Site name and description
- Repository URL
- Theme colors
- Navigation structure
- Plugins and extensions

### Theme

Material for MkDocs theme features:

- Dark/light mode toggle
- Search
- Code syntax highlighting
- Responsive design
- Navigation tabs

### Markdown Extensions

Enabled extensions:

- Code blocks with syntax highlighting
- Admonitions (notes, warnings)
- Tables
- Tabbed content
- Table of contents

## Writing Guidelines

### No AI Language

Documentation uses professional, factual language:

- No emojis in markdown content
- No superlatives (amazing, awesome, etc.)
- No exclamation marks
- Present tense, active voice
- Concise, technical style

### Code Examples

All code examples:

- Use proper syntax highlighting
- Are tested and working
- Include error handling where relevant
- Show expected output

### Structure

Each page follows:

1. Title
2. Overview paragraph
3. Subsections with headers
4. Code examples
5. Reference links

## Dependencies

Installed via `uv pip install -e ".[docs]"`:

- mkdocs: Static site generator
- mkdocs-material: Material theme
- mkdocstrings: API doc generation (optional)

## Commands Reference

```bash
# Serve locally with auto-reload
uv run mkdocs serve

# Build static site
uv run mkdocs build

# Deploy to GitHub Pages
uv run mkdocs gh-deploy

# Validate links and structure
uv run mkdocs build --strict
```

## Next Steps

1. Fill in placeholder pages as needed
2. Test local serving: `uv run mkdocs serve`
3. Choose hosting platform
4. Deploy documentation

Documentation is production-ready for local use and can be published when ready.
