import os
import subprocess
import tempfile
import shutil
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from node_1.scaffolder import AutoCoverState, scaffolder_node
from node_2.generator import generator_node
@dataclass
class TestResult:
    """Language-agnostic test result representation"""
    passed: bool
    test_name: str
    error_message: Optional[str] = None
    traceback: Optional[str] = None

class LanguageHandler(ABC):
    """Abstract base class for language-specific test execution"""
    
    @abstractmethod
    def get_file_extensions(self) -> Dict[str, str]:
        """Return file extensions for source and test files"""
        pass
    
    @abstractmethod
    def setup_project_structure(self, temp_dir: Path, project_context: Dict) -> Dict[str, Path]:
        """Set up language-specific project structure"""
        pass
    
    @abstractmethod
    def write_source_file(self, source_dir: Path, source_code: str, filename: str) -> Path:
        """Write the source code file"""
        pass
    
    @abstractmethod
    def write_test_file(self, test_dir: Path, test_code: str, filename: str) -> Path:
        """Write the test file"""
        pass
    
    @abstractmethod
    def install_dependencies(self, temp_dir: Path, dependencies: List[str]) -> bool:
        """Install language-specific dependencies"""
        pass
    
    @abstractmethod
    def run_tests(self, temp_dir: Path, project_context: Dict) -> Dict[str, Any]:
        """Execute tests and return results"""
        pass
    
    @abstractmethod
    def clean_generated_code(self, code: str) -> str:
        """Clean generated code (remove markdown, fix imports, etc.)"""
        pass

class PythonHandler(LanguageHandler):
    """Handler for Python projects"""
    
    def get_file_extensions(self) -> Dict[str, str]:
        return {"source": ".py", "test": ".py"}
    
    def setup_project_structure(self, temp_dir: Path, project_context: Dict) -> Dict[str, Path]:
        src_dir = temp_dir / project_context.get('source_directory', 'src')
        test_dir = temp_dir / project_context.get('test_directory', 'tests')
        
        src_dir.mkdir(parents=True, exist_ok=True)
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Python package files
        (src_dir / '__init__.py').touch()
        (test_dir / '__init__.py').touch()
        
        return {"source": src_dir, "test": test_dir}
    
    def write_source_file(self, source_dir: Path, source_code: str, filename: str) -> Path:
        source_file = source_dir / filename
        source_file.write_text(source_code)
        return source_file
    
    def write_test_file(self, test_dir: Path, test_code: str, filename: str) -> Path:
        test_filename = f"test_{filename}" if not filename.startswith('test_') else filename
        test_file = test_dir / test_filename
        test_file.write_text(test_code)
        return test_file
    
    def install_dependencies(self, temp_dir: Path, dependencies: List[str]) -> bool:
        if not dependencies:
            return True
            
        requirements_file = temp_dir / 'requirements.txt'
        requirements_file.write_text('\n'.join(dependencies))
        
        try:
            result = subprocess.run([
                'pip', 'install', '-r', str(requirements_file)
            ], capture_output=True, text=True, cwd=temp_dir)
            return result.returncode == 0
        except Exception:
            return False
    
    def run_tests(self, temp_dir: Path, project_context: Dict) -> Dict[str, Any]:
        try:
            cmd = ['python', '-m', 'pytest', 'tests', '-v', '--tb=short', '--json-report', '--json-report-file=results.json']
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir)
            return self._parse_pytest_results(temp_dir, result)
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def clean_generated_code(self, code: str) -> str:
        # Remove markdown
        code = re.sub(r'```python\s*\n?', '', code)
        code = re.sub(r'```\s*$', '', code, flags=re.MULTILINE)
        
        # Fix imports
        code = re.sub(r'from src import', 'from src.test_script import', code)
        
        if 'import pytest' not in code:
            code = 'import pytest\n' + code
            
        return code.strip()
    
    def _parse_pytest_results(self, temp_dir: Path, subprocess_result) -> Dict[str, Any]:
        results = {
            'success': subprocess_result.returncode == 0,
            'return_code': subprocess_result.returncode,
            'stdout': subprocess_result.stdout,
            'stderr': subprocess_result.stderr,
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'failures': []
        }
        
        # Try JSON report first
        json_file = temp_dir / 'results.json'
        if json_file.exists():
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    summary = data.get('summary', {})
                    results.update({
                        'tests_run': summary.get('total', 0),
                        'tests_passed': summary.get('passed', 0),
                        'tests_failed': summary.get('failed', 0)
                    })
                    
                    for test in data.get('tests', []):
                        if test.get('outcome') == 'failed':
                            results['failures'].append({
                                'test_name': test.get('nodeid', 'unknown'),
                                'error': test.get('call', {}).get('longrepr', 'Unknown error')
                            })
            except Exception:
                pass
        
        return results

class JavaScriptHandler(LanguageHandler):
    """Handler for JavaScript/Node.js projects"""
    
    def get_file_extensions(self) -> Dict[str, str]:
        return {"source": ".js", "test": ".test.js"}
    
    def setup_project_structure(self, temp_dir: Path, project_context: Dict) -> Dict[str, Path]:
        src_dir = temp_dir / project_context.get('source_directory', 'src')
        test_dir = temp_dir / project_context.get('test_directory', 'tests')
        
        src_dir.mkdir(parents=True, exist_ok=True)
        test_dir.mkdir(parents=True, exist_ok=True)
        
        return {"source": src_dir, "test": test_dir}
    
    def write_source_file(self, source_dir: Path, source_code: str, filename: str) -> Path:
        source_file = source_dir / filename
        source_file.write_text(source_code)
        return source_file
    
    def write_test_file(self, test_dir: Path, test_code: str, filename: str) -> Path:
        test_filename = filename.replace('.js', '.test.js')
        test_file = test_dir / test_filename
        test_file.write_text(test_code)
        return test_file
    
    def install_dependencies(self, temp_dir: Path, dependencies: List[str]) -> bool:
        # Create package.json
        package_json = {
            "name": "autocover-test",
            "version": "1.0.0",
            "scripts": {"test": "jest"},
            "dependencies": {},
            "devDependencies": {"jest": "^29.0.0"}
        }
        
        for dep in dependencies:
            package_json["devDependencies"][dep] = "latest"
        
        (temp_dir / 'package.json').write_text(json.dumps(package_json, indent=2))
        
        try:
            result = subprocess.run(['npm', 'install'], capture_output=True, text=True, cwd=temp_dir)
            return result.returncode == 0
        except Exception:
            return False
    
    def run_tests(self, temp_dir: Path, project_context: Dict) -> Dict[str, Any]:
        try:
            cmd = ['npm', 'test', '--', '--json', '--outputFile=results.json']
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir)
            return self._parse_jest_results(temp_dir, result)
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def clean_generated_code(self, code: str) -> str:
        # Remove markdown
        code = re.sub(r'```javascript\s*\n?', '', code)
        code = re.sub(r'```js\s*\n?', '', code)
        code = re.sub(r'```\s*$', '', code, flags=re.MULTILINE)
        
        return code.strip()
    
    def _parse_jest_results(self, temp_dir: Path, subprocess_result) -> Dict[str, Any]:
        results = {
            'success': subprocess_result.returncode == 0,
            'return_code': subprocess_result.returncode,
            'stdout': subprocess_result.stdout,
            'stderr': subprocess_result.stderr,
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'failures': []
        }
        
        # Parse Jest output
        try:
            if 'Tests:' in subprocess_result.stdout:
                output = subprocess_result.stdout
                if 'failed' in output:
                    failed_match = re.search(r'(\d+) failed', output)
                    if failed_match:
                        results['tests_failed'] = int(failed_match.group(1))
                
                if 'passed' in output:
                    passed_match = re.search(r'(\d+) passed', output)
                    if passed_match:
                        results['tests_passed'] = int(passed_match.group(1))
                
                results['tests_run'] = results['tests_passed'] + results['tests_failed']
        except Exception:
            pass
            
        return results

class TypeScriptHandler(LanguageHandler):
    """Handler for TypeScript projects"""
    
    def get_file_extensions(self) -> Dict[str, str]:
        return {"source": ".ts", "test": ".test.ts"}
    
    def setup_project_structure(self, temp_dir: Path, project_context: Dict) -> Dict[str, Path]:
        src_dir = temp_dir / project_context.get('source_directory', 'src')
        test_dir = temp_dir / project_context.get('test_directory', 'tests')
        
        src_dir.mkdir(parents=True, exist_ok=True)
        test_dir.mkdir(parents=True, exist_ok=True)
        
        return {"source": src_dir, "test": test_dir}
    
    def write_source_file(self, source_dir: Path, source_code: str, filename: str) -> Path:
        source_file = source_dir / filename
        source_file.write_text(source_code)
        return source_file
    
    def write_test_file(self, test_dir: Path, test_code: str, filename: str) -> Path:
        test_filename = filename.replace('.ts', '.test.ts')
        test_file = test_dir / test_filename
        test_file.write_text(test_code)
        return test_file
    
    def install_dependencies(self, temp_dir: Path, dependencies: List[str]) -> bool:
        # Create package.json and tsconfig.json
        package_json = {
            "name": "autocover-test",
            "version": "1.0.0",
            "scripts": {"test": "jest"},
            "devDependencies": {
                "jest": "^29.0.0",
                "@types/jest": "^29.0.0",
                "ts-jest": "^29.0.0",
                "typescript": "^5.0.0"
            }
        }
        
        tsconfig = {
            "compilerOptions": {
                "target": "ES2020",
                "module": "commonjs",
                "strict": true,
                "esModuleInterop": true
            }
        }
        
        jest_config = {
            "preset": "ts-jest",
            "testEnvironment": "node"
        }
        
        for dep in dependencies:
            package_json["devDependencies"][dep] = "latest"
        
        (temp_dir / 'package.json').write_text(json.dumps(package_json, indent=2))
        (temp_dir / 'tsconfig.json').write_text(json.dumps(tsconfig, indent=2))
        (temp_dir / 'jest.config.json').write_text(json.dumps(jest_config, indent=2))
        
        try:
            result = subprocess.run(['npm', 'install'], capture_output=True, text=True, cwd=temp_dir)
            return result.returncode == 0
        except Exception:
            return False
    
    def run_tests(self, temp_dir: Path, project_context: Dict) -> Dict[str, Any]:
        try:
            cmd = ['npm', 'test']
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir)
            return self._parse_jest_results(temp_dir, result)
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def clean_generated_code(self, code: str) -> str:
        # Remove markdown
        code = re.sub(r'```typescript\s*\n?', '', code)
        code = re.sub(r'```ts\s*\n?', '', code)
        code = re.sub(r'```\s*$', '', code, flags=re.MULTILINE)
        
        return code.strip()
    
    def _parse_jest_results(self, temp_dir: Path, subprocess_result) -> Dict[str, Any]:
        # Same as JavaScript handler
        return JavaScriptHandler()._parse_jest_results(temp_dir, subprocess_result)

class JavaHandler(LanguageHandler):
    """Handler for Java projects"""
    
    def get_file_extensions(self) -> Dict[str, str]:
        return {"source": ".java", "test": ".java"}
    
    def setup_project_structure(self, temp_dir: Path, project_context: Dict) -> Dict[str, Path]:
        # Standard Maven structure
        src_main = temp_dir / 'src' / 'main' / 'java'
        src_test = temp_dir / 'src' / 'test' / 'java'
        
        src_main.mkdir(parents=True, exist_ok=True)
        src_test.mkdir(parents=True, exist_ok=True)
        
        return {"source": src_main, "test": src_test}
    
    def write_source_file(self, source_dir: Path, source_code: str, filename: str) -> Path:
        source_file = source_dir / filename
        source_file.write_text(source_code)
        return source_file
    
    def write_test_file(self, test_dir: Path, test_code: str, filename: str) -> Path:
        test_filename = filename.replace('.java', 'Test.java')
        test_file = test_dir / test_filename
        test_file.write_text(test_code)
        return test_file
    
    def install_dependencies(self, temp_dir: Path, dependencies: List[str]) -> bool:
        # Create pom.xml for Maven
        pom_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
                             http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.autocover</groupId>
    <artifactId>test-project</artifactId>
    <version>1.0.0</version>
    
    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
    </properties>
    
    <dependencies>
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <version>5.9.0</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
    
    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-surefire-plugin</artifactId>
                <version>3.0.0-M7</version>
            </plugin>
        </plugins>
    </build>
</project>'''
        
        (temp_dir / 'pom.xml').write_text(pom_xml)
        
        try:
            result = subprocess.run(['mvn', 'dependency:resolve'], capture_output=True, text=True, cwd=temp_dir)
            return result.returncode == 0
        except Exception:
            return False
    
    def run_tests(self, temp_dir: Path, project_context: Dict) -> Dict[str, Any]:
        try:
            cmd = ['mvn', 'test']
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir)
            return self._parse_maven_results(result)
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def clean_generated_code(self, code: str) -> str:
        # Remove markdown
        code = re.sub(r'```java\s*\n?', '', code)
        code = re.sub(r'```\s*$', '', code, flags=re.MULTILINE)
        
        return code.strip()
    
    def _parse_maven_results(self, subprocess_result) -> Dict[str, Any]:
        results = {
            'success': subprocess_result.returncode == 0,
            'return_code': subprocess_result.returncode,
            'stdout': subprocess_result.stdout,
            'stderr': subprocess_result.stderr,
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'failures': []
        }
        
        # Parse Maven Surefire output
        output = subprocess_result.stdout
        
        # Look for "Tests run: X, Failures: Y, Errors: Z"
        test_summary = re.search(r'Tests run: (\d+), Failures: (\d+), Errors: (\d+)', output)
        if test_summary:
            tests_run = int(test_summary.group(1))
            failures = int(test_summary.group(2))
            errors = int(test_summary.group(3))
            
            results.update({
                'tests_run': tests_run,
                'tests_failed': failures + errors,
                'tests_passed': tests_run - failures - errors
            })
        
        return results

class LanguageAgnosticExecutor:
    """Language-agnostic test executor"""
    
    def __init__(self):
        self.handlers = {
            'python': PythonHandler(),
            'javascript': JavaScriptHandler(),
            'typescript': TypeScriptHandler(),
            'java': JavaHandler()
        }
        self.temp_dir = None
    
    def detect_language(self, project_context: Dict, file_path: str) -> str:
        """Detect programming language from context or file extension"""
        
        # Check explicit language in project context
        if 'language' in project_context:
            lang = project_context['language'].lower()
            if lang in self.handlers:
                return lang
        
        # Detect from file extension
        ext = Path(file_path).suffix.lower()
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java'
        }
        
        return extension_map.get(ext, 'python')  # Default to python
    
    def execute_tests(self, source_code: str, test_code: str, file_path: str,
                     project_context: Dict, dependencies: List[str]) -> Dict[str, Any]:
        """Execute tests in a language-agnostic way"""
        
        language = self.detect_language(project_context, file_path)
        handler = self.handlers.get(language)
        
        if not handler:
            return {
                'success': False,
                'error': f'Unsupported language: {language}'
            }
        
        try:
            # Create temporary directory
            self.temp_dir = Path(tempfile.mkdtemp(prefix=f"autocover_{language}_"))
            
            # Set up project structure
            dirs = handler.setup_project_structure(self.temp_dir, project_context)
            
            # Clean and write files
            clean_source = handler.clean_generated_code(source_code) if source_code else source_code
            clean_test = handler.clean_generated_code(test_code)
            
            filename = Path(file_path).name
            if not filename.endswith(handler.get_file_extensions()['source']):
                filename += handler.get_file_extensions()['source']
            
            handler.write_source_file(dirs['source'], clean_source, filename)
            handler.write_test_file(dirs['test'], clean_test, filename)
            
            # Install dependencies
            deps_success = handler.install_dependencies(self.temp_dir, dependencies)
            
            # Run tests
            test_results = handler.run_tests(self.temp_dir, project_context)
            test_results['dependencies_installed'] = deps_success
            test_results['language'] = language
            
            return test_results
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Execution failed: {str(e)}',
                'language': language
            }
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None

# def executor_node(state: AutoCoverState) -> AutoCoverState:
#     """
#     Language-agnostic LangGraph node for executing generated tests
    
#     Args:
#         state: AutoCoverState from generator node
        
#     Returns:
#         Updated state with test execution results
#     """
#     print("🔄 Running Language-Agnostic Executor Node...")
    
#     # Check if we have generated tests
#     generated_tests = state.get('generated_tests')
#     if not generated_tests:
#         print("❌ No generated tests found")
#         error_state = state.copy()
#         error_state.update({
#             'build_success': False,
#             'test_results': {
#                 'success': False,
#                 'error': 'No generated tests to execute'
#             }
#         })
#         return error_state
    
#     executor = LanguageAgnosticExecutor()
    
#     try:
#         # Detect language and run tests
#         project_context = state.get('project_context', {})
#         language = executor.detect_language(project_context, state['file_path'])
        
#         print(f"🔍 Detected language: {language.upper()}")
#         print("📁 Setting up test environment...")
        
#         # Execute tests
#         test_results = executor.execute_tests(
#             source_code=state['source_code'],
#             test_code=generated_tests,
#             file_path=state['file_path'],
#             project_context=project_context,
#             dependencies=state.get('dependencies', [])
#         )
        
#         # Prepare updated state
#         updated_state = state.copy()
        
#         # Determine build success
#         build_success = test_results.get('success', False)
        
#         # Extract test failures for the fixer node
#         failures = []
#         if test_results.get('failures'):
#             for failure in test_results['failures']:
#                 failure_msg = failure.get('error', str(failure)) if isinstance(failure, dict) else str(failure)
#                 test_name = failure.get('test_name', 'unknown') if isinstance(failure, dict) else 'unknown'
#                 failures.append(f"{test_name}: {failure_msg}")
        
#         updated_state.update({
#             'build_success': build_success,
#             'test_results': test_results,
#             'test_failures': failures if failures else None,
#             'execution_context': {
#                 'language': language,
#                 'dependencies_installed': test_results.get('dependencies_installed', False),
#                 'tests_executed': test_results.get('tests_run', 0)
#             }
#         })
        
#         # Print summary
#         if build_success:
#             print(f"✅ {language.upper()} tests executed successfully!")
#             print(f"   📊 {test_results.get('tests_run', 0)} tests run")
#             print(f"   ✅ {test_results.get('tests_passed', 0)} passed")
#             print(f"   ❌ {test_results.get('tests_failed', 0)} failed")
#         else:
#             print(f"❌ {language.upper()} test execution failed")
#             if test_results.get('error'):
#                 print(f"   Error: {test_results['error']}")
#             if failures:
#                 print(f"   {len(failures)} test failures found")
        
#         return updated_state
        
#     except Exception as e:
#         print(f"💥 Executor failed: {e}")
        
#         # Return state with error information
#         error_state = state.copy()
#         error_state.update({
#             'build_success': False,
#             'test_results': {
#                 'success': False,
#                 'error': f'Executor failed: {str(e)}'
#             },
#             'test_failures': [f'Execution error: {str(e)}']
#         })
        
#         return error_state

# Example usage for different languages
def test_multilang_executor():
    """Test the executor with different languages"""
    
    # Python example
    python_state = {
        'source_code': '''def add(a, b):
    return a + b''',
        'generated_tests': '''import pytest
from src.calculator import add

def test_add():
    assert add(2, 3) == 5''',
        'file_path': 'calculator.py',
        'project_context': {'language': 'python'},
        'dependencies': ['pytest'],
    }
    
    # JavaScript example  
    js_state = {
        'source_code': '''function add(a, b) {
    return a + b;
}
module.exports = { add };''',
        'generated_tests': '''const { add } = require('../src/calculator');

test('adds 1 + 2 to equal 3', () => {
    expect(add(1, 2)).toBe(3);
});''',
        'file_path': 'calculator.js',
        'project_context': {'language': 'javascript'},
        'dependencies': ['jest'],
    }
    
    executor = LanguageAgnosticExecutor()
    
    # Test Python
    print("Testing Python:")
    py_result = executor.execute_tests(**python_state)
    print(f"Python Result: {py_result}")
    
    # Test JavaScript
    print("\nTesting JavaScript:")
    js_result = executor.execute_tests(**js_state)
    print(f"JavaScript Result: {js_result}")

if __name__ == "__main__":
    test_multilang_executor()