"""
Tool Manager for Gemini Autonomous Engine
========================================

Defines the tools available to the Gemini agent and handles their execution.
"""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from security import validate_command


class ToolManager:
    def __init__(self, project_dir: Union[str, Path]):
        self.project_dir = Path(project_dir).resolve()
        
    def _is_safe_path(self, path: Union[str, Path]) -> bool:
        """Ensure path is within project directory."""
        try:
            target_path = (self.project_dir / path).resolve()
            return str(target_path).startswith(str(self.project_dir))
        except Exception:
            return False

    def execute_bash(self, command: str) -> str:
        """
        Execute a bash command if it passes security validation.
        
        Args:
            command: The bash command to execute
            
        Returns:
            Command output (stdout + stderr) or error message
        """
        # Security check
        is_allowed, reason = validate_command(command)
        if not is_allowed:
            return f"[SECURITY BLOCK] Command blocked: {reason}"
            
        try:
            # Run command in project directory
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            # Enhanced Tool Feedback (Round 5 Optimization)
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                hint = ""
                
                # Common Error Heuristics
                if "ModuleNotFoundError" in error_msg or "ImportError" in error_msg:
                    hint = "\n[SYSTEM HINT] Missing dependencies. Check 'requirements.txt' or 'package.json' and install them."
                elif "SyntaxError" in error_msg:
                    hint = "\n[SYSTEM HINT] Syntax error detected. Review the code carefully."
                elif "No such file or directory" in error_msg:
                    hint = "\n[SYSTEM HINT] File path incorrect. Use 'list_directory' to verify paths."
                elif "command not found" in error_msg:
                    hint = "\n[SYSTEM HINT] Command not found. Check if the tool is installed or use a different command."
                
                return f"Error (Exit Code {result.returncode}):\n{error_msg}{hint}"
            
            # Combine stdout and stderr
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR:\n{result.stderr}"
            
            # Smart Truncation
            lines = output.splitlines()
            if len(lines) > 200:
                head = lines[:10]
                tail = lines[-50:]
                truncated_count = len(lines) - 60
                output = "\n".join(head) + \
                         f"\n\n... [TRUNCATED {truncated_count} LINES OF OUTPUT] ...\n\n" + \
                         "\n".join(tail)
            
            return output
            
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 120 seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"

    def read_file(self, path: str) -> str:
        """
        Read content of a file.
        
        Args:
            path: Relative path to file
            
        Returns:
            File content or error message
        """
        if not self._is_safe_path(path):
            return "Error: Access denied (path outside project directory)"
            
        target_path = self.project_dir / path
        
        if not target_path.exists():
            return f"Error: File not found: {path}"
            
        if not target_path.is_file():
            return f"Error: Not a file: {path}"
            
        try:
            return target_path.read_text(encoding='utf-8')
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def write_file(self, path: str, content: str) -> str:
        """
        Write content to a file.
        
        Args:
            path: Relative path to file
            content: Content to write
            
        Returns:
            Success message or error message
        """
        if not self._is_safe_path(path):
            return "Error: Access denied (path outside project directory)"
            
        target_path = self.project_dir / path
        
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding='utf-8')
            return f"Successfully wrote to {path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

    def list_directory(self, path: str = ".") -> str:
        """
        List contents of a directory.
        
        Args:
            path: Relative path to directory (default: root)
            
        Returns:
            Directory listing or error message
        """
        if not self._is_safe_path(path):
            return "Error: Access denied (path outside project directory)"
            
        target_path = self.project_dir / path
        
        if not target_path.exists():
            return f"Error: Directory not found: {path}"
            
        if not target_path.is_dir():
            return f"Error: Not a directory: {path}"
            
        try:
            items = []
            for item in target_path.iterdir():
                type_str = "DIR " if item.is_dir() else "FILE"
                items.append(f"{type_str:4} {item.name}")
            
            return "\n".join(sorted(items))
        except Exception as e:
            return f"Error listing directory: {str(e)}"

    def search_codebase(self, pattern: str) -> str:
        """
        Search for a string pattern in the codebase using grep.
        """
        try:
            # Use grep -r to search recursively
            # -n: line numbers
            # -I: ignore binary files
            # --exclude-dir: ignore common junk directories
            cmd = [
                "grep", "-rnI",
                "--exclude-dir=.git", "--exclude-dir=node_modules", "--exclude-dir=__pycache__", 
                "--exclude-dir=venv", "--exclude-dir=dist", "--exclude-dir=build",
                pattern, "."
            ]
            
            result = subprocess.run(
                cmd, 
                cwd=self.project_dir, 
                capture_output=True, 
                text=True
            )
            
            output = result.stdout
            if not output:
                return "No matches found."
                
            # Truncate if too long
            lines = output.splitlines()
            if len(lines) > 100:
                return "\n".join(lines[:100]) + f"\n... ({len(lines)-100} more matches truncated)"
            
            return output
            
        except Exception as e:
            return f"Error searching codebase: {str(e)}"

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Return the tool definitions for Gemini API.
        """
        return [
            {
                "function_declarations": [
                    {
                        "name": "execute_bash",
                        "description": "Execute a bash command. Only safe commands are allowed (ls, cat, grep, git, npm, etc.).",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "command": {
                                    "type": "STRING",
                                    "description": "The bash command to execute"
                                }
                            },
                            "required": ["command"]
                        }
                    },
                    {
                        "name": "read_file",
                        "description": "Read the content of a file.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "path": {
                                    "type": "STRING",
                                    "description": "Relative path to the file"
                                }
                            },
                            "required": ["path"]
                        }
                    },
                    {
                        "name": "write_file",
                        "description": "Write content to a file. Creates directories if needed.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "path": {
                                    "type": "STRING",
                                    "description": "Relative path to the file"
                                },
                                "content": {
                                    "type": "STRING",
                                    "description": "The content to write"
                                }
                            },
                            "required": ["path", "content"]
                        }
                    },
                    {
                        "name": "list_directory",
                        "description": "List contents of a directory.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "path": {
                                    "type": "STRING",
                                    "description": "Relative path to the directory (default: .)"
                                }
                            },
                            "required": ["path"]
                        }
                    }
                ]
            }
        ]
