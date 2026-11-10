# Running 2Block

## Start playing

You need Python 3.11+ and a WebGL-capable browser. Nothing needs to be installed
with pip or npm for local play.

From the repository root:

```sh
python scripts/check_environment.py
python -m apps.server
```

Leave the terminal open. Visit **http://127.0.0.1:8765** using that address
exactly; the development server rejects other Host values.

1. Choose a guest name, colors, and headwear in the hub.
2. Click **Play Now** on a game card.
3. When the world loads, click **Let's play**.
4. Move with WASD, jump with Space, and hold Shift to sprint.
5. Right-drag to look around; use the scroll wheel to zoom.

The game runs in the browser with real perspective and WebGL depth testing.
It uses the GPU when hardware acceleration is available. There is no isometric
Tk renderer anymore. Profile changes stay in this browser's local storage.

Open the hub in another tab and join the same game to test multiplayer. Join
the other game to check room isolation.

## Things to try

| Activity | How |
| --- | --- |
| Build | Press 2, choose a color, click a nearby ground cell or block face |
| Remove | Press 3 and click a block you placed |
| Explore | Press 1 to put away building tools |
| Find coins | Walk or jump through the seven spinning gold pickups |
| Complete the course | Jump up the gold platforms to the flag |
| Save a checkpoint | Stand on the flag platform; the HUD confirms it |
| Respawn | Press R or use the game menu |
| Wave | Press 4 or click Wave in the hotbar |
| Help / fullscreen / leave | Open Menu or press Esc |

You can build within five units, up to height eight, with a 256-block room cap.
Blocks need support underneath. Remove a stack from the top down. Spawn and
checkpoint columns are protected. Only your current session can remove blocks
it placed. Red lava returns you to your checkpoint.

Touch controls appear on touchscreens. Use the arrows and Jump; drag the world
in Explore mode to orbit. Select Build/Remove and tap to edit. A keyboard and
mouse remain the most comfortable way to play.

The menu stops your movement while other guests keep playing. A disconnected
client offers Reconnect. Reconnecting creates a new guest session: coins,
checkpoints, and ownership of earlier blocks are not restored. All room builds
are temporary and disappear when the runtime stops.

## Optional desktop protocol

Browser play needs no handler. To test the desktop route, open another terminal
at the repository root and run:

```sh
python -m apps.client --register
```

Use **Open with desktop launcher** under a game card, then accept the browser's
external-app prompt. The Python launcher validates the URI and opens the WebGL
game in your default browser. It is not a native embedded game window.

On Windows registration writes under the current user's registry:

```text
HKEY_CURRENT_USER\Software\Classes\twoblock
  (Default) = URL:2Block Protocol
  URL Protocol = ""
  shell\open\command
    (Default) = <pythonw.exe> "<checkout>\scripts\client.py" "%1"
```

Executable paths are quoted when needed. No administrator rights are required.
The absolute bootstrap path lets it work regardless of the browser's working
directory. Re-register after moving the checkout or changing Python.
Registration replaces an existing association for this scheme.

On Linux, install `xdg-utils` first. Registration writes `twoblock.desktop` to
`$XDG_DATA_HOME/applications` (normally `~/.local/share/applications`) and calls
`xdg-mime default`. Run it in a graphical login session.

macOS can play in the browser and launch the Python entry point directly.
Native macOS protocol registration is not implemented.

The hub shows installation help after five seconds without a join acknowledgment.
That timeout does not prove the launcher is absent. Accepting a delayed browser
prompt can still complete the launch. Tickets expire after two minutes; use the
game card again for a fresh one.

## Direct launch

This bypasses OS registration while exercising URI parsing and browser opening:

```sh
python -m apps.client 'twoblock://join?gameId=block-yard&server=http%3A%2F%2F127.0.0.1%3A8765&user=Guest&avatar=%7B%22body%22%3A%22%2358c9a5%22%2C%22head%22%3A%22%23f2c78f%22%2C%22hat%22%3A%22cap%22%7D'
```

Use PowerShell, Bash, or Zsh for the single-quoted command; `cmd.exe` needs double
quotes. Add `--headless` before the URI to join and leave without opening a
browser. Headless mode checks the API, not the renderer.

## Build a Windows installer

Use standard CPython **3.13 on Windows**, with Tcl/Tk enabled for installer
messages. MSYS Python is not the packaging target.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-build.txt
.\scripts\build_windows.ps1
```

The output is `dist/2Block-Setup.exe`. The portal advertises its download only
when the file exists. Running it copies the launcher to
`%LOCALAPPDATA%\2Block\2Block.exe` and registers `twoblock://`. Players do not need
Python, but still need a WebGL browser. The launcher loads game assets from the
running local server; it does not bundle an offline world.

Close the launcher before replacing its executable. Browser game tabs do not
hold the launcher process open. Builds are unsigned and may trigger reputation
warnings. Public releases need signing and clean-machine installer testing;
GitHub Actions provides a build artifact, not a signed release.

## Unregister

Source installation:

```sh
python -m apps.client --unregister
```

Packaged installation, in PowerShell:

```powershell
& "$env:LOCALAPPDATA\2Block\2Block.exe" --unregister
Remove-Item -LiteralPath "$env:LOCALAPPDATA\2Block\2Block.exe"
```

You can then remove the empty directory. Linux removes the desktop entry; a
stale MIME preference may remain until the desktop cache refreshes. An older
handler is not restored automatically. Browser play keeps working without any
protocol registration.

## Checks

```sh
python -m unittest discover -s tests -v
node --test tests/test_3d.mjs
node --check apps/web/game/client.js
```

For manual acceptance, check both worlds in your browser: camera orbit and
zoom, jumping and landing, sprint speed, shared blocks in two tabs, build reach
and ownership, seven unique coin pickups, the flag checkpoint, lava/respawn,
wave animation, pause/resume, touch controls, and reconnect after stopping and
restarting the server. Also check the desktop prompt and installer on Windows.
Automated physics and matrix tests do not establish frame rate or visual quality.

## Troubleshooting

**Blank world / graphics error:** enable hardware acceleration and check that
your browser supports WebGL. Try a current Firefox, Edge, or Chrome. The game
shows a startup error if a WebGL context cannot be created.

**Cannot move:** click Let's play, close the game menu, and click the world to
focus it. A visible menu or hidden tab intentionally sends zero movement input.

**Connection lost after sleep:** click Reconnect, or return to the hub. Guest
sessions expire after 15 seconds without updates; browser background throttling
can cause this too.

**Can't place a block:** walk closer, choose a supported empty cell, and keep
spawn/checkpoints clear. The server rejects blocks inside a player and edits
more frequent than five per second. Only your own blocks can be removed.

**Port in use:** stop the other process using port 8765. The client deliberately
trusts only `http://127.0.0.1:8765`; changing ports requires changing both the
shared server constant and the server bind address.

**Desktop button does nothing:** re-register from the Python installation you
intend to keep, check the browser prompt, or use Play Now. Managed browser
policies can prohibit external protocols; the project cannot override them.
