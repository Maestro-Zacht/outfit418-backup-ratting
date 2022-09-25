# Outfit418 Backup Ratting
[![PyPI version](https://badge.fury.io/py/outfit418_backup_ratting.svg)](https://badge.fury.io/py/outfit418_backup_ratting)

## Installation
1. `pip install outfit418-backup-ratting`
2. Add `outfit418_backup_ratting` (note the underscore) to your `INSTALLED_APPS`
3. Run migrations
4. Restart AllianceAuth

## Tasks
Add to local.py
```python
CELERYBEAT_SCHEDULE['outfit418_update_fake_chars'] = {
    'task': 'outfit418_backup_ratting.tasks.update_fake_users',
    'schedule': crontab(minute=0, hour=0),
}
```