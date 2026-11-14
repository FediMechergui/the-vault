# THE VAULT

**Maximum security. Minimum secret.** Your face, your secret dance, and a signature drawn in the air unlock one image: **MECHNI FEHEM HATA CHY**.

Built from all 18 pages of `The_Vaulte_Cahier_des_charges.pdf`. This is a local biometric demonstration, not certified authentication for real secrets.

## Try it on your own network

Download the APK and server/source ZIP from [GitHub Releases](https://github.com/FediMechergui/the-vault/releases). The same APK works with different PCs: it discovers THE VAULT on the local network, remembers the selected computer, and follows changes to its IP address. No IP address or PC-specific certificate needs to be compiled into the APK.

**v0.1.0:** [Android APK](https://github.com/FediMechergui/the-vault/releases/download/v0.1.0/the-vault-v0.1.0.apk) · [Server and complete source](https://github.com/FediMechergui/the-vault/releases/download/v0.1.0/the-vault-server-v0.1.0.zip). The universal APK is about 52 MB, signed and verified for Android 10+.

You need Android 10+, a front camera, and a PC on the same Wi-Fi. The PC needs an activated desktop MATLAB installation with **Signal Processing Toolbox** and **Statistics and Machine Learning Toolbox**. It uses the current OS user's activation. **Compiler SDK and Docker are not required for the quick-start mode.** MATLAB Online Basic alone is not a desktop activation.

### Windows setup — once

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if it is not already installed:

```powershell
winget install --id astral-sh.uv --exact
```

Open a new PowerShell. Download/extract the server ZIP and enter its folder, or clone the repository:

```powershell
git clone https://github.com/FediMechergui/the-vault.git
cd the-vault
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1
```

Setup creates a Python 3.11 environment, installs the services, downloads the official MediaPipe models, and generates unique local credentials and a TLS certificate. It does not replace existing credentials or install MATLAB.

For Windows Firewall, run this once from an **Administrator PowerShell** in the project folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/enable-lan.ps1
```

The rules allow TCP 8443 and UDP 5353 from **directly connected local subnets**, on all Windows network profiles. This supports moving the server between local networks, including networks Windows labels Public. Do not expose these ports through your router. Guest Wi-Fi or access-point isolation can prevent local devices discovering each other.

### Start and connect

```powershell
.venv/Scripts/python.exe scripts/start.py --local --backend matlab-engine
```

Or double-click **Start THE VAULT.cmd**. Keep its terminal open. Wait for `Phone discovery ready`, then install/open the APK on your phone. A single available server is selected automatically. If several computers are running THE VAULT, select yours in **Settings → Find my computer**. Use that button to retry if the server was still starting.

The first connection trusts the server discovered on your local network; pair for the first time on a network you trust. Its SHA-256 certificate fingerprint is then pinned in secure storage for both HTTPS and WebSockets. A changed certificate or different computer cannot silently receive saved account credentials. Keep `.local/server-id` and `infra/certs` when moving your existing server. Changing its identity requires explicit re-pairing through a fresh app/account setup.

For a nonstandard MATLAB installation:

```powershell
.venv/Scripts/python.exe scripts/start.py --local --backend matlab-engine --matlab-root "D:/MATLAB/R2026b"
```

The local mode uses SQLite, temporary in-memory sessions and local meme storage. It still runs real MediaPipe and MATLAB. On macOS/Linux, use `uv venv --python 3.11 .venv`, `uv pip install --python .venv/bin/python -r requirements.txt -r vision-py/requirements.txt`, `.venv/bin/python scripts/bootstrap.py --models`, then `.venv/bin/python scripts/start.py --local --backend matlab-engine`. Host discovery includes standard Windows/macOS/Linux MATLAB locations; licensed execution has been verified on Windows R2026b.

## First unlock

1. Create a pseudonym and explicitly consent before the camera starts.
2. Choose and order one to three layers.
3. Enroll face twice: repeat two distinct expressions in the same order.
4. Enroll body three times: prop up the phone, include hands and feet, and repeat a 3–6 second movement.
5. Enroll hand five times: show an open hand, pinch and release, trace with your index, then pinch again.
6. Save the sequence and open the vault. Face authentication adds a random blink/head-turn challenge. Randomized mode shuffles the three layers and adds another challenge.
7. Reveal the meme and the explicitly fictional transparency dashboard.

Long-press the logo for live landmarks, timing and scores. No demo mode bypasses recognition. **Delete all my data** removes the account, templates and attempts. Accounts are local to the paired phone and server; account recovery is not implemented.

## What is implemented

- Flutter Android client: camera stream, consent, enrollment, configurable challenges, guided overlays, pinch-controlled trail, vault animation and transparency screen.
- FastAPI: HTTPS/WebSocket orchestration, authenticated sessions, three-failure/five-minute lockout, 15-minute vault JWTs, administration and short-lived media tickets.
- Real MediaPipe Tasks over gRPC: 468 face landmarks and 52 blendshapes, 33 body landmarks, 21 hand landmarks. Live gesture labels use geometric/blendshape rules; personal motions use temporal template matching.
- MATLAB and Python scoring: Savitzky–Golay smoothing, resampling, 10% windowed DTW, non-reflecting Procrustes, bounded enrollment thresholds and AND gating. Final fusion is currently calculated by the Python gateway.
- AES-256-GCM templates, no persisted camera frames, transient capture sessions, and automatic 30-day attempt-log deletion.
- mDNS discovery using `_thevault._tcp.local.` and native Android network service discovery. The desktop advertises public identity and certificate fingerprint only.

## Docker architecture

For PostgreSQL, Redis and MinIO instead of the quick-start storage, install Docker Desktop with Linux containers and run:

```powershell
.venv/Scripts/python.exe scripts/start.py --backend matlab-engine
```

The gateway connects to the host MATLAB scorer over authenticated HTTPS on 9910. Keep the launcher open for MATLAB and LAN discovery. Direct `docker compose up -d --build` uses the explicit Python reference and does not advertise the host to phones or detect desktop MATLAB.

Network-licensed MATLAB in Docker and compiled MATLAB Runtime remain optional. Runtime compilation requires Compiler SDK once on Linux; no compiled Runtime package is included in this release. See [MATLAB setup](docs/matlab.md). MinIO is built from its pinned upstream source with its AGPL licence retained.

## Build the Android client

The source uses Flutter **3.50.0 / Dart 3.14**, Android SDK 36, NDK 28.2.13676358 and the standalone `material_ui` package. The tested Flutter revision is `ab2912035e160d9cad6306df307576da6128ebdb`.

```powershell
cd mobile
flutter pub get
flutter analyze
flutter test
flutter build apk --release
```

The universal APK is `mobile/build/app/outputs/flutter-apk/app-release.apk`. Published APKs use a private release signing key. Create `mobile/android/key.properties` with `storeFile`, `storePassword`, `keyAlias` and `keyPassword` to sign your own releases. Without it, local builds use the Android development key. Never publish the keystore or key properties. No `VAULT_SERVER` override or bundled server certificate is needed for discovery.

## Validation and limits

Real Windows MATLAB R2026b startup and toolbox operations, all three MATLAB unit tests, and nine synthetic face/body/hand scoring comparisons against Python passed. Maximum numerical difference in those fixtures was below 1e-14. See [MATLAB evidence](docs/matlab-smoke.json).

HTTPS/WebSocket/gRPC integration passed with the MATLAB-backed local stack. The blank test frame was correctly rejected. Same-PC mDNS discovery and verification of the advertised TLS fingerprint passed. These are not a physical Android-camera or biometric accuracy study. See [validation](docs/validation.md) and the [acceptance protocol](docs/acceptance.md).

```powershell
.venv/Scripts/python.exe -m pytest
.venv/Scripts/python.exe scripts/verify_matlab.py
curl.exe --cacert infra/certs/server.pem https://localhost:8443/api/v1/health
```

Physical-device discovery/capture, sustained 15 FPS, end-to-end latency, volunteer FAR/EER, spoof resistance and the demonstration video still require field validation. MATLAB Runtime compilation and the Docker-to-host bridge have not yet been verified. The APK is for trying the project, not evidence that all PDF acceptance targets have been achieved.

## Source and private files

`mobile/` contains Flutter/Android; `gateway/` the API; `vision-py/` MediaPipe; `matlab-engine/` MATLAB and its wrappers; `vault_core/` Python algorithms; `scripts/` setup/discovery/validation; and `docs/` the protocol and evidence. The original PDF and the supplied captioned meme are included.

`.env`, private certificate keys, `.local`, databases, MATLAB activations, SDK installations and Android signing keys are excluded from Git and release source archives. Models are downloaded from official URLs during setup. Do not share those private files.

Admin endpoints require the local `ADMIN_KEY` in `X-Admin-Key`. API details: [protocol](docs/protocol.md). Admin capabilities include the score floor, meme replacement, attempt logs and purging; there is no admin dashboard.
