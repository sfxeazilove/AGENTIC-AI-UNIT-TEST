import os
import openai
from typing import Dict, Any, List
from dataclasses import dataclass
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()
OPEN_AI_KEY = os.getenv("OPEN_AI_KEY")

@dataclass
class TestGenerationPrompt:
    """Structure for organizing test generation prompts"""
    system_prompt: str
    user_prompt: str
    context: Dict[str , Any]

class OpenAITestGenerator:
    def __init__(self, api_key):
        self.api_key = api_key

    def generate_tests(self, prompt):
        client = openai.OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt.system_prompt},
                {"role": "user", "content": prompt.user_prompt}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content

class TestGenerator:
    """Handles test code generation using LLM"""

    def __init__(self, llm_client="OpenAI"):
        """
        Initialize the test generator
        Args:
            llm_client: LLM client eg (OpenAI, Anthropic , etc)

        """
        self.llm_client = llm_client

    def create_generation_prompt(self, state: Dict[str, Any]) -> TestGenerationPrompt:
        """
        Create a comprehensive prompt for test generation

        Args:
            state: AutoCoverState containing scaffolder results
        
        Returns:
            TestGenerationPrompt with system and user prompts
        """

        #extract key information from scaffolder results
        target_functions = state.get('target_functions', [])
        project_context = state.get('project_context', {})
        test_framework = state.get('test_framework', "")
        dependencies = state.get('dependencies', [])
        existing_patterns = state.get('existing_patterns', {})
        source_code = state.get('source_code', '')

        #build system prompt
        system_prompt = f"""
            You are an expert test engineer. Your task is to generate comprehensive, high-quality
            unit test.

            REQUIREMENTS:
            - Use {test_framework} as the testing framework
            - Follow language-specific testing best practices
            - Include proper setup and teardown when needed
            - Use descriptive test names that explain what is being tested
            - Add docstrings to test functions
            - Handle dependencies and mocking appropriately

            PROJECT CONTEXT:
            - Language: {project_context.get('language', '')}
            - Test Framework: {test_framework}
            - Build Tool: {project_context.get('build_tool', '')}
            - Source Directory: {project_context.get('source_directory','')}
            - Test Directory: {project_context.get('test_directory', '')}

            EXISTING TEST PATTERNS:
            - Test file count: {existing_patterns.get('test_count', 0)}
            - Naming patterns: {existing_patterns.get('naming_patterns', [])}

            DEPENDENCIES TO CONSIDER:
            {self._format_dependencies(dependencies)}

            Generate complete, runnable test code that can be executed immediately
        """

        #build user prompt with function details
        user_prompt = f"""
            Generate comprehensive unit tests for the following code:

            SOURCE CODE:
            {source_code}

            FUNCTIONS TO TEST:
            {self._format_functions_for_prompt(target_functions)}

            REQUIREMENTS:
            1. Create a complete test file that can run independently
            2. Test all public functions and methods
            3. Include tests for:
                - Normal/happy path scenarios
                - Edge cases (empty inputs, boundary values , etc)
                - Error conditions and exception handline
                - Different input types where applicable
            4. Use proper fixtures and setup for class-based tests
            5. Mock external dependencies if needed
            6. Follow the existing project's testsing patterns where possible

            Generate only the test code, no explanations or markdown formatting
        """
        return TestGenerationPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context={
                'target_functions': target_functions,
                'project_context' : project_context,
                'test_framework' : test_framework
            }
        )
    
    def _format_dependencies(self, dependencies: List[str]) -> str:
        """Format dependencies for the prompt"""
        if not dependencies:
            return "No external dependencies detected"
        
        formatted = []
        for i , dep in enumerate(dependencies):
            formatted.append(f"- {i}: {dep}")
        return "\n".join(formatted)
    
    def _format_functions_for_prompt(self, functions: List[Dict]) -> str:
        """Format function information for the prompt"""
        if not functions:
            return "No functions detected"
        
        formatted = []
        for func in functions:
            func_info = f"""
                Function: {func.get('name', 'unknown')}
                - Parameters: {[p.get('name') for p in func.get('parameters', [])]}
                - Return Type: {func.get('return_type', 'unknown')}
                - Complexity: {func.get('complexity', 1)}
                - Has Docstring: {bool(func.get('docstring'))}
            """
            if func.get('docstring'):
                func_info += f"\n- Documentation: {func['docstring'][:200]}..."

            formatted.append(func_info)

        return "\n".join(formatted)
    
    def generate_tests(self, prompt: TestGenerationPrompt) -> str:
        """
        Generate test code using LLM

        Args:
            prompt: TestGenerationPrompt with system and user prompts

        Returns:
            Generated test code as string
        """
        if not self.llm_client:
            #fallback template-based generation for demo
            # return self._generate_template_tests(prompt.context)
            return ("cannot initialize llm client")
        
        try:
            #open AI integration - i would make it more LLM agnostic later
            
            #initialize client
            print(f"USING THE OPEN AI CLIENT")
            client = OpenAITestGenerator(api_key=OPEN_AI_KEY)
            response = client.generate_tests(prompt)
            # print(f"Response from Client is: {response}")
            return response
        except Exception as e:
            print(f"LLM generation failed: {e}")
            return self._generate_template_tests(prompt.context)
    
    def _generate_template_tests(self, context: Dict[str, Any]) -> str:
        #pass
        """
        Fallback template-based test generation
        
        Args:
            context: Function and project context
            
        Returns:
            Template-generated test code
        """
        
        target_functions = context.get('target_functions', [])
        test_framework = context.get('test_framework', 'pytest')
        
        # Generate imports
        imports = [
            "import pytest",
            "from unittest.mock import Mock, patch, MagicMock"
        ]
        
        # Try to determine import path
        project_context = context.get('project_context', {})
        file_path = project_context.get('relative_path', '')
        
        if file_path:
            module_name = file_path.replace('.py', '').replace('/', '.').replace('\\', '.')
            if module_name.startswith('.'):
                module_name = module_name[1:]
            imports.append(f"from {module_name} import *")
        
        # Generate test class/functions
        test_code_parts = [
            "\n".join(imports),
            "",
            "",
            "class TestGeneratedTests:",
            '    """Generated test class for comprehensive coverage"""',
            ""
        ]
        
        # Generate tests for each function
        for func in target_functions:
            func_name = func.get('name', 'unknown')
            if func_name == '__init__':
                continue
                
            test_code_parts.extend(self._generate_function_tests(func, test_framework))
        
        return "\n".join(test_code_parts)
    
    def _generate_function_tests(self, func_info: Dict[str, Any], framework: str) -> List[str]:
        """Generate test methods for a specific function"""
        
        func_name = func_info.get('name', 'unknown')
        parameters = func_info.get('parameters', [])
        return_type = func_info.get('return_type', 'unknown')
        
        tests = []
        
        # Basic test
        tests.extend([
            f"    def test_{func_name}_basic(self):",
            f'        """Test basic functionality of {func_name}"""',
            f"        # TODO: Implement basic test for {func_name}",
            f"        # This test should cover the happy path scenario",
            f"        pass",
            ""
        ])
        
        # Edge case test
        tests.extend([
            f"    def test_{func_name}_edge_cases(self):",
            f'        """Test edge cases for {func_name}"""',
            f"        # TODO: Test boundary values, empty inputs, etc.",
            f"        pass",
            ""
        ])
        
        # Error handling test if function might raise exceptions
        if parameters:  # Functions with params more likely to have error conditions
            tests.extend([
                f"    def test_{func_name}_error_handling(self):",
                f'        """Test error handling for {func_name}"""',
                f"        # TODO: Test invalid inputs, type errors, etc.",
                f"        pass",
                ""
            ])
        
        return tests
    
def generator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node for generating test code

    Args:
        state: AutoCoverState from scaffolder
    Returns:
        Updated state with generated tests
    """  
    print("🔄 Running Generator Node...") 

    try:
        #initialize generator
        generator = TestGenerator(llm_client="OpenAI")

        #create generation prompt
        prompt = generator.create_generation_prompt(state)

        print(f" Generating tests for {len(state.get('target_functions', []))} functions...")

        #Generate tests
        generated_tests = generator.generate_tests(prompt)

        #Update state
        updated_state = state.copy()
        updated_state.update({
            'generated_tests': generated_tests,
            'generation_attempt' : state.get('generation_attempt', 0) + 1,
            'generation_context': {
                'prompt_used': {
                'system': prompt.system_prompt[:200] + "...",
                'user': prompt.user_prompt[:200] + "..."
            },
                'function_count': len(state.get('target_functions', [])),
                'framework': state.get('test_framework', '')
            }
        }) 
        print(f"Generated {len(generated_tests.splitlines())} lines of test code")
        return updated_state

    except Exception as e:
        print(f"Generator failed: {e}")
        # Return state with error information
        error_state = state.copy()
        error_state.update({
            'generated_tests': None,
            'generation_attempt': state.get('generation_attempt', 0) + 1,
            'generation_error': str(e)
        })
        
        return error_state 

     
if __name__ == "__main__":
    #scaffolder output 
    from node_1.scaffolder import scaffolder_node, AutoCoverState
    #lets call it mockstate
    target_file = Path("/Users/eazilove/Documents/agent-unit-test/node_1/test_script.py")
    
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
        scaffolder_result = scaffolder_node(test_state)
    except Exception as e:
        raise ValueError(f"Cannot run the Scaffolder node: {e}")
    
    # mockstate = """{'source_code': 'def calculate_discount(price: float, discount_percent: int) -> tuple:\n    \'\'\'Calculate discount amount and final price\n    \n    Args:\n        price: Original price of the item\n        discount_percent: Percentage discount to apply (0-100)\n        \n    Returns:\n        tuple: (final_price, discount_amount)\n        \n    Raises:\n        ValueError: If price is negative or discount is out of range\n    \'\'\'\n    if price < 0:\n        raise ValueError("Price cannot be negative")\n    if discount_percent < 0 or discount_percent > 100:\n        raise ValueError("Discount percent must be between 0 and 100")\n    \n    discount_amount = price * (discount_percent / 100)\n    final_price = price - discount_amount\n    return final_price, discount_amount\n\n\ndef apply_bulk_discount(total_amount: float, item_count: int = 1) -> float:\n    \'\'\'Apply bulk discount based on item count\'\'\'\n    if item_count >= 10:\n        return total_amount * 0.9  # 10% discount\n    elif item_count >= 5:\n        return total_amount * 0.95  # 5% discount\n    return total_amount\n\n\nclass ShoppingCart:\n    \'\'\'Shopping cart to manage items and calculate totals\'\'\'\n    \n    def __init__(self):\n        self.items = []\n        self.tax_rate = 0.08\n    \n    def add_item(self, item: str, price: float, quantity: int = 1):\n        \'\'\'Add an item to the cart\'\'\'\n        if price < 0:\n            raise ValueError("Price cannot be negative")\n        if quantity < 1:\n            raise ValueError("Quantity must be at least 1")\n            \n        self.items.append({\n            \'item\': item,\n            \'price\': price,\n            \'quantity\': quantity\n        })\n    \n    def remove_item(self, item: str) -> bool:\n        \'\'\'Remove an item from the cart\'\'\'\n        for i, cart_item in enumerate(self.items):\n            if cart_item[\'item\'] == item:\n                self.items.pop(i)\n                return True\n        return False\n    \n    def get_subtotal(self) -> float:\n        \'\'\'Calculate subtotal before tax\'\'\'\n        return sum(item[\'price\'] * item[\'quantity\'] for item in self.items)\n    \n    def get_tax_amount(self) -> float:\n        \'\'\'Calculate tax amount\'\'\'\n        return self.get_subtotal() * self.tax_rate\n    \n    def get_total(self) -> float:\n        \'\'\'Calculate total including tax\'\'\'\n        return self.get_subtotal() + self.get_tax_amount()\n    \n    def clear_cart(self):\n        \'\'\'Empty the shopping cart\'\'\'\n        self.items = []', 'file_path': 'test_script.py', 'generated_tests': None, 'generation_attempt': 0, 'test_results': None, 'build_success': None, 'test_failures': None, 'fixed_tests': None, 'fix_attempt': 0, 'max_iterations': 3, 'current_iteration': 0, 'is_complete': False, 'project_context': {'project_root': '.', 'language': 'python', 'test_framework': 'pytest', 'build_tool': 'pip', 'source_directory': 'src', 'test_directory': 'tests', 'target_file': 'test_script.py', 'relative_path': 'test_script.py', 'dependencies': ['pytest>=7.0.0', 'flask>=2.0.0', 'requests>=2.25.0'], 'has_existing_tests': True}, 'test_framework': 'pytest', 'existing_patterns': {'test_count': 1, 'naming_patterns': ['test-existing.py'], 'common_imports': [], 'test_structure': {'uses_describe_blocks': False, 'uses_setup_teardown': False, 'common_assertions': [], 'test_data_patterns': []}, 'mocking_patterns': []}, 'dependencies': ['pytest>=7.0.0', 'flask>=2.0.0', 'requests>=2.25.0'], 'target_functions': [{'name': 'calculate_discount', 'parameters': [], 'return_type': 'tuple', 'docstring': 'Calculate discount amount and final price\n    \n    Args:\n        price: Original price of the item\n        discount_percent: Percentage discount to apply (0-100)\n        \n    Returns:\n        tuple: (final_price, discount_amount)\n        \n    Raises:\n        ValueError: If price is negative or discount is out of range', 'code': 'def calculate_discount(price: float, discount_percent: int) -> tuple:\n    \'\'\'Calculate discount amount and final price\n    \n    Args:\n        price: Original price of the item\n        discount_percent: Percentage discount to apply (0-100)\n        \n    Returns:\n        tuple: (final_price, discount_amount)\n        \n    Raises:\n        ValueError: If price is negative or discount is out of range\n    \'\'\'\n    if price < 0:\n        raise ValueError("Price cannot be negative")\n    if discount_percent < 0 or discount_percent > 100:\n        raise ValueError("Discount percent must be between 0 and 100")\n    \n    discount_amount = price * (discount_percent / 100)\n    final_price = price - discount_amount\n    return final_price, discount_amount', 'start_line': 1, 'end_line': 21, 'complexity': 3}, {'name': 'apply_bulk_discount', 'parameters': [], 'return_type': 'float', 'docstring': 'Apply bulk discount based on item count', 'code': "def apply_bulk_discount(total_amount: float, item_count: int = 1) -> float:\n    '''Apply bulk discount based on item count'''\n    if item_count >= 10:\n        return total_amount * 0.9  # 10% discount\n    elif item_count >= 5:\n        return total_amount * 0.95  # 5% discount\n    return total_amount", 'start_line': 24, 'end_line': 30, 'complexity': 4}, {'name': '__init__', 'parameters': [], 'return_type': None, 'docstring': None, 'code': 'def __init__(self):\n        self.items = []\n        self.tax_rate = 0.08', 'start_line': 36, 'end_line': 38, 'complexity': 1}, {'name': 'add_item', 'parameters': [], 'return_type': None, 'docstring': 'Add an item to the cart', 'code': 'def add_item(self, item: str, price: float, quantity: int = 1):\n        \'\'\'Add an item to the cart\'\'\'\n        if price < 0:\n            raise ValueError("Price cannot be negative")\n        if quantity < 1:\n            raise ValueError("Quantity must be at least 1")\n            \n        self.items.append({\n            \'item\': item,\n            \'price\': price,\n            \'quantity\': quantity\n        })', 'start_line': 40, 'end_line': 51, 'complexity': 3}, {'name': 'remove_item', 'parameters': [], 'return_type': 'bool', 'docstring': 'Remove an item from the cart', 'code': "def remove_item(self, item: str) -> bool:\n        '''Remove an item from the cart'''\n        for i, cart_item in enumerate(self.items):\n            if cart_item['item'] == item:\n                self.items.pop(i)\n                return True\n        return False", 'start_line': 53, 'end_line': 59, 'complexity': 3}, {'name': 'get_subtotal', 'parameters': [], 'return_type': 'float', 'docstring': 'Calculate subtotal before tax', 'code': "def get_subtotal(self) -> float:\n        '''Calculate subtotal before tax'''\n        return sum(item['price'] * item['quantity'] for item in self.items)", 'start_line': 61, 'end_line': 63, 'complexity': 3}, {'name': 'get_tax_amount', 'parameters': [], 'return_type': 'float', 'docstring': 'Calculate tax amount', 'code': "def get_tax_amount(self) -> float:\n        '''Calculate tax amount'''\n        return self.get_subtotal() * self.tax_rate", 'start_line': 65, 'end_line': 67, 'complexity': 1}, {'name': 'get_total', 'parameters': [], 'return_type': 'float', 'docstring': 'Calculate total including tax', 'code': "def get_total(self) -> float:\n        '''Calculate total including tax'''\n        return self.get_subtotal() + self.get_tax_amount()", 'start_line': 69, 'end_line': 71, 'complexity': 1}, {'name': 'clear_cart', 'parameters': [], 'return_type': None, 'docstring': 'Empty the shopping cart', 'code': "def clear_cart(self):\n        '''Empty the shopping cart'''\n        self.items = []", 'start_line': 73, 'end_line': 75, 'complexity': 1}], 'max_iteration': 0}"""

    #test the generator
    result = generator_node(scaffolder_result)
    
    print("\n" + "="*50)
    print("GENERATOR RESULTS")
    print("="*50)
    print(f"Generation Attempt: {result.get('generation_attempt')}")
    print(f"Generated Tests Length: {len(result.get('generated_tests', ''))}")
    print("\nGENERATED TEST CODE:")
    print("-" * 30)
    print(result.get('generated_tests', 'No tests generated'))
