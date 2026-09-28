# One-click wheel session

Use `C:\Users\13982\18649_team4\start.py` and `stop.py` directly.
The user selected Python scripts only, without .lnk shortcuts. The scripts
start child processes in the background without opening terminal windows.
On Windows, `pythonw start.py` or `pythonw stop.py` also avoids a launcher console.

**Start connects automatically.** Clamp the Logitech wheel, release the pedals,
raise the car's driven wheels for bench use and keep hands clear before starting.
Connection can give the Logitech wheel a short bump. Healthy Pi commands and a
centered wheel enable vehicle steering under the current firmware policy.

## What the scripts own

- `start.py` checks key-based SSH, starts the installed Pi bridge as a uniquely
  named user systemd service, then opens/connects the existing course wheel GUI.
  The GUI's Raw log and Current chart additions are preserved. Telemetry display
  still requires the corresponding telemetry-capable bridge deployed to the Pi.
- G HUB is opened if not already running. The scripts never stop shared G HUB
  processes. No servo console, USB keepalive or firmware flash is performed.
- A second start reuses a healthy session. `python start.py --restart` explicitly
  stops/restarts the managed pair. Simultaneous launch/stop operations are locked.
- `stop.py` stops only the recorded GUI process tree, checking PID creation time,
  and its uniquely named Pi service. It leaves the Pi powered on and unrelated
  processes alone. Stop terminates the vehicle command stream; firmware link-loss
  behavior applies. It is not a hardware emergency-stop replacement.
- If startup fails, its GUI/service are stopped. If SSH is unavailable during
  stop, the GUI stops locally and session state is retained so stop can be retried.
- The launcher does not kill an independently started receiver to claim UDP 8000,
  deploy Pi files, install firmware or change wheel feedback settings.

Commands:

```text
python start.py
python start.py --restart
python stop.py
```

Overrides: `start.py --host <ssh-alias> --course-repo <course-folder>`.
`LOGITECH_WHEEL_REPO` also selects the course checkout. The session manager uses
portable Python/psutil APIs with platform-specific detached process options and
native OpenSSH. This project's supplied Logitech SDK GUI is for Windows; these
hardware/software prerequisites still apply on any other host platform.

## SSH and dependencies

This machine's `C:\Users\13982\.ssh\config` contains alias `wheelpi`, currently
`labuser@172.26.166.33`, with dedicated Ed25519 identity
`C:\Users\13982\.ssh\wheelpi_ed25519`. Only its public key was added to the Pi's
`~/.ssh/authorized_keys`; existing keys/password authentication were preserved.
The private key remains on this laptop and is not stored in the repository.

`ssh wheelpi` now logs in without a password. The launcher uses BatchMode and
strict host-key checking, so it fails rather than prompting or accepting a
changed host identity. If campus DHCP changes the Pi address, update the alias's
HostName after discovering the current address. Startup uses the actual SSH
connection addresses for UDP routing, not a hardcoded laptop IP.

For another configured machine:

1. Install `requirements-launcher.txt` into the Python that runs start/stop.
2. Set up and verify an SSH alias/key and known-host entry for the Pi.
3. Keep the course checkout beside the team checkout, or specify its path. Its
   `.venv` needs the course GUI dependencies. On Windows, install G HUB and keep
   the guide's 64-bit HWND wrapper fix.
4. The Pi needs systemd user services, Python/pyserial and the deployed bridge at
   `~/18649/part2/part2_bridge.py`. Deploy the matching `pi/*.py` files together;
   the bridge now imports `background_io.py` and `bridge_diagnostics.py` as well
   as the protocol/timing helpers. Start/stop intentionally do not overwrite it.

## Logs and verification

- Startup/stop errors and Python stack traces: `logs/session/launcher.log`.
- Current ownership and paths: `logs/session/state.json`.
- Per-run stdout/stderr/faulthandler: `logs/session/<session>/proxy.log`.
- GUI logs/native Python crash reports: `logs/wheel-gui/*.log` and `*.crash.txt`.
- Pi CSV and console/crash output: `~/18649/part2/logs/session-<session>.csv`
  and `.console.log`, also named in state.json. The systemd service stops all
  its children, sends SIGINT for normal CSV cleanup, then enforces a five-second
  stop timeout.

Verified on this laptop: passwordless native OpenSSH; automatic GUI/wheel SDK
connection; Pi reports LINK_OK with advancing sequences; repeated start creates
no duplicate; stop removes the owned parent/child processes and releases local
UDP 8001/8002 and Pi UDP 8000; Pythonw restarts without a console. Evidence is in
`logs/session/lifecycle-check.log`. The final session was left running as requested.
A Windows venv launcher PID differs from the real GUI PID; the readiness check
accepts only the launcher or its descendants, covered by a real-process regression.
