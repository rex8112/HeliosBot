"""
Tools Wrapper
"""

__title__ = 'discord_tools'
__author__ = 'rex8112'
__copyright__ = 'Copyright 2020-2021 rex8112'
__version__ = '0.1.0'

import logging

from .waitfor import WaitFor
from .utils import mention_string

try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
