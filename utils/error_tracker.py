"""
In-memory error tracker for debugging production issues
"""
from collections import deque
from datetime import datetime
import traceback

class ErrorTracker:
    """Track recent errors in memory"""

    def __init__(self, max_errors=50):
        self.errors = deque(maxlen=max_errors)

    def log_error(self, error_type, message, exception=None, context=None):
        """Log an error with context"""
        error_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': error_type,
            'message': message,
            'context': context or {}
        }

        if exception:
            error_entry['exception'] = str(exception)
            error_entry['traceback'] = traceback.format_exc()

        self.errors.append(error_entry)

        # Also write to file for persistence
        try:
            from pathlib import Path
            import json
            log_file = Path('/app/logs/error_tracker.log')
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, 'a') as f:
                f.write(json.dumps(error_entry) + '\n')
        except:
            pass  # Don't let logging errors crash the app

    def get_recent_errors(self, count=10):
        """Get recent errors"""
        return list(self.errors)[-count:]

    def clear(self):
        """Clear all errors"""
        self.errors.clear()

# Global error tracker instance
error_tracker = ErrorTracker()
