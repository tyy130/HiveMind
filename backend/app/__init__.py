"""
MiroFish Backend - Flask application factory
"""

import os
import warnings

# inhibit multiprocessing resource_tracker warning(From third-party libraries such as transformers)
# Needs to be set before all other imports
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request
from flask_cors import CORS

from .config import Config
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask Apply factory function"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Preserve Unicode characters directly instead of escaping them as \uXXXX.
    # Flask >= 2.3 use app.json.ensure_ascii,Use older versions JSON_AS_ASCII Configuration
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False

    # Setup log
    logger = setup_logger('mirofish')

    # only in reloader Print startup information in child process(avoid debug Print twice in mode)
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process

    if should_log_startup:
        logger.info("=" * 50)
        logger.info("MiroFish Backend Starting...")
        logger.info("=" * 50)

    # enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register simulation process cleanup function(Ensure all simulation processes are terminated when the server is shut down)
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info("Registered simulation process cleanup function")

    # Request log middleware
    @app.before_request
    def log_request():
        logger = get_logger('mirofish.request')
        logger.debug(f"Request: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            logger.debug(f"Request body: {request.get_json(silent=True)}")

    @app.after_request
    def log_response(response):
        logger = get_logger('mirofish.request')
        logger.debug(f"response: {response.status_code}")
        return response

    # Registration blueprint
    from .api import graph_bp, simulation_bp, report_bp
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')

    # health check
    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'MiroFish Backend'}

    if should_log_startup:
        logger.info("MiroFish Backend Startup completed")

    return app
