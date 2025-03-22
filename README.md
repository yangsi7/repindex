# repindex

`repindex` is a Python tool that indexes a repository and generates structured outputs for visualization and documentation.

## Features

- **Repository Structure**: Generates a tree-like representation of the repository.
- **Dependency Graphs**:
  - **Full Graph**: Includes both imports and exports with objects listed.
  - **Imports Only Graph**: Only considers imports for listing objects.
  - **Exports Only Graph**: Only considers exports for listing objects.
  - **No Objects Graph**: Includes all relationships but does not list objects.
- **Markdown Documentation**:
  - **Full Documentation**: Compiles all files and their contents into a structured Markdown document.
  - **Light Documentation**: Includes only code files (`.ts`, `.tsx`, `.css`, `.py`, `.sh`, etc.) and excludes files like `.json`, `.html`, `.txt`, etc.
  - **Single Document**: Creates a consolidated Markdown document with repository overview, tree structure, dependencies, and code contents.
- **LLM Context Generation**: Designed to provide comprehensive codebase context for Large Language Models.
- **Skip Patterns Support**: Exclude files or directories using glob patterns.
- **Clipboard Support**: Copy the single document output directly to clipboard.

## Installation

Install `repindex` using `pip`:

```bash
# Basic installation
pip install repindex

# With clipboard support
pip install repindex[clipboard]
```

### Usage

```bash
repindex /path/to/repository [-o /path/to/output_dir] [options]
```

#### Basic Arguments

- **repository_path**: The path to the repository you want to index.
- **-o, --output_dir**: (Optional) The directory where outputs will be saved. Defaults to the current directory.

#### Additional Options

- **--lang**: Force a specific language (e.g., python, react)
- **--no-ignore**: Do not ignore default directories like .git, node_modules, etc.
- **--no-cache**: Disable caching & diff generation
- **--minimal**: Produce minimal outputs
- **--skip**: Comma-separated list of glob patterns to ignore (e.g., "*.log,temp*,backup/*")
- **--single-doc**: Generate a single consolidated Markdown document
- **--copy-to-clipboard**: Copy the single document output to clipboard (requires pyperclip)
- **--context-for**: Generate a context file for specified file(s)

**Example:**
```bash
# Basic indexing
repindex ./my_project -o ./output

# Generate a single document and copy to clipboard
repindex ./my_project --single-doc --copy-to-clipboard

# Generate a context file for specific files
repindex ./my_project --context-for src/main.py src/utils.py

# Skip specific files or directories
repindex ./my_project --skip "*.log,temp*,docs/*"
```

#### Outputs

The outputs are saved in a `repindex/` directory inside the specified output directory:

- **tree_structure.txt**: Tree representation of the repository.
- **Dependency Graphs**:
  - `dependency_graph_full.json`: Full graph with imports and exports, including objects.
  - `dependency_graph_imports.json`: Only imports with objects listed.
  - `dependency_graph_exports.json`: Only exports with objects listed.
  - `dependency_graph_no_objects.json`: All relationships without listing objects.
- **Markdown Documentation**:
  - `documentation.md`: Full documentation with all files and contents.
  - `documentation_light.md`: Light documentation including only code files.
  - `repindex_single_doc.md`: (When using --single-doc) Consolidated document with all information.
- **Context Files**:
  - `context_YYYYMMDD_HHMMSS.md`: (When using --context-for) Context document for specified files.

#### Running Tests

To run the unit tests:
```bash
python -m unittest discover tests
```

#### Code Style

The code adheres to PEP8 standards. You can check code style using flake8:
```bash
pip install flake8
flake8 repindex tests
```

#### Continuous Integration

Continuous Integration is set up using GitHub Actions. The workflow runs tests and linting on each push and pull request.

#### License

This project is licensed under the MIT License.

#### Author
- Name: Simon Yang
- GitHub: [yangsi7](https://github.com/yangsi7)

#### Contributing

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

#### Acknowledgments

- Thanks to Me, Myself and I, who have helped improve this project.

#### Development

To set up a development environment for `repindex`:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Linux/macOS
source venv/bin/activate
# On Windows
# venv\Scripts\activate

# Install the package in development mode with all optional dependencies
pip install -e ".[dev,clipboard]"

# Run tests
python -m unittest discover tests
```

This will install the package in editable mode so changes to the code will be immediately reflected when running the tool.

#### Publishing to PyPI

To publish a new version of `repindex` to PyPI:

1. **Update the Version Number**:  
   Update the `__version__` in your `repindex/__init__.py` or wherever the version is defined.

2. **Install Build Tools**:
   ```bash
   pip install build twine
   ```

3. **Create a Distribution**:
   ```bash
   python3 -m build
   ```
   This command will generate source and wheel distributions in the `dist/` directory.

4. **Upload to PyPI**:
   Make sure you have a valid PyPI account and have configured your `.pypirc` file if needed. Then:
   ```bash
   twine upload dist/*
   ```
   
   You will be prompted for your PyPI username and password (or token).

5. **Verify Installation**:
   After a successful upload:
   ```bash
   pip install --upgrade repindex
   ```

# Skip Patterns

The `--skip` option allows you to specify patterns of files or directories to exclude from indexing. Multiple patterns can be provided as a comma-separated list.

## Skip Pattern Syntax

Patterns use glob syntax with the following features:

- `*` - Matches any sequence of characters (except path separators)
- `?` - Matches any single character
- `dirname/*` - Excludes all files and subdirectories inside `dirname`

## Examples

```bash
# Skip all log files and the entire docs directory
repindex ./my_project --skip "*.log,docs/*"

# Skip Python cache files and temporary files
repindex ./my_project --skip "__pycache__/*,*.pyc,*.tmp"

# Skip multiple directories
repindex ./my_project --skip "node_modules/*,dist/*,build/*" 
```

## How Skip Patterns Work

When a skip pattern ends with `/*` (e.g., `logs/*`), it will:
1. Exclude the directory itself from tree generation
2. Skip all files inside that directory from being indexed
3. Prevent any subdirectories from being traversed

Skip patterns are applied to:
- Tree representation
- File dependencies 
- Single document generation
- All indexed outputs

---