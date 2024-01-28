class InternalError(RuntimeError):
    """a deep-based unexpected error"""


class SchemeError(RuntimeError):
    """
    this error is almost caused by incorrect
    ``Constructor`` instance
    """


class ParsingError(RuntimeError):
    """a wrong parsing code"""


class ProxyHubError(RuntimeError):
    """no proxies available"""


class RaspizdyaistvoError(RuntimeError):
    """Чек рубрику 'Обратите внимание'"""
