class InternalError(Exception):
    """a deep-based unexpected error"""


class SchemeError(Exception):
    """
    this error is almost caused by incorrect
    ``Constructor`` instance
    """


class ParsingError(Exception):
    """a wrong parsing code"""


class ProxyHubError(Exception):
    """no proxies available"""


class RaspizdyaistvoError(RuntimeError):
    """Чек рубрику 'Обратите внимание'"""
