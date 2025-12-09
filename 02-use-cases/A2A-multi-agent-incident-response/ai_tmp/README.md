# AI Temporary Files

This folder contains AI-generated helper files organized per your folder structure.

## Structure

```
ai_tmp/
├── scripts/         # Utility scripts
├── docs/           # Documentation
└── test_data/      # Reusable test data
```

## Contents

### scripts/
- **`force_runtime_restart.sh`** - Force restart AgentCore runtimes (troubleshooting)

### docs/
- **`LOCAL_BUILD_README.md`** - Guide for building Docker images from local source
- **`UPDATE_KEYS_README.md`** - Guide for updating API keys

### test_data/
- (Empty - reserved for future test data)

## Main Deployment Scripts (in parent directory)

These are in the project root, not in ai_tmp:

- **`build_and_deploy_local.sh`** ⭐ - Build Docker images from YOUR local code and deploy
- **`update_api_keys.sh`** - Update API keys from `.a2a.config`
  - Use `--force` flag to rebuild from GitHub

## Usage

### Deploy from local source:
```bash
cd /path/to/A2A-multi-agent-incident-response
./build_and_deploy_local.sh
```

### Update API keys:
```bash
cd /path/to/A2A-multi-agent-incident-response
./update_api_keys.sh
```

### Force restart runtime:
```bash
./ai_tmp/scripts/force_runtime_restart.sh <runtime-id>
```

## Cleanup

This folder can be safely deleted if you don't need the helper scripts and docs.
The main deployment scripts (`build_and_deploy_local.sh`, `update_api_keys.sh`) are in the parent directory.

