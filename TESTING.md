# THE VAULT — simple testing guide

Use this after the [installation steps](README.md#windows-install-once). Start with one layer so a camera, connection or gesture problem is easy to locate. Add the other layers after that succeeds.

**Use a disposable test account.** The final cleanup test deletes it. Do not use an existing account you want to keep. Expected results below are checks to perform, not a claim that these physical-phone tests have already passed.

## 1. Check the server and phone connection

For slow or interrupted takes, install **APK v0.1.3** and apply the [PC capture patch](README.md#update-an-existing-pc-server). A four-second delay now shows a waiting notice; a response within 12 seconds can recover. If no reply arrives, the capture stops with a specific message. Start a fresh take after a stopped session. The server reports `vision_timeout`, `vision_frame` or `vision_unavailable` in its terminal; note that category and the phone's exact message if a take still fails. See [capture recovery](docs/capture-recovery.md) for the reproduced failure and validation limits.

Use **APK v0.1.2 or newer**. The original v0.1.0 APK closed its Android activity at the end of the eight-second discovery timer. The v0.1.1 release also bundled that old APK. Update the phone app; server v0.1.1 remains compatible.

For the startup regression, leave the app open without tapping anything for **30 seconds**. It must stay open with the server available and with the server stopped. Start the server again, then run **Find my computer** twice; each search must finish without closing the app. A missing server should produce guidance, not an automatic exit. This is a physical-phone check to perform, not a claim that your phone has already passed it.

1. Open desktop MATLAB as the same user who will start the server. Resolve any activation dialog.
2. In the project folder, start:

```powershell
.venv/Scripts/python.exe scripts/start.py --local --backend matlab-engine
```

3. Leave that window open. In a second PowerShell in the same folder:

```powershell
curl.exe --cacert infra/certs/server.pem https://localhost:8443/api/v1/health
```

**Pass:** `ready` is `true`; `services.scoring.engine` is `matlab-engine`; `services.scoring.matlab` is `true`. A standalone `--check` is installation discovery only and does not prove licence availability.

4. Put the phone on the same LAN. Open the APK; allow several seconds for discovery. If needed, use **Settings → Find my computer**. If multiple PCs appear, select yours.

**Pass:** the app connects to the expected computer without entering its IP address. If it cannot connect, follow the README troubleshooting table before attempting enrollment.

## 2. First unlock: hand only

1. Tap **Create your vault**, choose a test pseudonym and tick the consent checkbox. Do not proceed with real biometric capture until you consent.
2. On the ritual screen, turn **Face** and **Body** off, leaving **Hand** selected. Keep randomized mode off.
3. Tap **Record this layer** for Hand. Allow Android camera permission when requested.
4. Hold one open hand in good light, within the camera frame. Wait for clear tracking.
5. Start the take and follow the three-second countdown.
6. Pinch thumb and index together; release to begin drawing. Trace a simple, distinctive pattern with the index fingertip. Pinch again to finish. Complete it before the capture timeout.
7. Repeat the same pattern **five times**, using similar size, orientation and speed. Follow any quality-retry instructions.
8. Return to the ritual screen, confirm Hand shows as recorded, and tap **Save my ritual**.
9. Return home, tap **Open my vault**, and repeat the enrolled hand pattern.

**Pass:** a tracked trail follows the finger, all five enrollment repetitions are required, the matching attempt succeeds, and the captioned meme appears. The transparency screen clearly labels its counters as fictional.

If enrollment is too variable, simplify the pattern and record it again. A quality error is not a successful recognition, and the meme must not appear merely because the capture timer ended.

## 3. Add the face layer

1. Open the ritual screen and enable **Face** alongside Hand.
2. Choose two distinct expressions you can repeat comfortably. Perform them in the same order during each of **two** enrollment takes. Face capture is approximately 3.8 seconds.
3. Save the ritual with Face before Hand.
4. Open the vault. First complete the random liveness instruction: blink twice, or face forward and turn in the requested direction.
5. After that check passes, perform the two secret expressions, then the hand pattern.

**Pass:** the app requires liveness before secret-expression authentication, presents the layers in the saved order, and reveals the meme only after both pass.

The current expression validator checks sufficient movement and compares the temporal signal; it does not explicitly count two distinct expressions. Basic liveness is not certified replay protection.

## 4. Add the body layer and test all three

1. Enable Body. Put the phone on a stable support and step back until both hands and feet are visible.
2. Choose a short, comfortable movement sequence. Record it **three times**, taking roughly 3–6 seconds each time; the app's body capture target is 5 seconds.
3. Save **Face → Body → Hand**.
4. Open the vault and complete the liveness prompt, expressions, body movement and hand signature in order.

**Pass:** each layer produces a verdict; the next challenge starts only after success; the vault opens only after all three pass. Record the total duration instead of assuming it meets the original 30-second target.

Repeat once with a different saved order. Then enable randomized mode with all three layers selected.

**Randomized-mode pass:** the three layers are shuffled, an extra randomly selected layer is added, and all scheduled challenges must succeed. An extra Face challenge also has a liveness requirement.

## 5. Check failures and lockout

Use the disposable account and a clearly tracked, intentionally different gesture. Keep the motion large/long enough to be a valid capture.

| Test | Expected result |
| --- | --- |
| Move the hand out of frame or obscure the camera | Quality guidance/retry; no unlock |
| Perform a different but valid gesture | Failed match; no meme. If accepted, record this as a recognition failure to investigate. |
| Skip a required layer | No full-sequence unlock |
| Complete three failed matching attempts | Account locked for five minutes |
| Try again while locked | Lockout message; no bypass by starting a new auth session |
| Wait five minutes, then perform the correct sequence | Authentication becomes available again |

Low-quality captures do **not** count toward the three-match lockout. Do not report a successful lockout test unless the server actually returned three failed matches. Real-user acceptance/rejection rates need a separate study.

## 6. Check automatic reconnection

Cancel active captures before changing networks.

1. Close and reopen the app while the server stays running. It should reconnect to the paired computer.
2. Stop the server with Ctrl+C. The phone should report a connection problem instead of unlocking.
3. Restart the same project folder. Tap **Find my computer** if needed. The same account and enrolled layers should remain available in local storage.
4. Optional: move phone and PC together to another trusted LAN, or renew the PC's address. Preserve `.env`, `.local/server-id`, the database and `infra/certs`.

**Pass:** the paired computer is found at its new address without rebuilding the APK. This does not require an active capture to survive a network change. A guest network, VPN route or multicast filtering may prevent discovery.

Optional with two PCs: a new/unpaired app should offer a choice when multiple servers are found. An app already holding credentials must not silently transfer them to a different computer. Do not replace real certificates just to test pin rejection; automated/native-client evidence already covers incorrect-pin rejection.

## 7. Check diagnostics and deletion

1. Long-press the home logo, or enable Demonstration mode in Settings.
2. During a capture, check landmarks, gesture labels, sample count, round-trip latency and FPS. Decision scores appear after a scored challenge; they are not a continuous per-frame authentication score.
3. Note the observed values and phone/PC/network conditions. Do not equate the server's model inference time with full phone round-trip time.
4. After finishing the disposable-account tests, choose **Settings → Delete all my data**.

**Pass:** the account/templates/attempt logs are logically deleted, old credentials and active sessions stop working, and the app returns to account creation. This is not a claim about physical disk erasure or private backups. Uninstalling the app alone does not delete server-side data.

## 8. Optional automated checks

Run from the project folder. These commands test synthetic/reference behavior; they do not replace the physical steps above.

```powershell
.venv/Scripts/python.exe -m pytest
.venv/Scripts/python.exe scripts/verify_matlab.py
```

Expected recorded baseline: **34 Python tests**, **three MATLAB unit tests**, and **nine synthetic score comparisons**. The MATLAB verifier starts and closes its own Engine session and needs the actual desktop licence/toolboxes. Keep any output differences for diagnosis.

With the real server running, test HTTPS, a blank JPEG through WebSocket/gRPC, and deletion of a temporary non-biometric account:

```powershell
.venv/Scripts/python.exe scripts/smoke_stack.py --output .local/my-stack-smoke.json
```

**Pass:** health is ready, the blank image is rejected as insufficient quality, and the test credential is revoked after deletion. The blank frame is not a face/body/hand recognition test.

For developers with Flutter installed:

```powershell
cd mobile
flutter analyze
flutter test
```

Recorded baseline: clean analysis and **five tests**. The APK release also passed signature and 16 KB alignment verification. See [validation evidence](docs/validation.md).

## 9. Record your result

Copy this table into an issue or your own notes. Leave unperformed checks as **Not tested**.

| Check | Pass / Fail / Not tested | Observation |
| --- | --- | --- |
| Server health uses MATLAB | | |
| Phone discovers expected PC | | |
| Consent and camera permission | | |
| Hand: five repetitions and unlock | | |
| Face: two repetitions and liveness | | |
| Body: three repetitions | | |
| Full sequence and changed order | | |
| Randomized sequence plus extra layer | | |
| Wrong gesture / poor quality | | |
| Three failures / five-minute lockout | | |
| Restart / LAN-address change | | |
| Diagnostics and fictional dashboard | | |
| Account deletion | | |

Include: documentation release, APK version, Android version/model, PC OS, MATLAB release/toolboxes, local or Docker mode, selected layers, approximate FPS/latency, and the exact step that failed. Share relevant error text, not `.env`, licence details, private keys, database contents or participant images.

## 10. Formal acceptance comes later

The original targets remain **15 FPS/session**, **<300 ms frame round trip**, **<1 second scoring after capture**, **<30 seconds for a three-layer login**, **EER <10% per layer**, and **FAR <1% with three layers**. The volunteer, concurrency, spoof and usability study is described in [acceptance.md](docs/acceptance.md). Do not turn a few successful unlocks into an accuracy claim. Record actual observations, including failures.
