# AWS Events API & MCP Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-blue.svg)](https://modelcontextprotocol.io)

An AI assistant skill and Model Context Protocol (MCP) configuration for interacting with the **AWS Events API** (`api.awsevents.com`). Designed for Google Antigravity, Kiro, Claude Code, and other MCP-compatible coding assistants to explore AWS conference session catalogs (such as **AWS re:Invent**), manage reservations, track favorites, and plan personal schedules.

Based on the [AWS Builder Center guide](https://builder.aws.com/content/3JjrKKy63DJ80xhHTHd50DUIoxx/how-to-plan-reinvent-2026-with-the-new-aws-events-api-and-mcp-server) by Brooke Jamieson.

---

## 🛠️ MCP Server Configuration

The AWS Events MCP server is hosted at `https://api.awsevents.com/mcp` using streamable HTTP transport.

### OAuth Details
- **Client ID**: `7vmom55m1qstvq8i71ph127bfq` (Shared public client ID; uses PKCE with no client secret)
- **Scopes**: `openid`, `email`, `events/access`
- **Identity Provider**: `AWSBuilderID`
- **Callback Ports**: Loopback ports `8484`–`8489` (or `8976` for Kiro)

### Configuration Snippets

#### 1. Google Antigravity (CLI & IDE)
Add to `~/.gemini/config/mcp_config.json` (global) or `.agents/mcp_config.json` (project):

```json
{
  "mcpServers": {
    "awsevents": {
      "serverUrl": "https://api.awsevents.com/mcp",
      "url": "https://api.awsevents.com/mcp",
      "oauth": {
        "clientId": "7vmom55m1qstvq8i71ph127bfq",
        "redirectUri": "http://127.0.0.1:8976",
        "oauthScopes": [
          "openid",
          "email",
          "events/access"
        ]
      }
    }
  }
}
```

Or via Antigravity CLI:
```bash
agy mcp add awsevents https://api.awsevents.com/mcp
```

#### 2. Kiro
Add to your Kiro MCP configuration (`~/.kiro/settings/mcp.json` or `.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "awsevents": {
      "url": "https://api.awsevents.com/mcp",
      "oauth": {
        "clientId": "7vmom55m1qstvq8i71ph127bfq",
        "redirectUri": "http://127.0.0.1:8976",
        "oauthScopes": ["openid", "email", "events/access"]
      }
    }
  }
}
```
> **Note**: Do not add a path to `redirectUri` in Kiro; Kiro appends `/oauth/callback` automatically.

#### 3. Claude Code
Add via the Claude CLI:

```bash
claude mcp add --transport http --scope user awsevents \
  https://api.awsevents.com/mcp \
  --callback-port 8484 --client-id 7vmom55m1qstvq8i71ph127bfq
```

---

## 📦 Skill Installation

The skill instructs the agent on catalog pagination (`nextToken`), response optimization (`includeAbstracts=false`), schedule reconciliation (`GetSchedule`), and error handling (`403` unregistered attendee vs `409` closed seating).

### Google Antigravity
Clone or copy [`SKILL.md`](SKILL.md) to:
- **Global**: `~/.gemini/antigravity-cli/skills/aws-events-api-mcp/SKILL.md`
- **Workspace**: `.agents/skills/aws-events-api-mcp/SKILL.md`

### Kiro
Copy [`SKILL.md`](SKILL.md) to:
- `~/.kiro/skills/aws-events-api-mcp/SKILL.md`

---

## ⚡ What You Can Ask Your Assistant

- *"Go through the re:Invent 2026 catalog and shortlist 300 and 400 level sessions about agents or MCP."*
- *"What workshops are scheduled for Tuesday afternoon?"*
- *"Favorite all sessions on my shortlist."*
- *"Show me my schedule and flag any overlapping time slots."*
- *"Block out Wednesday 12:00 to 13:00 and label it lunch."*
- *"Reserve seats for my top 3 sessions as soon as seating opens."*

---

## 🧰 Available MCP Tools

| Tool | Description |
|---|---|
| `ListEvents` | Lists ongoing and upcoming AWS events (e.g. AWS re:Invent). |
| `GetEvent` | Gets details for a specific event by ID. |
| `ListSessions` | Paginated listing of sessions within an event catalog. |
| `GetSession` | Retrieves details and abstract for a specific session. |
| `GetSchedule` | Fetches the signed-in attendee's personal schedule. |
| `ReserveSessions` | Reserves seats for 1–10 sessions. |
| `CancelReservation` | Cancels a session reservation. |
| `AssociateFavorites` | Marks 1–10 sessions as favorites. |
| `DisassociateFavorite`| Removes a session from favorites. |
| `CreatePersonalTime` | Adds a custom personal time block to the schedule. |
| `UpdatePersonalTime` | Modifies an existing personal time entry. |
| `DeletePersonalTime` | Removes a personal time block. |

---

## 📚 References & Resources

- [AWS Events API Developer Guide](https://docs.aws.amazon.com/events/latest/devguide/what-is-events-api.html)
- [AWS Events MCP Server Guide](https://docs.aws.amazon.com/events/latest/devguide/mcp-server.html)
- [AWS Events API OpenAPI Spec](https://api.awsevents.com/v1/openapi.json)
- [How to plan re:Invent 2026 with the new AWS Events API and MCP server](https://builder.aws.com/content/3JjrKKy63DJ80xhHTHd50DUIoxx/how-to-plan-reinvent-2026-with-the-new-aws-events-api-and-mcp-server) by Brooke Jamieson
