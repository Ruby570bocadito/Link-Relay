<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=0,2,3,6&height=200&section=header&text=Link-Relay&fontSize=60&fontAlignY=38&desc=Minimalist%20Encrypted%20Relay%20Server&descAlignY=55&descSize=18&animation=fadeIn" width="100%"/>
</p>

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=20&pause=1000&color=00F7FF&center=true&vCenter=true&width=600&lines=Secure+Point-to-Point+Communication;Encrypted+Covert+C2+Channel;Minimalist+Relay+Server;Zero-Latency+Message+Routing" alt="Typing SVG" />
</p>

<p align="center">
  <img src="https://img.shields.io/github/license/Ruby570bocadito/Link-Relay?style=for-the-badge&labelColor=0d1117&color=00f7ff" />
  <img src="https://img.shields.io/github/v/release/Ruby570bocadito/Link-Relay?style=for-the-badge&labelColor=0d1117&color=00f7ff&include_prereleases" />
  <img src="https://img.shields.io/github/last-commit/Ruby570bocadito/Link-Relay?style=for-the-badge&labelColor=0d1117&color=00f7ff" />
  <img src="https://img.shields.io/github/stars/Ruby570bocadito/Link-Relay?style=for-the-badge&labelColor=0d1117&color=00f7ff" />
  <img src="https://img.shields.io/github/issues/Ruby570bocadito/Link-Relay?style=for-the-badge&labelColor=0d1117&color=00f7ff" />
  <img src="https://img.shields.io/github/repo-size/Ruby570bocadito/Link-Relay?style=for-the-badge&labelColor=0d1117&color=00f7ff" />
</p>

---

## 🔥 Overview

**Link-Relay** is a minimalist encrypted relay server designed for secure point-to-point communication channels. Originally built for covert C2 (Command & Control) operations, it provides a lightweight, low-latency tunnel between clients and targets through an encrypted relay layer.

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   ┌────────┐     ┌──────────────────┐     ┌──────────────┐     │
│   │ Client │◄───►│ Encrypted Tunnel │◄───►│ Relay Server │◄───►│
│   └────────┘     └──────────────────┘     └──────────────┘     │
│                                                      │          │
│                                                      ▼          │
│                                              ┌──────────────┐   │
│                                              │    Target    │   │
│                                              └──────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Architecture Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant T as Encrypted Tunnel
    participant R as Relay Server
    participant TG as Target

    C->>T: Encrypt & Send Payload
    T->>R: Relay Encrypted Packet
    R->>R: Decrypt & Route
    R->>TG: Forward Decrypted Command
    TG->>R: Encrypt & Send Response
    R->>T: Relay Response
    T->>C: Decrypt & Deliver
    
    Note over C,TG: End-to-End Encryption
    Note over R: No Persistent Storage
```

---

## ⚡ Quick Start

```bash
# Clone the repository
git clone https://github.com/Ruby570bocadito/Link-Relay.git
cd Link-Relay

# Install dependencies
# (adjust based on your implementation - Python/Go/Node)
pip install -r requirements.txt
# or
go mod download
# or
npm install

# Start the relay server
python relay_server.py --port 8080 --key ./server.key

# Connect a client
python client.py --relay localhost:8080 --target example.com:443
```

---

## 📡 API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/relay/connect` | Establish encrypted relay session | Token |
| `POST` | `/relay/send` | Send encrypted payload through relay | Session |
| `GET` | `/relay/poll` | Poll for incoming messages | Session |
| `POST` | `/relay/disconnect` | Terminate relay session | Session |
| `GET` | `/health` | Server health check | None |
| `GET` | `/status` | Relay server status & metrics | None |

---

## 🛡️ Security

- **End-to-end encryption** — payloads are encrypted client-side and only decrypted at the target
- **No persistent logging** — relay server never stores messages to disk
- **Session isolation** — each relay session is cryptographically isolated
- **Forward secrecy** — ephemeral key exchange per session

---

## 📦 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LISTEN_PORT` | `8080` | Relay server listen port |
| `TLS_CERT` | — | Path to TLS certificate |
| `TLS_KEY` | — | Path to TLS key |
| `MAX_SESSION_TTL` | `3600s` | Maximum session lifetime |
| `RATE_LIMIT` | `100/s` | Incoming request rate limit |

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

<p align="center">
  <b>Link-Relay</b> — <i>Minimalist Encrypted Relay Server</i><br>
  Built with 🔥 by <a href="https://github.com/Ruby570bocadito">Ruby570bocadito</a>
</p>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=0,2,3,6&height=120&section=footer&text=Secure.%20Stealthy.%20Reliable.&fontSize=20&fontAlignY=70" width="100%"/>
</p>
