

import { Client } from "@notionhq/client";

import { toISOStringLocalTz, nextDueDate } from "./time_utils.js";

const notion = new Client({ auth: process.env.NOTION_API_KEY });

async function query_db({ options, databaseId }) {
    // Query the given database with the given filter, and return the results. This is a very
    // thin wrapper for other users.
    return await notion.databases.query({
        database_id: databaseId,
        sorts: [
            // Sort by last edited time, descending, so we always get the most recent event first.
            {
                timestamp: "last_edited_time",
                direction: "descending",
            }
        ],
        ...options,
    });
}

export async function get_completed_recurring_tasks({ timestamp, databaseId }) {
    // Get recurring tasks (have a "Schedule") that have been completed (updated) since the given
    // timestamp. This will also find previously-completed tasks that have been updated, if they
    // were updated for some reason. We return a list of tasks, de-duplicated on name, that should
    // be recreated with the next due date on the given schedule.

    // Get recurring tasks completed since the given timestamp
    const response = await query_db({
        databaseId,
        options: {
            filter: {
                and: [
                    {
                        property: "Last edited time",
                        date: {
                            on_or_after: timestamp.toISOString(),
                        },
                    },
                    {
                        property: "Schedule",
                        text: {
                            is_not_empty: true,
                        },
                    },
                    {
                        property: "Done",
                        checkbox: {
                            equals: true,
                        },
                    },
                ]
            }
        }
    });

    // De-duplicate the list of tasks by name
    const unique_names = new Set();
    const unique_tasks = [];
    response.results.forEach(task => {
        console.log(task.properties);
        const task_name = task.properties.Name.title[0].plain_text;
        if (!unique_names.has(task_name)) {
            unique_tasks.push(task);
            unique_names.add(task_name);
        }
    });
    console.log(`Found ${unique_tasks.length} distinct recurring tasks`);

    // Return our task list
    return {
        tasks: unique_tasks
    }
}


async function check_open_task_exists_with_name({ name, databaseId }) {
    // Check if an open task by this name already exists.
    const response = await query_db({
        databaseId,
        options: {
            filter: {
                and: [
                    {
                        property: "Name",
                        text: {
                            equals: name,
                        },
                    },
                    {
                        property: "Done",
                        checkbox: {
                            equals: false,
                        },
                    },
                ]
            }
        }
    });

    if (response.results.length > 0) {
        // Found at least one open task by this name
        console.log(`There are ${response.results.length} open tasks with this name`);
        return true;
    } else {
        // Didn't find anything by this name - proceed!
        return false;
    }
}

export async function create_new_recurring_tasks({ tasks, databaseId }) {
    // Create new tasks for each of the recurring tasks. Just to be extra safe, we check that
    // there isn't already an uncompleted task with the same name (which could happen if our
    // script gets interrupted partway through).
    //
    // For each new task we create, we'll copy everything from the old task, set the "Parent"
    // to the most recently completed task (create a singly-linked list), and update the due
    // date to the next occurrence of this schedule

    // I don't use forEach because I can't use `continue` inside forEach. I _could_ use return,
    // but that's subtle and unexpected - it's clearer to use an explicit for loop.
    const num_tasks = tasks.length;
    for (let i = 0; i < num_tasks; i++) {
        const task = tasks[i];
        try {
            // If the task already exists, skip it
            const exists = await check_open_task_exists_with_name({ name: task.properties.Name.title[0].plain_text, databaseId })
            if (exists === true) {
                console.log("Skipping...")
                continue;
            }

            await create_new_recurring_task({ task, databaseId });
        } catch (error) {
            console.log(error);
        }
    }
}

async function create_new_recurring_task({ task, databaseId }) {
    // Copy relevant fields from the task and create a new, open task, with the due date
    // set to the next occurrence of the schedule. Additionally, we set "Parent" on the new
    // task so we can track task lists over time.
    const properties = {
        "Name": {
            type: "title",
            title: [
                {
                    type: 'text',
                    text: {
                        content: task.properties.Name.title[0].plain_text,
                    },
                },
            ],
        },
        "Done": {
            type: "checkbox",
            checkbox: false,
        },
        "Status": {
            type: "select",
            select: {
                name: "To Do",
            },
        },
        "Priority": {
            type: "select",
            select: {
                id: task.properties.Priority.select.id,
            },
        },
        "Tags": {
            type: "multi_select",
            multi_select: task.properties.Tags.multi_select.map(m => ({ id: m.id })),
        },
        "Due date": {
            type: "date",
            date: {
                // Notion doesn't really understand timezones, so we have to work around it. Assuming all
                // timestamps in notion are in _local time_, we have to format our string as local time
                start: toISOStringLocalTz({ date: nextDueDate({ schedule: task.properties.Schedule.rich_text[0].plain_text }).next }),
            },
        },
        "Schedule": {
            type: "rich_text",
            rich_text: [
                {
                    type: "text",
                    text: {
                        content: task.properties.Schedule.rich_text[0].plain_text,
                    }
                },
            ]
        },
        "Parent": {
            type: "rich_text",
            rich_text: [
                {
                    type: "text",
                    text: {
                        content: task.id,
                    }
                },
            ]
        },
    };

    // Add the page with updated properties to the database
    await addPageToDb({ properties, databaseId });
}

async function addPageToDb({ properties, databaseId }) {
    try {
        await notion.pages.create({
            parent: { database_id: databaseId },
            properties: properties,
        });
        console.log("Success! Entry added.");
    } catch (error) {
        console.log(error);
        console.error(error.body);
    }
}