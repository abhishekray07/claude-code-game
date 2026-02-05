#!/usr/bin/env node
/**
 * WebSocket router for Fly.io instance routing
 *
 * Handles fly-replay routing for WebSocket connections:
 * - If ?instance=X matches FLY_MACHINE_ID, proxy to ttyd
 * - If not, respond with fly-replay header to redirect
 */

const http = require('http');
const net = require('net');
const { URL } = require('url');

const TTYD_PORT = 7682;  // ttyd runs on this port internally
const ROUTER_PORT = 7681; // Router listens on the external port
const FLY_MACHINE_ID = process.env.FLY_MACHINE_ID || '';

console.log(`[router] Starting with FLY_MACHINE_ID: ${FLY_MACHINE_ID}`);
console.log(`[router] Listening on port ${ROUTER_PORT}, proxying to ttyd on ${TTYD_PORT}`);

const server = http.createServer((req, res) => {
  // Handle regular HTTP requests (token endpoint, static files)
  const url = new URL(req.url, `http://${req.headers.host}`);
  const targetInstance = url.searchParams.get('instance');

  // Check if we need to redirect
  if (targetInstance && FLY_MACHINE_ID && targetInstance !== FLY_MACHINE_ID) {
    console.log(`[router] HTTP redirect from ${FLY_MACHINE_ID} to ${targetInstance}`);
    res.writeHead(307, {
      'fly-replay': `instance=${targetInstance}`
    });
    res.end();
    return;
  }

  // Proxy to ttyd
  const options = {
    hostname: '127.0.0.1',
    port: TTYD_PORT,
    path: req.url,
    method: req.method,
    headers: req.headers
  };

  const proxyReq = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res);
  });

  proxyReq.on('error', (err) => {
    console.error(`[router] Proxy error: ${err.message}`);
    res.writeHead(502);
    res.end('Bad Gateway');
  });

  req.pipe(proxyReq);
});

// Handle WebSocket upgrade requests
server.on('upgrade', (req, socket, head) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const targetInstance = url.searchParams.get('instance');

  console.log(`[router] WebSocket upgrade request, target: ${targetInstance}, current: ${FLY_MACHINE_ID}`);

  // Check if we need to redirect via fly-replay
  if (targetInstance && FLY_MACHINE_ID && targetInstance !== FLY_MACHINE_ID) {
    console.log(`[router] Replaying WebSocket from ${FLY_MACHINE_ID} to ${targetInstance}`);
    socket.write(
      'HTTP/1.1 307 Temporary Redirect\r\n' +
      `fly-replay: instance=${targetInstance}\r\n` +
      '\r\n'
    );
    socket.destroy();
    return;
  }

  console.log(`[router] Proxying WebSocket to ttyd`);

  // Connect to ttyd
  const ttydSocket = net.connect(TTYD_PORT, '127.0.0.1', () => {
    // Forward the original upgrade request to ttyd
    const headers = Object.entries(req.headers)
      .map(([k, v]) => `${k}: ${v}`)
      .join('\r\n');

    ttydSocket.write(
      `${req.method} ${req.url} HTTP/1.1\r\n` +
      `${headers}\r\n` +
      '\r\n'
    );

    // Send any buffered data
    if (head.length > 0) {
      ttydSocket.write(head);
    }

    // Bidirectional pipe
    socket.pipe(ttydSocket);
    ttydSocket.pipe(socket);
  });

  ttydSocket.on('error', (err) => {
    console.error(`[router] ttyd connection error: ${err.message}`);
    socket.destroy();
  });

  socket.on('error', (err) => {
    console.error(`[router] Client socket error: ${err.message}`);
    ttydSocket.destroy();
  });

  socket.on('close', () => {
    ttydSocket.destroy();
  });

  ttydSocket.on('close', () => {
    socket.destroy();
  });
});

server.listen(ROUTER_PORT, '0.0.0.0', () => {
  console.log(`[router] Router listening on 0.0.0.0:${ROUTER_PORT}`);
});
