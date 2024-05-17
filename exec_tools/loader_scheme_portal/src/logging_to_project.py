import logging


logger_to_project = logging.getLogger(__name__)
logger_to_project.setLevel(logging.DEBUG)

handler = logging.FileHandler(f"{__name__}.log", mode='a')
formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)

logger_to_project.addHandler(handler)
