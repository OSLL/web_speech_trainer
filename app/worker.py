"""Start one worker role with settings from celeryconfig."""

import sys
from app.celery_app import celery
from app.celeryconfig import worker_options


def main():
    role = sys.argv[1]
    queues, concurrency = worker_options(role)
    celery.worker_main(
        [
            "worker",
            "--loglevel=info",
            f"--concurrency={concurrency}",
            "-Q",
            queues,
            "-n",
            f"{role}@%h",
        ]
    )


if __name__ == "__main__":
    main()
