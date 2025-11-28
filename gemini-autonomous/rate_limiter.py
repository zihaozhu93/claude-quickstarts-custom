import json
import time
import os
from pathlib import Path
from datetime import datetime, timezone

class RateLimiter:
    def __init__(self, project_dir: Path, max_rpd: int = 250, max_tpm: int = 1000000):
        self.project_dir = project_dir
        self.max_rpd = max_rpd
        self.max_tpm = max_tpm
        self.usage_file = project_dir / "usage_stats.json"
        
        # TPM Tracking (Rolling Window)
        self.token_window = [] # List of (timestamp, token_count)
        
        self._load_usage()

    def _load_usage(self):
        """Load daily usage stats, resetting if it's a new day (UTC)."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        if self.usage_file.exists():
            try:
                data = json.loads(self.usage_file.read_text())
                if data.get("date") == today:
                    self.current_rpd = data.get("requests", 0)
                else:
                    self.current_rpd = 0 # New day, reset
            except Exception:
                self.current_rpd = 0
        else:
            self.current_rpd = 0
            
        self.current_date = today

    def _save_usage(self):
        """Save current usage stats to file."""
        data = {
            "date": self.current_date,
            "requests": self.current_rpd,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        self.usage_file.write_text(json.dumps(data, indent=2))

    def check_and_wait(self, estimated_tokens: int):
        """
        Check RPD and TPM limits. 
        - Raises Exception if RPD limit reached.
        - Sleeps if TPM limit approaching.
        """
        # 1. Check RPD (Requests Per Day)
        if self.current_rpd >= self.max_rpd:
            raise Exception(f"Daily Request Limit Reached ({self.current_rpd}/{self.max_rpd}). Please wait until tomorrow (UTC).")
        
        if self.current_rpd >= self.max_rpd * 0.9:
            print(f"\n[WARNING] Approaching Daily Request Limit: {self.current_rpd}/{self.max_rpd}")

        # 2. Check TPM (Tokens Per Minute)
        now = time.time()
        # Clean up old window entries (> 60s ago)
        self.token_window = [(t, c) for t, c in self.token_window if now - t < 60]
        
        current_tpm = sum(c for t, c in self.token_window)
        
        if current_tpm + estimated_tokens > self.max_tpm:
            wait_time = 60 - (now - self.token_window[0][0]) + 1
            print(f"\n[Rate Limit] TPM Limit approaching ({current_tpm + estimated_tokens} > {self.max_tpm}). Sleeping for {wait_time:.1f}s...")
            time.sleep(wait_time)
            
            # Re-clean after sleep
            now = time.time()
            self.token_window = [(t, c) for t, c in self.token_window if now - t < 60]

    def record_request(self, token_count: int):
        """Record a successful request."""
        self.current_rpd += 1
        self._save_usage()
        
        now = time.time()
        self.token_window.append((now, token_count))
