import { spawn, ChildProcess } from 'child_process';
import * as vscode from 'vscode';
import * as fs from 'fs';

export interface ChatMessage {
    type: 'user' | 'assistant';
    content: string;
    timestamp: string;
}

export interface ChatSession {
    sessionId: string;
    messages: ChatMessage[];
}

export class AIAgentService {
    private pythonProcess: ChildProcess | null = null;
    private currentSessionId: string = 'vscode_session';
    private agentPath: string;

    constructor() {
        // Path to your AI agent directory
        this.agentPath = '/Volumes/workplace/SMUS-admin-agent';
    }

    /**
     * Initialize the AI agent service
     */
    public async initialize(): Promise<void> {
        try {
            // Test if the AI agent is accessible
            await this.testConnection();
            console.log('AI Agent service initialized successfully');
        } catch (error) {
            console.error('Failed to initialize AI agent service:', error);
            throw error;
        }
    }

    /**
     * Test connection to the AI agent
     */
    private async testConnection(): Promise<void> {
        return new Promise((resolve, reject) => {
            const testProcess = spawn('python', ['-c', 'from smus_admin_agent import SMUSAdminAgent; print("OK")'], {
                cwd: this.agentPath,
                env: { ...process.env, VIRTUAL_ENV: `${this.agentPath}/venv` }
            });

            let output = '';
            testProcess.stdout.on('data', (data) => {
                output += data.toString();
            });

            testProcess.on('close', (code) => {
                if (code === 0 && output.includes('OK')) {
                    resolve();
                } else {
                    reject(new Error(`AI agent test failed with code ${code}`));
                }
            });

            testProcess.on('error', (error) => {
                reject(error);
            });
        });
    }

    /**
     * Send a message to the AI agent and get streaming response
     */
    public async sendMessage(
        message: string, 
        onChunk: (chunk: string) => void,
        sessionId?: string
    ): Promise<void> {
        const session = sessionId || this.currentSessionId;
        
        return new Promise((resolve, reject) => {
            // Create Python script to handle the chat
            const pythonScript = `
import asyncio
import sys
import os
sys.path.append('${this.agentPath}/src')
from smus_admin_agent import SMUSAdminAgent

async def main():
    try:
        agent = SMUSAdminAgent()
        async for chunk in agent.stream_response("${message.replace(/"/g, '\\"')}", "${session}"):
            print(f"CHUNK:{chunk}", end="", flush=True)
        print("\\nEND_STREAM")
    except Exception as e:
        print(f"ERROR:{str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
`;

            // Write the script to a temporary file
            const scriptPath = `${this.agentPath}/temp_chat.py`;
            fs.writeFileSync(scriptPath, pythonScript);

            // Execute the Python script
            const pythonProcess = spawn('python', [scriptPath], {
                cwd: this.agentPath,
                env: { 
                    ...process.env, 
                    VIRTUAL_ENV: `${this.agentPath}/venv`,
                    PATH: `${this.agentPath}/venv/bin:${process.env.PATH}`
                }
            });

            let responseBuffer = '';
            
            pythonProcess.stdout.on('data', (data) => {
                const output = data.toString();
                responseBuffer += output;
                
                // Process chunks
                const lines = responseBuffer.split('\n');
                responseBuffer = lines.pop() || ''; // Keep incomplete line
                
                for (const line of lines) {
                    if (line.startsWith('CHUNK:')) {
                        const chunk = line.substring(6);
                        onChunk(chunk);
                    } else if (line === 'END_STREAM') {
                        // Clean up temp file
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

            pythonProcess.stderr.on('data', (data) => {
                console.error('Python stderr:', data.toString());
            });

            pythonProcess.on('close', (code) => {
                // Clean up temp file
                try {
                    require('fs').unlinkSync(scriptPath);
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

    /**
     * Get conversation history for a session
     */
    public async getSessionHistory(sessionId?: string): Promise<ChatMessage[]> {
        const session = sessionId || this.currentSessionId;
        
        return new Promise((resolve, reject) => {
            const pythonScript = `
import sys
import json
sys.path.append('${this.agentPath}/src')
from smus_admin_agent import SMUSAdminAgent

try:
    agent = SMUSAdminAgent()
    history = agent.get_session_history("${session}")
    print(json.dumps(history))
except Exception as e:
    print(f"ERROR:{str(e)}")
`;

            const scriptPath = `${this.agentPath}/temp_history.py`;
            require('fs').writeFileSync(scriptPath, pythonScript);

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
                // Clean up temp file
                try {
                    require('fs').unlinkSync(scriptPath);
                } catch (e) {
                    console.error('Failed to clean up temp file:', e);
                }

                if (code === 0) {
                    try {
                        const history = JSON.parse(output.trim());
                        const messages: ChatMessage[] = history.map((entry: any) => ({
                            type: entry.type === 'human' ? 'user' : 'assistant',
                            content: entry.content,
                            timestamp: entry.timestamp
                        }));
                        resolve(messages);
                    } catch (error) {
                        reject(new Error('Failed to parse history response'));
                    }
                } else {
                    reject(new Error(`Failed to get history, exit code: ${code}`));
                }
            });

            pythonProcess.on('error', (error) => {
                reject(error);
            });
        });
    }

    /**
     * Clear conversation history for a session
     */
    public async clearSession(sessionId?: string): Promise<void> {
        const session = sessionId || this.currentSessionId;
        
        return new Promise((resolve, reject) => {
            const pythonScript = `
import sys
sys.path.append('${this.agentPath}/src')
from smus_admin_agent import SMUSAdminAgent

try:
    agent = SMUSAdminAgent()
    agent.clear_session("${session}")
    print("SUCCESS")
except Exception as e:
    print(f"ERROR:{str(e)}")
`;

            const scriptPath = `${this.agentPath}/temp_clear.py`;
            require('fs').writeFileSync(scriptPath, pythonScript);

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
                // Clean up temp file
                try {
                    require('fs').unlinkSync(scriptPath);
                } catch (e) {
                    console.error('Failed to clean up temp file:', e);
                }

                if (code === 0 && output.includes('SUCCESS')) {
                    resolve();
                } else {
                    reject(new Error('Failed to clear session'));
                }
            });

            pythonProcess.on('error', (error) => {
                reject(error);
            });
        });
    }

    /**
     * Set the current session ID
     */
    public setSessionId(sessionId: string): void {
        this.currentSessionId = sessionId;
    }

    /**
     * Get the current session ID
     */
    public getCurrentSessionId(): string {
        return this.currentSessionId;
    }
} 