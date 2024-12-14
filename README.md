# repindex

`repindex` is a Python tool that indexes a repository, detects its language, ignores irrelevant folders, extracts dependencies, and generates structured outputs (tree, dependency graphs, documentation). It also supports incremental indexing with diffs, context extraction for specific files, and customizable modes.

## Features

- **Automatic Language Detection**: Identifies if the repo is React/Node (package.json) or Python (pyproject.toml/requirements.txt/setup.py) and applies appropriate ignore rules.
- **Ignoring Directories**: By default, ignores hidden directories and language-specific large directories (`node_modules` for React, `__pycache__`, `env`, `venv` for Python).
- **Customizable**: `--no-ignore` to include all directories, `--lang` to force a specific language.
- **Dependency Graphs**: 
  - `dependency_graph_full.json`: Full graph with imports and exports.
  - `dependency_graph_imports.json`: Only imports.
  - `dependency_graph_exports.json`: Only exports.
  - `dependency_graph_no_objects.json`: All relationships without listing objects.
- **Documentation**:
  - `documentation.md`: Full documentation for all files.
  - `documentation_light.md`: Only code files (.ts, .tsx, .css, .py, .sh).
- **Incremental Indexing & Diff**:
  - Caches file hashes, shows changed/new/removed files with diffs in `repindex_changes.md`.
- **Context Extraction Mode**:
  - `--context-for <file1> [<file2>...]` generates a single Markdown file including the specified files and all their dependencies. Useful for providing context to ChatGPT.
- **Minimal Mode**:
  - `--minimal` to skip non-essential outputs and speed up indexing.

## Installation

```bash
pip install repindex