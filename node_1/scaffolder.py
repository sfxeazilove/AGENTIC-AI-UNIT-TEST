import os
import json
import ast
import re
from pathlib import Path
from typing import Dict, List, Optional , TypedDict, Any
from dataclasses import dataclass
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

class AutoCoverState(TypedDict):
    #input
    source_code : str
    file_path: str

    #scaffolder output
    project_context: Dict[str, Any]
    test_framework: str
    existing_patterns: Dict[str, Any]
    dependencies: List[str]
    target_functions: List[Dict[str, Any]]

    #Later pipeline outputs
    generated_tests: Optional[str]
    generation_attempt: int
    test_results: Optional[Dict]
    build_success: Optional[bool]
    test_failures: Optional[List[str]]
    fixed_tests: Optional[str]
    fix_attempt: int

    #control flow
    max_iterations: int
    current_iteration: int
    is_complete: bool


@dataclass
class ProjectConfig:
    language: str
    test_framework: str
    test_directory: str
    test_file_pattern: str
    source_directory: str
    dependencies: List[str]
    build_tool: Optional[str] = None

class CodeAnalyzer:
    """Analyzes source code to extract functions classes and structure"""

    def __init__(self):
        self.parsers = {
            "python": self._setup_parser(Language(tspython.language())),
            "javascript": self._setup_parser(Language(tsjavascript.language())),
            "typescript": self._setup_parser(Language(tsjavascript.language())),
            "java" : self._setup_parser(Language(tsjava.language()))
        }

    def _setup_parser(self, language: Language) -> Parser:
        parser = Parser()
        parser.language = language  # Changed from parser.set_language(language)
        return parser
    
    def extract_functions(self, code: str, language: str) -> List[Dict[str, Any]]:
        """Extract function definitions from source code"""
        if language not in self.parsers:
            return self._fallback_extract_functions(code, language)
        
        parser = self.parsers[language]
        tree = parser.parse(bytes(code, 'utf8'))

        functions=[]
        self._traverse_tree(tree.root_node, code, functions, language)
        return functions
    
    def _traverse_tree(self, node, code: str, functions:List, language:str):
        """Recursively traverse AST to find function definitions"""
        if self._is_function_node(node, language):
            func_info = self._extract_function_info(node, code, language)
            if func_info:
                functions.append(func_info)
        
        for child in node.children:
            self._traverse_tree(child, code, functions, language)

    def _is_function_node(self, node, language: str) -> bool:
        """check if node represents a function definition"""
        function_types = {
            'python' : ['function_definition'],
            'javascript' : ['function_declaration', 'method_definition', 'arrow_function'],
            'typescript' : ['function_declaration', 'method_definition', 'arrow_function'],
            'java' : ['method_declaration']
        }
        return node.type in function_types.get(language, [])
    
    def _extract_function_info(self, node, code:str, language: str) -> Optional[Dict[str, Any]]:
        """Extract detailed information about a function"""
        try:
            start_byte = node.start_byte
            end_byte = node.end_byte
            function_code = code[start_byte:end_byte]

            #extract function name
            name = self._get_function_name(node, language)
            if not name:
                return None
            #Extract parameters
            params = self._get_function_parameters(node, language)

            #Extract return type hints (if available)
            return_type = self._get_return_type(node, language)

            #Extract docstring/comments
            docstring = self._get_docstring(node, code, language)

            return {
                'name': name,
                'parameters':params,
                'return_type':return_type,
                'docstring': docstring,
                'code' : function_code,
                'start_line' : node.start_point[0] + 1,
                'end_line' : node.end_point[0] + 1,
                'complexity' : self._estimate_complexity(function_code)
            }
        except Exception as e:
            print(f"Error extracting function info: {e}")
            return None
        
    def _get_function_name(self, node, language: str) -> Optional[str]:
        """Extract function name from AST node"""
        for child in node.children:
            if child.type =='identifier':
                return child.text.decode('utf8')
        return None
    
    def _get_function_parameters(self, node, language:str) -> List[Dict[str, Any]]:
        """Extract function parameters"""
        params = []

        #find parameter list node
        param_node = None
        for child in node.children:
            if child.type == 'parameters' or child.type == 'parameter_list':
                param_node = child
                break
            if not param_node:
                return params
            
            #extract indvidual parameters
            for child in param_node.children:
                if child.type == 'identifier':
                    #simple parameter
                    params.append({
                        'name': child.text.decode('utf8'),
                        'type': None,
                        'default':None,
                        'required': True
                    })

                elif child.type == 'typed_parameter' or child.type == 'default_parameter':
                    #parameter with type annotation or default value
                    param_info = self._parse_complex_parameter(child, language)
                    if param_info:
                        params.append(param_info)

        return params
    
    def _parse_complex_parameter(self, node, language: str) -> Optional[Dict[str, Any]]:
        """Parse complex parameter with type hints or defaults"""
        name = None
        param_type = None
        default = None

        for child in node.children:
            if child.type == 'identifier' and not name:
                name = child.text.decode('utf8')
            elif child.type == 'type' or 'type' in child.type:
                param_type = child.text.decode('utf8')
            elif 'default' in child.type or child.type in ['string', 'number', 'true', 'false', 'null']:
                default = child.text.decode('utf8')

        if name:
            return {
                'name' : name,
                'type' : param_type,
                'default' : default,
                'required' : default is None
            }
        return None
    
    def _get_return_type(self, node, language: str) -> Optional[str]:
        """Extract return type annotation"""
        if language == 'python':
            # Look for -> return_type annotation
            for child in node.children:
                if child.type == 'type':
                    return child.text.decode('utf8')
                # Check for -> arrow and following type
                for i, subchild in enumerate(child.children):
                    if subchild.text.decode('utf8') == '->' and i + 1 < len(child.children):
                        return child.children[i + 1].text.decode('utf8')
        
        elif language in ['javascript', 'typescript']:
            # Look for TypeScript return type annotations
            for child in node.children:
                if child.type == 'type_annotation':
                    return child.text.decode('utf8').lstrip(':').strip()
        
        elif language == 'java':
            # Java method return type is typically the first type before method name
            for child in node.children:
                if child.type in ['type_identifier', 'primitive_type', 'generic_type']:
                    return child.text.decode('utf8')
        
        return None
    
    def _get_docstring(self, node, code: str, language: str) -> Optional[str]:
        """Extract function docstring or comments"""
        if language == 'python':
            # Look for string literal as first statement in function body
            for child in node.children:
                if child.type == 'block':
                    for stmt in child.children:
                        if stmt.type == 'expression_statement':
                            for expr in stmt.children:
                                if expr.type == 'string':
                                    # Remove quotes and clean up
                                    docstring = expr.text.decode('utf8')
                                    return self._clean_docstring(docstring)
        
        elif language in ['javascript', 'typescript']:
            # Look for JSDoc comments before function
            start_line = node.start_point[0]
            lines = code.split('\n')
            
            # Check lines before function for /** */ comments
            for i in range(max(0, start_line - 10), start_line):
                line = lines[i].strip()
                if line.startswith('/**'):
                    # Extract JSDoc comment
                    comment_lines = []
                    for j in range(i, min(len(lines), start_line)):
                        comment_line = lines[j].strip()
                        if comment_line.startswith('*'):
                            comment_lines.append(comment_line.lstrip('*').strip())
                        if comment_line.endswith('*/'):
                            break
                    return '\n'.join(comment_lines) if comment_lines else None
        
        elif language == 'java':
            # Look for Javadoc comments
            start_line = node.start_point[0]
            lines = code.split('\n')
            
            for i in range(max(0, start_line - 10), start_line):
                line = lines[i].strip()
                if line.startswith('/**'):
                    comment_lines = []
                    for j in range(i, min(len(lines), start_line)):
                        comment_line = lines[j].strip()
                        if comment_line.startswith('*') and not comment_line.startswith('/**'):
                            comment_lines.append(comment_line.lstrip('*').strip())
                        if comment_line.endswith('*/'):
                            break
                    return '\n'.join(comment_lines) if comment_lines else None
        
        return None
    
    def _clean_docstring(self, docstring: str) -> str:
        """Clean up extracted docstring"""
        # Remove quotes
        if docstring.startswith('"""') or docstring.startswith("'''"):
            docstring = docstring[3:]
        if docstring.endswith('"""') or docstring.endswith("'''"):
            docstring = docstring[:-3]
        elif docstring.startswith('"') or docstring.startswith("'"):
            docstring = docstring[1:]
            if docstring.endswith('"') or docstring.endswith("'"):
                docstring = docstring[:-1]
        
        # Clean up whitespace
        return docstring.strip()
    
    def _estimate_complexity(self, code: str) -> int:
        """Simple complexity estimation based on control structures"""
        complexity = 1  # Base complexity
        control_keywords = ['if', 'elif', 'else', 'for', 'while', 'try', 'except', 'catch']
        for keyword in control_keywords:
            complexity += code.count(keyword)
        return complexity
    
    def _fallback_extract_functions(self, code: str, language: str) -> List[Dict[str, Any]]:
        """Fallback function extraction using regex"""
        patterns = {
            'python': r'def\s+(\w+)\s*\([^)]*\):',
            'javascript': r'function\s+(\w+)\s*\([^)]*\)|(\w+)\s*=\s*\([^)]*\)\s*=>',
            'java': r'(public|private|protected)?\s*(static)?\s*\w+\s+(\w+)\s*\([^)]*\)',
        }
        
        pattern = patterns.get(language, r'(\w+)\s*\([^)]*\)')
        matches = re.findall(pattern, code, re.MULTILINE)
        
        functions = []
        for match in matches:
            name = match if isinstance(match, str) else next(filter(None, match), '')
            if name:
                functions.append({
                    'name': name,
                    'parameters': [],
                    'return_type': None,
                    'docstring': None,
                    'code': '',
                    'start_line': 0,
                    'end_line': 0,
                    'complexity': 1
                })
        
        return functions
    

class ProjectScaffolder:
    """Main scaffolder that analyzes project structure and prepare test context"""

    def __init__(self):
        self.code_analyzer = CodeAnalyzer()

    def scaffold_project(self, state: AutoCoverState) -> AutoCoverState:
        """Main scaffolding function - analyzes project and updates state"""
        file_path = Path(state['file_path'])

        #step 1: Detect project structure
        project_root = self._find_project_root(file_path)
        project_config = self._analyze_project_structure(project_root)

        #step2: Analyze existing test patterns
        existing_patterns = self._analyze_existing_tests(project_root, project_config)

        #step 3: Extract target functions from source code
        target_functions = self._analyze_source_code(state['source_code'], project_config.language)

        #step 4: Build comprehensive project context
        project_context = self._build_project_context(project_root, project_config, file_path)

        #Update state with scaffolder results
        state.update({
            'project_context': project_context,
            'test_framework' : project_config.test_framework,
            'existing_patterns': existing_patterns,
            'dependencies': project_config.dependencies,
            'target_functions':target_functions,
            'generation_attempt':0,
            'fix_attempt': 0,
            'current_iteration':0,
            'max_iteration': 0,
            'is_complete': False
        })

        return state
    
    def _find_project_root(self, file_path: Path) -> Path:
        """Find project root by looking for config files"""
        current = file_path.parent if file_path.is_file() else file_path

        #look for common project indicators
        indicators = [
            'package.json',      # Node.js
            'requirements.txt',  # Python
            'pyproject.toml',    # Python
            'setup.py',          # Python
            'pom.xml',           # Java Maven
            'build.gradle',      # Java Gradle
            'go.mod',            # Go
            'Cargo.toml',        # Rust
            '.git',              # Git repository
        ]

        while current != current.parent:
            for indicator in indicators:
                if (current / indicator).exists():
                    return current
            current = current.parent

        return file_path.parent
    
    def _analyze_project_structure(self, project_root: Path) -> ProjectConfig:
        """Analyze project to determine language, framework and structure"""

        #detect language and framework
        if (project_root / 'package.json').exists():
            return self._analyze_node_project(project_root)
        elif (project_root / 'requirements.txt').exists() or (project_root / 'pyproject.toml').exists():
            return self._analyze_python_project(project_root)
        elif (project_root / 'pom.xml').exists():
            return self._analyze_java_maven_project(project_root)
        elif (project_root / 'build.gradle').exists():
            return self._analyze_java_gradle_project(project_root)
        else:
            return self._analyze_generic_project(project_root)
        
    def _analyze_node_project(self, project_root: Path) -> ProjectConfig:
        """Analyze Node.js project structure"""
        package_json_path = project_root / 'package.json'

        dependencies = []
        test_framework = 'jest' #Default

        if package_json_path.exists():
            try:
                with open(package_json_path, 'r') as f:
                    package_data = json.load(f)

                #extract dependencies
                all_deps = {}
                all_deps.update(package_data.get('dependencies', {}))
                all_deps.update(package_data.get('devDependencies',{}))
                dependencies = list(all_deps.keys())

                #detect test framework
                if 'mocha' in all_deps:
                    test_framework = 'mocha'
                elif 'jasmine' in all_deps:
                    test_framework = 'jasmine'
                elif 'vitest' in all_deps:
                    test_framework = 'vitest'

            except Exception as e:
                print(f"Error reading package.json: {e}")

        return ProjectConfig(
            language='javascript',
            test_framework=test_framework,
            test_directory='__tests__' if test_framework == 'jest' else 'test',
            test_file_pattern='*.test.js',
            source_directory='src',
            dependencies=dependencies,
            build_tool='npm'
        )
    
    def _analyze_python_project(self, project_root: Path) -> ProjectConfig:
        """Analyze Python project structure"""
        dependencies = []
        
        # Try to read requirements.txt
        req_file = project_root / 'requirements.txt'
        if req_file.exists():
            try:
                with open(req_file, 'r') as f:
                    dependencies = [line.strip().split('==')[0] for line in f if line.strip() and not line.startswith('#')]
            except Exception as e:
                print(f"Error reading requirements.txt: {e}")
        
        # Detect test framework
        test_framework = 'pytest'
        if 'unittest' in dependencies or any('unittest' in dep for dep in dependencies):
            test_framework = 'unittest'
        
        return ProjectConfig(
            language='python',
            test_framework=test_framework,
            test_directory='tests',
            test_file_pattern='test_*.py',
            source_directory='src',
            dependencies=dependencies,
            build_tool='pip'
        )
    
    def _analyze_java_maven_project(self, project_root: Path) -> ProjectConfig:
        """Analyze Java Maven project structure"""
        return ProjectConfig(
            language='java',
            test_framework='junit',
            test_directory='src/test/java',
            test_file_pattern='*Test.java',
            source_directory='src/main/java',
            dependencies=[],  # Would parse pom.xml for actual dependencies
            build_tool='maven'
        )
    
    def _analyze_java_gradle_project(self, project_root: Path) -> ProjectConfig:
        """Analyze Java Gradle project structure"""
        return ProjectConfig(
            language='java',
            test_framework='junit',
            test_directory='src/test/java',
            test_file_pattern='*Test.java',
            source_directory='src/main/java',
            dependencies=[],  # Would parse build.gradle for actual dependencies
            build_tool='gradle'
        )
    
    def _analyze_generic_project(self, project_root: Path) -> ProjectConfig:
        """Fallback analysis for unknown project types"""
        return ProjectConfig(
            language='unknown',
            test_framework='unknown',
            test_directory='tests',
            test_file_pattern='*test*',
            source_directory='src',
            dependencies=[],
            build_tool=None
        )
    
    def _analyze_existing_tests(self, project_root: Path, config: ProjectConfig) -> Dict[str, Any]:
        """Analyze existing test files to understand patterns and conventions"""
        test_dir = project_root / config.test_directory
        
        if not test_dir.exists():
            return {
                'test_count': 0,
                'naming_patterns': [],
                'common_imports': [],
                'test_structure': {},
                'mocking_patterns': []
            }
        
        test_files = list(test_dir.rglob('*test*'))
        patterns = {
            'test_count': len(test_files),
            'naming_patterns': self._extract_naming_patterns(test_files),
            'common_imports': self._extract_common_imports(test_files, config.language),
            'test_structure': self._analyze_test_structure(test_files, config.language),
            'mocking_patterns': self._extract_mocking_patterns(test_files, config.language)
        }
        
        return patterns
    
    def _extract_naming_patterns(self, test_files: List[Path]) -> List[str]:
        """Extract common naming patterns from existing tests"""
        patterns = []
        for file in test_files[:5]:  # Sample first 5 files
            patterns.append(file.name)
        return patterns
    
    def _extract_common_imports(self, test_files: List[Path], language: str) -> List[str]:
        """Extract commonly used imports from existing tests"""
        imports = []
        # Implementation would parse test files and extract import statements
        return imports
    
    def _analyze_test_structure(self, test_files: List[Path], language: str) -> Dict[str, Any]:
        """Analyze the structure and organization of existing tests"""
        return {
            'uses_describe_blocks': False,
            'uses_setup_teardown': False,
            'common_assertions': [],
            'test_data_patterns': []
        }
    
    def _extract_mocking_patterns(self, test_files: List[Path], language: str) -> List[str]:
        """Extract mocking and stubbing patterns from existing tests"""
        return []
    
    def _analyze_source_code(self, source_code: str, language: str) -> List[Dict[str, Any]]:
        """Analyze the source code to extract functions that need testing"""
        return self.code_analyzer.extract_functions(source_code, language)
    
    def _build_project_context(self, project_root: Path, config: ProjectConfig, target_file: Path) -> Dict[str, Any]:
        """Build comprehensive project context for test generation"""
        return {
            'project_root': str(project_root),
            'language': config.language,
            'test_framework': config.test_framework,
            'build_tool': config.build_tool,
            'source_directory': config.source_directory,
            'test_directory': config.test_directory,
            'target_file': str(target_file),
            'relative_path': str(target_file.relative_to(project_root)),
            'dependencies': config.dependencies,
            'has_existing_tests': len(list(Path(project_root / config.test_directory).glob('*'))) > 0 if Path(project_root / config.test_directory).exists() else False
        }


def scaffolder_node(state: AutoCoverState) -> AutoCoverState:
    """LangGraph node function for the Scaffolder"""
    scaffolder = ProjectScaffolder()
    return scaffolder.scaffold_project(state)


# Example usage and testing
def create_sample_project():
    """Create a sample project structure in memory for testing"""
    import tempfile
    import shutil
    from pathlib import Path
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp())
    project_dir = temp_dir / "sample_project"
    project_dir.mkdir()
    
    # Create requirements.txt
    (project_dir / "requirements.txt").write_text("pytest>=7.0.0\nflask>=2.0.0\n")
    
    # Create src directory and shopping.py
    src_dir = project_dir / "src"
    src_dir.mkdir()
    
    shopping_content = '''def calculate_discount(price: float, discount_percent: int) -> tuple:
    """Calculate discount amount and final price
    
    Args:
        price: Original price of the item
        discount_percent: Percentage discount to apply (0-100)
        
    Returns:
        tuple: (final_price, discount_amount)
    """
    if price < 0:
        raise ValueError("Price cannot be negative")
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount percent must be between 0 and 100")
    
    discount_amount = price * (discount_percent / 100)
    final_price = price - discount_amount
    return final_price, discount_amount

class ShoppingCart:
    """Shopping cart to manage items"""
    
    def __init__(self):
        self.items = []
    
    def add_item(self, item: str, price: float):
        """Add an item to the cart"""
        self.items.append({"item": item, "price": price})
    
    def get_total(self) -> float:
        """Calculate total price"""
        return sum(item["price"] for item in self.items)
'''
    
    (src_dir / "shopping.py").write_text(shopping_content)
    
    # Create tests directory
    tests_dir = project_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_example.py").write_text("# Existing test file\n")
    
    return project_dir, src_dir / "shopping.py"

if __name__ == "__main__":
    try:
        # Create sample project
        # project_dir, target_file = create_sample_project()
    
        
        # Read actual source code
        # source_code = target_file.read_text()
        source_code = Path("test_script.py").read_text()
        target_file = "test_script.py"
        
        # Test with real file structure
        test_state = AutoCoverState(
            source_code=source_code,
            file_path=str(target_file),
            generated_tests=None,
            generation_attempt=0,
            test_results=None,
            build_success=None,
            test_failures=None,
            fixed_tests=None,
            fix_attempt=0,
            max_iterations=3,
            current_iteration=0,
            is_complete=False
        )
        
        print("🔍 Testing AutoCover Scaffolder...")
        print(f"📁 Target file: {target_file}")
        print("=" * 60)
        
        result = scaffolder_node(test_state)
        
        print("✅ SCAFFOLDER RESULTS:")
        print(f"🏗️  Project Root: {result['project_context']['project_root']}")
        print(f"🐍 Language: {result['project_context']['language']}")
        print(f"🧪 Test Framework: {result['test_framework']}")
        print(f"📦 Dependencies: {len(result['dependencies'])}")
        print(f"📝 Target Functions: {len(result['target_functions'])}")
        
        print("\n🎯 FUNCTIONS DETECTED:")
        for func in result['target_functions']:
            print(f"  • {func['name']}")
            print(f"    Parameters: {[p.get('name', 'unknown') for p in func['parameters']]}")
            print(f"    Return Type: {func['return_type'] or 'Not specified'}")
            print(f"    Complexity: {func['complexity']}")
            print(f"    Has Docstring: {'Yes' if func['docstring'] else 'No'}")
            print()
        
        print("🔧 PROJECT STRUCTURE:")
        context = result['project_context']
        print(f"  Source Directory: {context['source_directory']}")
        print(f"  Test Directory: {context['test_directory']}")
        print(f"  Has Existing Tests: {context['has_existing_tests']}")
        
        print("\n✨ Ready for Generator node!")
        
    except Exception as e:
        print(f"❌ Error testing scaffolder: {e}")
        import traceback
        traceback.print_exc()
    
    # finally:
    #     # Clean up temporary files
    #     try:
    #         import shutil
    #         shutil.rmtree(project_dir.parent)
    #         print("🧹 Cleaned up temporary files")
    #     except:
    #         pass