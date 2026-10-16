import logging
import sys

def setup_logging(debug: bool = False):
    """
    Configures the basic logging for the application.
    Logs INFO level and above to standard output.
    If debug is True, logs DEBUG level and above.
    """
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    logging.info("Logging configured.")
    if debug:
        logging.debug("Debug mode enabled.")