# Building qobserva-local for PyPI

## Prerequisites

- Node.js and npm installed
- React UI dependencies installed: `cd packages/qobserva_ui_react && npm install`

## Build Process

The build script (`next_steps/build_all_packages.py`) automatically:

1. **Builds React UI**: Runs `npm run build` in `packages/qobserva_ui_react`
2. **Copies dist**: Copies `packages/qobserva_ui_react/dist` → `packages/qobserva_local/qobserva_local/ui_dist`
3. **Builds Python package**: Builds the Python wheel/sdist with bundled React UI

## Manual Build

If you need to build manually:

```bash
# 1. Build React UI
cd packages/qobserva_ui_react
npm run build

# 2. Copy dist to qobserva_local
cd ../..
cp -r packages/qobserva_ui_react/dist packages/qobserva_local/qobserva_local/ui_dist

# 3. Build Python package
cd packages/qobserva_local
python -m build
```

## Maintenance

**When React UI changes:**
- Run the build script (it handles everything automatically)
- Or manually rebuild React and copy dist before building Python package
- This is standard practice for Python packages with bundled frontends

**Note:** The React UI source code stays in `packages/qobserva_ui_react`. Only the built `dist/` folder is bundled into the Python package.
