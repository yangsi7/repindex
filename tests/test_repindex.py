import os
import shutil
import tempfile
import unittest
from repindex import repindex

class TestRepindex(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory with test files
        self.test_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_dir, 'subdir'))

        files = {
            'file1.ts': 'import { func } from "./file2";\nexport const x = 1;',
            'file2.ts': 'export function func() {}',
            'file3.py': 'print("Hello, world!")',
            'file4.txt': 'Just some text.',
            'subdir/file5.sh': '#!/bin/bash\necho "Hello"',
        }

        for filename, content in files.items():
            filepath = os.path.join(self.test_dir, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(content)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_generate_tree(self):
        tree = repindex.generate_tree(self.test_dir, langs=[])
        self.assertIn('file1.ts', tree)
        self.assertIn('subdir', tree)

    def test_extract_dependencies(self):
        file1 = os.path.join(self.test_dir, 'file1.ts')
        deps = repindex.extract_dependencies(file1, langs=['react'])
        self.assertIn('./file2', deps['imports'])
        self.assertIn('x', deps['exports'])

    def test_build_dependency_graph(self):
        graph, _ = repindex.build_dependency_graph(self.test_dir, langs=['react'])
        self.assertIn('file1.ts', graph['nodes'])
        self.assertIn('file2.ts', graph['nodes'])
        self.assertTrue(any(edge['from'] == 'file1.ts' for edge in graph['edges']))

    def test_generate_markdown(self):
        markdown = repindex.generate_markdown(self.test_dir, langs=[])
        self.assertIn('### file1.ts', markdown)
        self.assertIn('import { func } from "./file2";', markdown)

    def test_generate_light_markdown(self):
        markdown = repindex.generate_light_markdown(self.test_dir, langs=[])
        self.assertIn('### file1.ts', markdown)
        self.assertNotIn('### file4.txt', markdown)
        self.assertIn('```python\nprint("Hello, world!")', markdown)
        self.assertIn('```bash\n#!/bin/bash\necho "Hello"', markdown)

if __name__ == '__main__':
    unittest.main()