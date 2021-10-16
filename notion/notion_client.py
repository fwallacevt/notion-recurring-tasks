from typing import Any, Dict, List, Mapping, Optional
import requests

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_API_VERSION = "2021-08-16"


class NotionClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def query_db(
        self,
        *,
        database_id: str,
        filter: Optional[Mapping[str, Any]] = None,
        # By default, sort by last edited time in descending order
        sorts: Optional[List[Mapping[str, str]]] = None,
        params: Mapping[str, Any] = {},
    ) -> List[Mapping[str, Any]]:
        """Query a database with the desired parameters."""
        # Set the database url
        database_url = f"{NOTION_API_URL}/databases/{database_id}/query"

        # Build the payload. In testing, Notion was able to handle the empty payload.
        payload: Dict[str, Any] = {}
        if filter is not None:
            payload["filter"] = filter
        elif sorts is not None:
            payload["sorts"] = sorts

        # Query the database with the provided parameters, and check that the call succeeded
        response = requests.post(
            database_url,
            headers={
                "Authorization": f"{self.api_key}",
                "Notion-Version": NOTION_API_VERSION,
            },
            data={**payload, **params},
        )
        response.raise_for_status()

        ret = response.json()
        return ret["results"]

    def retrieve_db(
        self,
        database_id: str,
    ) -> Mapping[str, Any]:
        """Retrieve a database."""
        # Set the database url
        database_url = f"{NOTION_API_URL}/databases/{database_id}"

        # Retrieve the database, and check that the call succeeded
        response = requests.get(
            database_url,
            headers={
                "Authorization": f"{self.api_key}",
                "Notion-Version": NOTION_API_VERSION,
            },
        )
        response.raise_for_status()

        return response.json()

    def add_page_to_db(self, database_id: str, properties: Mapping[str, Any]):
        """Add a page, with the database as its parent."""
        # Build the db url
        database_url = f"{NOTION_API_URL}/pages"

        # Insert a value, and check that the call succeeded
        data = {
            "parent": {"database_id": database_id},
            "properties": properties,
        }
        response = requests.post(
            database_url,
            headers={
                "Authorization": f"{self.api_key}",
                "Notion-Version": NOTION_API_VERSION,
            },
            json=data,
        )
        response.raise_for_status()

        ret = response.json()
        return ret
