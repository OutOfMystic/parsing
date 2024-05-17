Это отдельный проект!

Для корректного соотношения модулей и файлов откройте папку `loader_scheme_portal` в редакторе кода как основную. 
Это обеспечит правильное соотношение импортов внутри проекта.


python -m venv SchPoVenv
source SchPoVenv/bin/activate  # На Windows не тестировались зависимости для Selenium
pip install -r requirements.txt


Необходимо создать файл .env в корневой директории loader_scheme_portal. 
DOMAIN указывает на адрес CRM для обработки запросов.

Пример содержимого файла .env:
    DOMAIN=localhost:9000


Запуск src/main.py 
