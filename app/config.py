from dataclasses import dataclass
from os import getenv

ADMIN_TOKEN = getenv("ADMIN_TOKEN")
ADMIN_CHAT_ID = getenv("ADMIN_CHAT_ID")


@dataclass
class Bot:
    token: str


@dataclass
class DB:
    host: str
    db_name: str
    user: str
    password: str


@dataclass
class Config:
    bot: Bot
    db: DB
    update_group_codes: bool


def load_config():
    return Config(
        bot=Bot(token=getenv("BOT_TOKEN")),
        db=DB(
            host=getenv("DB_HOST"),
            db_name=getenv("DB_NAME"),
            user=getenv("DB_USER")),
            password=getenv("DB_PASSWORD"),
        ),
        update_group_codes=(getenv("UPDATE_GROUPS") or False),
    )


logging_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "file_formatter": {
            "format": "{asctime} — {levelname} — {name} — {module}:{funcName}:{lineno} — {message}",
            "datefmt": "[%d/%m/%Y] — %H:%M:%S",
            "style": "{",
        },
        "console_formatter": {
            "format": "{asctime} — {levelname} — {name} — {message}",
            "datefmt": "[%d/%m/%Y] — %H:%M",
            "style": "{",
        },
        "telegram_formatter": {
            "format": "{levelname} — {module}:{funcName}:{lineno} — {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "console_formatter",
        },
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "server.log",
            "formatter": "file_formatter",
        },
        "telegram": {
            "level": "ERROR",
            "class": "aiolog.telegram.Handler",
            "formatter": "telegram_formatter",
            "timeout": 10,  # 60 by default
            "queue_size": 100,  # 1000 by default
            "token": ADMIN_TOKEN,
            "chat_id": ADMIN_CHAT_ID,
        },
    },
    "loggers": {
        "app_logger": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file", "telegram"],
    },
}
