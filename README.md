# Kubernetes AI-Powered Cluster Troubleshooter

A read-only Python CLI for diagnosing unhealthy Kubernetes pods. It discovers
explicit pod failure signals, gathers focused API evidence, applies deterministic
Kubernetes rules, and can optionally use Google Gemini for evidence-bounded
investigation guidance.

## What it does

1. Authenticates with local kubeconfig or an in-cluster ServiceAccount.
2. Finds pods with concrete failure signals such as `CrashLoopBackOff`, image
   pull errors, unschedulable Pending state, `OOMKilled`, configuration errors,
   and excessive restarts.
3. Collects pod conditions, container state, recent events, current logs, and
   previous logs for restarted containers.
4. Runs deterministic rules before any AI request.
5. Optionally sends the bounded, structured evidence to Gemini for additional
   root-cause guidance. The tool never modifies Kubernetes resources.

## Quick start

```bash
git clone https://github.com/akshayshinde1211/k8s-ai-troubleshooter.git
cd k8s-ai-troubleshooter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py check-connectivity
python main.py scan
```

Limit scanning to one namespace when appropriate:

```bash
python main.py scan --namespace default
```

The CLI loads the current kubeconfig first. When it runs in Kubernetes, it falls
back to in-cluster ServiceAccount authentication.

## Test with the lab

Create controlled failures using the separate lab repository:

```bash
git clone https://github.com/akshayshinde1211/k8s-troubleshooting-lab.git
kubectl apply -f k8s-troubleshooting-lab/healthy/nginx.yaml
kubectl apply -f k8s-troubleshooting-lab/scenarios/crashloop/deployment.yaml
kubectl apply -f k8s-troubleshooting-lab/scenarios/imagepull/deployment.yaml
kubectl apply -f k8s-troubleshooting-lab/scenarios/pending/deployment.yaml
python main.py scan
```

Expected deterministic categories include `APPLICATION_RUNTIME`, `IMAGE`, and
`SCHEDULING`.

## Optional Gemini analysis

The deterministic diagnosis works without an API key. To add Gemini analysis,
copy `.env.example` to `.env`, set `GEMINI_API_KEY`, and opt in explicitly:

```bash
python main.py scan --namespace default --ai
```

Use `--model` to select a different Gemini model. Only bounded pod evidence is
sent: relevant status, conditions, recent events, truncated logs, and the
deterministic result. The prompt prohibits the model from inventing evidence.

## Read-only safety model

The CLI only reads Kubernetes information. It never deletes pods, patches
workloads, scales deployments, executes commands in containers, or changes
ConfigMaps and Secrets. AI output is advisory; an operator approves and applies
any remediation.

## In-cluster RBAC

The `manifests/` directory provides namespace-scoped RBAC:

- `pods`, `events`: list and get troubleshooting signals
- `pods/log`: read current and previous container logs
- `replicasets`, `deployments`: resolve owner context

Apply the manifests to the namespace being inspected:

```bash
kubectl apply -f manifests/serviceaccount.yaml
kubectl apply -f manifests/role.yaml
kubectl apply -f manifests/rolebinding.yaml
```

To run it in Kubernetes, build and publish an image, replace the placeholder
image in `manifests/deployment.yaml`, then apply the deployment manifest. No API
key is baked into the image; provide `GEMINI_API_KEY` through your secret
management process only when AI analysis is required.

## Container image

```bash
docker build -t k8s-ai-troubleshooter:local .
docker run --rm -v "$HOME/.kube:/home/app/.kube:ro" k8s-ai-troubleshooter:local scan
```

The image runs as a non-root user. For a local kubeconfig mount, ensure the
mounted file is readable by the container user or use an in-cluster deployment.

## Tests

```bash
pytest
```

The tests cover the deterministic category mapping independently of a live
cluster.

## Design choices

- The Kubernetes Python client provides typed API access and avoids fragile
  parsing of `kubectl` output.
- Pod phase and container state are evaluated separately: a `Running` pod can
  still be unhealthy when a container is not ready or restarting.
- Previous logs matter because the container that failed may no longer be the
  currently running instance.
- Rules run first to provide reliable diagnosis when Gemini is unavailable and
  to reduce the evidence sent to the model.
- The failure lab remains separate so test failures are reproducible without
  coupling application code to Kubernetes manifests.
