# AI-Based SOAR Automation for Cyber Incident Response - Currently building

An academic prototype of a **Security Orchestration, Automation, and Response (SOAR)** platform that leverages **rule-guided AI**, **explainable decision-making**, and **event-driven processing** to automate cyber incident response while retaining analyst control.

---

## Project Objectives

- Automate cyber incident detection and response using AI-assisted logic
- Reduce alert fatigue through intelligent scoring and prioritization
- Provide **explainable decisions** suitable for analyst review
- Demonstrate modern SOAR architecture using industry-relevant tools
- Maintain academic feasibility and interpretability

---

## High-Level Architecture

**Event-driven SOAR pipeline:**

Alert Sources → Kafka → Ingestion → Analysis → Explainability → Orchestration
↓
PostgreSQL
↓
React UI


Key characteristics:
- Decoupled ingestion via Kafka
- Rule-based + ML-assisted detection
- Human-in-the-loop response execution
- Full auditability and explainability

---

## Core Features

- **Kafka-based alert ingestion**
- **Schema-validated JSON alerts**
- **Rule-based risk scoring with configurable weights**
- **Machine learning classification (Scikit-learn)**
- **Explainable AI using SHAP**
- **Automated SOAR playbooks (YAML + Python)**
- **Redis-backed caching and rate tracking**
- **PostgreSQL persistence with JSONB**
- **Analyst dashboard for visibility and approval**

---

## Tech Stack

### Backend
- Python
- FastAPI
- Apache Kafka
- PostgreSQL
- Redis
- Scikit-learn
- SHAP
- Pandas / Polars (configurable)

### Frontend
- React

### Configuration & Automation
- YAML-based rules and playbooks
- JSON-based alert schemas

### Model Management
- Pickle / Joblib
- Timestamped model versions
- Metadata tracking via JSON

---



