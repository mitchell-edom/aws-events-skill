---
name: aws-events-api-mcp
description: Work with the AWS Events API and its MCP server to discover AWS conference events and sessions, connect Kiro or another MCP client, authenticate an attendee with AWS Builder ID OAuth and PKCE, inspect a personal schedule, or manage reservations, favorites, and personal time. Use this skill whenever a request mentions api.awsevents.com, AWS Events API, AWS conference or re:Invent session catalogs, the awsevents MCP server, event-session reservations, favorites, or personal event schedules. Use it even when the user only asks to find or plan conference sessions, because catalog-access and schedule rules depend on event registration and the chosen REST or MCP interface.
---

# AWS Events API and MCP

Use the canonical AWS Events documentation as the source of truth for this workflow. This API acts only for the signed-in attendee: it can read event catalogs and alter that attendee's own schedule, but it cannot register a person for an event or access another attendee's data.

## Source documentation and freshness

This public skill bundles no AWS documentation. Before answering behavior-specific questions, consult the current [AWS Events Developer Guide](https://docs.aws.amazon.com/events/latest/devguide/what-is-events-api.html) and, for REST contracts, the [live OpenAPI definition](https://api.awsevents.com/v1/openapi.json). Treat event dates, feature availability, operation status, quotas, endpoints, and error behavior as potentially changeable.

If the optional AWS MCP Server from the AWS Agent Toolkit is configured, use its documentation-search and retrieval capability for the current AWS sources. It does not require AWS credentials for documentation search. Do not require that MCP server or confuse it with the separate `awsevents` MCP server: local skills, the AWS documentation MCP, and the AWS Events MCP operate independently. If the AWS MCP Server is unavailable, use the canonical URLs directly and state that live verification could not be performed.

## Choose the interface

Use the MCP server for an AI assistant or agent. It exposes the REST operations as tools, but **every MCP tool call requires sign-in**, including `ListEvents` and catalog reads.

Use REST for scripts or applications. `ListEvents` and `GetEvent` are public. `ListSessions` and `GetSession` are public only for events that do not require registration. All schedule operations require an access token and event registration.

Before choosing an interface when access behavior matters, consult the live [overview](https://docs.aws.amazon.com/events/latest/devguide/what-is-events-api.html) and [MCP-server guide](https://docs.aws.amazon.com/events/latest/devguide/mcp-server.html).

## Connect Kiro to the MCP server

For a request to configure Kiro, add this server entry to the user's MCP configuration. Preserve other server entries. The `redirectUri` must end at the port, without a path; Kiro appends `/oauth/callback` itself. Reload the Kiro window after editing.

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

Do not choose a random port or add a path to `redirectUri`; either causes a `redirect_mismatch` during sign-in. On first tool use, the MCP client opens the browser sign-in flow and keeps its token locally. Verify connection by calling `ListEvents`.

For other MCP clients, use streamable HTTP endpoint `https://api.awsevents.com/mcp`, shared public client ID `7vmom55m1qstvq8i71ph127bfq`, and a callback URI exactly as registered for that client. The client ID is intentionally public; this OAuth flow uses PKCE and has no client secret. Consult the live [MCP-server guide](https://docs.aws.amazon.com/events/latest/devguide/mcp-server.html) for client-specific setup.

## REST API quick reference

Base URL: `https://api.awsevents.com`; all paths begin `/v1`; requests and responses are JSON. The live OpenAPI description is `https://api.awsevents.com/v1/openapi.json`.

| Intent | REST operation | Authentication |
|---|---|---|
| List current/upcoming events | `GET /v1/events` (`includePast=true` optional) | None |
| Inspect one event | `GET /v1/events/{eventId}` | None |
| List catalog pages | `GET /v1/events/{eventId}/sessions` | Required only when the event requires registration |
| Inspect one session | `GET /v1/events/{eventId}/sessions/{sessionId}` | Required only when the event requires registration |
| Read the attendee's schedule | `GET /v1/events/{eventId}/schedule` | Valid attendee token and registration |
| Reserve 1-10 sessions | `POST /v1/events/{eventId}/reservations` | Valid attendee token and registration |
| Cancel a reservation | `DELETE /v1/events/{eventId}/reservations/{sessionId}` | Valid attendee token and registration |
| Favorite 1-10 sessions | `POST /v1/events/{eventId}/favorites` | Valid attendee token and registration |
| Remove a favorite | `DELETE /v1/events/{eventId}/favorites/{sessionId}` | Valid attendee token and registration |
| Add personal time | `POST /v1/events/{eventId}/personal-time` | Valid attendee token and registration |
| Replace personal time | `PUT /v1/events/{eventId}/personal-time/{personalTimeId}` | Valid attendee token and registration |
| Delete personal time | `DELETE /v1/events/{eventId}/personal-time/{personalTimeId}` | Valid attendee token and registration |

For exact query parameters, field shapes, and examples, consult the live [REST API guide](https://docs.aws.amazon.com/events/latest/devguide/rest-api.html) and [OpenAPI definition](https://api.awsevents.com/v1/openapi.json).

* Traverse every `ListSessions` page until `nextToken` is **absent**. A short page is not the last page.
* Use `includeAbstracts=false` when abstracts are unnecessary, and `locale` for a requested language. Treat session fields as optional; event catalogs can omit fields.
* Treat `GetSchedule` as the source of truth. Use it to confirm schedule changes and obtain IDs omitted by write responses.

## Access and authentication

Before an authenticated REST call, consult the live [authentication guide](https://docs.aws.amazon.com/events/latest/devguide/authentication.html) and its linked details.

1. Determine whether the event requires registration from `ListEvents` or `GetEvent`.
2. For protected catalog reads and all schedule operations, the attendee needs both a valid access token and registration for the selected event. A valid token without registration gives `403`; signing in again does not fix it.
3. Send only the access token in `Authorization: Bearer $ACCESS_TOKEN` to `https://api.awsevents.com`.
4. For an application implementing sign-in, use OAuth authorization-code flow with PKCE, a fresh cryptographic verifier and state for every attempt, S256 base64url challenge without padding, `identity_provider=AWSBuilderID`, and a local exact-match redirect URI. Application callback ports are `8484` through `8489`, with `/callback`.
5. Refresh with the refresh token based on `expires_in`. On a `401`, refresh once and retry once. If it still returns `401`, require interactive sign-in rather than looping.

Access tokens last 60 minutes; refresh tokens last 30 days. Never log tokens, put them in URLs, or expose them in generated code, reports, or chat output. Browser apps keep tokens only in memory; other local apps use the OS keychain or a user-readable-only file. Consult the live [token-handling guidance](https://docs.aws.amazon.com/events/latest/devguide/auth-handling-tokens.html) for storage rules.

To sign out fully, revoke the refresh token, discard local tokens, and end the broker and Builder ID browser sessions. Consult the live [sign-out guidance](https://docs.aws.amazon.com/events/latest/devguide/auth-signing-out.html) before implementing this flow. Deleting an MCP configuration does not revoke its stored token.

## Schedule-changing operations

Reservation, favorite, and personal-time changes have attendee-visible effects. Confirm the intended event and exact sessions or personal-time details before a change unless the user already stated them unambiguously. If a reservation or favorite request lacks an unambiguous `eventId`, exact `sessionIds`, or required confirmation, state that no change occurred and request those missing inputs. For a later execution, state the full completion sequence: submit the change, inspect each per-session result, then use `GetSchedule` before reporting the final outcome. For a bulk reservation/favorite response, inspect each per-session success or failure: HTTP `200` does not mean every item succeeded. Confirm final state with `GetSchedule` and report successes, failures, and relevant clash information.

Use these request constraints:

* `ReserveSessions` and `AssociateFavorites`: send 1-10 distinct `sessionIds`; a favorite records interest and does not reserve a seat.
* `CancelReservation` and `DisassociateFavorite`: a `404` means the item is already absent and can be treated as complete on retry.
* `CreatePersonalTime`: `title` is 1-128 characters, `description` 1-250; timestamps are UTC `YYYY-MM-DDTHH:mm:ss` without `Z` or offset, seconds must be `00`, end must be after start, and duration must be a whole 5-minute increment. `location` is optional and at most 255 characters. Create returns no body, so retrieve the new ID from `GetSchedule`.
* `UpdatePersonalTime` replaces rather than merges. Send every field; omitting `location` clears it.

The service has no idempotency key. After an unknown write outcome (timeout, dropped connection, `500`, or `503`), do not repeat the original request. First read `GetSchedule`, compare it with the intended state, and submit only what remains. Only `CancelReservation` and `DisassociateFavorite` are direct-retry exceptions: retry later and treat `404` as already complete. For `DeletePersonalTime`, reconcile with `GetSchedule` before deciding whether another request is needed.

## Errors, quotas, and reporting

Consult the live [error guide](https://docs.aws.amazon.com/events/latest/devguide/errors.html) and [quota guide](https://docs.aws.amazon.com/events/latest/devguide/quotas.html) for troubleshooting.

* `400`: correct the malformed request; do not retry.
* `401`: sign in or refresh once, then retry once.
* `403` with JSON: attendee is not registered; do not retry. `403` without a body: edge refusal; slow down and retry.
* `404`: not found; treat a removal as already complete.
* `409`: operation temporarily closed; retry only after it reopens. It is not a malformed request.
* `429`: honor `Retry-After` in seconds. Batch writes count every named session toward quota, so batching saves round trips but not quota.
* `500`/`503`: back off reads; reconcile writes with `GetSchedule` before any follow-up change.

When presenting results, state the event ID, interface used, sign-in/registration constraint if applicable, operation outcome, per-session failures for bulk operations, and whether `GetSchedule` confirmed a write. Do not include token values.

## Canonical source map

* Service scope and access rules: https://docs.aws.amazon.com/events/latest/devguide/what-is-events-api.html
* Getting started: https://docs.aws.amazon.com/events/latest/devguide/getting-started.html
* MCP connection and tool list: https://docs.aws.amazon.com/events/latest/devguide/mcp-server.html
* OAuth and token handling: https://docs.aws.amazon.com/events/latest/devguide/authentication.html
* REST contracts: https://docs.aws.amazon.com/events/latest/devguide/rest-api.html and https://api.awsevents.com/v1/openapi.json
* Quotas and error recovery: https://docs.aws.amazon.com/events/latest/devguide/quotas.html and https://docs.aws.amazon.com/events/latest/devguide/errors.html

No AWS documentation is redistributed in this package. Consult the canonical sources above before redistributing AWS documentation or other AWS Content.
