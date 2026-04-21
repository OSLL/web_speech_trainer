import nltk
import os
import logging

logger = logging.getLogger(__name__)


def ensure_nltk_resources():
    download_dir = os.getenv("NLTK_DATA", "/root/nltk_data")
    os.makedirs(download_dir, exist_ok=True)

    if download_dir not in nltk.data.path:
        nltk.data.path.insert(0, download_dir)

    required_resources = (
        ("corpora/stopwords", "stopwords"),
        ("tokenizers/punkt", "punkt"),
        ("tokenizers/punkt_tab", "punkt_tab"),
    )

    for resource_path, package_name in required_resources:
        try:
            nltk.data.find(resource_path)
            logger.debug("NLTK resource already exists: %s", resource_path)
        except LookupError:
            logger.debug("Downloading NLTK resource: %s into %s", package_name, download_dir)
            nltk.download(package_name, download_dir=download_dir, quiet=True)

            # Повторная проверка, чтобы упасть понятной ошибкой, если скачать не удалось
            nltk.data.find(resource_path)
            logger.debug("NLTK resource downloaded: %s", resource_path)
