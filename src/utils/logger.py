import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict
from src.utils.env import LOG_LEVEL, NODE_ENV

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)
            
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)

class StructuredLogger:
    """Wrapper for structured logging with CloudWatch compatibility"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Configure logger with appropriate handler and formatter"""
        if self.logger.handlers:
            return  # Already configured
            
        # Set log level from environment
        level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
        self.logger.setLevel(level)
        
        # Create handler
        handler = logging.StreamHandler(sys.stdout)
        
        # Use JSON formatter for production, simple formatter for development
        if NODE_ENV == 'production':
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Prevent propagation to avoid duplicate logs
        self.logger.propagate = False
    
    def _log(self, level: str, message: str, extra_data: Dict[str, Any] = None):
        """Internal logging method with structured data"""
        if NODE_ENV == 'production':
            # Use structured logging for production
            record = self.logger.makeRecord(
                self.logger.name,
                getattr(logging, level.upper()),
                '',
                0,
                message,
                (),
                None
            )
            
            if extra_data:
                record.extra_data = extra_data
                
            self.logger.handle(record)
        else:
            # For development, include extra_data in the message
            if extra_data:
                formatted_message = f"{message} - {extra_data}"
            else:
                formatted_message = message
            
            getattr(self.logger, level.lower())(formatted_message)
    
    def info(self, message: str, extra_data: Dict[str, Any] = None):
        """Log info level message"""
        self._log('info', message, extra_data)
    
    def warning(self, message: str, extra_data: Dict[str, Any] = None):
        """Log warning level message"""
        self._log('warning', message, extra_data)
    
    def error(self, message: str, extra_data: Dict[str, Any] = None):
        """Log error level message"""
        self._log('error', message, extra_data)
    
    def debug(self, message: str, extra_data: Dict[str, Any] = None):
        """Log debug level message"""
        self._log('debug', message, extra_data)

def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)
