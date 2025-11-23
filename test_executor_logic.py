import asyncio
import sys
import io
import textwrap
import ast
from contextlib import redirect_stdout

# Mock async tool (not used in this test, but needed for AwaitTransformer)
async def factorial_tool(n):
    return n * 10

class AwaitTransformer(ast.NodeTransformer):
    def __init__(self, async_funcs):
        self.async_funcs = async_funcs

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id in self.async_funcs:
            return ast.Await(value=node)
        return node

async def test_execution():
    code = """
def fibonacci_numbers(n):
    fib_list = [0, 1]
    while len(fib_list) < n:
        next_fib = fib_list[-1] + fib_list[-2]
        fib_list.append(next_fib)
    return fib_list

def factorial(n):
    if n == 0:
        return 1
    else:
        return n * factorial(n-1)

fib_nums = fibonacci_numbers(8)
even_fib_nums = [num for num in fib_nums if num % 2 == 0]
factorial_even_fib_nums = [factorial(num) for num in even_fib_nums]
sum_factorial_even_fib_nums = sum(factorial_even_fib_nums)

print(sum_factorial_even_fib_nums)
"""
    
    print("--- Starting Test ---")
    
    cleaned_code = textwrap.dedent(code.strip())
    tree = ast.parse(cleaned_code)
    
    # Apply AwaitTransformer (should affect nothing as local functions shadow tools?)
    # Wait, AwaitTransformer checks function names.
    # If "factorial" is in async_funcs, it will wrap the call in await.
    # But "factorial" is defined locally!
    
    # In executor.py, async_funcs = set(tool_funcs)
    # If "factorial" is a tool, it's in the set.
    # So AwaitTransformer will wrap `factorial(num)` in `await`.
    
    # BUT `factorial` refers to the LOCAL function, which is synchronous!
    # So `await factorial(num)` will fail because `factorial(num)` returns an int, not an awaitable!
    
    print("Applying AwaitTransformer with 'factorial' as a tool...")
    tree = AwaitTransformer({"factorial"}).visit(tree)
    ast.fix_missing_locations(tree)
    
    # Wrap in async function
    func_def = ast.AsyncFunctionDef(
        name="__main",
        args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=tree.body,
        decorator_list=[]
    )
    wrapper = ast.Module(body=[func_def], type_ignores=[])
    ast.fix_missing_locations(wrapper)
    
    compiled = compile(wrapper, filename="<user_code>", mode="exec")
    
    local_vars = {}
    sandbox = {"print": print} # No tools in sandbox, as code defines them
    
    exec(compiled, sandbox, local_vars)
    
    # Capture stdout
    f = io.StringIO()
    
    print("Executing code...")
    try:
        with redirect_stdout(f):
            await local_vars["__main"]()
    except Exception as e:
        print(f"Execution error: {e}")
        import traceback
        traceback.print_exc()
        
    output = f.getvalue().strip()
    print(f"Captured Output: '{output}'")

if __name__ == "__main__":
    asyncio.run(test_execution())
