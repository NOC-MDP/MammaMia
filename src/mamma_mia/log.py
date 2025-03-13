def import_log_filter(record):
    return record["level"].name in {"SUCCESS", "WARNING", "ERROR", "CRITICAL"}