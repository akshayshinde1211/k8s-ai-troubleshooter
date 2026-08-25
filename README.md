# Kubernetes AI-Powered Cluster Troubleshooter

A Python command-line project for investigating unhealthy Kubernetes workloads.
It will discover problematic pods, collect focused diagnostic evidence, apply
deterministic Kubernetes rules, and optionally request AI-assisted analysis.

The first milestone establishes a reliable local connection to the Kubernetes API.
Automated troubleshooting and AI integration are intentionally out of scope for
this stage.

## Prerequisites

- Python 3.10 or newer
- `kubectl` configured for the cluster you want to inspect
- Permission to list pods across namespaces

## Clone and run in your cluster

From a shell with access to the cluster, clone the repository and prepare the
Python environment:

```bash
git clone https://github.com/akshayshinde1211/k8s-ai-troubleshooter.git
cd k8s-ai-troubleshooter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell, activate the virtual environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Verify Kubernetes API connectivity

The connectivity command reads the same active kubeconfig context used by
`kubectl`, calls the Kubernetes API, and prints up to ten pods returned by the
cluster.

```bash
python main.py check-connectivity
```

Expected output begins with:

```text
Kubernetes API connectivity check succeeded.
Retrieved <number> pod(s) in this response.
```

If it cannot load kubeconfig or the current identity lacks API access, the command
prints the Kubernetes error and exits with a non-zero status.

## Configuration

Copy `.env.example` to `.env` only when a later AI integration milestone requires
it. Do not commit `.env`; it is excluded by `.gitignore`.

## Safety

The project is read-only. It is intended to inspect Kubernetes resources and help
an operator decide on remediation; it does not change workloads.
