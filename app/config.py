"""Configuration loading for LLM Proxy."""

import json
import os
from pathlib import Path

# Defaults
DEFAULTS = {
    "port": 8000,
    "openai_base_url": "https://api.openai.com",
    "api_key_override": None,
    "log_dir": "./logs",
    "max_memory_requests": 1000,
    "log_request_bodies": True,
    "log_response_bodies": True,
}


def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from JSON file, falling back to defaults."""
    config = DEFAULTS.copy()
    
    config_file = Path(config_path)
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                file_config = json.load(f)
                config.update(file_config)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[CONFIG] Warning: Could not load {config_path}: {e}")
            print(f"[CONFIG] Using defaults")
    
    # Environment variables override config file
    if os.environ.get("LLM_PROXY_PORT"):
        config["port"] = int(os.environ["LLM_PROXY_PORT"])
    if os.environ.get("LLM_PROXY_OPENAI_URL"):
        config["openai_base_url"] = os.environ["LLM_PROXY_OPENAI_URL"]
    if os.environ.get("LLM_PROXY_API_KEY"):
        config["api_key_override"] = os.environ["LLM_PROXY_API_KEY"]
    
    return config


# Global config instance
_config = None


def get_config() -> dict:
    """Get the global config, loading it if necessary."""
    global _config
    if _config is None:
        _config = load_config()
    return _config
