"""Example background task."""
from taskiq import task

from worker import broker


@task(broker=broker)
async def example_task(name: str) -> str:
    """Example task that echoes the name."""
    return f"Hello, {name}!"
