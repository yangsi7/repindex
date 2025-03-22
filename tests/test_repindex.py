import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from repindex import repindex

class TestRepindex(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_dir, 'subdir'))
        os.makedirs(os.path.join(self.test_dir, 'node_modules'))
        os.makedirs(os.path.join(self.test_dir, 'dist'))

        files = {
            'file1.ts': 'import { func } from "./file2";\nexport const x = 1;',
            'file2.ts': 'export function func() {}',
            'file3.py': 'print("Hello, world!")',
            'file4.txt': 'Just some text.',
            'subdir/file5.sh': '#!/bin/bash\necho "Hello"',
            'node_modules/package.json': '{"name": "test"}',
            'dist/build.js': 'console.log("build");',
        }
        for filename, content in files.items():
            fp = os.path.join(self.test_dir, filename)
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, 'w') as f:
                f.write(content)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_generate_tree(self):
        tree = repindex.generate_tree_text(self.test_dir, '', langs=[], debug=False)
        self.assertIn('file1.ts', tree)
        self.assertIn('subdir', tree)

    def test_extract_dependencies(self):
        file1 = os.path.join(self.test_dir, 'file1.ts')
        deps = repindex.extract_dependencies(file1, langs=['react'])
        self.assertIn('./file2', deps['imports'])
        self.assertIn('x', deps['exports'])

    def test_build_dependency_graph(self):
        graph, _ = repindex.build_dependency_graph(self.test_dir, langs=['react'], debug=False)
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
        
    def test_should_ignore(self):
        # Test default ignores
        self.assertTrue(repindex.should_ignore(os.path.join(self.test_dir, 'node_modules'), langs=['react'], debug=False))
        self.assertTrue(repindex.should_ignore(os.path.join(self.test_dir, 'dist'), langs=[], debug=False))
        
        # Test skip patterns
        self.assertTrue(repindex.should_ignore(
            os.path.join(self.test_dir, 'file1.ts'), 
            langs=[], 
            skip_patterns=['*.ts'],
            debug=False
        ))
        
        # Test no_ignore flag
        self.assertFalse(repindex.should_ignore(
            os.path.join(self.test_dir, 'node_modules'), 
            langs=['react'], 
            no_ignore=True,
            debug=False
        ))
        
    def test_single_doc_generation(self):
        doc = repindex.generate_single_context_markdown(self.test_dir, langs=[], no_ignore=False, skip_patterns=None, debug=False)
        self.assertIn('# Repository Overview', doc)
        self.assertIn('## Folder Tree', doc)
        self.assertIn('## Indexed Files', doc)
        self.assertIn('file1.ts', doc)
        # The path in the tree is not fully qualified
        self.assertIn('└── file5.sh', doc)
        self.assertNotIn('node_modules/package.json', doc)  # Should be ignored
        
    def test_clipboard_functionality(self):
        # Mock the HAS_CLIPBOARD flag
        with patch('repindex.repindex.HAS_CLIPBOARD', True):
            # Mock sys.exit to prevent exiting during test
            with patch('sys.exit'):
                with patch('pyperclip.copy') as mock_copy:
                    # Create args with copy_to_clipboard enabled
                    mock_args = type('Namespace', (), {
                        'repository_path': self.test_dir,
                        'output_dir': '.',
                        'single_doc': True,
                        'copy_to_clipboard': True,
                        'lang': None,
                        'no_ignore': False,
                        'no_cache': True,
                        'context_for': None,
                        'minimal': False,
                        'skip': '',
                        'debug': False
                    })
                    
                    # Patch parser to return our args
                    with patch('argparse.ArgumentParser.parse_args', return_value=mock_args):
                        with patch('builtins.print') as mock_print:
                            repindex.main()
                            mock_copy.assert_called_once()
                            mock_print.assert_any_call("Single doc copied to clipboard.")
    
    def test_skip_patterns(self):
        # Test a basic extension pattern
        file_ts = os.path.join(self.test_dir, 'file1.ts')
        self.assertTrue(repindex.should_ignore(file_ts, langs=[], skip_patterns=['*.ts'], debug=False))
        
        # Test an exact basename pattern
        self.assertTrue(repindex.should_ignore(file_ts, langs=[], skip_patterns=['file1.ts'], debug=False))
        
        # Test a wildcard pattern for files in a directory
        file_sh = os.path.join(self.test_dir, 'subdir', 'file5.sh')
        # This one's a bit tricky - we need to make the pattern relative to where fnmatch is looking
        self.assertTrue(repindex.should_ignore(file_sh, langs=[], skip_patterns=['file5.*'], debug=False))
