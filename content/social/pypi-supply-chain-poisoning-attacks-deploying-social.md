## LinkedIn Post

If your security strategy assumes Python supply chain attacks only happen inside setup.py, your developer fleet is already exposed.

Modern PyPI adversaries have adapted. They are distributing multi-stage, compiled Rust stealers disguised as pre-built binary Wheels (.whl).

Here is how the attack works:
1. Typosquatting & Slopsquatting: Attackers publish malicious packages mirroring widely used libraries, targeting human typos or LLM hallucinated dependencies.
2. Bypassing Build Hooks: Binary wheels don't run setup.py. Instead, attackers bundle .pth files into the wheel. Under Python's core architecture, every .pth file in site-packages executes automatically whenever ANY Python process initializes.
3. The Native Rust Stealer: Once triggered, a stripped Rust binary deploys into memory. Rust gives attackers cross-platform targeting, complex control-flow obfuscation, and zero runtime dependencies.
4. Targeted Extraction: The malware sweeps developer machines for AWS credentials, SSH keys, npm/pypi tokens, and Claude/OpenAI configurations.

What should SecOps and DevOps teams do immediately?
- Mandate strict cryptographic hash pinning with pip --require-hashes or locked toolchains.
- Implement automated CI gates that unpack and scan .whl files for .pth, sitecustomize.py, or unexpected binary extensions.
- Enforce a 72-hour quarantine window on newly published PyPI dependencies.

Read our comprehensive intelligence breakdown and technical teardown at BreachModal: https://breachmodal.com/research/pypi-supply-chain-rust-stealers

## X Thread

1. 1/ The Python software supply chain has evolved. Plaintext setup.py stealers are dead. Today's PyPI threat actors deploy compiled, evasion-hardened Rust information stealers inside typo-squatted binary Wheels (.whl). Here is the technical breakdown. 🧵👇

2. 2/ Why Wheels? A .whl is an archive unpacked directly into site-packages without invoking setup scripts. Security scanners scanning for setup.py hooks see nothing anomalous. But adversaries have an older, deadlier trick: .pth files.

3. 3/ Python's interpreter parses any .pth file in site-packages at startup. If a line begins with 'import', it executes immediately. A developer simply running `python -V` in their venv executes the attacker's stage-one loader without ever importing the package.

4. 4/ Stage 3 drops a stripped native Rust executable. Why Rust? Zero external dependencies, trivial cross-platform compilation (Linux/macOS/Win), and complex binary graphs that reliably blind legacy EDR heuristics.

5. 5/ What are they after? Not ransomware. They harvest ~/.aws/credentials, ~/.ssh/id_rsa, ~/.kube/config, GitHub tokens, and AI credentials (~/.claude.json, OpenAI keys) to enable secondary enterprise supply chain intrusions.

6. 6/ Defenses: 1) Require hash pinning (`--require-hashes`). 2) Gate all wheels in CI for .pth / binary hooks. 3) Quarantine new packages under 72h old. 4) Use short-lived OIDC tokens. Full BreachModal report: https://breachmodal.com/research/pypi-supply-chain-rust-stealers

## Visual Brief

### Hero Image Concept
Cinematic 3D render of a glowing binary Python Wheel (.whl) splitting open like an armored vault, revealing a geometric, metallic Rust-compiled crystalline spider automaton reaching out towards developer terminals, dark obsidian background with crimson telemetry lines.

### Infographic Concept
Anatomy of a PyPI Wheel Attack: Vertical timeline contrasting developer actions (running pip, executing tests) against covert attacker actions (pth parsing, Rust process detachment, AWS/AI token exfiltration).

### LinkedIn Carousel
- Slide 1: Why pip install is no longer safe: The rise of weaponized Python wheels and compiled Rust stealers.
- Slide 2: The .pth Exploit: How attackers achieve code execution without you ever importing their package.
- Slide 3: Why Rust? Cross-platform compilation, zero dependencies, and the complete bypass of legacy EDR heuristics.
- Slide 4: The Developer Harvest: Why adversaries are hunting AWS configs, SSH keys, and Claude/OpenAI tokens.
- Slide 5: 4 Hard Controls to Protect Your CI/CD Pipelines: Hash pinning, wheel pre-inspection, and package quarantine.

### Short-form Video Script
Think pip install is safe? Think again. Attackers are dropping compiled Rust stealers inside typosquatted Python wheels. No setup.py. No explicit imports. Just pure .pth execution hijacking your terminal the second Python starts. They're harvesting your AWS keys, GitHub tokens, and Claude API secrets. Pin your hashes. Inspect your wheels. Stay vigilant.

## Press Release

BreachModal Intelligence has issued a global security advisory detailing advanced supply chain poisoning campaigns targeting the Python Package Index (PyPI). Threat actors are systematically deploying pre-built binary Wheels containing stealth execution hooks (.pth) that automatically launch multi-stage, compiled Rust information stealers upon Python interpreter initialization. The payloads bypass standard source linters and static repository scanners, harvesting cloud identities, SSH keys, package publishing tokens, and AI configuration keys across developer workstations and automated build pipelines. BreachModal urges enterprises to immediately enforce strict hash-pinned dependency locking, quarantine unverified new registry packages, and deploy pre-installation binary wheel inspection across all continuous integration workflows.

## Proof of Concept (Structured)

**Summary**: This proof of concept demonstrates the architectural risk of Python .pth execution hooks deployed in pre-built wheel distributions and provides automated verification tooling to audit wheels for unauthenticated startup hooks before installation. Preconditions require Python 3.8+ and write access to the target virtual environment.

**CVSS v3.1**: `CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:H/I:H/A:N`

**Steps**:

### Step 1: Environment Isolation Setup
```
python3 -m venv /tmp/audit_env && source /tmp/audit_env/bin/activate
```
Spins up an isolated virtual environment to prevent system-wide contamination during diagnostic testing.

### Step 2: Deploy Benign Diagnostic .pth Hook
```
SITE_PKG=$(python3 -c 'import site; print(site.getsitepackages()[0])') && echo 'import sys; sys.stderr.write("[BREACHMODAL DETECTED] .pth execution hook invoked automatically.\n")' > "$SITE_PKG/canary_audit.pth"
```
Injects an unimported code execution directive into the site-packages path, mirroring how weaponized wheels trigger execution on interpreter initialization.

### Step 3: Trigger Verification Execution
```
python3 -c 'import math; print(f"Calculation complete: {math.sqrt(16)}")'
```
Demonstrates that calling an arbitrary, benign Python script will immediately execute the .pth payload before executing user logic.

### Step 4: Automated Wheel Pre-Install Inspection
```
python3 -c "import zipfile, sys; z=zipfile.ZipFile(sys.argv[1]); bad=[f for f in z.namelist() if f.endswith(('.pth', 'sitecustomize.py', '.so', '.pyd'))]; print('Vulnerable components found:', bad) if bad else print('Archive clean')" target_package.whl
```
A production-grade pre-install gate that programmatically parses wheel zip entries to detect stealth startup files and binary extensions.

**Expected Output**: [BREACHMODAL DETECTED] .pth execution hook invoked automatically.
Calculation complete: 4.0

**Mitigations**:
- Mandate strict hash pinning across all requirements files using 'pip install --require-hashes -r requirements.txt' or cryptographically locked uv/poetry lockfiles.
- Deploy custom CI pre-build linting to unpack and reject any wheel containing .pth, sitecustomize.py, or usercustomize.py files.
- Adopt private caching registries (e.g., Artifactory, Nexus) configured with a mandatory 72-hour quarantine window on all newly released PyPI packages.
- Implement eBPF runtime monitoring (e.g., Tetragon, Falco) to detect unexpected process spawns and outbound network sockets initiated by Python binaries.

