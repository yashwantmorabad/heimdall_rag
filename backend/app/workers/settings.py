from app.workers.ingestion import ingest_document
from arq.connections import RedisSettings
from app.core.config import get_settings


# Use 127.0.0.1 instead of localhost for Windows async compatibility
_redis_url = get_settings().redis_url.replace("localhost", "127.0.0.1")


class WorkerSettings:
    functions = [ingest_document]
    redis_settings = RedisSettings.from_dsn(_redis_url)
    queue_name = "heimdall:jobs"
    max_jobs = 10
    job_timeout = 300  # 5 minutes per job
    keep_result = 3600  # Keep results for 1 hour
    health_check_interval = 30
    health_check_key = "heimdall:health"