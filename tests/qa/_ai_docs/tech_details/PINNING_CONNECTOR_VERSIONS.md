# anaconda-connector Installation Options

The `anaconda-connector` packages can be installed either as transitive dependencies (simpler) or with explicit version pinning (for reproducibility).

---

## Option 1: Transitive Dependencies (simpler)

Let conda resolve `anaconda-connector` automatically as a dependency of `anaconda-mcp` and `environments-mcp-server`:

```bash
conda create --name anaconda-mcp-rc2-pyXY \
  -c datalayer \
  -c anaconda-cloud/label/dev \
  -c defaults \
  -c conda-forge \
  --channel 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/' \
  python=X.Y \
  anaconda-mcp=1.0.0.rc.2 \
  environments-mcp-server=1.0.0.rc.2
```

Replace `X.Y` with `3.10` | `3.11` | `3.12` | `3.13`.

---

## Option 2: Pinned Versions (for reproducibility)

Explicitly pin `anaconda-connector` versions for reproducible test environments:

```bash
conda create --name anaconda-mcp-rc2-pyXY \
  -c datalayer \
  -c anaconda-cloud/label/dev \
  -c defaults \
  -c conda-forge \
  --channel 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/' \
  python=X.Y \
  anaconda-mcp=1.0.0.rc.2 \
  environments-mcp-server=1.0.0.rc.2 \
  anaconda-connector-core=0.1.11 \
  anaconda-connector-conda=0.1.11 \
  anaconda-connector-utilities=0.1.11
```

Replace `X.Y` with `3.10` | `3.11` | `3.12` | `3.13`.

---

## When to Use Each

| Use Case | Recommended Option |
|----------|-------------------|
| Quick setup, latest compatible versions | Option 1 (transitive) |
| Reproducing test results | Option 2 (pinned) |
| Debugging connector-specific issues | Option 2 (pinned) |
| Regression testing between versions | Option 2 (pinned) |
