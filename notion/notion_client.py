from os import environ
from typing import Any, List, Mapping
import requests

NOTION_API_URL = "https://api.notion.com/v1"

# Needs to support:
# - Querying databases
# - Adding pages

# TODO(fwallace): We could write something that will auto-generate these classes (essentially a simple ORM layer)
# based on the schema returned by https://developers.notion.com/reference/retrieve-a-database. The idea would be
# to parse the schema and generate a typed class based on that, with functions to serialize and deserialize
# values accordingly.


class NotionTodoPage:
    def __init__(self):
        pass

    # What should this class do? Similar to json utilities, it should deserialize and serialize values
    # Maybe I should port json utilities and teach them how to parse notion-specific structure?
    # I want it to take a json representation of a notion page, and know how to deserialize it
    # Maybe this should be paired with a little ORM wrapper to create typed classes for Notion tables?


class NotionClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def query_db(
        self,
        database_id: str,
        params: Mapping[str, Any],
        # By default, sort by last edited time in descending order
        sorts: List[Mapping[str, str]] = [
            {
                "timestamp": "last_edited_time",
                "direction": "descending",
            }
        ],
    ) -> Mapping[str, Any]:
        """Query a database with the desired parameters."""

        # Set the database url
        database_url = f"{NOTION_API_URL}/databases/{database_id}/query"

        # Build the payload
        # Wow, I'm tired... how do I copy a dictionary again?
        payload = {"sorts": sorts, **params}

        # Query the database with the provided parameters, and check that the call succeeded
        response = requests.post(
            database_url,
            headers={
                "Authorization": f"{self.api_key}",
                "Notion-Version": "2021-08-16",
            },
            data=payload,
        )
        print(response.json())
        response.raise_for_status()

        return response.json()

    def retrieve_db(
        self,
        database_id: str,
    ) -> Mapping[str, Any]:
        """Retrieve a database."""
        # Set the database url
        database_url = (
            f"{NOTION_API_URL}/databases/a3c0596b3fae409aa012e1a491283920"
        )

        # Retrieve the database, and check that the call succeeded
        response = requests.post(
            database_url,
            headers={
                "Authorization": f"{self.api_key}",
                "Notion-Version": "2021-08-16",
            },
        )
        print(response.json())
        response.raise_for_status()

        return response.json()

    async def add_page_to_db(
        self, database_id: str, properties: Mapping[str, Any]
    ):
        """Add a page, with the database as its parent."""
        pass


#     def query_databases(self, integration_token="YOUR INTEGRATION TOKEN"):
#         database_url = NOTION_URL + DATABASE_ID + "/query"
#         response = requests.post(
#             database_url, headers={"Authorization": f"{integration_token}"}
#         )
#         if response.status_code != 200:
#             raise ApiError(f"Response Status: {response.status_code}")
#         else:
#             return response.json()

#     def get_projects_titles(self, data_json):
#         return list(data_json["results"][0]["properties"].keys())

#     def get_projects_data(self, data_json, projects):
#         projects_data = {}
#         for p in projects:
#             if p != "Name" and p != "Date":
#                 projects_data[p] = [
#                     data_json["results"][i]["properties"][p]["checkbox"]
#                     for i in range(len(data_json["results"]))
#                 ]
#             elif p == "Date":
#                 dates = [
#                     data_json["results"][i]["properties"]["Date"]["date"][
#                         "start"
#                     ]
#                     for i in range(len(data_json["results"]))
#                 ]

#         return projects_data, dates


# async def check_open_task_exists_by_name(
#     client: NotionClient,
#     # Force everything to be named after this, since there are multiple parameters of the same type.
#     # This just serves to reduce user error.
#     *, task_name: str,
#     database_id: str) -> bool:
#     """ Check if any open (incomplete) tasks exist with this name. """
#     response = await client.query_db(database_id=database_id, params={"filter": {
#         "and": [
#             {
#                 "property": "Name",
#                 "text": {
#                     "equals": task_name
#                 }
#             },
#             {
#                 "property": "Done",
#                 "checkbox": {
#                     "equals": False,
#                 },
#             },

#         ]
#     }})

#     if len(response["results"]) > 0:
#         # Found at least one open task by this name
#         # TODO(fwallace): How do we want to handle logging? loguru?
#         logger.debug(f"There are {len(response["results"])} open tasks with this name")
#         return True
#     else:
#         # Didn't find anything by this name - proceed!
#         return False

# async def get_completed_recurring_tasks(client: NotionClient, *, timestamp: , database_id: str) -> List[NotionTask]:
#     """Get recurring tasks (have a "Schedule") that have been completed (updated) since the given
#     timestamp. This will also find previously-completed tasks that have been updated, if they
#     were updated for some reason. We return a list of tasks, de-duplicated on name, that should
#     be recreated with the next due date on the given schedule."""
#     # Get recurring tasks completed since the given timestamp
#     response = await client.query_db
#     pass

#     // Get recurring tasks completed since the given timestamp
#     const response = await query_db({
#         databaseId,
#         options: {
#             filter: {
#                 and: [
#                     {
#                         property: "Last edited time",
#                         date: {
#                             on_or_after: timestamp.toISOString(),
#                         },
#                     },
#                     {
#                         property: "Schedule",
#                         text: {
#                             is_not_empty: true,
#                         },
#                     },
#                     {
#                         property: "Done",
#                         checkbox: {
#                             equals: true,
#                         },
#                     },
#                 ]
#             }
#         }
#     });

#     // De-duplicate the list of tasks by name
#     const unique_names = new Set();
#     const unique_tasks = [];
#     response.results.forEach(task => {
#         console.log(task.properties);
#         const task_name = task.properties.Name.title[0].plain_text;
#         if (!unique_names.has(task_name)) {
#             unique_tasks.push(task);
#             unique_names.add(task_name);
#         }
#     });
#     console.log(`Found ${unique_tasks.length} distinct recurring tasks`);

#     // Return our task list
#     return {
#         tasks: unique_tasks
#     }
# }
