import configparser
import os
from pathlib import Path
import sys

# A simple object to hold the settings
class Settings:
    def __init__(self, parser):
        # TMDB (Prioritize environment variable)
        self.tmdb_api_key = os.getenv('TORDB_TMDB_API_KEY') or parser.get("tmdb", "api_key", fallback=None)
        if not self.tmdb_api_key or 'your_api_key' in self.tmdb_api_key:
            raise ValueError("TMDb API key is missing or invalid. Please set the TORDB_TMDB_API_KEY environment variable.")

        # Database (Prioritize environment variables)
        self.db_type = os.getenv('DB_TYPE', parser.get("database", "type", fallback="mysql"))
        self.db_host = os.getenv('MYSQL_HOST', parser.get("database", "host", fallback="mysql"))
        self.db_port = int(os.getenv('MYSQL_PORT', parser.getint("database", "port", fallback=3306)))
        self.db_user = os.getenv('MYSQL_USER', parser.get("database", "user", fallback="root"))
        self.db_password = os.getenv('MYSQL_ROOT_PASSWORD', parser.get("database", "password", fallback=""))
        self.db_name = os.getenv('MYSQL_DATABASE', parser.get("database", "dbname", fallback="tordb"))

    def get_database_url(self):
        if self.db_type == "mysql":
            return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        else: # Default to sqlite
            return "sqlite:///./tmdb_media.db"

# --- Main Configuration Loading Logic ---

config_parser = configparser.ConfigParser()

# The config.ini file is optional. If it exists, it will be used as a fallback for environment variables.
config_file_path = Path(__file__).parent.parent / "config.ini"
if config_file_path.is_file():
    print(f"INFO: Loading configuration from '{config_file_path}'", file=sys.stderr)
    config_parser.read(config_file_path)
else:
    print("INFO: 'config.ini' not found. Relying on environment variables.", file=sys.stderr)

try:
    # Create a single, importable instance of the settings
    settings = Settings(config_parser)
except ValueError as e:
    print(f"ERROR: Configuration error: {e}", file=sys.stderr)
    sys.exit(1)
