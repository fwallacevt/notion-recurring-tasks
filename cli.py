import asyncio
import sys

from dotenv import load_dotenv

sys.path.append(".")

from workers.recurring_tasks import handle_recurring_tasks

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(handle_recurring_tasks())
