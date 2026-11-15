# Android startup exit — v0.1.2

APK v0.1.0 closed automatically about eight seconds after launch, even without selecting a computer. The v0.1.1 documentation release contained the same affected APK.

## Confirmed cause

`MainActivity` declared a discovery helper named `finish(error: String? = null)`. The discovery deadline invoked `finish()` without an argument. Kotlin selected the inherited zero-argument `Activity.finish()` method, which closes the screen, instead of the helper that should return the discovered servers.

Inspection of the **published v0.1.0 APK's DEX bytecode** confirmed an `android.app.Activity.finish:()V` invocation in the generation-guarded discovery timer callback. This was an explicit activity close, so an Android fatal-exception log was not required to establish the cause.

The helper and all its call sites now use the unambiguous name `completeDiscovery`. The timer returns the discovery result and keeps the activity open. Automatic LAN discovery, certificate pinning and account credentials retain their existing behavior.

## Update

Install **the-vault-v0.1.2.apk**, application version 0.1.2 / build 2, over the existing signed release. Server v0.1.1 is compatible; no MATLAB or server reinstallation is needed. The original signing certificate is retained so Android can preserve app data during the update.

The unchanged server may still report a readiness or pairing error. Those errors should appear inside the app and must not close it.

## Regression coverage

`MainActivityDiscoveryTest` exercises the actual Kotlin activity with Robolectric's Android 14 main looper and a mocked network-discovery service. It checks:

- An empty search completes after the deadline, replies once and leaves the activity open.
- A resolved computer's address, name, port and certificate fingerprint reach Flutter.
- A second discovery can complete after the first timeout.
- A discovery-start failure returns an error without closing the activity.

The Android workflow builds the release APK and runs these native tests with `:app:testReleaseUnitTest`, in addition to Flutter analysis and the existing five Flutter tests. Network responses are mocked in the native tests; these checks do not establish physical-phone network or camera performance.

Build and test record: [GitHub Actions run 43740421634](https://github.com/FediMechergui/the-vault/actions/runs/43740421634), application source commit `4b69c57`. All four native tests passed with no errors, failures or skipped tests. The workflow exposes its native XML/HTML test report as an artifact; the [retained result record](android-discovery-regression-v0.1.2.json) lists each test.

Inspection of the signed v0.1.2 APK also confirmed that the discovery timer's `Activity.finish()` invocation is absent. [APK verification](apk-verification-v0.1.2.json) records its hash, package version, matching release certificate and 16 KB alignment check.

## Phone retest

Leave the updated app open for at least 30 seconds without touching it. Repeat with the server unavailable, then start the server and use Find my computer twice. The app must stay open and return a result or connection guidance. Continue with the [hand-only enrollment test](../TESTING.md#2-first-unlock-hand-only).

The original and revised specifications remain historical documents. This patch changes Android discovery completion only; the MATLAB algorithms, server protocol, biometric study requirements and previously recorded validation limits remain unchanged.
