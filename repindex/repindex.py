#!/usr/bin/env python3

import argparse
import ast
import datetime
import difflib
import hashlib
import json
import os
import re
import sys

#############################################
# Utility Functions
#############################################

def compute_file_hash(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def detect_language_type(root_dir, forced_lang=None):
    if forced_lang:
        return [forced_lang]

    langs = []
    # React/Node detection
    if os.path.exists(os.path.join(root_dir, 'package.json')):
        langs.append('react')
    # Python detection
    if (os.path.exists(os.path.join(root_dir, 'pyproject.toml')) or
        os.path.exists(os.path.join(root_dir, 'requirements.txt')) or
        os.path.exists(os.path.join(root_dir, 'setup.py'))):
        langs.append('python')

    return langs

def should_ignore(path, langs, no_ignore=False):
    if no_ignore:
        return False
    basename = os.path.basename(path)
    # Hidden directories
    if basename.startswith('.'):
        return True
    # React: ignore node_modules
    if 'react' in langs and basename == 'node_modules':
        return True
    # Python: ignore __pycache__, env, venv
    if 'python' in langs and basename in ['__pycache__', 'env', 'venv']:
        return True
    return False

def detect_code_fence_language(filename):
    if filename.endswith(('.ts', '.tsx')):
        return 'typescript'
    elif filename.endswith('.py'):
        return 'python'
    elif filename.endswith('.sh'):
        return 'bash'
    elif filename.endswith('.css'):
        return 'css'
    return ''

#############################################
# Dependency Extraction
#############################################

def add_ast_parents(node):
    for child in ast.iter_child_nodes(node):
        child.parent = node
        add_ast_parents(child)

def parse_python_structure(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    tree = ast.parse(content)
    tree.parent = None
    add_ast_parents(tree)

    imports = []
    functions = []
    classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module if node.module else ''
            for n in node.names:
                full_name = module + '.' + n.name if module else n.name
                imports.append(full_name)
        elif isinstance(node, ast.FunctionDef):
            if isinstance(node.parent, ast.Module):
                functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            class_methods = []
            for body_item in node.body:
                if isinstance(body_item, ast.FunctionDef):
                    class_methods.append(body_item.name)
            classes.append({
                "name": node.name,
                "methods": class_methods
            })

    # Exports: top-level functions and classes
    exports = functions + [c['name'] for c in classes]

    structure = {
        "language": "python",
        "functions": functions,
        "classes": classes
    }

    return imports, exports, structure

def extract_dependencies_ts(file_path):
    dependencies = {'imports': [], 'exports': [], 'structure': {}}
    import_pattern = r'import\s+(?:[\s\S]*?)from\s+[\'"](.+?)[\'"];'
    export_pattern = r'export\s+(?:default\s+)?(?:class|function|const|let|var|interface|type|enum)?\s*([\w]+)'

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        imports = re.findall(import_pattern, content)
        exports = re.findall(export_pattern, content)

    dependencies['imports'].extend(imports)
    dependencies['exports'].extend(exports)
    dependencies['structure'] = {
        "language": "typescript",
        "functions": exports,
        "classes": []
    }
    return dependencies

def extract_dependencies_python(file_path):
    dependencies = {'imports': [], 'exports': [], 'structure': {}}
    imports, exports, structure = parse_python_structure(file_path)
    dependencies['imports'] = imports
    dependencies['exports'] = exports
    dependencies['structure'] = structure
    return dependencies

def extract_dependencies(file_path, langs):
    ext = os.path.splitext(file_path)[1]
    if ext in ['.ts', '.tsx']:
        return extract_dependencies_ts(file_path)
    elif ext == '.py':
        return extract_dependencies_python(file_path)
    else:
        return {'imports': [], 'exports': [], 'structure': {}}

#############################################
# Building the Dependency Graph
#############################################

def resolve_import_path(file, imp, root_dir):
    if imp.startswith('.'):
        base = os.path.dirname(file)
        candidate = os.path.normpath(os.path.join(base, imp))
        exts = ['.ts', '.tsx', '.py']
        if os.path.isdir(os.path.join(root_dir, candidate)):
            possible_files = ['index.ts', 'index.tsx', '__init__.py']
            for pf in possible_files:
                pfp = os.path.join(candidate, pf)
                if os.path.exists(os.path.join(root_dir, pfp)):
                    return pfp
            return candidate
        else:
            if not any(candidate.endswith(e) for e in exts):
                for e in exts:
                    if os.path.exists(os.path.join(root_dir, candidate + e)):
                        return candidate + e
            return candidate
    else:
        base_candidate = os.path.join(root_dir, imp.replace('.', os.sep))
        exts = ['.ts', '.tsx', '.py']
        for e in exts:
            if os.path.exists(base_candidate + e):
                return os.path.relpath(base_candidate + e, root_dir)
        return imp

def build_dependency_graph(root_dir, langs, graph_type='full', no_ignore=False):
    graph = {'nodes': [], 'edges': []}
    file_dependencies = {}

    exts = ['.ts', '.tsx', '.py']
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if not should_ignore(os.path.join(dirpath, d), langs, no_ignore)]
        for filename in filenames:
            if os.path.splitext(filename)[1] in exts:
                filepath = os.path.join(dirpath, filename)
                relative_path = os.path.relpath(filepath, root_dir)
                if relative_path not in graph['nodes']:
                    graph['nodes'].append(relative_path)
                deps = extract_dependencies(filepath, langs)
                file_dependencies[relative_path] = deps

    for file, deps in file_dependencies.items():
        if graph_type in ['full', 'imports_only']:
            for imp in deps['imports']:
                target = resolve_import_path(file, imp, root_dir)
                if target in graph['nodes']:
                    edge = {'from': file, 'to': target, 'type': 'import'}
                    if graph_type != 'no_objects':
                        edge['objects'] = deps['imports']
                    graph['edges'].append(edge)
        if graph_type in ['full', 'exports_only']:
            if deps['exports']:
                edge = {'from': file, 'to': None, 'type': 'export'}
                if graph_type != 'no_objects':
                    edge['objects'] = deps['exports']
                graph['edges'].append(edge)

    return graph, file_dependencies

#############################################
# Documentation Generation
#############################################

def generate_tree(root_dir, prefix='', langs=[], no_ignore=False):
    tree = ''
    entries = sorted(os.listdir(root_dir))
    filtered_entries = []
    for entry in entries:
        path = os.path.join(root_dir, entry)
        if os.path.isdir(path):
            if should_ignore(path, langs, no_ignore):
                continue
        filtered_entries.append(entry)

    for idx, entry in enumerate(filtered_entries):
        path = os.path.join(root_dir, entry)
        connector = '├── ' if idx < len(filtered_entries)-1 else '└── '
        tree += f"{prefix}{connector}{entry}\n"
        if os.path.isdir(path):
            extension = '│   ' if idx < len(filtered_entries)-1 else '    '
            tree += generate_tree(path, prefix+extension, langs, no_ignore)
    return tree

def generate_markdown(root_dir, langs, no_ignore=False):
    markdown = ''
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if not should_ignore(os.path.join(dirpath, d), langs, no_ignore)]
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            relative_path = os.path.relpath(filepath, root_dir)
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                language = detect_code_fence_language(filename)
                markdown += f"### {relative_path}\n\n```{language}\n{content}\n```\n\n"
            except (UnicodeDecodeError, IOError):
                markdown += f"### {relative_path}\n\nError reading file.\n\n"
    return markdown

def generate_light_markdown(root_dir, langs, no_ignore=False):
    markdown = ''
    code_extensions = ('.ts', '.tsx', '.css', '.py', '.sh')
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if not should_ignore(os.path.join(dirpath, d), langs, no_ignore)]
        for filename in filenames:
            if filename.endswith(code_extensions):
                filepath = os.path.join(dirpath, filename)
                relative_path = os.path.relpath(filepath, root_dir)
                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        content = file.read()
                    language = detect_code_fence_language(filename)
                    markdown += f"### {relative_path}\n\n```{language}\n{content}\n```\n\n"
                except (UnicodeDecodeError, IOError):
                    markdown += f"### {relative_path}\n\nError reading file.\n\n"
    return markdown

#############################################
# Structure Files
#############################################

def generate_structure_files(file_dependencies, output_path):
    detailed = {}
    top_level = {}
    for f, deps in file_dependencies.items():
        detailed[f] = deps['structure']
        top_level[f] = {
            "imports": deps['imports'],
            "exports": deps['exports']
        }

    with open(os.path.join(output_path, 'detailed_structure.json'), 'w', encoding='utf-8') as dfile:
        json.dump(detailed, dfile, indent=4)
    with open(os.path.join(output_path, 'top_level_structure.json'), 'w', encoding='utf-8') as tfile:
        json.dump(top_level, tfile, indent=4)

#############################################
# Incremental Indexing & Diff
#############################################

def load_cache(cache_file):
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"files": {}}

def save_cache(cache, cache_file):
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=4)

def generate_diff(old_content, new_content):
    diff = difflib.unified_diff(
        old_content.splitlines(),
        new_content.splitlines(),
        lineterm='',
        fromfile='old',
        tofile='new'
    )
    return "\n".join(diff)

def update_cache_and_generate_diff(root_dir, langs, no_ignore, output_path, no_cache=False):
    cache_file = os.path.join(output_path, 'repindex_cache.json')
    if no_cache:
        if os.path.exists(cache_file):
            os.remove(cache_file)
        return

    cache = load_cache(cache_file)
    old_files = cache.get('files', {})

    current_files = {}
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if not should_ignore(os.path.join(dirpath, d), langs, no_ignore)]
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                fhash = compute_file_hash(content)
                current_files[os.path.relpath(filepath, root_dir)] = {
                    "hash": fhash,
                    "content": content
                }
            except:
                # If can't read, skip
                pass

    changed = []
    for f, data in current_files.items():
        old_data = old_files.get(f)
        if not old_data or old_data['hash'] != data['hash']:
            changed.append(f)

    removed = [f for f in old_files if f not in current_files]

    if changed or removed:
        changes_file = os.path.join(output_path, 'repindex_changes.md')
        with open(changes_file, 'w', encoding='utf-8') as cf:
            cf.write(f"# Changes since last run ({datetime.datetime.now().isoformat()})\n\n")

            if changed:
                cf.write("## Changed or New Files:\n\n")
                for f in changed:
                    cf.write(f"### {f}\n\n")
                    new_content = current_files[f]['content']
                    old_content = old_files.get(f, {}).get('content', '')
                    diff = generate_diff(old_content, new_content)
                    if diff.strip():
                        cf.write("```diff\n" + diff + "\n```\n\n")
                    else:
                        cf.write("_No diff available (new file)_\n\n")

            if removed:
                cf.write("## Removed Files:\n\n")
                for f in removed:
                    cf.write(f"- {f}\n")

    new_cache = {
        "files": {f: {"hash": d["hash"]} for f, d in current_files.items()},
        "timestamp": datetime.datetime.now().isoformat()
    }
    save_cache(new_cache, cache_file)

#############################################
# Context Extraction
#############################################

def gather_dependencies_for_files(root_dir, langs, no_ignore, target_files):
    graph, file_deps = build_dependency_graph(root_dir, langs, 'full', no_ignore)
    involved = set()

    def recurse(f):
        if f in involved:
            return
        involved.add(f)
        for e in graph['edges']:
            if e['from'] == f and e['type'] == 'import' and e['to'] is not None:
                recurse(e['to'])

    for tf in target_files:
        if tf in graph['nodes']:
            recurse(tf)
        else:
            pass

    return involved, file_deps

def generate_context_file(root_dir, involved, file_deps, target_files, output_path):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    context_file = os.path.join(output_path, f"context_{ts}.md")

    with open(context_file, 'w', encoding='utf-8') as cf:
        cf.write(f"# Context for Files: {', '.join(target_files)}\n\n")
        cf.write("## Involved Files\n\n")
        for f in sorted(involved):
            marker = "(TARGET)" if f in target_files else ""
            cf.write(f"- {f} {marker}\n")

        cf.write("\n## File Contents\n\n")
        # main files first
        for f in target_files:
            fullpath = os.path.join(root_dir, f)
            if os.path.exists(fullpath):
                with open(fullpath, 'r', encoding='utf-8') as file:
                    content = file.read()
                language = detect_code_fence_language(os.path.basename(fullpath))
                cf.write(f"### {f} (Main)\n\n```{language}\n{content}\n```\n\n")
                deps = file_deps.get(f, {})
                if 'structure' in deps:
                    cf.write("#### Structure\n\n```json\n" + json.dumps(deps['structure'], indent=4) + "\n```\n\n")

        for f in sorted(involved):
            if f not in target_files:
                fullpath = os.path.join(root_dir, f)
                if os.path.exists(fullpath):
                    with open(fullpath, 'r', encoding='utf-8') as file:
                        content = file.read()
                    language = detect_code_fence_language(os.path.basename(fullpath))
                    cf.write(f"### {f}\n\n```{language}\n{content}\n```\n\n")
                    deps = file_deps.get(f, {})
                    if 'structure' in deps:
                        cf.write("#### Structure\n\n```json\n" + json.dumps(deps['structure'], indent=4) + "\n```\n\n")

    return context_file

#############################################
# Main CLI
#############################################

def main():
    parser = argparse.ArgumentParser(description='Index a repository and generate structured outputs.')
    parser.add_argument('repository_path', help='Path to the repository to index')
    parser.add_argument('-o', '--output_dir', default='.', help='Output directory (default: current directory)')
    parser.add_argument('--lang', help='Force a specific language (e.g., python, react)')
    parser.add_argument('--no-ignore', action='store_true', help='Do not ignore default ignored directories')
    parser.add_argument('--no-cache', action='store_true', help='Disable caching and diff generation')
    parser.add_argument('--context-for', nargs='+', help='Generate a context file for the specified file(s)')
    parser.add_argument('--minimal', action='store_true', help='Produce minimal outputs (skip docs, etc.)')

    args = parser.parse_args()

    repo_path = args.repository_path
    output_dir = args.output_dir
    output_path = os.path.join(output_dir, 'repindex')

    if not os.path.isdir(repo_path):
        print(f"Error: The repository path '{repo_path}' does not exist or is not a directory.")
        sys.exit(1)

    os.makedirs(output_path, exist_ok=True)

    langs = detect_language_type(repo_path, forced_lang=args.lang)

    if args.context_for:
        involved, file_deps = gather_dependencies_for_files(repo_path, langs, args.no_ignore, args.context_for)
        context_file = generate_context_file(repo_path, involved, file_deps, args.context_for, output_path)
        print(f"Context file generated at: {context_file}")
        sys.exit(0)

    # Full indexing mode
    print("Detecting structure...")
    tree_output = generate_tree(repo_path, langs=langs, no_ignore=args.no_ignore)

    if not args.minimal:
        with open(os.path.join(output_path, 'tree_structure.txt'), 'w', encoding='utf-8') as tree_file:
            tree_file.write(os.path.basename(repo_path) + '\n')
            tree_file.write(tree_output)

    print("Building dependency graphs...")
    dependency_graph_full, file_deps = build_dependency_graph(repo_path, langs, 'full', args.no_ignore)
    dependency_graph_imports, _ = build_dependency_graph(repo_path, langs, 'imports_only', args.no_ignore)
    dependency_graph_exports, _ = build_dependency_graph(repo_path, langs, 'exports_only', args.no_ignore)
    dependency_graph_no_objects, _ = build_dependency_graph(repo_path, langs, 'no_objects', args.no_ignore)

    if not args.minimal:
        with open(os.path.join(output_path, 'dependency_graph_full.json'), 'w', encoding='utf-8') as jf:
            json.dump(dependency_graph_full, jf, indent=4)
        with open(os.path.join(output_path, 'dependency_graph_imports.json'), 'w', encoding='utf-8') as jf:
            json.dump(dependency_graph_imports, jf, indent=4)
        with open(os.path.join(output_path, 'dependency_graph_exports.json'), 'w', encoding='utf-8') as jf:
            json.dump(dependency_graph_exports, jf, indent=4)
        with open(os.path.join(output_path, 'dependency_graph_no_objects.json'), 'w', encoding='utf-8') as jf:
            json.dump(dependency_graph_no_objects, jf, indent=4)

        generate_structure_files(file_deps, output_path)

        print("Generating Markdown documentation...")
        markdown_output = generate_markdown(repo_path, langs, args.no_ignore)
        with open(os.path.join(output_path, 'documentation.md'), 'w', encoding='utf-8') as md_file:
            md_file.write(markdown_output)
        print("Markdown documentation generated.")

        print("Generating light Markdown documentation...")
        markdown_light_output = generate_light_markdown(repo_path, langs, args.no_ignore)
        with open(os.path.join(output_path, 'documentation_light.md'), 'w', encoding='utf-8') as md_file:
            md_file.write(markdown_light_output)
        print("Light Markdown documentation generated.")

    print("Updating cache and generating diffs if needed...")
    update_cache_and_generate_diff(repo_path, langs, args.no_ignore, output_path, no_cache=args.no_cache)

    print(f"All outputs have been saved to '{output_path}'.")


if __name__ == "__main__":
    main()