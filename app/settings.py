

logging_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'std_format': {
            'format': '{asctime} - {levelname} - {name} - {module}:{funcName}:{lineno} - {message}',
            'style': '{',
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'std_format',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'server.log',
            'formatter': 'std_format',
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
