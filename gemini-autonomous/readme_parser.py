import re
from pathlib import Path
from typing import List, Dict, Optional

class ReadmeParser:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.readme_path = project_dir / "README.md"

    def extract_tasks(self) -> List[Dict[str, str]]:
        """
        Extract incomplete tasks from README.md.
        Looks for lines starting with '- [ ]'.
        """
        if not self.readme_path.exists():
            return []

        content = self.readme_path.read_text(encoding='utf-8')
        tasks = []
        
        # Regex to find unchecked tasks: - [ ] Task Name
        # We capture the task description
        matches = re.findall(r'^\s*-\s*\[ \]\s*(.+)$', content, re.MULTILINE)
        
        for match in matches:
            task_desc = match.strip()
            # Filter out empty or trivial tasks
            if task_desc and len(task_desc) > 3:
                tasks.append({
                    "name": task_desc,
                    "description": f"Imported from README: {task_desc}",
                    "passes": False
                })
        
        return tasks

    def mark_task_complete(self, task_name: str) -> bool:
        """
        Mark a task as complete in README.md.
        Changes '- [ ] Task Name' to '- [x] Task Name'.
        """
        if not self.readme_path.exists():
            return False

        content = self.readme_path.read_text(encoding='utf-8')
        
        # Escape special regex characters in task_name just in case
        escaped_name = re.escape(task_name)
        
        # Pattern: - [ ] Task Name (ignoring case and whitespace)
        pattern = re.compile(r'(-\s*\[) \](\s*' + escaped_name + r')', re.IGNORECASE)
        
        if pattern.search(content):
            new_content = pattern.sub(r'\1x]\2', content)
            self.readme_path.write_text(new_content, encoding='utf-8')
            return True
            
        return False
