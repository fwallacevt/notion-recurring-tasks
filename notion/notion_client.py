from typing import Any, Dict, List, Mapping, Optional

import httpx  # type: ignore

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_API_VERSION = "2021-08-16"


class NotionClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def query_db(
        self,
        *,
        database_id: str,
        filter: Optional[Mapping[str, Any]] = None,
        # By default, sort by last edited time in descending order
        sorts: Optional[List[Mapping[str, str]]] = None,
        params: Mapping[str, Any] = {},
        page_size: Optional[int] = None,
    ) -> List[Mapping[str, Any]]:
        """Query a database with the desired parameters."""
        # Set the database url
        database_url = f"{NOTION_API_URL}/databases/{database_id}/query"

        # Build the payload. In testing, Notion was able to handle the empty payload.
        payload: Dict[str, Any] = {}
        if filter is not None:
            payload["filter"] = filter
        if sorts is not None:
            payload["sorts"] = sorts
        if page_size is not None:
            payload["page_size"] = page_size

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Query the database with the provided parameters, and check that the call succeeded
            response = await client.post(
                database_url,
                headers={
                    "Authorization": f"{self.api_key}",
                    "Notion-Version": NOTION_API_VERSION,
                },
                json={**payload, **params},
            )
            response.raise_for_status()

            ret = response.json()
            return ret["results"]

    async def retrieve_db(
        self,
        database_id: str,
    ) -> Mapping[str, Any]:
        """Retrieve a database."""
        # Set the database url
        database_url = f"{NOTION_API_URL}/databases/{database_id}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Retrieve the database, and check that the call succeeded
            response = await client.get(
                database_url,
                headers={
                    "Authorization": f"{self.api_key}",
                    "Notion-Version": NOTION_API_VERSION,
                },
            )
            response.raise_for_status()

            return response.json()

    async def add_page_to_db(self, database_id: str, properties: Mapping[str, Any]):
        """Add a page, with the database as its parent."""
        # Build the db url
        database_url = f"{NOTION_API_URL}/pages"

        # Insert a value, and check that the call succeeded
        data = {
            "parent": {"database_id": database_id},
            "properties": properties,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                database_url,
                headers={
                    "Authorization": f"{self.api_key}",
                    "Notion-Version": NOTION_API_VERSION,
                },
                json=data,
            )
            response.raise_for_status()

            return response.json()
