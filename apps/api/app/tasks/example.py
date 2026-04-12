"""Example background task."""
from worker import broker


@broker.task()
async def example_task(name: str) -> str:
    """Example task that echoes the name."""
    return f"Hello, {name}!"
