# Comfortnet__
Technology integrated with nature

### Intelligent IoT Infrastructure Monitoring & Predictive Maintenance

> **From real-time monitoring to proactive infrastructure intelligence.**

ComfortNet is a software prototype for intelligent monitoring of connected infrastructure. It combines real-time telemetry, environmental monitoring, system-health analytics, a digital-twin-style dashboard, deterministic failure scenarios, and a predictive-maintenance ML prototype into a single platform.

---

## 🚀 Live Demo
👉 **[Open ComfortNet Live Demo] https://comfortnet-znen.vercel.app/

## 🎯 Problem

Connected infrastructure can generate large amounts of telemetry, but raw sensor data alone does not provide actionable insight.

Operators need to know:

- What is happening now?
- Is the infrastructure operating normally?
- Is a component approaching an abnormal condition?
- What happens when a critical condition occurs?
- How can maintenance become proactive instead of reactive?

ComfortNet addresses these challenges through a unified monitoring and predictive-maintenance platform.

---

## 💡 Solution

ComfortNet combines:

- 📡 Real-time telemetry simulation
- 🌡️ Environmental monitoring
- 🔋 Battery and solar-status monitoring
- 🌬️ Air-quality monitoring
- 🖥️ Interactive infrastructure dashboard
- 🔧 Deterministic failure/demo scenarios
- 🤖 Predictive-maintenance ML prototype
- ⚙️ FastAPI backend services
- 🧪 Automated backend testing

### Core flow

```text
Telemetry / Simulator
        ↓
   FastAPI Backend
        ↓
 ┌──────┴─────────┐
 ↓                ↓
Analytics          ML
 ↓                ↓
 └──────┬─────────┘
        ↓
 ComfortNet Dashboard
        ↓
 Action / Maintenance Insight

### Current status;

ML prototype:              ✅ Implemented
Synthetic-data testing:   ✅ Implemented
Backend integration:       ✅ Implemented
Real field data:           ❌ Not yet collected
Field validation:          ❌ Not yet performed

### Comfortnet-backend/

│
├── app/
│   └── FastAPI backend services
│
├── ml/
│   ├── artifacts/
│   ├── features.py
│   ├── predict.py
│   └── ML components
│
├── simulator/
│   └── simulate_telemetry.py
│
├── tests/
│   └── automated backend tests
│
├── requirements.txt
├── README.md
└── ...

### 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | HTML, CSS, JavaScript |
| **Deployment** | Vercel |
| **Backend** | Python, FastAPI, Uvicorn |
| **API** | REST APIs, Swagger / OpenAPI |
| **Machine Learning** | Python, scikit-learn, Predictive-Maintenance ML |
| **Data & Simulation** | Python telemetry simulator, Synthetic IoT telemetry |
| **Testing** | pytest, Automated backend tests |
| **Development** | VS Code, GitHub, GitHub Desktop |
| **Architecture** | IoT Telemetry → FastAPI → Analytics/ML → Dashboard |
______THANK YOU______