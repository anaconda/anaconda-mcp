# Conda Setup — Miniconda vs. Full Anaconda

## Why it matters

Full Anaconda installs 500+ packages into the base environment. This triggers [PI-003](./KNOWN_ISSUES.md#pi-003-anaconda-connector-packages-fail-to-download--conda-anaconda-telemetry-sends-oversized-headers-to-s3): conda's telemetry plugin sends the full base package list as an HTTP header on every download request. The `anaconda-connector` channel redirects to AWS S3, which has a hard 8192-byte header limit — the oversized header causes downloads to fail with HTTP 400.

**Miniconda** (~30–50 packages in base) stays well under the limit. Use it for QA.

---

## Check what you have

```bash
conda list -n base | grep anaconda-navigator   # macOS / Linux
conda list -n base | findstr anaconda-navigator  # Windows
```

- **Returns a line** → full Anaconda — follow the steps below
- **Returns nothing** → Miniconda or trimmed install — you're good

---

## Switch from full Anaconda to Miniconda

If you already have full Anaconda installed:

**macOS / Linux** — uninstall first:
```bash
# Remove the Anaconda installation directory (adjust path if different)
rm -rf ~/anaconda3
# Remove conda init lines added to your shell config
conda init --reverse   # or manually remove the conda block from ~/.zshrc / ~/.bashrc
```

**Windows** — uninstall via **Add or Remove Programs** → search for "Anaconda", uninstall. Then delete any leftover `anaconda3` folder under your user profile if it remains.

After uninstalling, proceed with the Miniconda install below.

---

## Install Miniconda

### macOS / Linux

```bash
# Download and run the installer (pick your platform at https://docs.anaconda.com/miniconda/)
bash Miniconda3-latest-MacOSX-arm64.sh   # Apple Silicon
bash Miniconda3-latest-MacOSX-x86_64.sh  # Intel Mac
bash Miniconda3-latest-Linux-x86_64.sh   # Linux
```

Follow the prompts, accept the license, use the default install path. Restart your shell or run `source ~/.bashrc` / `source ~/.zshrc`.

### Windows

1. Download Miniconda: <https://docs.anaconda.com/miniconda/>
2. Run the `.exe` installer — choose **Just Me**, default path (`C:\Users\<you>\miniconda3`)
3. Open **Miniconda Prompt** from the Start Menu
4. Initialize for PowerShell if needed: `conda init powershell`

---

## Workaround if you must use full Anaconda

Disable conda's anonymous usage telemetry before running `conda create`:

```bash
conda config --set anaconda_anon_usage false
```

Re-enable after if desired:

```bash
conda config --set anaconda_anon_usage true
```
