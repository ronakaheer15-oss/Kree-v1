import ast
import operator

_operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

def _eval_node(node) -> float | int:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numeric constants are allowed.")
    elif isinstance(node, ast.Num):
        return node.n
    elif isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        op_type = type(node.op)
        if op_type in _operators:
            if op_type == ast.Div and right == 0:
                raise ZeroDivisionError("Division by zero")
            if op_type == ast.Mod and right == 0:
                raise ZeroDivisionError("Modulo by zero")
            if op_type == ast.Pow and abs(right) > 1000:
                raise ValueError("Exponent too large")
            return _operators[op_type](left, right)
        raise ValueError(f"Operator {op_type.__name__} is not allowed.")
    elif isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand)
        op_type = type(node.op)
        if op_type in _operators:
            return _operators[op_type](operand)
        raise ValueError(f"Unary operator {op_type.__name__} is not allowed.")
    elif isinstance(node, ast.Expression):
        return _eval_node(node.body)
    raise ValueError(f"Unsupported syntax: {type(node).__name__}")

def calculate(expression: str) -> str:
    """Safely evaluates a mathematical expression using AST parsing."""
    try:
        expr_str = expression.strip()
        if not expr_str:
            return "Error: Empty expression"
        tree = ast.parse(expr_str, mode="eval")
        result = _eval_node(tree.body)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return str(result)
    except ZeroDivisionError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"
