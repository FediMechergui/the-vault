# Acceptance and evaluation

Source: all 18 pages of the supplied cahier des charges, especially pages 5–8, 12–17. Automated correctness and biometric accuracy are separate questions.

| PDF requirement | Implementation | Verification still needed beyond automated tests |
| --- | --- | --- |
| EF-01/02: pseudonym + consent | Account API and consent screen; camera starts only inside enrollment/auth capture | Device permission flow |
| EF-03/04: 2/3/5 repetitions; reject variable templates | Server repetition gate; bounded pairwise mean + 2σ | Tune bounds using real repetitions |
| EF-05: layers/order | Select/reorder 1–3; randomized three + extra challenge | User comprehension |
| EF-06/10: real-time stream + diagnostics | Binary WebSocket, MediaPipe Tasks, live quality/landmarks, gesture labels, latency/FPS | Sustained 15 FPS and <300 ms on target phone/Wi-Fi |
| EF-07: per-layer verdict | Server-side scoring and capture-quality retries | Real genuine/impostor trials |
| EF-08: lockout | Three failed matches, five-minute lock | Tested with controlled scores |
| EF-09: JWT + meme | Full-sequence gate, 15-minute vault token, two-minute media ticket | Full physical three-layer run |
| EF-11: deletion | Account/templates/attempts/transient sessions deleted; JWTs recheck user | Storage/backups operational review if later deployed |
| EF-12: administration | Authenticated threshold, meme, log and purge API | Optional admin UI is not included |
| MATLAB cooperation | Automatic host discovery and existing-user licensing through Engine; authenticated HTTPS host bridge; optional network-license and compiled Runtime Docker paths | Real licensed host execution, MATLAB tests and numerical comparison; Linux compilation only for Runtime deployment |
| Security/privacy | TLS with specific development CA, encrypted templates, isolated services, no stored camera frames | Adversarial photo/video testing; no certification claimed |
| Reveal | Supplied captioned meme + animation/haptic/system sound + clearly fictional dashboard | Subjective comedic timing |

## Biometric study

Obtain written volunteer consent and a short retention agreement before collecting study signals. Use 15 volunteers × 10 genuine attempts + 5 imitation attempts **per layer**, as requested by the PDF. Separate enrollment data from evaluation attempts. Avoid tuning thresholds on the held-out test set. Purge participant data after evaluation.

Record `layer,genuine,score,latency_ms`, where `genuine` is exactly `0` or `1`. Then:

```powershell
.venv/Scripts/python.exe scripts/evaluate.py study.csv --output .local/evaluation.json
```

For MATLAB ROC figures, run `matlab-engine/evaluate_roc.m` against the same CSV. The script reports an empirical EER estimate; finite sample size limits precision. Measure full-sequence FAR independently; do not multiply layer FAR values and assume independence.

## Performance and usability

Use a release-mode Android build on the target phone, a stable stand and the same Wi-Fi network. Enable diagnostics. Measure frame round trip separately from server inference time. Report median/p95 latency and processed FPS with 1, 3 and 5 concurrent sessions. Time MATLAB decisions separately; the <1 second target excludes initial Runtime startup. Measure the complete three-layer login for five users against the <30 second goal.

Current implementation serializes MediaPipe tracker access to avoid detector teardown races. Concurrent-session scaling and CPU contention must be profiled before claiming the multi-session throughput target. Camera encoding runs outside the UI isolate; actual device throughput remains hardware dependent.

Test bright/dim light, partial occlusion, long tracking gaps, photo presentation, replayed videos, and an observer imitating the gesture. Basic random liveness is included; it is not ISO anti-spoofing certification.

## Honest completion criteria

Do not mark the PDF's APK-on-device, latency, FAR/EER, MATLAB execution, volunteer study or demonstration-video deliverables complete without evidence. No real participant results or evaluation video are fabricated in this repository. The automated tests use synthetic signals and controlled service doubles only where explicitly labeled.
