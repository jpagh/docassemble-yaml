from __future__ import annotations

import logging
import sys

_ROOT_LOGGER = "docassemble_lsp"
_DEFAULT_LEVEL = logging.WARNING
_configured = False


def configure_logging(*, level: int | str = _DEFAULT_LEVEL) -> None:
    global _configured
    if _configured:
        return
    if isinstance(level, str):
        # Defensive: normalize again for programmatic callers (CLI already uppercases via argparse type=str.upper)
        level = getattr(logging, level.upper(), logging.WARNING)
    logger = logging.getLogger(_ROOT_LOGGER)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter("[docassemble-lsp] %(levelname)-5s %(name)s:%(lineno)d %(message)s"))
        logger.addHandler(handler)
    set_log_level(level, force=True)
    _configured = True


def set_log_level(level: int, *, force: bool = False) -> None:
    logger = logging.getLogger(_ROOT_LOGGER)
    if not force and logger.level != _DEFAULT_LEVEL:
        return
    logger.setLevel(level)
    logger.log(level, "Log level set to %s", logging.getLevelName(level))


def reset_logging() -> None:
    """Reset logging state for testing isolation.

    Clears handlers, resets the level to default, and clears the
    configured flag so ``configure_logging`` can be called again.
    """
    global _configured
    logger = logging.getLogger(_ROOT_LOGGER)
    logger.handlers.clear()
    logger.setLevel(_DEFAULT_LEVEL)
    _configured = False
