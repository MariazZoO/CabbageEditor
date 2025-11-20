from PySide6.QtCore import QUrl

from config.app_config import get_app_config

settings = get_app_config()
root_dir = settings.paths.repo_root
html_path = settings.paths.frontend_dist
url = QUrl.fromLocalFile(str(html_path))
