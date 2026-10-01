import asyncio
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import httpx2
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from langchain_core.tools import tool
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from app.config import GOOGLE_CALENDAR_MCP_URL, GOOGLE_CALENDAR_TOKEN, GOOGLE_OAUTH_CREDENTIALS

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def autenticar() -> None:
    """Abre o consentimento Google e grava o token local ignorado pelo Git."""
    flow = InstalledAppFlow.from_client_secrets_file(str(GOOGLE_OAUTH_CREDENTIALS), SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    GOOGLE_CALENDAR_TOKEN.write_text(creds.to_json(), encoding="utf-8")


def _credentials() -> Credentials:
    if not GOOGLE_CALENDAR_TOKEN.exists():
        raise RuntimeError("Autenticação Google pendente: execute autenticar() em app.tools.calendario_google.")
    creds = Credentials.from_authorized_user_file(str(GOOGLE_CALENDAR_TOKEN), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
        GOOGLE_CALENDAR_TOKEN.write_text(creds.to_json(), encoding="utf-8")
    if not creds.valid:
        raise RuntimeError("Token Google inválido; execute autenticar() novamente.")
    return creds


async def _mcp_create_event(token: str, args: dict) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx2.AsyncClient(headers=headers, timeout=httpx2.Timeout(30, read=300)) as http:
        transport = streamable_http_client(GOOGLE_CALENDAR_MCP_URL, http_client=http)
        async with Client(transport) as client:
            result = await client.call_tool("create_event", args)
    if result.is_error:
        raise RuntimeError("; ".join(getattr(c, "text", "") for c in result.content))
    data = result.structured_content or {}
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        data = data["result"]
    if not isinstance(data, dict) or not data.get("id"):
        for item in result.content:
            text = getattr(item, "text", "")
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict) and parsed.get("id"):
                    data = parsed
                    break
            except (TypeError, ValueError):
                continue
    if not data.get("id"):
        raise RuntimeError("O Calendar MCP não retornou o ID do evento criado.")
    return data


def _calendar_api_fallback(token: str, args: dict) -> dict:
    body = {
        "summary": args["summary"],
        "start": {"dateTime": args["startTime"], "timeZone": args["timeZone"]},
        "end": {"dateTime": args["endTime"], "timeZone": args["timeZone"]},
        "location": args.get("location"),
        "description": args.get("description"),
    }
    req = Request(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read())


@tool
def add_google_event(
    title: str,
    start_time: str,
    end_time: str,
    location: str | None = None,
    notes: str | None = None,
) -> dict:
    """Cria um evento na agenda Google após autenticação local do usuário."""
    try:
        creds = _credentials()
        args = {
            "summary": title,
            "startTime": start_time,
            "endTime": end_time,
            "timeZone": "America/Sao_Paulo",
            "location": location or "",
            "description": notes or "",
        }
        try:
            event = asyncio.run(_mcp_create_event(creds.token, args))
        except Exception as exc:
            mensagem = str(exc).lower()
            if not any(s in mensagem for s in ("403", "404", "api has not been used", "api is disabled", "service_disabled")):
                raise
            event = _calendar_api_fallback(creds.token, args)
        return {"status": "ok", "id": event["id"], "link": event.get("htmlLink")}
    except HTTPError as exc:
        return {"status": "erro", "mensagem": f"Google Calendar respondeu HTTP {exc.code}."}
    except Exception as exc:
        return {"status": "erro", "mensagem": str(exc)}


TOOLS_GOOGLE = [add_google_event]
