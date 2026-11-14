# MATLAB setup

## Use the MATLAB already installed on this PC

This is now the default path. Run from the project virtual environment:

```powershell
.venv/Scripts/python.exe scripts/start.py
```

On macOS/Linux, use `.venv/bin/python scripts/start.py`. Run as the same operating
system user who can open desktop MATLAB successfully. The launcher discovers
MATLAB from `MATLAB_ROOT`, then `PATH`, then the Windows registry and standard
Windows/macOS/Linux installation folders. It ignores incomplete installations
and MATLAB Runtime alone. When multiple standard installations exist, it selects
the newest release; an explicit root takes priority.

The scorer runs **on the host PC** through MATLAB Engine. MATLAB uses that user's
existing activation or configured network license. No license files, MathWorks
account credentials, or activation tokens are copied into Docker or the project.
This mode requires **MATLAB, Signal Processing Toolbox, and Statistics and Machine
Learning Toolbox**. **Compiler and Compiler SDK are not required.**

The launcher uses an existing importable Engine API, or the preinstalled API
shipped with MATLAB R2026a and newer. If necessary, it installs the API from the
selected MATLAB installation's `extern/engines/python` folder into the current
project virtual environment. It never installs an arbitrary latest Engine release.
Use supported 64-bit Python with the same CPU architecture as MATLAB; Python 3.11
matches this project's dependencies and MATLAB R2023b through R2026b. Older
releases may require a different environment. See MathWorks' [Python compatibility
table](https://www.mathworks.com/support/requirements/python-compatibility.html)
and [Engine installation instructions](https://www.mathworks.com/help/matlab/matlab_external/install-the-matlab-engine-for-python.html).
If the bundled installer cannot write its build files, follow those instructions
to install the matching API with the necessary installation-folder permissions.

The startup check launches a private MATLAB session, verifies the actual
installation root, and executes both toolbox operations before routing the
gateway to it. Existing interactive MATLAB sessions are not modified or closed.
Keep the launcher terminal open; Ctrl+C closes THE VAULT's private session.
Docker infrastructure remains installed, but host scoring requires that terminal.

Docker connects to the host scorer over HTTPS on port 9910, using a separate
development CA and a random per-launch service credential. Only the public
scoring certificate is mounted into the gateway. The normal app certificate is
unchanged. On Linux, Compose maps `host.docker.internal` through `host-gateway`;
on Docker Desktop the same name reaches the host. If a firewall blocks that path,
allow the intended Docker-to-host connection. Host scoring can also be used with
`--local` to avoid Docker entirely.

```powershell
# Read-only discovery: does not install anything or check out a license.
.venv/Scripts/python.exe scripts/start.py --check

# Custom MATLAB location; paths with spaces are supported.
.venv/Scripts/python.exe scripts/start.py --matlab-root "C:/Program Files/MATLAB/R2025b"

# Require MATLAB, even on machines where detection finds none.
.venv/Scripts/python.exe scripts/start.py --backend matlab-engine

# Deliberately use the Python reference.
.venv/Scripts/python.exe scripts/start.py --backend python-reference

# All services local, with the same automatic MATLAB selection.
./scripts/start-local.ps1
```

Without a complete desktop installation, `auto` explicitly selects
`python-reference`. If MATLAB is found but activation, Engine loading, or toolbox
checks fail, startup fails with a diagnostic; it does not silently substitute
Python. A mismatched preexisting Engine API must be reinstalled from the selected
MATLAB release's `extern/engines/python` folder.

`GET /api/v1/health` reports `services.scoring.engine = "matlab-engine"`,
`matlab = true`, and the MATLAB release after successful startup. Detection alone
does not establish license availability. The `--no-build` flag skips Docker image
rebuilding only when those images already match the current project source.

## Optional compiled Runtime deployment

There are three separate pieces:

| Component | Image / location | Requirement |
| --- | --- | --- |
| MATLAB + Compiler SDK | `vault-matlab-compiler:r2025b`, built from `mathworks/matlab:r2025b` | Activated MATLAB, Compiler and Compiler SDK license to compile; Signal Processing and Statistics toolboxes for these algorithms |
| Compiled scorer | `matlab-engine/build/vault_matlab` | Build once on Linux for the Linux Runtime image |
| MATLAB Runtime | `containers.mathworks.com/matlab-runtime:r2025b` | No MATLAB license to execute the compiled package; Runtime license terms apply |

The official Runtime tag was verified against the registry. The original PDF's `containers/matlab-runtime` name omits the registry; the Dockerfile uses the correct fully qualified image.

## Installation

```powershell
docker build -f matlab-engine/Dockerfile.compiler -t vault-matlab-compiler:r2025b matlab-engine
```

This installs MATLAB Compiler, Compiler SDK, Signal Processing Toolbox and Statistics and Machine Learning Toolbox using MathWorks Package Manager. Installation alone does not activate a license. No credentials are baked into the image.

## Activation choices

For a campus/network license, ask the license administrator for a server that includes all required products, then set `MLM_LICENSE_FILE` in your local environment. A server address typically has the form `27000@license-server`. Do not commit it or any license file.

For an individual or trial license, use the container's official browser desktop to sign in yourself:

```powershell
docker run --rm --name vault-matlab-setup --shm-size=512m -p 127.0.0.1:8888:8888 --mount "type=bind,source=$PWD,target=/workspace" -v vault-matlab-home:/home/matlab vault-matlab-compiler:r2025b -browser
```

Open the localhost URL printed by the container. Sign in and activate a license/trial that actually includes **Compiler SDK**, not only MATLAB. Trial availability and entitlement are determined by MathWorks. The assistant cannot create an entitlement or activate your account without your participation. Credentials and license state remain in the dedicated local volume.

Inside MATLAB, run:

```matlab
cd('/workspace')
ver
run('matlab-engine/build_engine.m')
```

For a network license, the provided helper performs the same compilation:

```powershell
./scripts/compile-matlab.ps1 -LicenseServer $env:MLM_LICENSE_FILE
```

Compile on **Linux**, inside this container. A Windows-compiled package cannot be assumed to run inside the Linux Runtime image. Match the Runtime release and update level to the compiler used. Rebuild the runtime image after rebuilding the package.

## Switch the application to MATLAB

MATLAB Online (basic) is an online-only entitlement. It does not license the local
Docker installation and does not include Compiler or Compiler SDK. See the
[official comparison](https://www.mathworks.com/products/matlab-online/matlab-online-versions.html).
The already installed compiler needs a qualifying campus, individual or trial
entitlement that includes the required products. Request a trial from the
[Compiler SDK product page](https://www.mathworks.com/products/matlab-compiler-sdk.html).

You can still validate the algorithm source in Basic: upload the portable
`dist/the-vault-matlab-source.zip` archive to MATLAB Online, unzip it into the
current folder, then run `run('matlab-engine/run_validation.m')`. Basic includes
the Signal Processing and Statistics toolboxes used here. This does not connect
the online session to THE VAULT's local REST service or produce a compiled package.

If the embedded Online Services Agreement stalls after Accept, sign into
`https://matlab.mathworks.com/` directly, complete the agreement there if prompted,
then refresh the local setup page and sign in again. This is a troubleshooting
step, not confirmation that a license has been granted.

```powershell
docker compose -f docker-compose.yml -f compose.matlab.yml up -d --build
```

`GET /api/v1/health` must report `services.scoring.engine = "matlab-runtime"` and `matlab = true`. Every enrollment and score response also names the engine. Missing packages or initialization failures fail explicitly.

To run MATLAB inside Docker instead of using the host's activated installation,
an explicitly configured network license remains available:

```powershell
docker compose -f docker-compose.yml -f compose.matlab-network.yml up -d --build
```

This starts a licensed MATLAB process inside the container through the Python
Engine API. `compose.matlab-dev.yml` now connects Docker to host MATLAB and is
managed by `scripts/start.py`; it does not require `MLM_LICENSE_FILE`.

## Algorithms and tests

`vaulte_engine.m` accepts a JSON string and returns a JSON string, avoiding platform-specific MATLAB struct conversions in the REST wrapper. It dispatches enrollment, `score_face`, `score_body`, `score_hand` and `fuse_scores`. DTW uses normalized local RMS distance and a 10% band. Hand Procrustes disallows reflection, so mirror drawings are not treated as an ordinary rotation.

```matlab
addpath('matlab-engine/src')
results = runtests('matlab-engine/tests');
assertSuccess(results)
```

The Python and MATLAB implementations share the mathematical contract, but numerical parity must be measured with the compiled MATLAB engine before declaring parity. Python passing tests do not establish MATLAB execution success.

Official references: [MATLAB Docker image and licensing](https://hub.docker.com/r/mathworks/matlab), [MathWorks installer Dockerfile](https://github.com/mathworks-ref-arch/matlab-dockerfile/tree/main/alternates/building-on-matlab-docker-image), [Compiler SDK Python packages](https://www.mathworks.com/help/compiler_sdk/python/compiler.build.pythonpackage.html), [Runtime container configuration](https://www.mathworks.com/help/compiler/get-matlab-runtime-container.html).
