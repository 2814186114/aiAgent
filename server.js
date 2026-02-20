const express = require('express');
const { createServer } = require('http');
const { Server } = require('socket.io');
const WebSocket = require('ws');

const app = express();
const httpServer = createServer(app);
const ALLOWED_ORIGINS = process.env.ALLOWED_ORIGINS || 'http://localhost:5173,http://localhost:3000';
const io = new Server(httpServer, {
    cors: {
        origin: ALLOWED_ORIGINS.split(','),
        methods: ['GET', 'POST'],
    },
});

const PORT = 3001;
const PYTHON_PORT = 8000;

app.use(express.json());

app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        service: 'node-server',
        timestamp: new Date().toISOString(),
        pythonConnected: pythonWs !== null && pythonWs.readyState === WebSocket.OPEN,
    });
});

app.get('/api/status', async (req, res) => {
    try {
        const response = await fetch(`http://localhost:${PYTHON_PORT}/health`);
        const data = await response.json();
        res.json({
            node: 'running',
            python: 'running',
            llmConfigured: data.llm_configured,
        });
    } catch (error) {
        res.json({
            node: 'running',
            python: 'unreachable',
            error: error.message,
        });
    }
});

let pythonWs = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 10;
const reconnectInterval = 3000;

function connectToPython() {
    console.log('Attempting to connect to Python WebSocket...');

    pythonWs = new WebSocket(`ws://localhost:${PYTHON_PORT}/ws`);

    pythonWs.on('open', () => {
        console.log('Connected to Python WebSocket');
        reconnectAttempts = 0;
    });

    pythonWs.on('message', (data) => {
        try {
            const message = JSON.parse(data.toString());
            console.log('Received from Python:', message.type);

            if (message.type === 'step') {
                io.emit('agent-step', message.data);
            } else if (message.type === 'complete') {
                io.emit('agent-complete', message.data);
            }
        } catch (err) {
            console.error('Error parsing Python message:', err);
        }
    });

    pythonWs.on('close', () => {
        console.log('Python WebSocket connection closed');
        pythonWs = null;

        if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            console.log(`Reconnecting in ${reconnectInterval / 1000}s (attempt ${reconnectAttempts}/${maxReconnectAttempts})`);
            setTimeout(connectToPython, reconnectInterval);
        }
    });

    pythonWs.on('error', (err) => {
        console.error('Python WebSocket error:', err.message);
    });
}

connectToPython();

io.on('connection', (socket) => {
    console.log(`Client connected: ${socket.id}`);

    socket.emit('connection-status', {
        pythonConnected: pythonWs !== null && pythonWs.readyState === WebSocket.OPEN,
    });

    socket.on('user-message', async (data) => {
        console.log(`Received message from ${socket.id}:`, data.message);

        if (pythonWs && pythonWs.readyState === WebSocket.OPEN) {
            pythonWs.send(JSON.stringify({
                type: 'task',
                message: data.message,
                sessionId: socket.id,
                timestamp: new Date().toISOString(),
            }));
        } else {
            try {
                const response = await fetch(`http://localhost:${PYTHON_PORT}/process`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: data.message,
                        sessionId: socket.id,
                    }),
                });

                const result = await response.json();

                if (result.steps) {
                    for (const step of result.steps) {
                        socket.emit('agent-step', step);
                        await new Promise(resolve => setTimeout(resolve, 300));
                    }
                }

                socket.emit('agent-complete', {
                    answer: result.answer,
                    total_steps: result.steps?.length || 0,
                    iterations: result.iterations,
                });

            } catch (error) {
                console.error('Error communicating with Python service:', error);
                socket.emit('agent-error', {
                    message: `Error: Could not connect to AI service. Please check if Python server is running.`,
                });
            }
        }
    });

    socket.on('disconnect', () => {
        console.log(`Client disconnected: ${socket.id}`);
    });
});

httpServer.listen(PORT, () => {
    console.log(`Node.js server running on http://localhost:${PORT}`);
    console.log(`WebSocket server ready for connections`);
});

process.on('SIGTERM', () => {
    console.log('SIGTERM received, shutting down gracefully');
    if (pythonWs) pythonWs.close();
    httpServer.close(() => {
        console.log('Server closed');
        process.exit(0);
    });
});

process.on('SIGINT', () => {
    console.log('SIGINT received, shutting down gracefully');
    if (pythonWs) pythonWs.close();
    httpServer.close(() => {
        console.log('Server closed');
        process.exit(0);
    });
});
