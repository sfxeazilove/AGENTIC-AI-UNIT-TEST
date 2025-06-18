import os
import tempfile
import shutil
from pathlib import Path


# Test function you can use
def test_scaffolder_with_real_files():
    """Test scaffolder with real file structure"""
    from scaffolder import scaffolder_node, AutoCoverState
    
    # Setup test project
    # project_dir = setup_test_project()
    # target_file = project_dir / "src" / "shopping.py"
    target_file = Path("test_script.py")
    
    try:
        # Read the actual source code
        source_code = target_file.read_text()
        
        # Create state with real file path
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
        
        # Run scaffolder
        result = scaffolder_node(test_state)
        # print(f"The result is \n: {result}")
        
        # Print results
        print("=" * 50)
        print("SCAFFOLDER RESULTS")
        print("=" * 50)
        print(f"Project Root: {result['project_context']['project_root']}")
        print(f"Language: {result['project_context']['language']}")
        print(f"Test Framework: {result['test_framework']}")
        print(f"Build Tool: {result['project_context']['build_tool']}")
        print(f" the depedence is {result['dependencies']}")
        print(f"Dependencies: {len(result['dependencies'])} found")
        print(f"Has Existing Tests: {result['project_context']['has_existing_tests']}")
        print(f"Target Functions: {len(result['target_functions'])}")
        
        print("\nFUNCTIONS DETECTED:")
        for func in result['target_functions']:
            print(f"  📝 {func['name']}")
            print(f"     Parameters: {[p['name'] for p in func['parameters']]}")
            print(f"     Return Type: {func['return_type']}")
            print(f"     Complexity: {func['complexity']}")
            print(f"     Has Docstring: {'Yes' if func['docstring'] else 'No'}")
            # print(f"     Code: {func['code']}")
            if func['docstring']:
                print(f"     Doc: {func['docstring'][:100]}...")
            print()
        
        print("\nEXISTING TEST PATTERNS:")
        patterns = result['existing_patterns']
        print(f"  Existing test files: {patterns['test_count']}")
        print(f"  Naming patterns: {patterns['naming_patterns']}")
        
        print("\nPROJECT CONTEXT:")
        context = result['project_context']
        print(f"context is: {context}")
        print(f"  Source dir: {context['source_directory']}")
        print(f"  Test dir: {context['test_directory']}")
        print(f"  Target file: {context['relative_path']}")
        
        return result
        
    except Exception as e:
        print(f"Cannot generate Information: {e}")


if __name__ == "__main__":
    test_scaffolder_with_real_files()