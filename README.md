# THE VAULT

**Maximum security. Minimum secret.** Your face, a secret dance and a signature drawn in the air unlock one meme: **MECHNI FEHEM HATA CHY**.

This repository contains the Android app, the PC server, real MediaPipe tracking, MATLAB scoring, setup tools, the original specification and the revised specification. It is a local biometric demonstration. See the [test guide](TESTING.md) before treating a successful build as a successful phone demonstration.

## Download the right files

**[Release v0.1.2 — Android startup fix](https://github.com/FediMechergui/the-vault/releases/tag/v0.1.2)** contains:

| Download | Put it on | What it does |
| --- | --- | --- |
| [Android APK](https://github.com/FediMechergui/the-vault/releases/download/v0.1.2/the-vault-v0.1.2.apk) | Your Android phone | Installable, signed app; about 52 MB; Android 10+; fixes the automatic exit after discovery |
| [Server and complete source ZIP](https://github.com/FediMechergui/the-vault/releases/download/v0.1.2/the-vault-server-v0.1.2.zip) | Your PC | Services, MATLAB functions, setup scripts and all documentation |
| [Revised specification PDF](docs/THE_VAULT_Cahier_des_charges_v1.1.pdf) | Either device | French specification reflecting the implementation, changes and remaining acceptance work |
| [Testing guide](TESTING.md) | Either device | Simple steps, expected results, troubleshooting and a result checklist |
| `SHA256SUMS.txt` in the release | Optional verification | Hashes of the attached files |

The Android application is **v0.1.2, build 2**. Update the APK if you have v0.1.0: its eight-second discovery timer accidentally called Android's screen-closing method. The corrected APK is compatible with the **v0.1.1 server**, so an existing server installation can stay in place. Install the update over the old APK to preserve the app's saved pairing and credentials.

The revised specification remains **document edition 1.1**, describing the earlier baseline. This small Android patch is recorded separately in [the startup-fix notes](docs/android-startup-fix.md); the server architecture and MATLAB algorithms are unchanged.

## Before you start

| Requirement | Details |
| --- | --- |
| Phone | Android 10 or newer, front camera, permission to install the APK and use the camera |
| PC | The Windows instructions below are the verified path. macOS/Linux commands are included later but have not been validated on those platforms. |
| MATLAB | Complete desktop installation, activated for the same OS user who starts THE VAULT |
| Toolboxes | **Signal Processing Toolbox** and **Statistics and Machine Learning Toolbox** |
| Network | Phone and PC on the same reachable private IPv4 LAN; multicast/mDNS must be allowed. A PC on Ethernet and phone on Wi-Fi can work if the router bridges them. |
| Internet | Needed for the first downloads, updates, and whenever your MATLAB activation requires it. Camera processing runs on the PC. |
| Resources | The original plan recommends 16 GB RAM and four CPU cores. Leave several GB free for setup; MATLAB, Docker and local APK builds need additional space. These are planning recommendations, not a measured minimum. |

**You do not need Docker, Flutter, Android Studio or Compiler SDK to use the downloaded APK with the local server.** Setup installs a separate Python 3.11 environment. MATLAB Online Basic and MATLAB Runtime alone cannot run the desktop Engine mode.

## Windows: install once

### 1. Check MATLAB

Open desktop MATLAB normally as your own Windows user. Complete its activation if requested. In its Command Window, run:

```matlab
matlabroot
ver
```

Keep the path printed by `matlabroot` if installation discovery later needs help. Confirm the two toolboxes above are installed. A toolbox listed by `ver` is not proof of a licence checkout: THE VAULT executes actual toolbox operations at startup and reports any failure.

### 2. Install uv

Open a normal PowerShell window:

```powershell
winget install --id astral-sh.uv --exact
```

Close and reopen PowerShell, then run `uv --version`. If `winget` is unavailable, use an installation method from the [official uv guide](https://docs.astral.sh/uv/getting-started/installation/). Skip installation if `uv --version` already succeeds.

### 3. Extract the server and install its dependencies

Download the server ZIP above. Use **Extract All**; do not run the program inside the ZIP. Open the extracted `the-vault` folder, right-click empty space, and choose **Open in Terminal**. Use a folder where you have write permission.

Check that you are in the right folder:

```powershell
Get-Item README.md, scripts/setup.ps1
```

Then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1
```

This creates `.venv`, installs Python dependencies, downloads the official MediaPipe models, generates protobuf bindings, and creates unique local credentials and a TLS certificate. It does not install or activate MATLAB. It preserves existing credentials. The final message begins **Setup complete**.

Git users can obtain the same source with `git clone https://github.com/FediMechergui/the-vault.git`, then `cd the-vault`. Git is not needed when using the ZIP.

### 4. Allow local connections through Windows Firewall

Open **PowerShell as Administrator**, change to the same extracted folder, and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/enable-lan.ps1
```

This adds two inbound rules: **TCP 8443** for the app and **UDP 5353** for discovery. They apply to all Windows network profiles, including Public, but the remote-address scope is **LocalSubnet**. They do not enable access from arbitrary Internet addresses or automatically route discovery between subnets. Do not configure router port forwarding.

Close the Administrator window. Run the server from a normal PowerShell using the Windows account with the MATLAB activation.

## Start, verify and connect

### 5. Start the PC server

From the project folder:

```powershell
.venv/Scripts/python.exe scripts/start.py --local --backend matlab-engine
```

For subsequent launches, you can double-click **Start THE VAULT.cmd**. Keep its terminal open. It starts a private MATLAB session and the API/vision services. Expect startup output including:

```text
THE VAULT scoring: matlab-engine
THE VAULT is running. Keep this terminal open...
Phone discovery ready: <your computer> at <local address>:8443
```

The discovery line confirms advertisement, not complete dependency health. In a second normal PowerShell in the same folder, verify readiness:

```powershell
curl.exe --cacert infra/certs/server.pem https://localhost:8443/api/v1/health
```

Check for `ready: true` and, under `services.scoring`, `engine: "matlab-engine"` and `matlab: true`. The release and `license_source: "current-user"` are also reported. If MATLAB is detected but activation or a toolbox operation fails, the launcher exits with an error; it does not quietly substitute Python.

### 6. Install the APK and pair the phone

1. On the phone, open the APK download. If Android asks, allow that browser/file manager to install this app.
2. Connect the phone to the same local Wi-Fi as the PC. Avoid guest networks with client isolation.
3. Open THE VAULT. Allow several seconds for discovery. A single available server is selected automatically.
4. If several servers exist, or the server was still starting, open **Settings → Find my computer** and select yours. The computer name comes from its hostname.
5. Start with the [hand-only test](TESTING.md#2-first-unlock-hand-only), then add face and body.

No IP typing, licence copying, or APK rebuilding is required for the normal discovery flow. The app remembers the computer and its certificate, and can rediscover a changed LAN address. Discovery is implemented for native Android; a browser preview does not perform this Android discovery flow.

### Stop or restart

Press **Ctrl+C** in the launcher terminal to stop the local services and release THE VAULT's private MATLAB session. Use the same start command next time. Do not start two launchers on the same ports. In Docker mode, Ctrl+C stops host scoring/discovery; stop the containers separately with `docker compose stop`.

## Configuration you may need

| Need | Command or action |
| --- | --- |
| See the selected MATLAB installation without starting services | `.venv/Scripts/python.exe scripts/start.py --check` — `license_checked: false` is expected for this read-only check |
| Specify a custom MATLAB folder | Add `--matlab-root "D:/MATLAB/R2026b"` to your normal start command; use your own `matlabroot` path |
| Allow a slower MATLAB startup | Add `--startup-timeout 300` |
| Use a different local gateway port | Add `--port 8444` with `--local`; also configure a local-subnet firewall rule for that TCP port. Discovery advertises the selected port. The supplied firewall helper remains fixed to 8443. |
| Deliberately try Python scoring | `.venv/Scripts/python.exe scripts/start.py --local --backend python-reference`; health will say `matlab: false` |
| Let the launcher choose a backend | Use `--backend auto`; it chooses Python only if no complete MATLAB installation is found. |
| Change selected layers/order | Use the app's ritual screen, enroll the selected layers and save the sequence |
| See landmarks, timing and previous scores | Long-press the logo, or enable Demonstration mode in Settings |

MATLAB discovery checks an explicit path/`MATLAB_ROOT`, `PATH`, the Windows registry, and standard Windows/macOS/Linux installation folders. Multiple standard installations are considered newest first. The launcher uses the Engine API supplied with the selected installation, not an arbitrary latest PyPI version. Python architecture and release compatibility still matter: see [MathWorks Engine setup](https://www.mathworks.com/help/matlab/matlab_external/install-the-matlab-engine-for-python.html) and its [Python compatibility table](https://www.mathworks.com/support/requirements/python-compatibility.html).

## What stays private on the PC

| File or folder | Purpose | Keep when upgrading/moving the existing server? |
| --- | --- | --- |
| `.env` | JWT signing, template encryption, admin and optional database/storage credentials | Yes; losing `TEMPLATE_KEY` makes stored templates unreadable |
| `.local/server-id` | Stable identity remembered by the Android app | Yes |
| `infra/certs/server.pem` and `server-key.pem` | Gateway certificate and private key | Yes; replacing the certificate changes the app's pin |
| `.local/vault.db` and related local data | Local accounts, encrypted templates and logs | Yes, if retaining accounts; stop services before backup |
| `.local/scoring-certs/` | Separate certificate for host scoring | Keep with the private server backup |
| Docker named volumes | PostgreSQL and MinIO data in Docker mode | Back up separately if using that mode |

These are private operational files; do not upload them with the public source. Make any backup private, with the server stopped. Do not regenerate credentials or certificates merely to fix discovery. Deleting app storage does not delete the server's account or biometric templates.

The first pairing trusts the server advertised on the LAN. Pair on a network you trust. Afterward, the app pins the server's SHA-256 certificate fingerprint for HTTPS and WebSockets. A different pin is refused. Default gateway certificates last one year; certificate rotation requires planning for re-pairing because the existing pin will stop matching.

Before moving to a different server, use **Delete all my data** while the original server is reachable. Account recovery is not implemented. If you intentionally start over with a new identity, Android app-storage reset creates a fresh client setup and loses its management credential; it is not a backup or recovery mechanism.

## Troubleshooting

| What you see | What to do |
| --- | --- |
| `uv` is not recognized | Reopen PowerShell after installation; check `uv --version`. |
| Setup file not found | Extract the ZIP and enter the inner `the-vault` folder containing `README.md` and `scripts`. |
| `No complete desktop MATLAB installation` | Open desktop MATLAB; use its `matlabroot` as `--matlab-root`. Runtime/Online alone will not satisfy this mode. |
| MATLAB licence/toolbox preflight error | Open MATLAB as the same OS user; resolve activation and confirm both required toolboxes. Keep the specific terminal error for diagnosis. |
| Engine API installation/import failure | Check Python 3.11/release/64-bit compatibility and installation-folder permissions using the MathWorks links above. |
| Phone finds no computer | Check health first, keep the launcher open, join the same LAN, enable the two firewall rules and tap Find my computer. Guest isolation, VPN routing, multicast filtering or a second active interface may interfere. The current discovery implementation prefers the PC's default private IPv4 route. |
| Computer found but still starting | Wait for `ready: true`, then retry discovery. |
| Certificate/identity changed | Restore the original private server identity/certificate if this was accidental. Do not turn off TLS checks. Intentional replacement requires a fresh pairing/account plan. |
| Port already in use | Stop the earlier THE VAULT launcher; do not start local and Docker gateways together on 8443. |
| Camera unavailable/black | Grant camera permission after consent, close other camera apps and retry. Use a physical phone for the real gesture test. |
| Tracking/quality error | Improve lighting, reduce occlusion, stay in frame and retry that take. For body, include hands and feet. |
| Hand drawing does not start | Open hand first; pinch, release to draw, then pinch again before the timeout. |
| Enrollment repetitions too different | Use a simpler motion and consistent tempo; record that layer again. |
| Locked for five minutes | Three completed mismatches caused lockout; wait five minutes. Low-quality captures are retries, not matching failures. |
| Android says app not installed | Check Android 10+ and the download hash. An older copy signed with another key must be uninstalled before this signed APK; that loses its device credential. |
| Low disk/memory while building | Use the release APK. Flutter, Gradle, Android SDK and NDK are only needed by developers building the client. |

## Optional: macOS and Linux server

The host-discovery code supports standard locations on these platforms; licensed execution and phone connectivity have only been verified on Windows so far. Use a Python/MATLAB architecture combination supported by MathWorks.

From the extracted project folder, with uv installed:

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt -r vision-py/requirements.txt
.venv/bin/python scripts/bootstrap.py --models
.venv/bin/python scripts/start.py --local --backend matlab-engine
```

Allow incoming TCP 8443 and UDP 5353 from the intended local subnets using your OS firewall. `scripts/enable-lan.ps1` is Windows-only. The Android APK remains the phone client.

## Optional: Docker infrastructure and MATLAB Runtime

The local quick-start uses **SQLite + in-memory sessions + local media**. To use **PostgreSQL + Redis + MinIO**, install Docker with Linux containers, complete normal host setup, stop the local launcher and run:

```powershell
.venv/Scripts/python.exe scripts/start.py --backend matlab-engine
```

MATLAB still runs on the PC under its existing activation. Docker reaches its authenticated HTTPS scorer at port 9910. That Docker-to-host bridge has not yet been verified end to end. Follow [MATLAB setup](docs/matlab.md) for network-licensed container MATLAB and compiled Runtime alternatives.

Direct `docker compose up -d --build` uses the Python reference and does not perform host MATLAB detection or publish host mDNS discovery. The Runtime option needs a Linux Compiler SDK build; no compiled Runtime package is attached. The original PDF's Python fallback remains available.

## Optional: administration and building the app

Admin routes use the local `ADMIN_KEY` in `X-Admin-Key`. They support the acceptance score floor (0.80–0.99), PNG meme replacement, attempt-log reading and purging. There is no admin GUI or configurable fusion-weight editor. Use [the API protocol](docs/protocol.md); do not put the admin key in the phone app or public reports.

To build Android yourself: Flutter **3.50.0 / Dart 3.14**, tested revision `ab2912035e160d9cad6306df307576da6128ebdb`, Android SDK 36, NDK 28.2.13676358, and a compatible JDK/Gradle toolchain are required. The reproducible runner configuration is [.github/workflows/android.yml](.github/workflows/android.yml).

```powershell
cd mobile
flutter pub get
flutter analyze
flutter test
flutter build apk --release
```

Output: `mobile/build/app/outputs/flutter-apk/app-release.apk`. A private `mobile/android/key.properties` configures release signing; without it, local builds use the Android development key. Published APKs were signed with the project's private release key. Never share that key or its properties. No fixed server address or bundled PC certificate is required.

## Project structure and evidence

| Path | Contents |
| --- | --- |
| `mobile/` | Flutter app, Android discovery bridge, camera encoding and tests |
| `gateway/` | FastAPI, sessions, accounts, encrypted templates and media |
| `vision-py/` | Real MediaPipe face/body/hand models and gRPC service |
| `matlab-engine/` | MATLAB algorithms, Engine/Runtime wrapper and compiler tools |
| `vault_core/` | Python reference signal processing and scoring |
| `scripts/` | Setup, launcher, discovery, firewall, evaluation and validation |
| `docs/` | Revised PDF, specification source, protocol and recorded evidence |
| `tests/` | Automated Python correctness/integration tests |

Recorded checks: **34 Python tests, five Flutter tests, three real MATLAB tests, nine synthetic MATLAB/Python score comparisons**, native client certificate pinning, same-PC discovery, and APK signature/alignment verification. Physical-phone discovery/capture, sustained FPS, volunteer FAR/EER and spoof resistance are not established by those checks.

Read [TESTING.md](TESTING.md) for the practical test sequence, [validation.md](docs/validation.md) for evidence, and [acceptance.md](docs/acceptance.md) for the original study targets. The new PDF distinguishes implementation, verification and unfinished requirements. Its editable source and build command are in [docs/specification/README.md](docs/specification/README.md).
