from arq import WorkerSettings
from app.workers.ingestion import ingest_document

class WorkerSettings(WorkerSettings):
    functions = [ingest_document]
    redis_settings = "app.core.queue.get_redis_pool"  # Uses same pool factory
    queue_name = "heimdall:jobs"
    max_jobs = 10
    job_timeout = 300  # 5 minutes per job
    keep_result = 3600  # Keep results for 1 hour
    health_check_interval = 30
    health_check_key = "heimdall:health"