# file: transforms.py
from typing import Dict, Any, List, Optional
import copy

def find_node_by_id(node: Dict[str, Any], node_id: str) -> Optional[Dict[str, Any]]:
    if node.get("id") == node_id:
        return node
    for k in ("child","left","right","children"):
        if k in node:
            c = node[k]
            if isinstance(c, list):
                for ch in c:
                    res = find_node_by_id(ch, node_id)
                    if res: return res
            elif isinstance(c, dict):
                res = find_node_by_id(c, node_id)
                if res: return res
    return None

def replace_node(parent: Dict[str, Any], target_id: str, new_node: Dict[str, Any]) -> bool:
    for k in ("child","left","right","children"):
        if k in parent:
            c = parent[k]
            if isinstance(c, dict):
                if c.get("id") == target_id:
                    parent[k] = new_node
                    return True
                else:
                    if replace_node(c, target_id, new_node):
                        return True
            elif isinstance(c, list):
                for i, ch in enumerate(c):
                    if ch.get("id") == target_id:
                        parent[k][i] = new_node
                        return True
                    else:
                        if replace_node(ch, target_id, new_node):
                            return True
    return False

def canonicalize_exprs(node: Dict[str, Any]) -> Dict[str, Any]:
    n = copy.deepcopy(node)
    if "exprs" in n and isinstance(n["exprs"], list):
        n["exprs"] = sorted(n["exprs"], key=lambda x: str(x))
    for k in ("child","left","right","children"):
        if k in n:
            c = n[k]
            if isinstance(c, dict):
                n[k] = canonicalize_exprs(c)
            elif isinstance(c, list):
                n[k] = [canonicalize_exprs(ch) for ch in c]
    return n

def ra_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    ca = canonicalize_exprs(a)
    cb = canonicalize_exprs(b)
    return ca == cb

def apply_filter_project_transpose(tree: Dict[str, Any], node_id: str) -> Optional[Dict[str, Any]]:
    node = find_node_by_id(tree, node_id)
    if not node: return None
    if node.get("type") != "Project": return None
    child = node.get("child")
    if not child or child.get("type") != "Filter": return None
    new_filter = copy.deepcopy(child)
    new_project = copy.deepcopy(node)
    new_project["child"] = child.get("child")
    new_filter["child"] = new_project
    new_filter["id"] = child.get("id")
    new_project["id"] = node.get("id")
    top = copy.deepcopy(tree)
    if top.get("id") == node_id:
        return new_filter
    replaced = replace_node(top, node_id, new_filter)
    if not replaced:
        return None
    return top

def apply_join_commute(tree: Dict[str, Any], node_id: str) -> Optional[Dict[str, Any]]:
    node = find_node_by_id(tree, node_id)
    if not node: return None
    if node.get("type") != "Join": return None
    left = node.get("left")
    right = node.get("right")
    if not left or not right: return None
    new_node = copy.deepcopy(node)
    new_node["left"] = right
    new_node["right"] = left
    new_node["id"] = node.get("id")
    top = copy.deepcopy(tree)
    replaced = replace_node(top, node_id, new_node)
    if not replaced:
        return None
    return top

def apply_project_pushdown(tree: Dict[str, Any], node_id: str) -> Optional[Dict[str, Any]]:
    node = find_node_by_id(tree, node_id)
    if not node: return None
    if node.get("type") != "Project": return None
    child = node.get("child")
    if not child or child.get("type") != "Join": return None
    proj_exprs = set(node.get("exprs",[]))
    left_cols = set(child.get("left",{}).get("output_cols",[]))
    right_cols = set(child.get("right",{}).get("output_cols",[]))
    left_proj = {"id": child["left"].get("id")+"__proj", "type":"Project", "exprs": [e for e in node.get("exprs",[]) if any(c in left_cols for c in extract_cols(e))], "child": child["left"], "output_cols": list(left_cols & proj_exprs) or list(left_cols)}
    right_proj = {"id": child["right"].get("id")+"__proj", "type":"Project", "exprs": [e for e in node.get("exprs",[]) if any(c in right_cols for c in extract_cols(e))], "child": child["right"], "output_cols": list(right_cols & proj_exprs) or list(right_cols)}
    new_join = copy.deepcopy(child)
    new_join["left"] = left_proj
    new_join["right"] = right_proj
    new_proj = copy.deepcopy(node)
    new_proj["child"] = new_join
    top = copy.deepcopy(tree)
    replaced = replace_node(top, node_id, new_proj)
    if not replaced:
        return None
    return top

def extract_cols(expr: str) -> List[str]:
    toks = []
    cur = ""
    for ch in expr:
        if ch.isalnum() or ch == "_" or ch=='.':
            cur += ch
        else:
            if cur:
                toks.append(cur)
                cur = ""
    if cur:
        toks.append(cur)
    return toks

RULE_MAP = {
    "FilterProjectTranspose": apply_filter_project_transpose,
    "JoinCommute": apply_join_commute,
    "ProjectPushdown": apply_project_pushdown
}

def apply_sequence(source: Dict[str, Any], sequence: List[Dict[str, Any]], vocab: List[str]) -> Dict[str, Any]:
    cur = copy.deepcopy(source)
    trace = [copy.deepcopy(cur)]
    for step in sequence:
        rule = step.get("rule")
        node_id = step.get("node_id")
        if rule not in vocab or rule not in RULE_MAP:
            return {"ok": False, "error": f"rule_not_supported:{rule}", "trace": trace}
        fn = RULE_MAP[rule]
        res = fn(cur, node_id)
        if res is None:
            return {"ok": False, "error": f"rule_application_failed:{rule}@{node_id}", "trace": trace}
        cur = res
        trace.append(copy.deepcopy(cur))
    return {"ok": True, "final": cur, "trace": trace}
