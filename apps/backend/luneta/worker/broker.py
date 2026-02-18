from taskiq import TaskiqScheduler
from taskiq_redis import RedisQueueBroker, ListQueue

from luneta.core.settings import settings


broker = RedisQueueBroker(
    url=settings.redis_url,
    list_cls=ListQueue,
)

scheduler = TaskiqScheduler(broker=broker)


if __name__ == "__main__":
    # This entrypoint allows: python -m luneta.worker.broker
    import taskiq.cli  # type: ignore

    taskiq.cli.main()

