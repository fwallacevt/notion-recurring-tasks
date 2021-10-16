from dotenv import load_dotenv
import sys

sys.path.append(".")

from workers.recurring_tasks import handle_recurring_tasks

if __name__ == "__main__":
    load_dotenv()
    handle_recurring_tasks()
