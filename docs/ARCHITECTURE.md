# 2Block architecture

## Current shape

The playable client is a dependency-free WebGL application. The Python desktop
entry point remains an optional protocol launcher: it validates a `twoblock://`
URI and opens the same browser client. The former isometric Tk renderer has
been replaced. Tk is only used for optional installer and startup-error dialogs.

| Component | Location | Responsibility |
| --- | --- | --- |
| Hub | `apps/web` | Catalog, guest profile, browser play, desktop fallback |
| Game | `apps/web/game` | WebGL rendering, camera, controls, HUD, snapshot smoothing |
| Launcher | `apps/client` | Protocol validation, OS registration, installer |
| Runtime | `apps/server` | Rooms, session capabilities, physics, pickups, building |
| Shared contract | `packages/common` | URI and profile validation |

Everything runs against `http://127.0.0.1:8765`. The server binds to loopback and
serves an explicit asset allowlist, not the source directory. There are no CDN
scripts, runtime package downloads, accounts, databases, or durable world saves.

## Entry and identity

The hub stores `twoblock.guest.v1` in localStorage:

```json
{"user":"Guest","avatar":{"body":"#58c9a5","head":"#f2c78f","hat":"cap"}}
```

Names contain 1–24 printable characters, colors are `#RRGGBB`, and hats are
`none`, `cap`, or `tall`. Malformed storage falls back to defaults. The server
validates profiles again; guest names are unverified display labels and may be
duplicated. They do not establish ownership or permissions.

Play Now navigates to `/play#<encoded join JSON>`. The page removes the fragment
before making API calls, retaining only the non-sensitive game ID in the query
so reloading stays in the selected world. The fragment contains the guest
profile and optional one-use launch ID, never a session bearer token.

The desktop route uses:

```text
twoblock://join?gameId=<id>&server=<encoded origin>&user=<encoded name>&avatar=<encoded JSON>&launchId=<optional id>
```

The launcher rejects duplicate/unknown fields, bad authorities, fragments,
control characters, links longer than 4096 characters, invalid profiles, and
server addresses other than exactly `http://127.0.0.1:8765`. The URI is passed as
an argument, never evaluated as a command. Management flags cannot accompany a
URI. The launcher opens `/play` with the profile in a fragment; the browser then
performs the join. Python's headless diagnostic mode still joins directly.

Windows registration writes under HKCU; Linux uses a per-user desktop entry and
`xdg-mime`. macOS protocol registration is not implemented. Source handlers use
absolute paths. A packaged Windows launcher copies itself to the user's app-data
directory; it does not include an embedded browser or offline game assets.

## Launch confirmation

The hub prepares short-lived launch records before enabling the cards. Browser
play consumes its ticket on join. The desktop button preserves the click's user
gesture for protocol navigation, starts polling, and offers installation help
if no join arrives within five seconds. Polling continues until success or
expiry. Changing tabs does not count as a successful launch.

Tickets are random 32-character capabilities, expire after 120 seconds, and can
be consumed once for the selected game. There are at most 256 launch records.
An acknowledgment confirms an accepted game join. It cannot prove that a human
is playing or that the renderer continues working. Headless diagnostics can
acknowledge too. Browsers provide no dependable installed-handler query.

Each accepted guest join gets a random public player ID and a separate bearer
session token. Tokens stay in client memory, out of profiles, URLs, snapshots,
and request logs. Sessions expire after 15 seconds without movement updates.
Reconnect creates a new session without reusing a consumed ticket.

## 3D client

`renderer.js` owns a WebGL 1 context, shader compilation, geometry buffers,
directional lighting, sky-colored distance fog, and depth-tested triangle draws.
`math.js` contains column-major view/projection matrices and slab-based ray/box
intersection. A perspective camera follows the smoothed player position; orbit
and zoom are local UI state. Camera rays shorten the orbit near scenery.

Floor tiles and blocks share a cached static geometry buffer. It is rebuilt only
when the received block list changes. Avatars, waving arms, bobbing pickups, and
checkpoint markers share a dynamic buffer. A separate translucent draw previews
a build/remove target. DOM labels project player names into screen coordinates.
This is real perspective rendering with depth testing, not depth-sorted Canvas
polygons. It uses GPU acceleration when the browser provides it.

The renderer uses requestAnimationFrame and caps device pixel ratio at two.
Snapshots arrive approximately every 50ms. Display positions and facing smooth
toward server values, with large respawn displacements snapping. There is no
client prediction or rollback; network latency still affects movement response.

Input supports camera-relative movement, jump, sprint, orbit, zoom, hotbar tools,
respawn, and wave. Pointer capture handles camera drags. The game does not require
pointer lock. Welcome/pause dialogs clear movement and keep the heartbeat alive.
Hidden tabs send no movement; background throttling may still expire a session.
The reconnect banner provides an explicit recovery path.

The UI includes a first-join guide, coin/checkpoint progress, tool hints, reach
previews, player labels, pause/help/fullscreen, and touch movement/jump controls.
Touch editing uses taps; touch orbit is available in Explore mode.

## Server rules

One process stores two independent rooms, each with at most 16 guests and 256
blocks. Original blocks form towers and a short floating-platform course. Room
builds live until restart, including after their builder leaves. Block ownership
is scoped to a public player ID for that session. A rejoining guest cannot
remove blocks owned by the previous session. This is deliberately temporary;
a persistent ownership system would need a separate identity design.

The runtime advances a player's physics from elapsed monotonic time when that
player sends input. A request accounts for at most 250ms, subdivided into steps
of at most 20ms. Walking speed is four units/second, sprinting six, gravity 20,
and jump impulse 7.8. Input is normalized to prevent diagonal speed gains.
Only grounded players may jump. Position is never accepted from the client.

Players have a vertical AABB and separate x/z collision resolution for sliding
along walls. Vertical resolution handles landing on block tops and hitting
ceilings. The floor is y=0; horizontal coordinates are clamped to [-15,15].
Players can overlap. These are simple character collisions, not rigid-body
physics or a compatibility implementation of Roblox's character controller.

Seven coin pickups are checked by server distance and can be collected once
per guest session. A flag platform activates a checkpoint. Lava at ground level
or an explicit respawn returns the player there. Coins and checkpoint selection
survive respawning but reset on a new session. Wave is a server-timed two-second
public emote. The health field currently remains 100; combat is not implemented.

Build actions require integer grid coordinates, a valid color, a cell within
five units, an empty supported location inside [-14,14] and y=0..7, room capacity,
and no intersection with a player. Spawn/checkpoint columns remain clear. Edits
are limited to one per 200ms per session. Only a block's current owner can remove
it, and supported blocks must be removed from the top down. Original scenery
is protected. Blocks are shared immediately through subsequent room snapshots.

A reentrant lock covers mutations and snapshot creation. Cleanup is lazy on
session/launch operations. There is no durable storage, editor scripting, chat,
combat, account system, or automatic updater.

## API

Bodies are JSON objects up to 8192 bytes. Mutations require `application/json`.

| Route | Request | Response |
| --- | --- | --- |
| GET `/api/games` | — | `{games: [...]}` |
| GET `/api/config` | — | `{server, windowsInstaller}` |
| POST `/api/launches` | `{gameId}` | `{launchId, expiresIn}` |
| GET `/api/launches/<id>` | Launch capability | `{status}` |
| POST `/api/join` | `{gameId,user,avatar,launchId?}` | `{token,playerId,world}` |
| POST `/api/step` | `{dx,dz,jump?,sprint?}` + bearer | World snapshot |
| POST `/api/action` | `{kind,...}` + bearer | World snapshot |
| POST `/api/leave` | `{}` + bearer | `{ok:true}` |

Actions are `wave`, `respawn`, `place`, and `remove`. Building supplies integer
`x,y,z` and placement also supplies `color`. A snapshot includes public players,
blocks, coins, checkpoints, and hazards. Players expose position, yaw, appearance,
grounded state, coins/collected IDs, checkpoint, and waving state. No bearer
credentials are exposed. Static world metadata is repeated for simplicity.

Invalid requests use 400, expired/missing sessions 401, invalid Origin/Host 403,
missing routes 404, bad body size 413, and wrong content type 415. Snapshot and
asset responses use no-store. A self-only CSP rejects external scripts and
framing. No CORS permissions are granted. Host must match the loopback origin;
foreign browser Origins and cross-site Fetch Metadata are rejected. Native
clients can omit Origin. This does not defend against another local process
running as the same user.

## Before public hosting

Python's [`http.server`](https://docs.python.org/3/library/http.server.html) is a
development server. Replace it with a maintained bounded-concurrency service
behind TLS before exposing the API. Add rate/connection limits, structured
errors, metrics, and proper request budgeting.

Separate catalog/ticket issuance from room workers. Resolve public server
addresses from trusted HTTPS manifests and signed short-lived tickets; do not
allow arbitrary server URLs in the handler. A public guest system still needs
abuse limits, moderation, reporting, and mute/block tools. Do not treat a guest
name as verified identity.

Move physics to a fixed-tick room loop and use a persistent transport with input
sequence numbers, bounded catch-up, delta snapshots, prediction, and interpolation.
The current per-request model can make physics depend on input arrival and is
intended for loopback testing. Benchmark before selecting more complex transport.

A creator platform needs a versioned world format, asset validation and quotas,
and eventually a sandbox with no process/filesystem/network access. Persisted
ownership must be explicit. Downloaded game content must never become executable
code merely because the launcher received a game ID.

Public launchers need signed builds/update manifests, checksums, rollback-safe
updates, platform packaging, and clean-machine tests. Windows builds currently
remain unsigned; Linux uses source registration; macOS packaging remains future
work. Browser play remains the simplest route.

## Verification and performance

Python tests cover protocol validation, launcher handoff construction, HTTP asset
and action routes, room isolation, speed limits, jumping/landing, coin uniqueness,
checkpoint/lava respawn, build reach/support/ownership, and wave expiry. Node's
built-in tests check projection matrices and ray intersections. Run commands
and manual browser acceptance checks are in [INSTALL.md](INSTALL.md).

There are no measured performance claims yet. Measure cold/warm load, frame-time
percentiles, memory, network bytes, and physics time with 16 guests and a full
256-block room. Record browser/GPU, hardware acceleration, device pixel ratio,
OS, sample count, and world contents. WebGL math tests do not prove successful
shader compilation on a particular GPU or replace browser visual testing.
