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
import sys
import os
sys.path.append("/home/lon8/python/parsing/")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from parse_module.connection import db_manager
from parse_module.console.command import CustomPrompt

db_manager.commit()
prompt = CustomPrompt()
prompt.start_prompt()
