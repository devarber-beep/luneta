from taskiq import task


@task
async def send_notification_task(notification_id: str) -> None:
    """
    Placeholder Taskiq task for notifications (emails, etc.).
    """
    return None

