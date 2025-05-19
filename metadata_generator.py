# metadata_generator.py
import ast
import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Any
import argparse

EXCLUDE_DIRS = {'.vscode','myenv',  'venv', 'env', '.venv', 'virtualenv', '.idea', '__pycache__', '.git'}

def parse_metadata(docstring: str) -> Dict:
    """Extract YAML metadata from docstring"""
    if not docstring:
        return {}
    
    pattern = r'^-{3,}\n(?P<metadata>.+?)\n^-{3,}\n?(?P<description>.*)'
    match = re.search(pattern, docstring, re.DOTALL | re.MULTILINE)
    
    metadata = {}
    if match:
        try:
            metadata = yaml.safe_load(match.group('metadata')) or {}
        except yaml.YAMLError:
            pass
    return metadata

class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.modules: Dict[str, Any] = {}
        self.current_module = None
        self.current_class = None

    def visit_Module(self, node):
        self.current_module = "global"
        self.generic_visit(node)
        self.current_module = None

    def visit_ClassDef(self, node):
        self.current_class = node.name
        docstring = ast.get_docstring(node) or ""
        metadata = parse_metadata(docstring)
        
        class_info = {
            "name": node.name,
            "type": "class",
            "methods": [],
            "docstring": docstring.split('---', 2)[-1].strip() if '---' in docstring else docstring,
            "metadata": metadata,
            "dependencies": self._get_dependencies(node),
            "line": node.lineno
        }
        self.modules.setdefault(self.current_module, {}).setdefault("classes", []).append(class_info)
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node):
        docstring = ast.get_docstring(node) or ""
        metadata = parse_metadata(docstring)
        
        func_info = {
            "name": node.name,
            "type": "method" if self.current_class else "function",
            "parameters": [arg.arg for arg in node.args.args],
            "docstring": docstring.split('---', 2)[-1].strip() if '---' in docstring else docstring,
            "metadata": metadata,
            "dependencies": self._get_dependencies(node),
            "line": node.lineno
        }
        
        if self.current_class:
            self.modules[self.current_module]["classes"][-1]["methods"].append(func_info)
        else:
            self.modules.setdefault(self.current_module, {}).setdefault("functions", []).append(func_info)

        self.generic_visit(node)

    def _get_dependencies(self, node) -> List[str]:
        dependencies = set()
        
        def _get_full_name(node):
            if isinstance(node, ast.Name):
                return node.id
            elif isinstance(node, ast.Attribute):
                base = _get_full_name(node.value)
                return f"{base}.{node.attr}" if base else node.attr
            return None

        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                if isinstance(n.func, (ast.Attribute, ast.Name)):
                    full_name = _get_full_name(n.func)
                    if full_name:
                        dependencies.add(full_name)
            elif isinstance(n, ast.Import):
                dependencies.update(alias.name for alias in n.names)
            elif isinstance(n, ast.ImportFrom):
                module = n.module or ""
                for alias in n.names:
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    dependencies.add(full_name)
        
        return sorted([d for d in dependencies if d])

def parse_python_file(file_path: str) -> Dict:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Parse module-level metadata
    module_metadata = {}
    first_comment = re.search(r'^"""(.*?)"""', content, re.DOTALL)
    if first_comment:
        module_metadata = parse_metadata(first_comment.group(1))
    
    tree = ast.parse(content)
    analyzer = CodeAnalyzer()
    analyzer.visit(tree)
    
    return {
        "file": file_path,
        "modules": analyzer.modules,
        "metadata": module_metadata
    }

def generate_system_metadata(project_root: str, output_file: str = "system_metadata.yaml"):
    system_data = {"modules": [], "entry_points": [], "external_connections": []}
    
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                try:
                    file_data = parse_python_file(full_path)
                except Exception as e:
                    print(f"Skipping {full_path} due to error: {str(e)}")
                    continue

                relative_file_path = str(Path(full_path).relative_to(project_root))
                module_path = relative_file_path.replace("/", ".").replace(".py", "")
                
                module_entry = {
                    "name": module_path,
                    "filename": relative_file_path,
                    "metadata": file_data.get("metadata", {}),
                    "components": [],
                    "dependencies": []
                }

                # Process functions
                for component in file_data["modules"].get("global", {}).get("functions", []):
                    if "name" not in component:
                        continue
                    
                    component_entry = {
                        "name": component["name"],
                        "type": "function",
                        "filename": relative_file_path,
                        "metadata": component.get("metadata", {}),
                        "dependencies": component.get("dependencies", []),
                        "docstring": component.get("docstring", ""),
                        "line": component.get("line", -1)
                    }
                    module_entry["components"].append(component_entry)
                    module_entry["dependencies"].extend(component.get("dependencies", []))

                # Process classes
                for component in file_data["modules"].get("global", {}).get("classes", []):
                    if "name" not in component:
                        continue
                    
                    component_entry = {
                        "name": component["name"],
                        "type": "class",
                        "filename": relative_file_path,
                        "metadata": component.get("metadata", {}),
                        "dependencies": component.get("dependencies", []),
                        "docstring": component.get("docstring", ""),
                        "line": component.get("line", -1)
                    }
                    module_entry["components"].append(component_entry)
                    module_entry["dependencies"].extend(component.get("dependencies", []))

                module_entry["dependencies"] = sorted(list(set(module_entry["dependencies"])))
                system_data["modules"].append(module_entry)
    
    with open(output_file, "w") as f:
        yaml.dump(system_data, f, sort_keys=False)
    
    return system_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate system metadata YAML from Python project")
    parser.add_argument("project_root", help="Root directory of the Python project")
    parser.add_argument("-o", "--output", default="system_metadata.yaml", help="Output YAML file")
    
    args = parser.parse_args()
    generate_system_metadata(args.project_root, args.output)
    print(f"Metadata generated successfully at {args.output}")