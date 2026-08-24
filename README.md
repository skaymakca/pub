# Pub

Central publishing hub at [skaymakca.github.io/pub/](https://skaymakca.github.io/pub/). Drop markdown docs or self-contained HTML sites into the repo, push, and they deploy automatically via GitHub Actions.

## Local Development

Requires [Hugo](https://gohugo.io/) (extended edition), at the same version CI uses
— see [Hugo version](#hugo-version) below.

```
make dev       # Start local server at http://localhost:1313/pub/ (includes drafts)
make build     # Production build into public/
make clean     # Remove public/ and resources/
```

The dev server live-reloads on file changes.

## Adding Markdown Documents

### 1. Create a project folder (one-time)

```
mkdir -p content/my-project/
```

### 2. Add `_index.md` (one-time per project)

Every project folder needs an `_index.md` file. This is how Hugo knows the folder is a "section" — without it, the folder won't appear on the landing page and its pages won't get a section listing.

The file needs frontmatter with at least a `title`. Optionally add a `description` (shown on the landing page under the title):

```yaml
---
title: "My Project"
description: "Optional one-line description shown on the landing page"
---
```

You can also put markdown body content below the frontmatter. It renders at the top of the section's listing page (above the list of child pages).

### 3. Drop `.md` files

Copy markdown files into the project folder:

```
content/my-project/
  _index.md          # Section definition (title + description)
  getting-started.md # → /pub/my-project/getting-started/
  api-reference.md   # → /pub/my-project/api-reference/
  deep/
    nested-doc.md    # → /pub/my-project/deep/nested-doc/
```

Each `.md` file becomes a page. The URL maps directly from the file path.

**Frontmatter is optional.** If a file has no frontmatter, Hugo uses the filename (without extension, with hyphens converted to spaces) as the page title. If frontmatter exists, Hugo reads `title` from it and ignores unknown fields — so markdown exported from other systems (with extra frontmatter keys) works without modification.

### 4. Push

```
git add content/my-project/
git commit -m "Add my-project docs"
git push
```

GitHub Actions builds and deploys automatically.

## Markdown Rendering Details

Hugo uses [Goldmark](https://github.com/yuin/goldmark) (CommonMark-compliant) with the following behavior:

### Inline HTML

Raw HTML in markdown **is rendered as-is**. The site has `markup.goldmark.renderer.unsafe = true` in `hugo.toml`, so tags like `<details>`, `<summary>`, `<div>`, `<video>`, `<iframe>`, etc. pass through to the final page. Example:

```markdown
Here is a collapsible section:

<details>
<summary>Click to expand</summary>

Hidden content here. **Markdown works inside HTML blocks** as long as
there is a blank line between the HTML tag and the markdown content.

</details>
```

### Links Between Documents

**Relative markdown links work**, but you need to use Hugo's URL paths (not file paths):

```markdown
<!-- Link to another page in the same project section -->
[See the API docs](../api-reference/)

<!-- Link to a page in a different section -->
[Vorge docs](/pub/vorge/getting-started/)

<!-- Link to an HTML site -->
[Coverage report](/pub/sites/coverage/)
```

Key points:
- Links resolve to the **rendered URL**, not the source file. Use directory-style paths ending in `/`, not `.md` file references.
- `[link](../sibling-page/)` — relative links work for pages in the same section.
- `[link](/pub/other-section/page/)` — absolute links (from site root) work across sections. Include `/pub/` since the site is served from a subdirectory.
- Standard anchor links (`[link](#heading-id)`) work. Hugo auto-generates heading IDs from heading text (lowercased, hyphens for spaces).

### Hugo Shortcodes

Hugo shortcodes (`{{< shortcode >}}`) are **not** available in this site since no custom shortcodes are defined. Stick to standard markdown and raw HTML.

### Images

Place images alongside markdown files or in `static/`:

```markdown
<!-- Image in static/ (accessible at /pub/images/diagram.png) -->
![Diagram](/pub/images/diagram.png)

<!-- Relative image in the same content directory requires a page bundle setup -->
```

For simplicity, putting images in `static/images/` and using absolute paths is the most straightforward approach.

## Adding HTML Sites

HTML sites are self-contained files served verbatim — Hugo does not process them. A
"site" here can be a single `index.html` or a whole multi-page bundle with its own nav and
stylesheet.

### 1. Place the site

```
static/sites/my-site/
  index.html    # Entry point
  css/          # Optional assets (if not inlined)
  *.html        # Further pages, linked relatively
```

The site is served at `/pub/sites/my-site/`.

### 2. Add a manifest entry

Edit `data/sites.yaml` to add the site so it appears on the Sites page and the landing page:

```yaml
- title: "My Site"
  url: "/pub/sites/my-site/"
  description: "What this site covers"
```

**Format of `sites.yaml`:**

The file is a YAML list. Each entry has three fields:

| Field         | Required | Description                                          |
|---------------|----------|------------------------------------------------------|
| `title`       | yes      | Display name shown in listings                       |
| `url`         | yes      | Absolute path including `/pub/` prefix               |
| `description` | no       | One-line summary shown below the title in listings   |

The `url` must match where the site lives in `static/`. Since the site is deployed at `/pub/`, all URLs need the `/pub/` prefix.

### 3. Push

```
git add static/sites/my-site/ data/sites.yaml
git commit -m "Add my-site"
git push
```

## Project Structure

```
pub/
  hugo.toml                     # Site config
  Makefile                      # dev / build / clean
  content/
    _index.md                   # Landing page content
    sites/
      _index.md                 # Sites section definition (+ /reports/ alias)
    <project>/
      _index.md                 # Section title + description
      *.md                      # Markdown pages
  data/
    sites.yaml                  # Manifest of HTML sites
  layouts/                      # Hugo templates
  assets/css/main.css           # Site styles
  static/
    sites/<name>/index.html     # Self-contained HTML sites
    reports/                    # legacy redirect stubs only — do not add here
  .github/workflows/deploy.yml # CI/CD
```

### Generated sites

Some sites under `static/sites/` are produced by a generator rather than hand-written. Those
carry a `README.md` naming the generator — edit there and re-run, or the next regeneration
discards your change.

### The `reports` → `sites` rename

The section was called `reports` until August 2026. Two redirects keep old links alive:

- `/pub/reports/` → `/pub/sites/` via an `aliases` entry in `content/sites/_index.md`.
- `/pub/reports/disney-trip-research/` → its new home via a meta-refresh stub, because Hugo
  aliases apply to content pages and **not** to files under `static/`.

Add nothing new under `static/reports/`.

## Hugo version

`HUGO_VERSION` in `.github/workflows/deploy.yml` is the single source of truth. The
Makefile reads it from there, so there is nowhere else to update.

`make build` runs `make check-hugo` first and fails on a mismatch. This matters more
than it looks: Hugo deprecations land in specific versions, so a newer local Hugo will
happily build templates that the pinned CI version renders **empty rather than
erroring**. That failure is silent and production-only.

To upgrade: bump `HUGO_VERSION`, upgrade locally to match, run `make build`, push.
