import {
  create_new_recurring_tasks,
  get_completed_recurring_tasks,
  get_last_execution_time_utc,
  save_new_execution
} from "./app/notion.js";

const TASKS_DB_ID = process.env.NOTION_TASKS_DB_ID;

const EXECUTIONS_DB_ID = process.env.NOTION_EXECUTIONS_DB_ID;

async function handle_recurring_tasks() {
  // First, get the last time this ran
  const fname = "execution_data.json";
  const ts = await get_last_execution_time_utc({ databaseId: EXECUTIONS_DB_ID });
  console.log(ts);

  // Query all tasks in our database that have been modified since that time
  const tasks_to_recreate = await get_completed_recurring_tasks({ ...ts, databaseId: TASKS_DB_ID });

  // Now, for each of these recurring tasks, we have to create a new task
  // for the next time that schedule should execute
  await create_new_recurring_tasks({ ...tasks_to_recreate, databaseId: TASKS_DB_ID });

  // We successfully finished - update our file
  await save_new_execution({ databaseId: EXECUTIONS_DB_ID });
}

handle_recurring_tasks();
