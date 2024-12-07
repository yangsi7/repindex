#!/usr/bin/env python3

import argparse
import json
import os
import re
import sys

def generate_tree(root_dir, prefix='', ignored_folders=None):
    if ignored_folders is None:
        ignored_folders = []
    tree = ''
    entries = sorted(
        [e for e in os.listdir(root_dir) if e not in ignored_folders]
    )
    for idx, entry in enumerate(entries):
        path = os.path.join(root_dir, entry)
        connector = '├── ' if idx < len(entries) - 1 else '└── '
        tree += f"{prefix}{connector}{entry}\n"
        if os.path.isdir(path):
            extension = '│   ' if idx < len(entries) - 1 else '    '
            tree += generate_tree(path, prefix + extension, ignored_folders)
    return tree

def extract_dependencies(file_path):
    dependencies = {'imports': [], 'exports': []}
    import_pattern = r'import\s+(?:[\s\S]*?)from\s+[\'"](.+?)[\'"];'
    export_pattern = (
        r'export\s+(?:default\s+)?'
        r'(?:class|function|const|let|var|interface|type|enum)?\s*([\w]+)'
    )

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            imports = re.findall(import_pattern, content)
            exports = re.findall(export_pattern, content)
            dependencies['imports'].extend(imports)
            dependencies['exports'].extend(exports)
    except (UnicodeDecodeError, IOError) as e:
        print(f"Warning: Could not read file {file_path}: {str(e)}")
    return dependencies

def build_dependency_graph(root_dir, graph_type='full', ignored_folders=None):
    if ignored_folders is None:
        ignored_folders = []

    graph = {'nodes': [], 'edges': []}
    file_dependencies = {}
    file_paths = {}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Filter out ignored directories
        dirnames[:] = [d for d in dirnames if d not in ignored_folders]

        for filename in filenames:
            if filename.endswith(('.ts', '.tsx')):
                filepath = os.path.join(dirpath, filename)
                relative_path = os.path.relpath(filepath, root_dir)
                if relative_path not in graph['nodes']:
                    graph['nodes'].append(relative_path)
                deps = extract_dependencies(filepath)
                file_dependencies[relative_path] = deps

    for file, deps in file_dependencies.items():
        if graph_type in ['full', 'imports_only']:
            for imp in deps['imports']:
                # Resolve imported file path
                if imp.startswith('.'):
                    imported_file = os.path.normpath(
                        os.path.join(os.path.dirname(file), imp)
                    )
                    if os.path.isdir(os.path.join(root_dir, imported_file)):
                        imported_file = os.path.join(imported_file, 'index.ts')
                    else:
                        if not any(imported_file.endswith(ext)
                                   for ext in ['.ts', '.tsx']):
                            imported_file += '.ts'
                else:
                    imported_file = imp  # External module or alias

                if imported_file in graph['nodes']:
                    edge = {
                        'from': file,
                        'to': imported_file,
                        'type': 'import',
                    }
                    if graph_type != 'no_objects':
                        edge['objects'] = deps['imports']
                    graph['edges'].append(edge)

        if graph_type in ['full', 'exports_only']:
            for exp in deps['exports']:
                edge = {
                    'from': file,
                    'to': None,
                    'type': 'export',
                }
                if graph_type != 'no_objects':
                    edge['objects'] = deps['exports']
                graph['edges'].append(edge)

    return graph

def detect_language(filename):
    if filename.endswith(('.ts', '.tsx')):
        return 'typescript'
    elif filename.endswith('.py'):
        return 'python'
    elif filename.endswith('.sh'):
        return 'bash'
    elif filename.endswith('.css'):
        return 'css'
    else:
        return ''

def generate_markdown(root_dir, ignored_folders=None):
    if ignored_folders is None:
        ignored_folders = []

    markdown = ''
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Filter out ignored directories
        dirnames[:] = [d for d in dirnames if d not in ignored_folders]

        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            relative_path = os.path.relpath(filepath, root_dir)
            markdown += f"### {relative_path}\n\n"
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                    language = detect_language(filename)
                    markdown += f"```{language}\n{content}\n```\n\n"
            except (UnicodeDecodeError, IOError) as e:
                print(f"Warning: Could not read file {filepath}: {str(e)}")
                markdown += f"\nError: Could not read file content\n\n\n"
    return markdown

def generate_light_markdown(root_dir, ignored_folders=None):
    if ignored_folders is None:
        ignored_folders = []

    markdown = ''
    code_extensions = ('.ts', '.tsx', '.css', '.py', '.sh')
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Filter out ignored directories
        dirnames[:] = [d for d in dirnames if d not in ignored_folders]

        for filename in filenames:
            if filename.endswith(code_extensions):
                filepath = os.path.join(dirpath, filename)
                relative_path = os.path.relpath(filepath, root_dir)
                markdown += f"### {relative_path}\n\n"
                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        content = file.read()
                        language = detect_language(filename)
                        markdown += f"```{language}\n{content}\n```\n\n"
                except (UnicodeDecodeError, IOError) as e:
                    print(f"Warning: Could not read file {filepath}: {str(e)}")
                    markdown += f"\nError: Could not read file content\n\n\n"
    return markdown

def main():
    parser = argparse.ArgumentParser(
        description='Index a repository and generate structured outputs.'
    )
    parser.add_argument(
        'repository_path', help='Path to the repository to index'
    )
    parser.add_argument(
        '-o', '--output_dir',
        default='.',
        help='Output directory (default: current directory)'
    )
    parser.add_argument(
        '--ignore',
        default='',
        help='Comma-separated list of directories to ignore'
    )

    args = parser.parse_args()

    repo_path = args.repository_path
    output_dir = args.output_dir
    ignored_folders = [f.strip() for f in args.ignore.split(',') if f.strip()]
    output_path = os.path.join(output_dir, 'repindex')

    if not os.path.isdir(repo_path):
        print(
            f"Error: The repository path '{repo_path}' "
            f"does not exist or is not a directory."
        )
        sys.exit(1)

    os.makedirs(output_path, exist_ok=True)

    # Step 1: Generate repository structure
    print("Generating repository structure...")
    tree_output = generate_tree(repo_path, ignored_folders=ignored_folders)
    with open(
        os.path.join(output_path, 'tree_structure.txt'),
        'w',
        encoding='utf-8'
    ) as tree_file:
        tree_file.write(os.path.basename(repo_path) + '\n')
        tree_file.write(tree_output)
    print("Repository structure generated.")

    # Step 2: Generate dependency graphs
    print("Building dependency graphs...")

    # Full graph
    dependency_graph_full = build_dependency_graph(
        repo_path, graph_type='full', ignored_folders=ignored_folders
    )
    with open(
        os.path.join(output_path, 'dependency_graph_full.json'),
        'w',
        encoding='utf-8'
    ) as json_file:
        json.dump(dependency_graph_full, json_file, indent=4)

    # Imports only graph
    dependency_graph_imports = build_dependency_graph(
        repo_path, graph_type='imports_only', ignored_folders=ignored_folders
    )
    with open(
        os.path.join(output_path, 'dependency_graph_imports.json'),
        'w',
        encoding='utf-8'
    ) as json_file:
        json.dump(dependency_graph_imports, json_file, indent=4)

    # Exports only graph
    dependency_graph_exports = build_dependency_graph(
        repo_path, graph_type='exports_only', ignored_folders=ignored_folders
    )
    with open(
        os.path.join(output_path, 'dependency_graph_exports.json'),
        'w',
        encoding='utf-8'
    ) as json_file:
        json.dump(dependency_graph_exports, json_file, indent=4)

    # No objects graph
    dependency_graph_no_objects = build_dependency_graph(
        repo_path, graph_type='no_objects', ignored_folders=ignored_folders
    )
    with open(
        os.path.join(output_path, 'dependency_graph_no_objects.json'),
        'w',
        encoding='utf-8'
    ) as json_file:
        json.dump(dependency_graph_no_objects, json_file, indent=4)

    print("Dependency graphs created.")

    # Step 3: Generate Markdown documentation
    print("Generating Markdown documentation...")
    markdown_output = generate_markdown(repo_path, ignored_folders=ignored_folders)
    with open(
        os.path.join(output_path, 'documentation.md'),
        'w',
        encoding='utf-8'
    ) as md_file:
        md_file.write(markdown_output)
    print("Markdown documentation generated.")

    # Generate light Markdown documentation
    print("Generating light Markdown documentation...")
    markdown_light_output = generate_light_markdown(repo_path, ignored_folders=ignored_folders)
    with open(
        os.path.join(output_path, 'documentation_light.md'),
        'w',
        encoding='utf-8'
    ) as md_file:
        md_file.write(markdown_light_output)
    print("Light Markdown documentation generated.")

    print(f"All outputs have been saved to '{output_path}'.")


if __name__ == "__main__":
    main()