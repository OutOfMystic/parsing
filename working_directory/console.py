"""
Уровень Main:
 - list
 - select scheme [scheme]
Уровень Scheme:
 - list
 - select sector [sector]
 - quit
 - concat [main_sector] [sector1] (sector2) (sector3)...
 - outline [sector]
 - show
Уровень Sector:
 - show
 - apply [condition] [expression]
"""

import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from parse_module.connection import db_manager
from parse_module.console.command import CustomPrompt

db_manager.commit()
prompt = CustomPrompt()
prompt.start_prompt()
