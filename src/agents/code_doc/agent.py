# Main agent implementation
# agents/code_doc/agent.py
import os
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
import git
import re

from agent_core.models.base import ModelInterface
from agents.base_agent import BaseAgent
from agents.code_doc.git_monitor import GitMonitor
from agents.code_doc.code_parser import CodeParser

class CodeDocAgent(BaseAgent):
    """Agent for monitoring code changes and suggesting documentation updates."""
    
    def __init__(self, config: Dict[str, Any], model_interface: ModelInterface):
        super().__init__("code_documentation", config, model_interface)
        self.watch_paths = config.get("watch_paths", [])
        self.ignore_patterns = config.get("ignore_patterns", [])
        self.parser = CodeParser()
        self.git_monitor = None
        
    async def initialize(self) -> None:
        """Initialize the code documentation agent."""
        self.logger.info("Initializing code documentation agent")
        if self.config.get("commit_analysis", False):
            try:
                self.git_monitor = GitMonitor(self.watch_paths)
                self.logger.info("Git monitoring enabled")
            except Exception as e:
                self.logger.error(f"Failed to initialize Git monitoring: {str(e)}")
                self.git_monitor = None
    
    async def run_cycle(self) -> Dict[str, Any]:
        """Run a documentation cycle."""
        self.logger.info("Running code documentation cycle")
        
        # Analyze either git changes or file system changes
        if self.git_monitor and self.config.get("commit_analysis", False):
            changes = await self._analyze_git_changes()
        else:
            changes = await self._analyze_file_changes()
        
        if not changes:
            self.logger.info("No changes detected")
            return {"status": "no_changes"}
        
        # Process changes and generate documentation suggestions
        results = await self._process_changes(changes)
        
        # Format and store results
        formatted_results = self._format_results(results)
        
        return {
            "status": "completed",
            "changes_detected": len(changes),
            "documentation_suggestions": formatted_results
        }
    
    async def _analyze_git_changes(self) -> List[Dict[str, Any]]:
        """Analyze changes from Git."""
        if not self.git_monitor:
            return []
            
        self.logger.info("Analyzing Git changes")
        changes = self.git_monitor.get_recent_changes()
        filtered_changes = self._filter_relevant_changes(changes)
        return filtered_changes
    
    async def _analyze_file_changes(self) -> List[Dict[str, Any]]:
        """Analyze changes from the file system."""
        self.logger.info("Analyzing file system for changes")
        # This would track file modifications based on timestamps or hashing
        # For now, we'll return an example
        return [
            {
                "file": "src/example.py",
                "type": "modified",
                "last_modified": "2023-05-06T10:30:00"
            }
        ]
    
    def _filter_relevant_changes(self, changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter changes based on ignore patterns."""
        filtered = []
        for change in changes:
            file_path = change.get("file", "")
            # Check if file matches any ignore pattern
            if not any(re.match(pattern, file_path) for pattern in self.ignore_patterns):
                filtered.append(change)
        return filtered
    
    async def _process_changes(self, changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process code changes and generate documentation suggestions."""
        results = []
        
        for change in changes:
            file_path = change.get("file")
            if not os.path.exists(file_path):
                continue
                
            # Parse the code file
            code_content = Path(file_path).read_text(encoding='utf-8')
            parsed_code = self.parser.parse(file_path, code_content)
            
            # Generate documentation with the AI model
            prompt = self._create_doc_prompt(parsed_code, change)
            suggestion = await self.model.generate(
                prompt=prompt,
                system_prompt="You are an expert code documentation assistant. Your task is to suggest documentation updates based on code changes.",
                parameters={"temperature": 0.2}
            )
            
            results.append({
                "file": file_path,
                "type": change.get("type"),
                "suggestion": suggestion
            })
            
        return results
    
    def _create_doc_prompt(self, parsed_code: Dict[str, Any], change: Dict[str, Any]) -> str:
        """Create a prompt for documentation generation."""
        return f"""
        I need documentation suggestions for the following code changes:
        
        File: {change.get('file')}
        Change type: {change.get('type')}
        
        Code:
        ```python
        {parsed_code.get('content', '')}
        ```
        
        Existing functions/classes:
        {parsed_code.get('functions', [])}
        {parsed_code.get('classes', [])}
        
        Please provide documentation suggestions for:
        1. Module-level documentation
        2. Function/method documentation
        3. Class documentation
        
        The documentation should follow PEP 257 guidelines and include:
        - Purpose/responsibility of each component
        - Parameters and return values
        - Examples if appropriate
        """
    
    def _format_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format results for storage or display."""
        formatted = {}
        
        for result in results:
            file_path = result.get("file")
            formatted[file_path] = {
                "type": result.get("type"),
                "suggestion": result.get("suggestion")
            }
            
        return formatted