import { ChatMessage, ChatResponse } from '../types';

const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

export class ChatWebSocket {
  private ws: WebSocket | null = null;
  private jobId: string;
  private isIntentionalClose: boolean = false;

  constructor(jobId: string) {
    this.jobId = jobId;
  }

  connect(
    onMessage: (response: ChatResponse) => void,
    onError: (error: Event) => void
  ) {
    // Backend expects: /api/v1/chat/{job_id}
    const wsUrl = `${WS_BASE_URL}/api/v1/chat/${this.jobId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('[WebSocket] Connected to chat');
    };

    this.ws.onmessage = (event) => {
      try {
        const data: ChatResponse = JSON.parse(event.data);
        onMessage(data);
      } catch (error) {
        console.error('[WebSocket] Failed to parse message:', error);
      }
    };

    this.ws.onerror = (error) => {
      // Ignore errors from intentional close (React StrictMode double-mount)
      if (this.isIntentionalClose) {
        console.log('[WebSocket] Ignoring error from intentional close');
        return;
      }
      console.error('[WebSocket] Error:', error);
      onError(error);
    };

    this.ws.onclose = () => {
      console.log('[WebSocket] Disconnected');
    };
  }

  sendMessage(question: string, history: ChatMessage[]) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ question, history }));
    } else {
      console.error('[WebSocket] Connection not open');
    }
  }

  disconnect() {
    if (this.ws) {
      // Mark as intentional close to prevent error callback
      this.isIntentionalClose = true;
      this.ws.close();
      this.ws = null;
    }
  }
}
