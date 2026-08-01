"""
MiroFish Backend Start the portal
"""

import os
import sys

# Configure UTF-8 before imports to prevent garbled Unicode output on Windows.
if sys.platform == 'win32':
    # Set environment variables to ensure Python use UTF-8
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    # Reconfigure the standard output stream as UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add project root directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import Config


def main():
    """main function"""
    # Verify configuration
    errors = Config.validate()
    if errors:
        print("Configuration error:")
        for err in errors:
            print(f"  - {err}")
        print("\nplease check .env configuration in file")
        sys.exit(1)

    # Create app
    app = create_app()

    # Get running configuration
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5001))
    debug = Config.DEBUG

    # Start service
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    main()
