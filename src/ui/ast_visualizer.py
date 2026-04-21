from src.compiler.ast_nodes import Node

_BRANCH = "├── "
_LAST   = "└── "
_PIPE   = "│   "
_EMPTY  = "    "

# Attributes that hold child AST nodes (not leaf values)
_CHILD_ATTRS = {
    "statements", "then_branch", "else_branch", "body",
    "left", "right", "operand", "expression", "condition",
    "params", "args", "value",
}


def _node_label(node):
    """Short one-line label for a node."""
    name = type(node).__name__
    extras = []
    for attr in ("name", "op", "operator", "type_name", "return_type"):
        if hasattr(node, attr):
            val = getattr(node, attr)
            if val is not None:
                extras.append(f"{attr}={repr(val)}")
    if hasattr(node, "value") and not isinstance(getattr(node, "value"), Node):
        val = getattr(node, "value")
        if val is not None:
            extras.append(f"value={repr(val)}")
    return f"{name}({', '.join(extras)})" if extras else name


def _collect_children(node):
    """Return a list of (label, child) pairs for all child nodes."""
    children = []
    if not hasattr(node, "__dict__"):
        return children
    for attr, val in vars(node).items():
        if attr.startswith("_") or attr not in _CHILD_ATTRS:
            continue
        if isinstance(val, list):
            for i, item in enumerate(val):
                if isinstance(item, Node):
                    children.append((f"{attr}[{i}]", item))
                elif isinstance(item, tuple):
                    # e.g. params = [(type, name), ...]
                    children.append((f"{attr}[{i}]", item))
        elif isinstance(val, Node):
            children.append((attr, val))
    return children


def _render(node, prefix="", is_last=True, lines=None):
    if lines is None:
        lines = []

    connector = _LAST if is_last else _BRANCH

    if isinstance(node, tuple):
        lines.append(f"{prefix}{connector}({', '.join(repr(v) for v in node)})")
        return lines

    if not isinstance(node, Node):
        lines.append(f"{prefix}{connector}{repr(node)}")
        return lines

    lines.append(f"{prefix}{connector}{_node_label(node)}")

    child_prefix = prefix + (_EMPTY if is_last else _PIPE)
    children = _collect_children(node)
    for i, (label, child) in enumerate(children):
        is_child_last = (i == len(children) - 1)
        _render(child, prefix=child_prefix, is_last=is_child_last, lines=lines)

    return lines


def visualize_ast(node):
    """Return a pretty-printed tree string for the given AST root."""
    if node is None:
        return "(empty)"
    if isinstance(node, list):
        lines = []
        for item in node:
            lines += _render(item, is_last=True)
        return "\n".join(lines)
    lines = _render(node, prefix="", is_last=True)
    return "\n".join(lines)
