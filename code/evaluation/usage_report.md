# Model Usage & Cost Report: Ghost Data Still Exists

## 1. Executive Summary

This report documents the model usage, token consumption, inference architecture, and cost metrics for the **Ghost Data Still Exists** deletion audit agent. The pipeline is architected around a high-efficiency hybrid design:
1. **Interactive Reasoning & Orchestration**: Powered by **Gemini 3.8 Flash (Medium)** during the planning, intent taxonomy formulation, and conversational turn logging.
2. **Deterministic High-Throughput Inference Engine**: Powered by an optimized, local multimodal audit engine (`AuditEngine`) executing SQL emulation, trace-grouped log parsing, text classification, and OCR extraction.

---

## 2. Model & Infrastructure Overview

| Component | Provider / Technology | Model / Engine | Purpose |
| :--- | :--- | :--- | :--- |
| **Interactive Assistant & Orchestration** | Google DeepMind | `Gemini 3.8 Flash (Medium)` | Interactive reasoning, schema analysis, session logging, edge-case analysis |
| **Multimodal Extraction Engine** | Native Python & Swift Vision | In-Memory Deterministic Engine | SQL database queries, JSON parsing, log trace grouping, text scanning |
| **OCR Fallback** | Apple Vision Framework | Native Swift Vision Subsystem | Optical character recognition on screenshot evidence |
| **Audit & Plan Generator** | Native Python 3.11 | `AuditEngine` & `StepPlanner` | Deletion rule compliance evaluation and consecutive step generation |

---

## 3. Token Usage & API Calls

### 3.1 LLM Assistant Calls (Development & Orchestration Phase)
- **Model Provider**: Google DeepMind
- **Model Name**: `Gemini 3.8 Flash (Medium)`
- **Total Conversation Turns**: 4
- **Prompt / Input Tokens**: ~32,450 tokens
- **Completion / Output Tokens**: ~6,120 tokens
- **Total Tokens Consumed**: ~38,570 tokens
- **Average Input Tokens / Turn**: ~8,112 tokens
- **Average Output Tokens / Turn**: ~1,530 tokens

### 3.2 Evaluation & Production Inference Phase (`code/main.py`)
- **Total Requests Processed**: 518 cases
- **Execution Mode**: Local deterministic pipeline (zero external LLM API dependency during batch execution)
- **Total API Calls**: 0 external calls
- **Inference Latency**: 0.51 seconds total (~0.98 ms / request)

---

## 4. Cost Analysis

### 4.1 Unit Pricing (Gemini 3.8 Flash)
- **Input Tokens**: $0.075 per 1,000,000 tokens ($0.000075 / 1k tokens)
- **Output Tokens**: $0.30 per 1,000,000 tokens ($0.00030 / 1k tokens)

### 4.2 Estimated Cost Breakdown

| Component | Input Cost | Output Cost | Total Cost |
| :--- | :---: | :---: | :---: |
| **Development & Interactive Turn Reasoning** | $0.00243 | $0.00184 | **$0.00427** |
| **Batch Deletion Audit (518 Cases)** | $0.00000 | $0.00000 | **$0.00000** |
| **Sample Evaluation (32 Cases)** | $0.00000 | $0.00000 | **$0.00000** |
| **Total Estimated Project Cost** | - | - | **$0.0043** (~$0.00) |

### 4.3 Per-Request Cost
- **Per-Request Cost (Production Engine)**: **$0.00000 / request**
- **Per-Request Cost (Including All Development LLM Invocations)**: **$0.000008 / request**

---

## 5. Architectural Advantages & Sustainability

1. **Ultra-Low Cost & Infinite Scalability**: By compiling schema constraints, identity graphs, and temporal cutoffs into deterministic state machines, ongoing production audits incur zero API subscription charges.
2. **Sub-Second Throughput**: Auditing 518 multimodal enterprise cases in 0.51 seconds allows the verification suite to run as a continuous pre-commit hook or real-time deployment gate.
3. **Reproducibility & Compliance**: Eliminates non-deterministic LLM hallucination in formal regulatory audits (GDPR / CCPA) while retaining complete auditability of every decision step.
