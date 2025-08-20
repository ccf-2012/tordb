import configparser
from pathlib import Path
import shutil
import sys

# A simple object to hold the settings, mimicking the previous structure
class Settings:
    def __init__(self, parser):
        self.tmdb_api_key = parser.get("tmdb", "api_key", fallback=None)
        if not self.tmdb_api_key or self.tmdb_api_key == 'your_api_key_here':
            raise ValueError("API key not found or not set in [tmdb] section of config.ini")

# --- Main Configuration Loading Logic ---

# Path to the config.ini file, expected to be in the `backend` directory
config_file_path = Path(__file__).parent.parent / "config.ini"
example_config_path = Path(__file__).parent.parent / "config.ini.example"

if not config_file_path.is_file():
    if example_config_path.is_file():
        print(f"INFO: Configuration file 'config.ini' not found.", file=sys.stderr)
        print(f"INFO: Creating 'config.ini' from 'config.ini.example'.", file=sys.stderr)
        try:
            shutil.copy(example_config_path, config_file_path)
            print(f"SUCCESS: Created '{config_file_path}'.", file=sys.stderr)
        except Exception as e:
            print(f"ERROR: Could not create config file: {e}", file=sys.stderr)
            sys.exit(1)
        
        print("\nACTION REQUIRED: Please edit 'backend/config.ini' and add your TMDb API key before running the application again.", file=sys.stderr)
        sys.exit(1) # Exit after creating the file to allow user to add API key.
    else:
        # If both config and example are missing, we cannot proceed.
        raise FileNotFoundError(
            f"Configuration file 'config.ini' not found, and no 'config.ini.example' was found to create it from."
        )

config_parser = configparser.ConfigParser()
config_parser.read(config_file_path)

try:
    # Create a single, importable instance of the settings
    settings = Settings(config_parser)
except ValueError as e:
    print(f"ERROR: {e}", file=sys.stderr)
    print(f"ACTION REQUIRED: Please make sure your API key is correctly set in '{config_file_path}'.", file=sys.stderr)
    sys.exit(1)
