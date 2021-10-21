from loguru import logger
import sys

from dotenv import load_dotenv

sys.path.append(".")

from workers.recurring_tasks import handle_recurring_tasks

# Catch any exceptions and log them
@logger.catch
if __name__ == "__main__":
    load_dotenv()
    handle_recurring_tasks()
