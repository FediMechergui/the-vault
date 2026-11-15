# Capture recovery — 15 November 2026

Version v0.1.3 addresses short capture deadlines and temporary tracking errors. The running old server passed health checks but returned `Vision service unavailable` for its first synthetic blank frame; 20 subsequent frames over four sessions succeeded. The old error handling prevents identifying that first failure's exact exception. See [the evidence and changes](capture-recovery.md).

Local validation passed 39 Python tests (36 suite tests and three additional real gRPC transport tests), Flutter analysis and all 10 Flutter tests. Five new widget tests exercise the actual capture screen with a simulated camera and server: delayed frame and command replies, a stalled frame, tracking recovery and malformed messages. The transport test accepted a 4.1-second processing delay. These are controlled tests; the updated phone capture still needs a physical retest.

The APK build and four native discovery tests passed in [Actions run 43745668674](https://github.com/FediMechergui/the-vault/actions/runs/43745668674). The [test and live-probe record](capture-recovery-verification.json), [APK verification](apk-verification-v0.1.3.json), [updater checks](capture-updater-verification.json) and [23-page PDF checks](specification-v1.3-verification.json) are retained. The original signing certificate and 16 KB alignment are verified. Document edition 1.3 adds the capture behavior and current validation limits.

# Android startup fix — 15 November 2026

The original APK's compiled DEX confirmed that the eight-second discovery timer invoked `android.app.Activity.finish()`, closing the app without requiring a tap or a server connection. The completion helper has been renamed to `completeDiscovery`; see [the cause and update instructions](android-startup-fix.md).

The [v0.1.2 Android build](https://github.com/FediMechergui/the-vault/actions/runs/43740421634) passed Flutter analysis, the existing five Flutter tests and four native discovery regression tests on Robolectric's Android 14 framework. The native network-discovery service is mocked; its [test result record](android-discovery-regression-v0.1.2.json) is retained. Inspection of the signed APK confirmed that the discovery timer's screen-closing call is absent. Physical-phone startup, connection and gesture retesting remains necessary. APK signature, upgrade compatibility and alignment verification are recorded in [apk-verification-v0.1.2.json](apk-verification-v0.1.2.json).

Server v0.1.1 remains compatible. This patch does not change the MATLAB algorithms or claim new camera, biometric accuracy or performance results. The specification PDF stays at document edition 1.1; the Android change is recorded in the patch notes above.

# Validation update — 14 November 2026

Documentation release **v0.1.1** adds a revised 22-page French specification, an installation/configuration README and a physical-phone test guide. The PDF was rendered for visual review; checks confirmed all source text, 22 bookmarks, 21 contents links and text within page boundaries. Local guide links and documented launcher flags were checked. This documentation update reuses the signed **0.1.0 / build 1** APK with the same SHA-256; it does not claim new app or physical-phone test results.

- Real MATLAB R2026b started through Engine using the current OS user's activation. Both required toolbox preflight operations passed.
- All 3 MATLAB unit tests passed. Enrollment and 9 scoring comparisons (3 per layer) matched the Python reference within 1e-14 on synthetic fixtures. See [matlab-smoke.json](matlab-smoke.json).
- The local HTTPS gateway reports `matlab-engine`, `matlab: true`, release `2026b`. Real MediaPipe/gRPC blank-frame rejection and account deletion/revocation passed. This mode uses SQLite, in-memory sessions and local assets. See [matlab-stack-smoke.json](matlab-stack-smoke.json).
- 34 Python tests passed, including stable discovery identity, advertised certificate fingerprints and address updates. A first sandboxed invocation could not access pytest's temporary directory; the unrestricted run passed.
- Same-PC mDNS discovery found the service over the LAN address and verified that its advertised certificate fingerprint matched the TLS server. See [discovery-smoke.json](discovery-smoke.json). This is not proof of phone-side discovery.
- The actual Dart native HTTPS and WebSocket clients connected with the paired certificate and rejected an incorrect SHA-256 pin. Authenticated WebSocket startup passed, and the disposable account was deleted. See [native-tls-smoke.json](native-tls-smoke.json).
- With explicit user approval, Windows Firewall permits TCP 8443 and UDP 5353 on all profiles, restricted to `LocalSubnet`. Rule state, port filters and address filters were checked.
- Local Android builds were stopped after C: approached exhaustion and a concurrent Flutter process reported insufficient paging space. Only the stopped project's rebuildable Gradle cache was removed. The APK build was moved to GitHub Actions; no private signing key is sent to CI.
- GitHub Actions [run 43617144907](https://github.com/FediMechergui/the-vault/actions/runs/43617144907) passed Flutter analysis, the five Flutter tests and the universal release APK build. Its application source commit is `06ab088`.
- The downloaded APK was signed locally with the private project release key. Android `apksigner` verified the signature, and `zipalign` verified 16 KB alignment. The package targets Android 10+ and includes ARM64, ARMv7 and x86-64. Its SHA-256 and metadata are in [apk-verification.json](apk-verification.json). No physical phone installation is claimed.

The release adds a generic Android client with automatic LAN discovery, persistent server identity and certificate pinning. First pairing uses trust on first use on the local network. Physical Android discovery/capture, multi-session load, sustained streaming performance, FAR/EER and spoof studies remain outstanding. Runtime compilation and Docker-to-host bridge validation remain outstanding; host MATLAB source execution is now verified.

The record below is historical and describes the earlier state before MATLAB was installed successfully and the Android NDK became available.

---

# Validation record — 13 November 2026

## Completed checks

- Python: 32 tests passed. Covers signal comparison, enrollment repetition and
  quality gates, account consent, credential scope, ordered multi-layer unlocking,
  liveness, WebSocket pinch capture, replay rejection, lockout, absolute session
  expiry, and deletion revoking an active capture session.
- Host MATLAB configuration: discovery precedence, partial-install rejection,
  explicit backend selection, use of the shipped Engine API, license-error
  behavior, toolbox preflight cleanup, and owned-session shutdown passed using
  explicitly identified Engine test doubles. No license checkout was fabricated.
- The real host HTTPS scorer rejected unauthenticated requests; the gateway client
  completed health, enrollment and scoring requests with the correct service key
  and certificate. This transport check used the Python reference algorithms.
- All three Compose overrides parsed successfully: host MATLAB, network-licensed
  container MATLAB, and compiled Runtime. Read-only detection on this PC reported
  no complete host MATLAB installation; strict MATLAB mode correctly failed.
- Flutter: static analysis passed; two tests passed for consent-gated enrollment
  and padded YUV camera conversion with portrait rotation. Analysis was repeated
  successfully after the camera shutdown fix.
- The final client analysis and release web build also passed after adding the
  configurable `VAULT_SERVER` default.
- Live Docker stack: all service health checks passed with PostgreSQL, Redis,
  MinIO and the **Python reference** scorer. A blank JPEG traversed HTTPS /
  WebSocket / gRPC and was correctly rejected. The disposable account was deleted
  and its credential rejected afterwards. See [stack-smoke.json](stack-smoke.json).
- Real MediaPipe models: public still-image fixtures produced 468 face, 33 body
  and 21 hand landmarks. Warm CPU inference medians were approximately 16, 24 and
  17 ms respectively. These are repeated still-image measurements, not measured
  mobile streaming FPS. See [vision-smoke.json](vision-smoke.json).
- Browser preview: Chrome rendered the compiled Flutter app without JavaScript
  errors and received a successful backend health response. The isolated test
  browser allowed the local development certificate; the separate live stack
  test verified TLS against the specific CA. See [web-smoke.json](web-smoke.json)
  and [web-preview.png](web-preview.png).
- MATLAB R2025b, Compiler, Compiler SDK and the two required toolboxes installed
  successfully in `vault-matlab-compiler:r2025b`. Installed files were checked.

## Pending evidence

Real host MATLAB license checkout, MATLAB algorithm tests, compilation, Runtime
integration and numerical parity remain unverified. Desktop Engine mode now uses
the existing OS user's MATLAB activation and does not require Compiler SDK.
Online Basic alone still does not provide that local desktop activation. The
currently running stack truthfully reports `python-reference`, `matlab: false`.

An additional Docker-to-host HTTPS check could not finish: `docker run` timed
out after 45 seconds while C: reported zero free bytes. Removal of the temporary
`vault-host-check-74cbcfcc` container also timed out; it was created with `--rm`
and contains only a public certificate mount and a disposable test credential.
The host test scorer was stopped. Once Docker is responsive, remove that named
test container if it remains, and rerun the bridge check. Compose validation and
same-host HTTPS tests do not establish successful Docker-to-host connectivity.

The Android APK build encountered insufficient C: drive space while extracting
NDK 28.2. An attempted cache relocation and NDK installation on D: were stopped
after Windows reported `HealthStatus: Warning` and `OperationalStatus: Full
Repair Needed` for that volume. No APK was produced. Some disposable cache and
partial installer files remain in `D:\the-vault-tools`; source files remain on C:.
The interrupted Gradle cache and downloaded distribution on C: were cleared to
recover space. They will be downloaded again by the project wrapper when needed.
APK installation and a physical face/body/hand enrollment and unlock still need
device validation. Sustained FPS, end-to-end latency, volunteer FAR/EER, spoof
resistance and the demonstration video remain outstanding. See
[acceptance.md](acceptance.md) for the evaluation protocol.
