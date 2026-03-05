"""Taskiq worker entrypoint. Run with: taskiq worker worker:broker (from apps/api)."""
from taskiq import TaskiqScheduler
from taskiq_redis import ListQueue, RedisQueueBroker

from app.settings import settings

broker = RedisQueueBroker(url=settings.redis_url, list_cls=ListQueue)
scheduler = TaskiqScheduler(broker=broker)

# Import tasks so they are registered with the broker
import app.tasks.example  # noqa: F401

if __name__ == "__main__":
    import taskiq.cli  # noqa: E402

    taskiq.cli.main()
