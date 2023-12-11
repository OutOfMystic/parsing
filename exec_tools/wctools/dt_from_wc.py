import re

import pyperclip

data = pyperclip.paste()

user_blocks = re.split(r'(?=^[A-Za-zА-Яа-я ]+\nTeam:)', data, flags=re.MULTILINE)

results = []

for block in user_blocks:
    # Находим имя пользователя и время работы (Work Time)
    match = re.search(r'^([A-Za-zА-Яа-я ]+).*?Work Time: (\d{2}:\d{2}:\d{2})', block, flags=re.DOTALL)
    if match:
        name = match.group(1).strip()
        work_time = match.group(2)
        results.append(f'{name} {work_time}')

# Вывод результатов
for result in results:
    print(result)

# Вывод результатов
pyperclip.copy('\n'.join(results))
