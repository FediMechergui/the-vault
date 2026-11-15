# Capture recovery — v0.1.3

The Vivo Y04 user reported that the camera preview appeared, but a slow take failed while the app stayed open. This is a capture failure, distinct from the automatic Android activity exit fixed in v0.1.2.

## Evidence

The running v0.1.1 PC server passed eight health requests in 13–48 ms. Its first blank-frame HTTPS/WebSocket/gRPC smoke test nevertheless returned `Vision service unavailable`. Direct checks of all three trackers then succeeded, followed by 20 successful frames over four new capture sessions (about 33–500 ms per frame on the PC). These probes used a temporary account, deleted afterward, and synthetic blank images in memory.

This reproduces an intermittent processing failure, but does **not** establish the exact exception behind that first failure or the phone's Wi-Fi timing. The old server discarded the RPC error category and the app used a generic message for unexpected errors. Model startup or a temporary processing delay remains a possible cause, not a proven diagnosis.

## Changes

- Give MediaPipe RPC processing up to 10 seconds instead of three. The first frame constructs a session's tracker.
- Show a waiting notice after four seconds and stop after 12 seconds without a frame/command reply. A reply during the grace period keeps the capture open.
- Clear temporary vision errors after tracking recovers. Keep quality errors visible until the user starts another take.
- Bound the WebSocket connection attempt and the complete API response, and distinguish timeout, transport, certificate and malformed-response failures.
- Close the camera and stream when capture fails, and handle cleanup errors. Start the socket close before waiting for the input subscription to cancel.
- Send safe vision error categories to the app and log the category in the PC terminal. Frame data and credentials are not logged.

The quality rules, required repetitions, liveness checks, MATLAB scores, certificate pinning and session lifetime are unchanged. Failed frames are not accepted as completed takes. There is no automatic replay of enrollment/scoring requests or resumption of an expired authentication session.

## Install

Install APK v0.1.3 over the existing app. For an existing server, use [the update instructions](../README.md#update-an-existing-pc-server). The patch changes only three gateway files and preserves the existing Python environment, models, MATLAB setup, pairing certificate, keys and database. Stop and restart the server to activate it.

The new app can still use a v0.1.1 or v0.1.2 server; install the server patch to receive the longer processing deadline and detailed error categories too.

## Validation and phone retest

Ten Flutter tests pass, including five capture-screen regressions with a simulated camera: a delayed frame recovers, a stalled frame stops safely, a temporary vision error clears, a delayed Start take reply recovers, and malformed tracking data is handled. A real local gRPC test accepts a 4.1-second reply that exceeded the old deadlines and checks safe error mapping. The Python suite totals 39 passing tests, including stream recovery after vision errors. See [the validation record](validation.md).

The Android build is [GitHub Actions run 43745668674](https://github.com/FediMechergui/the-vault/actions/runs/43745668674), app source `493b437`. It also runs the four Android discovery regressions from v0.1.2.

On the phone, open hand enrollment and wait for tracking to appear, then perform a take. A short delay should show the waiting notice and recover. If a take still fails, record its exact message and the corresponding PC terminal line. Retest after returning from the background using a fresh challenge. Physical Vivo capture success and mobile end-to-end latency remain unverified.
