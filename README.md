# 🌾 Prakriti - Agentic KG-RAG System for Indian Agriculture
An intelligent agricultural advisory system that combines Knowledge Graphs with Retrieval-Augmented Generation (RAG) to provide contextual, multilingual agricultural advice to Indian farmers.

## 🚀 Features
- Knowledge Graph Integration: Neo4j AuraDB with comprehensive agricultural data
- RAG Pipeline: LangChain-powered retrieval combining structured and unstructured data
- Autonomous Agent: Real-time updates with pest alerts, weather events, and disease outbreaks
- Interactive Chat: Natural language interface for agricultural queries
- Graph Visualization: Visual exploration of agricultural knowledge relationships
- Real-time Events: Live updates on agricultural conditions and alerts

## 🏗️ Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React Frontend │────│   FastAPI Backend │────│   Neo4j AuraDB  │
│   (Port 5173)   │    │   (Port 8000)    │    │   (Cloud)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │                        │                        │
    ┌─────────┐              ┌─────────┐              ┌─────────┐
    │ Chat UI │              │   RAG   │              │ Knowledge│
    │ Graph   │              │Pipeline │              │  Graph   │
    │Visualiz.│              │LangChain│              │   Data   │
    └─────────┘              └─────────┘              └─────────┘
```

## 📋 Prerequisites
- Node.js 18+ and pnpm
- Python 3.11+
- Neo4j AuraDB account (configured in .env)
- OpenAI API key (for LLM functionality)
