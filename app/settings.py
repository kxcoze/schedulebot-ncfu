

logging_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'file_formatter': {
            'format': '{asctime} — {levelname} — {name} — {module}:{funcName}:{lineno} — {message}',
            'datefmt': '[%d/%m/%Y] — %H:%M:%S',
            'style': '{',
        },
        'console_formatter': {
            'format': '{asctime} — {levelname} — {name} — {message}',
            'datefmt': '[%d/%m/%Y] — %H:%M',
            'style': '{',
        }
    },
    'handlers': {
        'console': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'console_formatter',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'server.log',
            'formatter': 'file_formatter',
        }
    },
    'loggers': {
        'app_logger': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False,
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file'],
    },
}
