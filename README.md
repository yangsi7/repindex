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

## Installation

Install `repindex` using `pip`:

```bash
pip install repindex
```

Usage

repindex /path/to/repository [-o /path/to/output_dir]

	•	repository_path: The path to the repository you want to index.
	•	-o, --output_dir: (Optional) The directory where outputs will be saved. Defaults to the current directory.

Example

repindex ./my_project -o ./output

Outputs

The outputs are saved in a repindex/ directory inside the specified output directory:
	•	tree_structure.txt: Tree representation of the repository.
	•	Dependency Graphs:
	•	dependency_graph_full.json: Full graph with imports and exports, including objects.
	•	dependency_graph_imports.json: Only imports with objects listed.
	•	dependency_graph_exports.json: Only exports with objects listed.
	•	dependency_graph_no_objects.json: All relationships without listing objects.
	•	Markdown Documentation:
	•	documentation.md: Full documentation with all files and contents.
	•	documentation_light.md: Light documentation including only code files.

Running Tests

To run the unit tests:

python -m unittest discover tests

Code Style

The code adheres to PEP8 standards. You can check code style using flake8:

pip install flake8
flake8 repindex tests

Continuous Integration

Continuous Integration is set up using GitHub Actions. The workflow runs tests and linting on each push and pull request.

License

This project is licensed under the MIT License.

Author

	•	Simon Yang
	•	GitHub: yangsi7

Contributing

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

Acknowledgments

	•	Thanks to Me, Myself and I, who have helped improve this project.

---
