
import ast
import asyncio
import time
import builtins
import textwrap
import re
from datetime import datetime

# ───────────────────────────────────────────────────────────────
# CONFIG
# ───────────────────────────────────────────────────────────────
ALLOWED_MODULES = {
    "math", "cmath", "decimal", "fractions", "random", "statistics", "itertools", "functools", "operator", "string", "re", "datetime", "calendar", "time", "collections", "heapq", "bisect", "types", "copy", "enum", "uuid", "dataclasses", "typing", "pprint", "json", "base64", "hashlib", "hmac", "secrets", "struct", "zlib", "gzip", "bz2", "lzma", "io", "pathlib", "tempfile", "textwrap", "difflib", "unicodedata", "html", "html.parser", "xml", "xml.etree.ElementTree", "csv", "sqlite3", "contextlib", "traceback", "ast", "tokenize", "token", "builtins"
}
MAX_FUNCTIONS = 50
TIMEOUT_PER_FUNCTION = 500  # seconds

class KeywordStripper(ast.NodeTransformer):
    """Rewrite all function calls to remove keyword args and keep only values as positional."""
    def visit_Call(self, node):
        self.generic_visit(node)
        if node.keywords:
            # Convert all keyword arguments into positional args (discard names)
            for kw in node.keywords:
                node.args.append(kw.value)
            node.keywords = []
        return node


# ───────────────────────────────────────────────────────────────
# AST TRANSFORMER: auto-await known async MCP tools
# ───────────────────────────────────────────────────────────────
class AwaitTransformer(ast.NodeTransformer):
    def __init__(self, async_funcs):
        self.async_funcs = async_funcs

    def visit_Await(self, node):
        # Mark inner call so we don't wrap it again
        if isinstance(node.value, ast.Call):
            setattr(node.value, "_skip_auto_await", True)
        node.value = self.visit(node.value)
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        if getattr(node, "_skip_auto_await", False):
            return node
        if isinstance(node.func, ast.Name) and node.func.id in self.async_funcs:
            return ast.Await(value=node)
        return node

# ───────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ───────────────────────────────────────────────────────────────

# ───────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ───────────────────────────────────────────────────────────────
def count_function_calls(code: str) -> int:
    tree = ast.parse(code)
    return sum(isinstance(node, ast.Call) for node in ast.walk(tree))

def build_safe_globals(mcp_funcs: dict, multi_mcp=None) -> dict:
    safe_globals = {
        "__builtins__": {
            k: getattr(builtins, k)
            for k in ("range", "len", "int", "float", "str", "list", "dict", "print", "sum", "type", "__import__")
        },
        **mcp_funcs,
    }

    for module in ALLOWED_MODULES:
        safe_globals[module] = __import__(module)

    # Store LLM-style result
    safe_globals["final_answer"] = lambda x: safe_globals.setdefault("result_holder", x)

    # Optional: add parallel execution
    if multi_mcp:
        async def parallel(*tool_calls):
            coros = [
                multi_mcp.function_wrapper(tool_name, *args)
                for tool_name, *args in tool_calls
            ]
            return await asyncio.gather(*coros)

        safe_globals["parallel"] = parallel

    return safe_globals


# ───────────────────────────────────────────────────────────────
# MAIN EXECUTOR
# ───────────────────────────────────────────────────────────────
async def run_user_code(code: str, multi_mcp) -> dict:
    start_time = time.perf_counter()
    start_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Validate Syntax
    syntax_error = validate_code(code)
    if syntax_error:
        return {
            "status": "error",
            "error": syntax_error,
            "execution_time": start_timestamp,
            "total_time": "0.0"
        }

    try:
        func_count = count_function_calls(code)
        if func_count > MAX_FUNCTIONS:
            return {
                "status": "error",
                "error": f"Too many functions ({func_count} > {MAX_FUNCTIONS})",
                "execution_time": start_timestamp,
                "total_time": str(round(time.perf_counter() - start_time, 3))
            }

        tool_funcs = {
            tool.name: make_tool_proxy(tool.name, multi_mcp)
            for tool in multi_mcp.get_all_tools()
        }

        sandbox = build_safe_globals(tool_funcs, multi_mcp)
        local_vars = {}

        cleaned_code = textwrap.dedent(code.strip())
        tree = ast.parse(cleaned_code)

        has_return = any(isinstance(node, ast.Return) for node in tree.body)
        has_result = any(
            isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "result" for t in node.targets
            )
            for node in tree.body
        )
        if not has_return and has_result:
            tree.body.append(ast.Return(value=ast.Name(id="result", ctx=ast.Load())))

        tree = KeywordStripper().visit(tree) # strip "key" = "value" cases to only "value"
        
        # Detect locally defined functions that shadow tools
        local_defs = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                local_defs.add(node.name)
        
        # Only auto-await tools that are NOT shadowed by local definitions
        safe_tools_to_await = set(tool_funcs) - local_defs
        
        tree = AwaitTransformer(safe_tools_to_await).visit(tree)
        ast.fix_missing_locations(tree)

        func_def = ast.AsyncFunctionDef(
            name="__main",
            args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=tree.body,
            decorator_list=[]
        )
        wrapper = ast.Module(body=[func_def], type_ignores=[])
        ast.fix_missing_locations(wrapper)

        compiled = compile(wrapper, filename="<user_code>", mode="exec")
        exec(compiled, sandbox, local_vars)

        try:
            timeout = max(3, func_count * TIMEOUT_PER_FUNCTION)  # minimum 3s even for plain returns
            
            # Capture stdout
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            
            with redirect_stdout(f):
                returned = await asyncio.wait_for(local_vars["__main"](), timeout=timeout)
            
            stdout_output = f.getvalue().strip()
            
            # Determine final result: explicit return > result_holder > stdout
            result_value = returned
            if result_value is None:
                result_value = sandbox.get("result_holder", None)
            if result_value is None or str(result_value) == "None":
                result_value = stdout_output if stdout_output else "Executed successfully (no output)."

            # If result looks like tool error text, extract
            # Handle CallToolResult errors from MCP
            if hasattr(result_value, "isError") and getattr(result_value, "isError", False):
                error_msg = None

                try:
                    error_msg = result_value.content[0].text.strip()
                except Exception:
                    error_msg = str(result_value)

                # DEBUG: Print error to stderr
                import sys
                sys.stderr.write(f"\n🔴 TOOL ERROR ({len(error_msg)} chars): {error_msg}\n")
                sys.stderr.flush()

                return {
                    "status": "error",
                    "error": error_msg,
                    "execution_time": start_timestamp,
                    "total_time": str(round(time.perf_counter() - start_time, 3))
                }

            # Else: normal success
            return {
                "status": "success",
                "result": str(result_value),
                "execution_time": start_timestamp,
                "total_time": str(round(time.perf_counter() - start_time, 3))
            }


        except Exception as e:
            return {
                "status": "error",
                "error": f"{type(e).__name__}: {str(e)}",
                "execution_time": start_timestamp,
                "total_time": str(round(time.perf_counter() - start_time, 3))
            }


    except asyncio.TimeoutError:
        return {
            "status": "error",
            "error": f"Execution timed out after {func_count * TIMEOUT_PER_FUNCTION} seconds",
            "execution_time": start_timestamp,
            "total_time": str(round(time.perf_counter() - start_time, 3))
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "execution_time": start_timestamp,
            "total_time": str(round(time.perf_counter() - start_time, 3))
        }

# ───────────────────────────────────────────────────────────────
# TOOL WRAPPER
# ───────────────────────────────────────────────────────────────
def validate_code(code: str) -> str:
    """Validate Python code syntax. Returns error message or None."""
    try:
        ast.parse(code)
        return None
    except SyntaxError as e:
        return f"SyntaxError: {e.msg} at line {e.lineno}"

def make_tool_proxy(tool_name: str, mcp):
    async def _tool_fn(*args):
        # DEBUG: Log what's being passed to the tool
        print(f"[MCP] Calling tool '{tool_name}' with args: {args}")
        print(f"[MCP] Arg types: {[type(arg).__name__ for arg in args]}")
        print(f"[MCP] Arg values: {[repr(arg) for arg in args]}")
        
        # CRITICAL FIX: Check if any args are string representations that shouldn't be
        # This happens when variables in loops aren't properly evaluated
        processed_args = []
        for arg in args:
            # If arg is a string that looks like a variable name or 'result', 
            # it means the variable wasn't evaluated - this is a bug
            if isinstance(arg, str) and arg in ('result', 'num', 'fib_nums', 'fibonacci_sequence'):
                print(f"[MCP] WARNING: Received variable name '{arg}' as string instead of value!")
                print(f"[MCP] This indicates the variable was not evaluated before passing to tool")
                # We can't fix this here - the value is already lost
                # The fix needs to be earlier in the execution chain
                processed_args.append(arg)
            else:
                processed_args.append(arg)
        
        # Retry logic for tool calls (simple retry for transient errors)
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                result = await mcp.function_wrapper(tool_name, *processed_args)
                
                # Unwrap CallToolResult
                if hasattr(result, "content") and result.content:
                    text_content = result.content[0].text
                    
                    # Try to parse JSON
                    import json
                    try:
                        data = json.loads(text_content)
                        # If it's a dict with a 'result' key, return that value
                        # This handles cases where extra fields might be present
                        if isinstance(data, dict) and "result" in data:
                            extracted_result = data["result"]
                            print(f"[MCP] Tool '{tool_name}' returned (extracted): {extracted_result}")
                            return extracted_result
                        print(f"[MCP] Tool '{tool_name}' returned (parsed JSON): {data}")
                        return data
                    except json.JSONDecodeError:
                        print(f"[MCP] Tool '{tool_name}' returned (raw text): {text_content[:100]}...")
                        return text_content
                
                print(f"[MCP] Tool '{tool_name}' returned (direct): {result}")
                return result
            except Exception as e:
                last_error = e
                print(f"[MCP] Tool '{tool_name}' attempt {attempt + 1} failed: {e}")
                # Wait briefly before retry
                await asyncio.sleep(0.5 * (attempt + 1))
        
        raise last_error

    return _tool_fn
