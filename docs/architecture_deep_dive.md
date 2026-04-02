# 🏛️ Architecture Deep Dive: Logara AI

This document provides a detailed technical overview of how Logara AI processes logs and generates intelligence using LLMs and Vector Databases.

---

## 🛰️ High-Level Data Flow

1. **Ingestion**: Logs are collected from multiple sources (Docker, Kubernetes, System Logs, Application SDKs) and sent to the **Ingestion Service**.
2. **Preprocessing**: The logs are cleaned, timestamps are normalized, and metadata (service name, log level, host) is extracted.
3. **Embedding**: Each log entry is converted into a high-dimensional vector using a sentence-transformer model.
4. **Storage**: These vectors are stored in **Qdrant** (Vector DB) for fast semantic retrieval.
5. **Analysis**: When a user queries a log or an anomaly is detected, the **AI Engine** retrieves relevant context from the Vector DB and sends it to a **Local LLM** (via **Ollama**) for summarization and root cause analysis.

---

## 🛠️ Core Components

### 1. Ingestion Service

- **Purpose**: Acts as the entry point for all log data.
- **Tech Stack**: FastAPI / Node.js
- **Key Task**: Validates log formats and maintains high throughput using a buffer (Redis/Kafka).

### 2. AI Engine (The Brain)

- **Purpose**: Orchestrates the interaction between the data and the LLM.
- **Strategy**: Uses **RAG (Retrieval-Augmented Generation)** to provide the LLM with the most relevant historical logs when analyzing a current error.
- **Features**:
  - Semantic similarity search (find "logs like this").
  - Automated anomaly detection using density-based clustering.

### 3. Vector Database (Qdrant)

- **Purpose**: Enables lightning-fast searching across millions of log entries based on *meaning* rather than just keywords.
- **Why Qdrant?**: It's optimized for production and provides great filtering capabilities for metadata-heavy logs.

---

## 📊 Deployment Strategy

Logara AI is designed to be **Docker-first**. This means:

- Developers can spin up the entire stack (Backend, Frontend, Qdrant) with `docker-compose up`.
- It can be easily deployed to a Kubernetes cluster as a sidecar or a central logging service.

---

## 🛡️ Security & Privacy

- **PII Redaction**: Before logs are sent to the LLM, Logara AI includes an optional step to mask PII (Emails, IP Addresses, Passwords).
- **Local Model Support**: For air-gapped or privacy-sensitive environments, Logara AI can interface with local models via Ollama.
