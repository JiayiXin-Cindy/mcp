import * as vscode from 'vscode';
import { spawn } from 'child_process';

export class ChatViewProvider implements vscode.WebviewViewProvider {

    public static readonly viewType = 'amazon-datazone.dataAgentView';
    private _view?: vscode.WebviewView;
    private agentPath: string = '/Volumes/workplace/SMUS-admin-agent';
    private currentSessionId: string = 'vscode_session';

    constructor(
        private readonly _extensionUri: vscode.Uri,
    ) { }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken,
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            // Allow scripts in the webview
            enableScripts: true,
            localResourceRoots: [
                this._extensionUri
            ]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'sendMessage':
                    await this.handleSendMessage(data.message);
                    break;
                case 'clearChat':
                    await this.handleClearChat();
                    break;
                case 'loadHistory':
                    await this.handleLoadHistory();
                    break;
            }
        });
    }

    private async handleSendMessage(message: string) {
        if (!this._view) {
            return;
        }

        // Add user message to chat
        this._view.webview.postMessage({
            type: 'addMessage',
            message: {
                type: 'user',
                content: message,
                timestamp: new Date().toISOString()
            }
        });

        // Send typing indicator
        this._view.webview.postMessage({
            type: 'typing',
            isTyping: true
        });

        try {
            await this.sendMessageToAgent(message);
        } catch (error) {
            console.error('Error sending message to agent:', error);
            this._view.webview.postMessage({
                type: 'addMessage',
                message: {
                    type: 'assistant',
                    content: `Error: ${error}`,
                    timestamp: new Date().toISOString()
                }
            });
        }

        // Stop typing indicator
        this._view.webview.postMessage({
            type: 'typing',
            isTyping: false
        });
    }

    private async sendMessageToAgent(message: string): Promise<void> {
        return new Promise((resolve, reject) => {
            const pythonScript = `
import asyncio
import sys
import os
sys.path.append('${this.agentPath}/src')
from smus_admin_agent import SMUSAdminAgent

async def main():
    try:
        agent = SMUSAdminAgent()
        response_content = ""
        async for chunk in agent.stream_response("${message.replace(/"/g, '\\"')}", "${this.currentSessionId}"):
            response_content += chunk
            print(f"CHUNK:{chunk}", end="", flush=True)
        print("\\nEND_STREAM")
    except Exception as e:
        print(f"ERROR:{str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
`;

            // Write script to temp file
            const fs = require('fs');
            const scriptPath = `${this.agentPath}/temp_vscode_chat.py`;
            fs.writeFileSync(scriptPath, pythonScript);

            // Execute Python script
            const pythonProcess = spawn('python', [scriptPath], {
                cwd: this.agentPath,
                env: { 
                    ...process.env, 
                    VIRTUAL_ENV: `${this.agentPath}/venv`,
                    PATH: `${this.agentPath}/venv/bin:${process.env.PATH}`
                }
            });

            let responseBuffer = '';
            let fullResponse = '';

            pythonProcess.stdout.on('data', (data) => {
                const output = data.toString();
                responseBuffer += output;
                
                const lines = responseBuffer.split('\n');
                responseBuffer = lines.pop() || '';
                
                for (const line of lines) {
                    if (line.startsWith('CHUNK:')) {
                        const chunk = line.substring(6);
                        fullResponse += chunk;
                        
                        // Send chunk to webview
                        if (this._view) {
                            this._view.webview.postMessage({
                                type: 'streamChunk',
                                chunk: chunk
                            });
                        }
                    } else if (line === 'END_STREAM') {
                        // Send final message
                        if (this._view) {
                            this._view.webview.postMessage({
                                type: 'addMessage',
                                message: {
                                    type: 'assistant',
                                    content: fullResponse,
                                    timestamp: new Date().toISOString()
                                }
                            });
                        }
                        
                        // Clean up
                        try {
                            fs.unlinkSync(scriptPath);
                        } catch (e) {
                            console.error('Failed to clean up temp file:', e);
                        }
                        resolve();
                        return;
                    } else if (line.startsWith('ERROR:')) {
                        const error = line.substring(6);
                        reject(new Error(error));
                        return;
                    }
                }
            });

            pythonProcess.on('close', (code) => {
                try {
                    fs.unlinkSync(scriptPath);
                } catch (e) {
                    console.error('Failed to clean up temp file:', e);
                }
                
                if (code !== 0) {
                    reject(new Error(`Python process exited with code ${code}`));
                } else {
                    resolve();
                }
            });

            pythonProcess.on('error', (error) => {
                reject(error);
            });
        });
    }

    private async handleClearChat() {
        try {
            await this.clearAgentSession();
            if (this._view) {
                this._view.webview.postMessage({
                    type: 'clearMessages'
                });
            }
        } catch (error) {
            console.error('Error clearing chat:', error);
        }
    }

    private async clearAgentSession(): Promise<void> {
        return new Promise((resolve, reject) => {
            const pythonScript = `
import sys
sys.path.append('${this.agentPath}/src')
from smus_admin_agent import SMUSAdminAgent

try:
    agent = SMUSAdminAgent()
    agent.clear_session("${this.currentSessionId}")
    print("SUCCESS")
except Exception as e:
    print(f"ERROR:{str(e)}")
`;
            
            const fs = require('fs');
            const scriptPath = `${this.agentPath}/temp_clear.py`;
            fs.writeFileSync(scriptPath, pythonScript);

            const pythonProcess = spawn('python', [scriptPath], {
                cwd: this.agentPath,
                env: { 
                    ...process.env, 
                    VIRTUAL_ENV: `${this.agentPath}/venv`,
                    PATH: `${this.agentPath}/venv/bin:${process.env.PATH}`
                }
            });

            let output = '';
            pythonProcess.stdout.on('data', (data) => {
                output += data.toString();
            });

            pythonProcess.on('close', (code) => {
                try {
                    fs.unlinkSync(scriptPath);
                } catch (e) {
                    console.error('Failed to clean up temp file:', e);
                }

                if (code === 0 && output.includes('SUCCESS')) {
                    resolve();
                } else {
                    reject(new Error('Failed to clear session'));
                }
            });
        });
    }

    private async handleLoadHistory() {
        // Implementation for loading conversation history
        // Similar to clearAgentSession but for getting history
    }

    private _getHtmlForWebview(webview: vscode.Webview) {
        const styleVSCodeUri = webview.asWebviewUri(vscode.Uri.joinPath(this._extensionUri, 'media', 'vscode.css'));

        return `<!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <link href="${styleVSCodeUri}" rel="stylesheet">
                <title>Data Agent</title>
                <style>
                    body {
                        font-family: var(--vscode-font-family);
                        font-size: var(--vscode-font-size);
                        color: var(--vscode-foreground);
                        background-color: var(--vscode-editor-background);
                        margin: 0;
                        padding: 10px;
                    }
                    #chat-container {
                        display: flex;
                        flex-direction: column;
                        height: 100vh;
                    }
                    #chat-messages {
                        flex: 1;
                        overflow-y: auto;
                        padding: 10px 0;
                        border-bottom: 1px solid var(--vscode-panel-border);
                        margin-bottom: 10px;
                    }
                    .message {
                        margin: 8px 0;
                        padding: 8px;
                        border-radius: 4px;
                    }
                    .user-message {
                        background-color: var(--vscode-textBlockQuote-background);
                        border-left: 3px solid var(--vscode-textBlockQuote-border);
                    }
                    .assistant-message {
                        background-color: var(--vscode-editor-inactiveSelectionBackground);
                        border-left: 3px solid var(--vscode-focusBorder);
                    }
                    .message-header {
                        font-weight: bold;
                        font-size: 12px;
                        color: var(--vscode-descriptionForeground);
                        margin-bottom: 4px;
                    }
                    .message-content {
                        white-space: pre-wrap;
                        word-wrap: break-word;
                    }
                    #chat-input-container {
                        display: flex;
                        gap: 8px;
                        align-items: center;
                    }
                    #chat-input {
                        flex: 1;
                        padding: 8px;
                        border: 1px solid var(--vscode-input-border);
                        background-color: var(--vscode-input-background);
                        color: var(--vscode-input-foreground);
                        border-radius: 2px;
                    }
                    button {
                        padding: 8px 12px;
                        background-color: var(--vscode-button-background);
                        color: var(--vscode-button-foreground);
                        border: none;
                        border-radius: 2px;
                        cursor: pointer;
                    }
                    button:hover {
                        background-color: var(--vscode-button-hoverBackground);
                    }
                    .typing-indicator {
                        font-style: italic;
                        color: var(--vscode-descriptionForeground);
                        padding: 4px 8px;
                    }
                </style>
            </head>
            <body>
                <div id="chat-container">
                    <div id="chat-messages">
                        <div class="message assistant-message">
                            <div class="message-header">Data Agent</div>
                            <div class="message-content">Hello! I'm your SMUS Admin Agent. I can help you with data-related questions and Amazon DataZone queries. How can I assist you today?</div>
                        </div>
                    </div>
                    <div id="chat-input-container">
                        <input type="text" id="chat-input" placeholder="Ask about DataZone or data..." />
                        <button id="send-button">Send</button>
                        <button id="clear-button">Clear</button>
                    </div>
                </div>
                
                <script>
                    const vscode = acquireVsCodeApi();
                    const chatMessages = document.getElementById('chat-messages');
                    const chatInput = document.getElementById('chat-input');
                    const sendButton = document.getElementById('send-button');
                    const clearButton = document.getElementById('clear-button');
                    
                    let currentAssistantMessage = null;
                    
                    function addMessage(type, content, timestamp) {
                        const messageDiv = document.createElement('div');
                        messageDiv.className = \`message \${type}-message\`;
                        
                        const headerDiv = document.createElement('div');
                        headerDiv.className = 'message-header';
                        headerDiv.textContent = type === 'user' ? 'You' : 'Data Agent';
                        
                        const contentDiv = document.createElement('div');
                        contentDiv.className = 'message-content';
                        contentDiv.textContent = content;
                        
                        messageDiv.appendChild(headerDiv);
                        messageDiv.appendChild(contentDiv);
                        chatMessages.appendChild(messageDiv);
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                        
                        return contentDiv;
                    }
                    
                    function sendMessage() {
                        const message = chatInput.value.trim();
                        if (message) {
                            vscode.postMessage({
                                type: 'sendMessage',
                                message: message
                            });
                            chatInput.value = '';
                        }
                    }
                    
                    function clearChat() {
                        vscode.postMessage({
                            type: 'clearChat'
                        });
                    }
                    
                    sendButton.addEventListener('click', sendMessage);
                    clearButton.addEventListener('click', clearChat);
                    
                    chatInput.addEventListener('keypress', (e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            sendMessage();
                        }
                    });
                    
                    // Handle messages from extension
                    window.addEventListener('message', event => {
                        const message = event.data;
                        
                        switch (message.type) {
                            case 'addMessage':
                                if (message.message.type === 'assistant') {
                                    currentAssistantMessage = null;
                                }
                                addMessage(message.message.type, message.message.content, message.message.timestamp);
                                break;
                                
                            case 'streamChunk':
                                if (!currentAssistantMessage) {
                                    currentAssistantMessage = addMessage('assistant', '', new Date().toISOString());
                                }
                                currentAssistantMessage.textContent += message.chunk;
                                chatMessages.scrollTop = chatMessages.scrollHeight;
                                break;
                                
                            case 'typing':
                                // Handle typing indicator
                                break;
                                
                            case 'clearMessages':
                                chatMessages.innerHTML = '<div class="message assistant-message"><div class="message-header">Data Agent</div><div class="message-content">Chat cleared. How can I help you?</div></div>';
                                currentAssistantMessage = null;
                                break;
                        }
                    });
                </script>
            </body>
            </html>`;
    }
} 