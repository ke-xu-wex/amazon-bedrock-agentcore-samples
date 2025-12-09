# API Key Update Script

## Quick Start

Update API keys from config:
```bash
./update_api_keys.sh
```

Force rebuild and restart all agents:
```bash
./update_api_keys.sh --force
```

## What It Does

### Normal Mode (`./update_api_keys.sh`)
1. ✅ Reads all API keys from `.a2a.config`
2. ✅ Updates CloudFormation stacks with new keys
3. ✅ Refreshes runtime environment variables
4. ✅ Only updates what changed
5. ✅ **No keys exposed in output**

### Force Mode (`./update_api_keys.sh --force`)
1. 🔨 Triggers CodeBuild to rebuild ALL Docker images
2. 🔨 Waits for all builds to complete
3. 🔨 Lambda automatically updates runtimes with new images
4. 🔨 Forces stack updates even if keys unchanged
5. 🔨 Fully restarts all agent services
6. 🔨 **Complete clean slate deployment**

## When To Use Each Mode

### Use Normal Mode When:
- You updated API keys in `.a2a.config`
- You changed model IDs (gpt-4o-mini, gemini-2.5-flash, etc.)
- Keys expired and you got new ones
- **Fast** (1-2 minutes)

### Use Force Mode When:
- Agents aren't working after key updates
- You modified agent source code
- Environment variables seem cached/stale
- You want a complete fresh restart
- Troubleshooting mysterious issues
- **Slower** (3-5 minutes with builds)

## Configuration

Edit `.a2a.config` before running:

```yaml
api_keys:
  google: YOUR_GOOGLE_API_KEY
  google_model: gemini-2.5-flash
  openai: YOUR_OPENAI_API_KEY
  openai_model: gpt-4o-mini
  tavily: YOUR_TAVILY_API_KEY
```

## Security

✅ **All API keys are masked** - No sensitive data in terminal output  
✅ **Secure updates** - Keys only passed via CloudFormation parameters  
✅ **No logs** - Sensitive operations redirected to /dev/null  

## Agents Updated

1. **Web Search Agent**
   - OpenAI API Key
   - OpenAI Model ID
   - Tavily API Key

2. **Host Agent**
   - Google API Key  
   - Google Model ID

3. **Monitoring Agent**
   - No external API keys (uses AWS credentials)

## Troubleshooting

**"No changes needed"** - Normal! Keys already match config.

**Stack update fails** - Check AWS Console CloudFormation for details.

**Agents still not working after update** - Try force mode:
```bash
./update_api_keys.sh --force
```

**Want to see what changed** - Check AWS Console:
1. Go to CloudFormation
2. Click stack name (e.g., `web-search-agent-a2a`)
3. View "Parameters" tab
4. Check "Events" tab for update history


