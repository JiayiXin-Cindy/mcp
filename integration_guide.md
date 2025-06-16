# SMUS Data Agent VS Code Integration Guide

## Quick Integration Steps (Recommended)

### 1. Simple Terminal Integration

The easiest way to integrate your AI agent is to add a command that opens it in a VS Code terminal.

**Update package.json - Add to "contributes.commands":**
```json
{
  "command": "amazon-datazone.openDataAgent",
  "title": "Open Data Agent Chat",
  "category": "Amazon DataZone"
}
```

**Update extension.ts - Add to activate() function:**
```typescript
const openDataAgentCommand = vscode.commands.registerCommand('amazon-datazone.openDataAgent', async () => {
    const terminal = vscode.window.createTerminal({
        name: 'SMUS Data Agent',
        cwd: '/Volumes/workplace/SMUS-admin-agent',
        env: {
            ...process.env,
            VIRTUAL_ENV: '/Volumes/workplace/SMUS-admin-agent/venv',
            PATH: '/Volumes/workplace/SMUS-admin-agent/venv/bin:' + process.env.PATH
        }
    });
    
    terminal.sendText('source venv/bin/activate && smus-data-agent');
    terminal.show();
});

context.subscriptions.push(openDataAgentCommand);
```

### 2. Add Menu Button

**Update package.json - Add to "contributes.menus":**
```json
"view/title": [
    {
        "command": "amazon-datazone.openDataAgent",
        "when": "view == amazon-datazone.dataAgentView",
        "group": "navigation",
        "title": "Open Chat"
    }
]
```

## Advanced Webview Integration

### 1. Update ChatViewProvider for Full Integration

Replace your existing ChatViewProvider with enhanced version that:
- Communicates with Python agent via child_process
- Handles streaming responses
- Manages conversation sessions

### 2. Key Integration Points

```typescript
// In ChatViewProvider.ts
import { spawn } from 'child_process';

private async sendMessageToAgent(message: string): Promise<void> {
    const pythonScript = `
import asyncio
import sys
sys.path.append('/Volumes/workplace/SMUS-admin-agent/src')
from smus_data_agent import SMUSDataAgent

async def main():
    agent = SMUSDataAgent()
    async for chunk in agent.stream_response("${message}", "vscode_session"):
        print(f"CHUNK:{chunk}", end="", flush=True)
    print("\\nEND_STREAM")

asyncio.run(main())
`;
    
    // Execute Python script and handle streaming response
}
```

### 3. Webview HTML with Real-time Chat

Your webview needs:
- Message display area
- Input field
- Send/Clear buttons
- JavaScript to handle streaming responses

## File Structure

```
SMUS-admin-agent-vscode/
├── src/
│   ├── extension.ts              # Main extension + agent command
│   ├── ChatViewProvider.ts       # Enhanced chat interface
│   ├── aiAgentService.ts         # Python communication (optional)
│   └── existing files...
├── package.json                  # Updated with new commands/menus
└── integration_guide.md         # This file
```

## Testing Steps

1. **Update package.json** with new command
2. **Update extension.ts** with terminal command
3. **Reload extension** (F5 in VS Code)
4. **Test command**: Cmd+Shift+P → "Amazon DataZone: Open Data Agent Chat"
5. **Verify**: Terminal opens with AI agent running

## Implementation Priority

**Phase 1: Terminal Integration (Quick)**
- Add terminal command (5 minutes)
- Test basic functionality

**Phase 2: Webview Integration (Advanced)**
- Update ChatViewProvider
- Add streaming communication
- Enhance UI/UX

## Error Handling

Add these checks:
- Verify Python environment exists
- Check if AI agent is installed
- Handle connection failures gracefully
- Provide helpful error messages

## Configuration Options

Consider adding VS Code settings:
```json
"amazon-datazone.agentPath": "/path/to/agent",
"amazon-datazone.sessionId": "custom_session"
```

This guide provides both quick integration and advanced options for your VS Code extension. 