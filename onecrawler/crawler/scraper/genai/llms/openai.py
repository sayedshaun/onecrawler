from typing import Any, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel

from .base import BaseLLM

T = TypeVar("T", bound=BaseModel)


class OpenAILLM(BaseLLM):
    @staticmethod
    def _make_nullable(prop_schema: dict) -> dict:
        """Widens a property schema to also accept null, without dropping it."""
        if "anyOf" in prop_schema:
            any_of = prop_schema["anyOf"]
            if any(isinstance(o, dict) and o.get("type") == "null" for o in any_of):
                return prop_schema
            return {**prop_schema, "anyOf": [*any_of, {"type": "null"}]}

        prop_type = prop_schema.get("type")
        if prop_type == "null":
            return prop_schema

        if prop_type is not None:
            types = prop_type if isinstance(prop_type, list) else [prop_type]
            if "null" not in types:
                types = [*types, "null"]
            return {**prop_schema, "type": types}

        return {"anyOf": [prop_schema, {"type": "null"}]}

    @classmethod
    def _to_strict_schema(cls, schema: dict) -> dict:
        """Recursively normalizes a Pydantic JSON schema for OpenAI's strict mode.

        OpenAI's strict structured-output mode requires every object to set
        "additionalProperties": false and list *every* property in "required".
        Pydantic v2 only lists fields without a default in "required" and never
        sets "additionalProperties" — so any schema with an optional/defaulted
        field (which onecrawler's own GenAI prompt encourages, e.g. "use null if
        missing") is rejected by the API unless normalized here. Fields that were
        originally optional are made nullable so omission is still representable.
        """
        schema = dict(schema)

        defs = schema.get("$defs")
        if isinstance(defs, dict):
            schema["$defs"] = {
                name: cls._to_strict_schema(sub) for name, sub in defs.items()
            }

        properties = schema.get("properties")
        if isinstance(properties, dict):
            original_required = set(schema.get("required", []))
            new_properties = {}
            for name, prop_schema in properties.items():
                normalized = cls._to_strict_schema(prop_schema)
                if name not in original_required:
                    normalized = cls._make_nullable(normalized)
                new_properties[name] = normalized
            schema["properties"] = new_properties
            schema["required"] = list(properties.keys())
            schema["additionalProperties"] = False

        items = schema.get("items")
        if isinstance(items, dict):
            schema["items"] = cls._to_strict_schema(items)

        return schema

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 300.0,
        **model_kwargs: Any,
    ) -> None:
        self.model = model
        self.model_kwargs = model_kwargs

        headers = {"Content-Type": "application/json"}
        # Keyless OpenAI-compatible servers (llama.cpp, vLLM, ...) don't want an
        # Authorization header; only send it when a key is actually configured.
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers=headers,
        )

    async def generate(self, prompt: str, schema: Optional[Type[T]] = None) -> T | str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            **self.model_kwargs,
        }

        if schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": self._to_strict_schema(schema.model_json_schema()),
                },
            }

        response = await self.client.post(
            "/chat/completions",
            json=payload,
        )

        response.raise_for_status()
        data = response.json()

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"OpenAI returned no choices: {data}")

        message = choices[0]["message"]
        refusal = message.get("refusal")

        if refusal:
            raise RuntimeError(refusal)

        content = message.get("content")
        if not content:
            raise RuntimeError(f"OpenAI returned empty content: {data}")

        if schema is None:
            return content

        return schema.model_validate_json(content)

    async def close(self) -> None:
        await self.client.aclose()
