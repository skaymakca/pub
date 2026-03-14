# Pub

Central publishing hub at [skaymakca.github.io/pub/](https://skaymakca.github.io/pub/). Drop markdown docs or pre-formatted HTML reports into the repo, push, and they deploy automatically via GitHub Actions.

## Local Development

Requires [Hugo](https://gohugo.io/) (extended edition).

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

<!-- Link to an HTML report -->
[Coverage report](/pub/reports/coverage/)
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

## Adding HTML Reports

HTML reports are self-contained files served verbatim — Hugo does not process them.

### 1. Place the report

```
static/reports/my-report/
  index.html    # Self-contained HTML report
  *.css / *.js  # Optional assets (if not inlined)
```

The report is served at `/pub/reports/my-report/`.

### 2. Add a manifest entry

Edit `data/reports.yaml` to add the report so it appears on the Reports page and the landing page:

```yaml
- title: "My Report"
  url: "/pub/reports/my-report/"
  description: "What this report covers"
```

**Format of `reports.yaml`:**

The file is a YAML list. Each entry has three fields:

| Field         | Required | Description                                          |
|---------------|----------|------------------------------------------------------|
| `title`       | yes      | Display name shown in listings                       |
| `url`         | yes      | Absolute path including `/pub/` prefix               |
| `description` | no       | One-line summary shown below the title in listings   |

The `url` must match where the report lives in `static/`. Since the site is deployed at `/pub/`, all URLs need the `/pub/` prefix.

### 3. Push

```
git add static/reports/my-report/ data/reports.yaml
git commit -m "Add my-report"
git push
```

## Project Structure

```
pub/
  hugo.toml                     # Site config
  Makefile                      # dev / build / clean
  content/
    _index.md                   # Landing page content
    reports/
      _index.md                 # Reports section definition
    <project>/
      _index.md                 # Section title + description
      *.md                      # Markdown pages
  data/
    reports.yaml                # Manifest of HTML reports
  layouts/                      # Hugo templates
  assets/css/main.css           # Site styles
  static/
    reports/<name>/index.html   # Self-contained HTML reports
  .github/workflows/deploy.yml # CI/CD
```
