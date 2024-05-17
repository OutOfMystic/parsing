from typing import Optional, Union

import requests
from ..logging_to_project import logger_to_project


def requests_to_json_or_svg(
    url: str,
    request_to_json: bool = True
) -> Optional[Union[str, None]]:
    try:
        response = requests.get(url)
        if response.status_code >= 400 and response.status_code <= 500:
            logger_to_project.error(
                f"Возникла ошибка клиента {response.status_code}"
            )
        elif response.status_code >= 500:
            logger_to_project.error(
                f"Возникла ошибка сервера {response.status_code}"
            )
        else:
            if request_to_json:
                return response.json()
            else:
                return response.text
        return None
    except requests.Timeout as e:
        logger_to_project.error(f"Возникла ошибка(Timeout) {e}")
        return None
    except Exception as e:
        logger_to_project.error(f"Возникла ошибка {e}")
        return None
