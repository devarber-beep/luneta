from taskiq_redis import ListQueueBroker

from app.settings import settings

broker = ListQueueBroker(url=settings.redis_url)

# Import tasks so they are registered with the broker
import app.tasks.example  # noqa: F401

if __name__ == "__main__":
    import taskiq.cli  # noqa: E402

    taskiq.cli.main()
