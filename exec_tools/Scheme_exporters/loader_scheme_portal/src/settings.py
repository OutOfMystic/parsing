#!/usr/bin/python3
import os
import sys

from pydantic_settings import BaseSettings  # Обновленный импорт

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
elif __file__:
    application_path = os.path.dirname(__file__)

BASE_DIR = os.path.join(application_path, os.pardir)

ENV_FILE = os.path.join(BASE_DIR, '.env')

class SettingsProject(BaseSettings):
    DOMAIN: str

    class Config:
        env_file = ENV_FILE


settings_project = SettingsProject()
