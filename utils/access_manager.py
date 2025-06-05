import os
from utils.logger import log 

ALLOWED_USERS_FILE = 'allowed_users.txt'

def load_allowed_users() -> set[int]:

    allowed_ids = set()
    if not os.path.exists(ALLOWED_USERS_FILE):
        log.warning(f"Файл {ALLOWED_USERS_FILE} не найден. Доступа ни у кого не будет.")
        return allowed_ids

    try:
        with open(ALLOWED_USERS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and line.isdigit():
                    allowed_ids.add(int(line))
        log.info(f"Загружено {len(allowed_ids)} разрешенных пользователей из {ALLOWED_USERS_FILE}")
        return allowed_ids
    except Exception as e:
        log.error(f"Ошибка при загрузке разрешенных пользователей: {e}")
        return allowed_ids