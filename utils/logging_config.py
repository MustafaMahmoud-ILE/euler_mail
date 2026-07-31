"""
Logging setup for Euler Mail.
Rotating file handler in the user data dir + WARNING-level stderr echo.
"""
import logging
import logging.handlers
from euler_mail.config.settings import LOG_DIR


def setup_logging(level: int = logging.DEBUG) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "euler_mail.log"

    root = logging.getLogger()
    root.setLevel(level)

    if root.handlers:
        return  # Already configured

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file: max 2 MB, keep 3 backups
    fh = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Console: only WARNING+
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
