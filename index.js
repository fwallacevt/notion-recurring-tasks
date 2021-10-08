import { get_last_execution_time_utc, update_last_execution_time_utc } from "./app/file_utils.js";
import { create_new_recurring_tasks, get_completed_recurring_tasks } from "./app/notion.js";

const DATABASE_ID = process.env.NOTION_DB_ID;

async function handle_recurring_tasks() {
  // First, get the last time this ran
  const fname = "execution_data.json";
  const ts = get_last_execution_time_utc(fname);

  // Query all tasks in our database that have been modified since that time
  const tasks_to_recreate = await get_completed_recurring_tasks({ ...ts, databaseId: DATABASE_ID });

  // Now, for each of these recurring tasks, we have to create a new task
  // for the next time that schedule should execute
  await create_new_recurring_tasks({ ...tasks_to_recreate, databaseId: DATABASE_ID });

  // We successfully finished - update our file
  update_last_execution_time_utc(fname);
}

handle_recurring_tasks();

// TODOs:
// - clean up/modularize (move db functions to db file, time functions to time file?)
// - add comments/docstrings
// - post on reddit?
