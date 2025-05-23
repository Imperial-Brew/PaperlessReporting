from pathlib import Path


def safe_get(d, *keys):
    for key in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(key)
    return d


def log_failures(fail_log_path, failed_ids):
    log_path = Path(fail_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    existing = set()
    if log_path.exists():
        with open(log_path, "r") as logfile:
            existing.update(line.strip() for line in logfile)

    with open(log_path, "a") as logwriter:
        for item in failed_ids:
            if str(item) not in existing:
                logwriter.write(f"{item}\n")
