"""
Gemini Autonomous Engine Runner
==============================

Main entry point for the autonomous agent.
Handles authentication, context building, and the main execution loop.
"""

import os
import sys
import argparse
import time
from pathlib import Path
from typing import List, Optional

import google.generativeai as genai
from google.auth import default
from google.auth.transport.requests import Request

from gemini_tools import ToolManager
from rate_limiter import RateLimiter

# Configuration
# Default to Gemini 3.0 Pro Preview as requested.
DEFAULT_MODEL = "gemini-3-pro-preview" 
# Gemini 3.0 has a massive context window (1M+). 
# We set a "soft limit" at 500k to balance performance/cost with "God Mode" capability.
# This allows for very long sessions while still preventing infinite loops from consuming the entire quota.
MAX_CONTEXT_TOKENS = 500000 

SYSTEM_INSTRUCTION = """
You are an expert Autonomous AI Software Engineer.
Your goal is to complete the project specified in `app_spec.txt` by implementing features in `feature_list.json`.

**CORE PHILOSOPHY (DEEP-DEV PROTOCOL):**
1.  **Architect, Not Just Coder**: You are a Senior Architect with amnesia. You must rigorously plan before coding.
2.  **Context First**: `TECH_STACK.md` is your Constitution. `planning_journal.md` is your Memory. `feature_list.json` is your Roadmap.
3.  **One Feature at a Time**: Focus on completing one feature perfectly before moving to the next.
4.  **Verify Then Commit**: Never mark a feature as passing until you have verified it.
5.  **Adversarial Review**: You must attack your own code before finalizing it.

**YOUR WORKFLOW (MANDATORY):**
1.  **Analyze**: Read the `Project Context`, `planning_journal.md`, `TECH_STACK.md`, and `feature_list.json`.
2.  **Plan (The Architect's Protocol)**:
    *   **Context Check**: Explicitly state your understanding of the task and check for conflicts with `TECH_STACK.md`.
    *   **Pseudo-Plan**: Write a pseudo-code plan or file modification list in `planning_journal.md`.
    *   **Defense**: Identify potential bugs, security risks, and edge cases *before* writing code.
3.  **Implement**: Write the code.
    *   **Type-First**: Define interfaces/schemas first.
    *   **Small Steps**: Implement core logic, then helpers.
4.  **Adversarial Review (Self-Correction)**:
    *   Review your own code as a "Black Hat" hacker.
    *   Check for memory leaks, N+1 queries, and security holes.
    *   Fix issues immediately.
5.  **Verify**: Run tests/server to validate.
6.  **Update Status**: Update `feature_list.json` and `planning_journal.md`.
7.  **Commit**: Commit changes.

**CRITICAL RULES:**
*   **Context**: You have the full project context.
*   **Safety**: Only use allowed commands.
*   **Quality**: Write production-ready code.
*   **Persistence**: Maintain `planning_journal.md` religiously.
*   **Journaling**: NEVER skip updating `planning_journal.md`. It must contain:
    *   ## Current Status
    *   ## Recent Actions
    *   ## Next Steps
    *   ## Known Issues
"""

LEGACY_SYSTEM_INSTRUCTION = """
You are an expert Software Archaeologist and Refactoring Specialist.
Your goal is to safely refactor legacy code using the "Archaeology Protocol" AND implement requested features.

**CORE PHILOSOPHY (ARCHAEOLOGY PROTOCOL):**
1.  **Observer First**: Do NOT change code until you fully understand it.
2.  **Visualizer**: Use Mermaid.js to map the system before touching it.
3.  **Seam-Buster**: Your primary goal is to break dependencies (Dependency Injection), not rewrite business logic.
4.  **Test-First**: Write "Characterization Tests" to lock in current behavior (even bugs) before refactoring.
5.  **Refactor Safely**: Use the Strangler Fig pattern. Small, verified steps.
6.  **Feature Implementation**: Once the code is testable and understood, implement the requested features safely.

**YOUR WORKFLOW:**
1.  **Analyze**: Read `planning_journal.md`, `TECH_STACK.md` (if exists), and `feature_list.json`.
2.  **Plan**: 
    *   Check `planning_journal.md` for context.
    *   Select the next active Phase from `feature_list.json`.
    *   **Context Check**: Explicitly state what you are about to do.
    *   **Pseudo-Plan**: Write your plan in `planning_journal.md`.
3.  **Execute**:
    *   **Phase 1 (Visualizer)**: Read code, generate Mermaid diagrams (Flowcharts, Class Diagrams).
    *   **Phase 2 (Seam-Buster)**: Refactor code to inject dependencies. Create Seams.
    *   **Phase 3 (Snapshot)**: Write Characterization Tests. Ensure they pass.
    *   **Phase 4 (Refactor)**: Clean up code, extract methods, rename variables.
    *   **Phase 5 (Feature Implementation)**: Implement new requirements (if any) using TDD.
4.  **Verify**: Run tests or verify diagrams.
5.  **Update Status**: 
    *   Update `feature_list.json` (mark phase as passing).
    *   Update `planning_journal.md`.
6.  **Commit**: Commit changes.

**CRITICAL RULES:**
*   **Persistence**: Maintain `planning_journal.md` religiously.
*   **Safety**: Do not break the build.
*   **Interactive**: If you need user feedback, ask for it in the journal or via `notify_user` (if available), or just state your assumption.
"""

class GeminiRunner:
    def __init__(self, project_dir: Path, model_name: str = DEFAULT_MODEL, mode: str = "autonomous", max_rpd: int = 250, max_tpm: int = 1000000):
        self.project_dir = project_dir.resolve()
        self.tool_manager = ToolManager(self.project_dir)
        self.model_name = model_name
        self.mode = mode
        
        # Initialize Rate Limiter
        self.rate_limiter = RateLimiter(project_dir, max_rpd, max_tpm)
        
        self._setup_auth()
        
        # Create list of callable tools for automatic execution
        # The SDK will generate schemas from the function signatures and docstrings
        self.tools_list = [
            self.tool_manager.execute_bash,
            self.tool_manager.read_file,
            self.tool_manager.write_file,
            self.tool_manager.list_directory,
            self.tool_manager.search_codebase
        ]
        
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            tools=self.tools_list,
            system_instruction=SYSTEM_INSTRUCTION
        )
        self.chat = self.model.start_chat(enable_automatic_function_calling=True)

    def _setup_auth(self):
        """
        Setup authentication using API Key or Application Default Credentials.
        """
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        
        if api_key:
            print("Using API Key from environment.")
            genai.configure(api_key=api_key)
        else:
            print("No API Key found. Trying Application Default Credentials (ADC)...")
            try:
                credentials, project = default()
                credentials.refresh(Request())
                # Note: google-generativeai SDK currently prefers API keys for some endpoints,
                # but let's try to configure it with the credentials if possible.
                # Actually, the SDK doesn't directly accept 'credentials' object in configure().
                # It mainly wants an API key.
                # However, for Vertex AI users, it's different.
                # Assuming the user is using the AI Studio (Generative AI) API.
                
                print("\n[WARNING] The Google GenAI SDK primarily requires an API Key.")
                print("If you are using Vertex AI, you should use the `vertexai` library instead.")
                print("For this script, please export GEMINI_API_KEY='your_key'.")
                print("You can get one here: https://aistudio.google.com/app/apikey")
                
                # We'll raise for now as the standard SDK needs a key.
                raise ValueError("GEMINI_API_KEY not set.")
                
            except Exception as e:
                print(f"Auth Error: {e}")
                raise ValueError("Please set GEMINI_API_KEY environment variable.")

    def build_context(self) -> str:
        """
        Build the current project context (file tree + key files).
        """
        context = ["# Project Context\n"]
        
        # 1. File Tree
        context.append("## Directory Structure")
        context.append("```")
        # Use ToolManager's list_directory to respect security and ignores
        context.append(self.tool_manager.list_directory("."))
        context.append("```\n")
        
        # 2. Key Files Content
        # We automatically include specific high-value files if they exist
        key_files = [
            "planning_journal.md", # Priority 1: Persistent Memory
            "TECH_STACK.md",       # Priority 2: Technical Constitution
            "feature_list.json",
            "app_spec.txt",
            "package.json",
            "requirements.txt",
            "init.sh",
            "README.md"
        ]
        
        context.append("## Key Files")
        for filename in key_files:
            # Check if file exists before trying to read
            if (self.project_dir / filename).exists():
                content = self.tool_manager.read_file(filename)
                if not content.startswith("Error"):
                    context.append(f"### {filename}")
                    context.append("```")
                    # Truncate very large files to avoid wasting token budget on static content
                    # But keep feature_list.json full as it's the source of truth
                    if filename == "feature_list.json":
                        context.append(content)
                    else:
                        context.append(content[:10000] + ("\n... (truncated)" if len(content) > 10000 else ""))
                    context.append("```\n")
                
        return "\n".join(context)

    def _get_token_count(self, history) -> int:
        """
        Estimate token count for the current session history.
        """
        try:
            return self.model.count_tokens(history).total_tokens
        except Exception:
            # Fallback estimation if API fails
            return 0

    def _retry_with_backoff(self, func, *args, **kwargs):
        """
        Execute a function with exponential backoff retry logic.
        """
        max_retries = 5
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                
                delay = base_delay * (2 ** attempt)
                print(f"\n[API Error] {e}. Retrying in {delay}s...")
                time.sleep(delay)

    def _input_with_timeout(self, prompt: str, timeout: int = 10) -> str:
        """
        Wait for user input with a timeout. Returns None if timeout expires.
        """
        print(f"{prompt} (Auto-proceeding in {timeout}s... Press Enter to intervene)", end='', flush=True)
        
        # Unix-only implementation using select
        import select
        import sys
        
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if ready:
            print() # Newline
            return sys.stdin.readline().strip()
        
        print("\n[Auto-proceeding]")
        return None

    def _detect_loop(self) -> str:
        """
        Check for repetitive tool usage in recent history.
        Returns an intervention message if a loop is detected, else None.
        """
        # Look at the last 10 messages
        history = self.chat.history[-10:]
        tool_calls = []
        
        for message in history:
            if hasattr(message, 'parts'):
                for part in message.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        # Create a signature: name + sorted args
                        fc = part.function_call
                        args = dict(fc.args)
                        # Convert args to a hashable string representation
                        arg_str = sorted([(k, str(v)) for k, v in args.items()])
                        signature = (fc.name, str(arg_str))
                        tool_calls.append(signature)
        
        # Check for 3 consecutive identical calls
        if len(tool_calls) >= 3:
            last_three = tool_calls[-3:]
            if last_three[0] == last_three[1] == last_three[2]:
                return f"\nSYSTEM INTERVENTION: You have executed the tool '{last_three[0][0]}' with identical arguments 3 times in a row. STOP. This strategy is not working. Analyze WHY it failed and try a DIFFERENT approach."
        
        return None

    def run_loop(self):
        """
        Main execution loop with Token Monitoring and Session Rotation.
        """
        print(f"Starting Gemini Autonomous Engine in {self.project_dir}")
        print(f"Model: {self.model_name}")
        print(f"Mode: {self.mode}")
        print(f"Token Limit: {MAX_CONTEXT_TOKENS}")
        print(f"Rate Limits: {self.rate_limiter.max_rpd} RPD, {self.rate_limiter.max_tpm} TPM")
        print("=" * 60)
        
        iteration = 0
        while True:
            iteration += 1
            print(f"\n[Iteration {iteration}] Observing...")
            
            # 1. Check Token Usage (Physical Sharding)
            current_tokens = self._get_token_count(self.chat.history)
            print(f"Current Context Tokens: {current_tokens} / {MAX_CONTEXT_TOKENS}")
            
            # Rate Limit Check (Pre-flight)
            # Estimate input tokens (Context + Prompt)
            # This is a rough estimate, but safer than nothing
            estimated_input_tokens = current_tokens + 2000 
            self.rate_limiter.check_and_wait(estimated_input_tokens)
            
            if current_tokens > MAX_CONTEXT_TOKENS:
                print(f"\n[WARNING] Token limit reached ({current_tokens} > {MAX_CONTEXT_TOKENS}).")
                print("Triggering Session Rotation (Archive Interrupt)...")
                
                # Archive Interrupt:
                # 1. The agent should have already saved progress to files in previous turns.
                # 2. We explicitly reset the chat session to clear history.
                # 3. The next iteration will rebuild context from the file system.
                
                print("Resetting Chat Session...")
                self.chat = self.model.start_chat(enable_automatic_function_calling=True)
                print("Session Rotated. Resuming with fresh context.")
                continue

            # 2. Observe
            context = self.build_context()
            
            # 3. Think & Act
            prompt = f"""
            Here is the current project state:
            
            {context}
            
            Please analyze the `planning_journal.md` and `feature_list.json` and execute the next necessary steps.
            If all tasks are completed, output "TASK_COMPLETE".
            """
            
            # Loop Detection
            loop_warning = self._detect_loop()
            if loop_warning:
                print(f"\n[Loop Detected] Injecting intervention: {loop_warning}")
                prompt += f"\n\n{loop_warning}\n"
            
            # Interactive Feedback Injection (Optional, for Legacy Mode mostly)
            if self.mode == "legacy":
                 user_feedback = self._input_with_timeout("\n[Interactive] Type feedback:", timeout=10)
                 if user_feedback:
                     print(f"Feedback received: {user_feedback}")
                     prompt += f"\n\nUSER FEEDBACK (CRITICAL): {user_feedback}\n"

            try:
                # Spinner logic
                import threading
                import itertools
                
                spinner = itertools.cycle(['-', '/', '|', '\\'])
                stop_spinner = False
                
                def spin():
                    while not stop_spinner:
                        sys.stdout.write(next(spinner))
                        sys.stdout.flush()
                        time.sleep(0.1)
                        sys.stdout.write('\b')
                
                print("Thinking...", end=' ', flush=True)
                t = threading.Thread(target=spin)
                t.start()
                
                try:
                    # Send the prompt to Gemini with exponential backoff
                    # Note: We keep stream=False to ensure automatic_function_calling works reliably
                    response = self._retry_with_backoff(self.chat.send_message, prompt)
                    
                    # Record successful request
                    # Estimate output tokens (response length / 4)
                    output_tokens = len(response.text) // 4
                    self.rate_limiter.record_request(estimated_input_tokens + output_tokens)
                    
                finally:
                    stop_spinner = True
                    t.join()
                    print(" Done.")
                
                # Print the model's text response
                print(f"\nGemini: {response.text}")
                
                # Check for termination condition
                if "TASK_COMPLETE" in response.text:
                    print("\nAll tasks completed successfully!")
                    break
                    
            except Exception as e:
                print(f"Fatal Error in loop: {e}")
                # If backoff failed, we might need manual intervention or just wait longer
                print("Waiting 60s before hard retry...")
                time.sleep(60)

    def _scan_project_codebase(self) -> str:
        """
        Recursively scan the project directory and read all relevant source files.
        Returns a formatted string with file paths and contents.
        Implements a 'Smart Context' strategy with token budgeting.
        """
        context = ["# Full Project Codebase\n"]
        
        # Budget: ~400k characters (approx 100k-130k tokens) to leave room for history
        CHAR_BUDGET = 400000 
        current_chars = 0
        
        # Define relevant extensions and ignore patterns
        relevant_extensions = {
            '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.scss', 
            '.sql', '.md', '.json', '.ini', '.yml', '.yaml', '.toml', 
            '.dockerfile', '.sh', '.txt'
        }
        ignore_dirs = {
            '.git', '__pycache__', 'node_modules', 'venv', 'env', '.idea', 
            '.vscode', 'dist', 'build', 'coverage', 'tmp', 'temp', 'migrations'
        }
        
        file_list = []
        
        # 1. Scan and collect metadata
        for root, dirs, files in os.walk(self.project_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in relevant_extensions or file in {'Dockerfile', 'Makefile', 'Gemfile'}:
                    try:
                        stat = file_path.stat()
                        if stat.st_size > 100000: # Skip huge files
                            continue
                        file_list.append((file_path, stat.st_size))
                    except Exception:
                        pass
        
        # 2. Prioritize Files
        # Priority: 
        # 0. Root config files (highest)
        # 1. Keyword Matches (Smart Context v2)
        # 2. Source code in 'app' or 'src'
        # 3. Tests
        # 4. Others
        
        # Extract keywords from planning_journal.md
        keywords = set()
        journal_path = self.project_dir / "planning_journal.md"
        if journal_path.exists():
            try:
                content = journal_path.read_text().lower()
                # Simple keyword extraction: look for words in "Next Steps" or "Current Status"
                # For now, we just grab common technical terms if they appear in the journal
                common_terms = ['auth', 'login', 'database', 'api', 'test', 'docker', 'config', 'utils', 'model', 'view', 'controller']
                for term in common_terms:
                    if term in content:
                        keywords.add(term)
            except Exception:
                pass
        
        def get_priority(path: Path):
            parts = path.parts
            filename = path.name.lower()
            
            # Level 0: Root configs
            if len(parts) == 2: return 0 
            
            # Level 1: Smart Context Matches
            for kw in keywords:
                if kw in filename or kw in str(path).lower():
                    return 1
            
            # Level 2: Source
            if 'app' in parts or 'src' in parts: return 2
            
            # Level 3: Tests
            if 'tests' in parts or 'test' in parts: return 3
            
            # Level 4: Default
            return 4
            
        file_list.sort(key=lambda x: (get_priority(x[0]), x[0]))
        
        # 3. Build Context within Budget
        file_count = 0
        
        for file_path, size in file_list:
            if current_chars + size > CHAR_BUDGET:
                context.append(f"### [SKIPPED] {file_path.name} (Context Budget Exceeded)")
                continue
                
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                rel_path = file_path.relative_to(self.project_dir)
                
                context.append(f"### File: {rel_path}")
                context.append("```")
                context.append(content)
                context.append("```\n")
                
                current_chars += len(content)
                file_count += 1
            except Exception:
                pass
        
        print(f"Scanned {file_count} files ({current_chars/1024:.1f} KB) for context.")
        if current_chars >= CHAR_BUDGET:
            print(f"[WARNING] Context budget reached. Some files were skipped.")
            
        return "\n".join(context)

    def generate_spec(self):
        """
        Reverse engineer app_spec.txt from existing code.
        """
        print(f"Generating app_spec.txt from project: {self.project_dir}")
        print("Scanning project files...")
        
        # 1. Build Comprehensive Context (Codebase)
        # We use the deep scan instead of the shallow build_context
        context = self._scan_project_codebase()
        
        # 2. Prompt for Spec Generation
        prompt = f"""
        You are an expert Software Architect.
        Your task is to reverse-engineer a comprehensive `app_spec.txt` from the provided project context.
        
        The `app_spec.txt` should describe the application in detail, including:
        1.  **Overview**: High-level description of what the app does.
        2.  **Tech Stack**: Languages, frameworks, and libraries used.
        3.  **Core Features**: Detailed list of existing features.
        4.  **Project Structure**: Explanation of the directory layout.
        5.  **Database Schema**: detailed tables and relationships (inferred from models).
        6.  **API Endpoints**: detailed routes and methods (inferred from views/controllers).
        
        Here is the full project codebase:
        
        {context}
        
        Please output the content of `app_spec.txt` inside a code block.
        """
        
        try:
            print("Analyzing code and generating spec (this may take a minute)...")
            response = self._retry_with_backoff(self.chat.send_message, prompt)
            
            # Extract content from code block if present
            content = response.text
            if "```" in content:
                import re
                match = re.search(r"```(?:xml|txt|markdown)?\n(.*?)```", content, re.DOTALL)
                if match:
                    content = match.group(1)
            
            # Save to file
            output_path = self.project_dir / "app_spec.txt"
            self.tool_manager.write_file("app_spec.txt", content)
            print(f"\nSuccessfully generated {output_path}")
            print("You can now review it and run the agent in autonomous mode.")
            
        except Exception as e:
            print(f"Error generating spec: {e}")

    def run_legacy_mode(self):
        """
        Initialize and run the Archaeology Protocol in a persistent loop.
        """
        print(f"Initializing Legacy Refactoring Mode (Archaeology Protocol)")
        
        # 1. Initialize feature_list.json if missing
        feature_list_path = self.project_dir / "feature_list.json"
        
        # Check if we need to initialize or append
        if not feature_list_path.exists():
            print("Creating initial feature_list.json for Archaeology Protocol...")
            initial_features = [
                {"name": "Phase 1: Visualizer (Cognitive Map)", "description": "Generate Mermaid diagrams to map dependencies.", "passes": False},
                {"name": "Phase 2: Seam-Buster (Dependency Injection)", "description": "Refactor to inject dependencies and create seams.", "passes": False},
                {"name": "Phase 3: Snapshot (Characterization Tests)", "description": "Write tests to lock in current behavior.", "passes": False},
                {"name": "Phase 4: Refactor (Strangler Fig)", "description": "Safely refactor the code.", "passes": False}
            ]
            
            # Ask for Feature Request
            print("\n[Feature Injection] Do you have a specific feature request? (Press Enter to skip)")
            feature_request = self._input_with_timeout("> ", timeout=30)
            
            if feature_request:
                print(f"Injecting Feature Request: {feature_request}")
                initial_features.append({
                    "name": "Phase 5: Feature Implementation",
                    "description": f"Implement requested feature: {feature_request}",
                    "passes": False
                })
            
            import json
            feature_list_path.write_text(json.dumps(initial_features, indent=2))
        
        # 2. Initialize planning_journal.md if missing
        journal_path = self.project_dir / "planning_journal.md"
        if not journal_path.exists():
            print("Creating initial planning_journal.md...")
            journal_path.write_text("# Planning Journal\n\n## Current Status\nStarting Legacy Refactoring.\n\n## Recent Actions\nInitialized project.\n\n## Next Steps\nBegin Phase 1.\n\n## Known Issues\nNone.\n")

        # 3. Enter the main loop
        self.run_loop()

def main():
    parser = argparse.ArgumentParser(description="Gemini Autonomous Engine")
    parser.add_argument("--project-dir", type=Path, default=Path("./gemini_project"))
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Gemini model to use")
    parser.add_argument("--mode", type=str, choices=["autonomous", "generate-spec", "legacy"], default="autonomous", help="Operation mode")
    parser.add_argument("--rpd", type=int, default=250, help="Max Requests Per Day")
    parser.add_argument("--tpm", type=int, default=1000000, help="Max Tokens Per Minute")
    args = parser.parse_args()
    
    try:
        # Pass mode and limits to runner
        runner = GeminiRunner(args.project_dir, args.model, mode=args.mode, max_rpd=args.rpd, max_tpm=args.tpm)
        
        if args.mode == "generate-spec":
            runner.generate_spec()
        elif args.mode == "legacy":
            runner.run_legacy_mode()
        else:
            runner.run_loop()
            
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
