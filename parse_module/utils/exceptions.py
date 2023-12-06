class InternalError(Exception):
    """a deep-based unexpected error"""
    pass


class SchemeError(Exception):
    """
    this error is almost caused by incorrect
    ``Constructor`` instance
    """
    pass


class ParsingError(Exception):
    """a wrong parsing code"""
    pass
