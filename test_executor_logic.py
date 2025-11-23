import asyncio
import sys
import io
import textwrap
import ast
from contextlib import redirect_stdout

# Mock async tool
async def factorial(n):
    await asyncio.sleep(0.01)
    return n * 10  # Mock factorial

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
fibs = [1, 2, 3]
print("Calculating factorials...")
facts = [factorial(x) for x in fibs]
print(f"Factorials: {facts}")
"""
    
    print("--- Starting Test ---")
    
    cleaned_code = textwrap.dedent(code.strip())
    tree = ast.parse(cleaned_code)
    
    # Apply AwaitTransformer
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
    sandbox = {"print": print, "factorial": factorial}
    
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
    
    if "Factorials: [10, 20, 30]" in output:
        print("✅ SUCCESS: Async list comprehension worked")
    else:
        print("❌ FAILURE: Async list comprehension failed")

if __name__ == "__main__":
    asyncio.run(test_execution())
