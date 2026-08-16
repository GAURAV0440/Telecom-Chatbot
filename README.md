# 3GPP Standards RAG Chatbot

AI-powered Retrieval-Augmented Generation (RAG) chatbot focused on Telecom 3GPP standards, designed to minimize hallucinations through evidence-grounded generation and strict retrieval filtering.

## 1. Project Title

3GPP Standards RAG Chatbot

## 2. Short Professional Description

This project implements a production-style RAG assistant that answers questions only from indexed 3GPP documentation. The current indexed standard is TS 36.413 V19.2.0. The system combines hybrid retrieval (semantic + lexical), scope gating, and evidence-only answer generation to reduce unsupported responses.

## 3. Key Features

- Hybrid retrieval using semantic search and BM25 lexical search.
- Explicit in-scope/out-of-scope query handling before generation.
- Evidence filtering thresholds before sending context to the LLM.
- Evidence-only LLM prompting with refusal behavior for insufficient evidence.
- Source-aware responses including specification, version, and section path from retrieved evidence.
- FastAPI backend with a chat endpoint and Streamlit chat frontend.
- Built-in retrieval and LLM evaluation scripts.

## 4. Problem Statement

Generic LLM chatbots can hallucinate domain facts when asked technical telecom questions. For standards-heavy workflows, answers must be traceable to source text. The goal of this project is to answer telecom questions from 3GPP standards while rejecting unsupported or unrelated queries.

## 5. Solution Overview

The assistant uses a RAG architecture where answer generation is conditioned on retrieved chunks from indexed 3GPP content. If no sufficiently relevant evidence is found, the system refuses with a fixed response:

I don't have sufficient evidence in the provided 3GPP standards.

## 6. Architecture

~~~mermaid
flowchart TD
		A[3GPP Document] --> B[Document Processing and Chunking]
		B --> C[Text Embeddings via FastEmbed]
		C --> D[Qdrant Vector Index]
		B --> E[BM25 Lexical Index]
		D --> F[Hybrid Retrieval]
		E --> F
		F --> G[Scope and Relevance Filtering]
		G --> H[Retrieved 3GPP Evidence]
		H --> I[Groq LLM with Evidence-only Prompting]
		I --> J[Grounded Answer + Source References]
~~~

## 7. RAG Pipeline

1. A standards document is parsed and chunked.
2. Chunks are embedded with BAAI/bge-small-en-v1.5.
3. Embeddings are indexed in Qdrant.
4. BM25 lexical scoring is built from chunk text.
5. For each user query, semantic and lexical candidates are merged.
6. Scope checks and relevance thresholds select final evidence.
7. Groq generates an answer only from selected evidence.
8. If evidence is insufficient, the model returns the fixed refusal message.

## 8. Retrieval Strategy

The retrieval layer is implemented as hybrid retrieval:

- Semantic retrieval:
	- FastEmbed
	- Model: BAAI/bge-small-en-v1.5
	- Vector store: Qdrant
- Lexical retrieval:
	- BM25 via rank-bm25

Evidence candidates are ranked using weighted semantic score, normalized BM25 score, lexical overlap, and technical phrase matching. Final evidence must satisfy relevance conditions before being passed to answer generation.

The retrieval layer also includes:

- Scope checking
- Semantic score filtering
- Hybrid score filtering
- Lexical overlap filtering
- Technical phrase matching gates

## 9. Hallucination Mitigation

This system is designed to reduce hallucinations, not to guarantee zero hallucinations.

Implemented mechanisms:

1. Restricted knowledge source
	 - Evidence is retrieved from indexed 3GPP documentation only.
2. Scope filtering
	 - Known out-of-scope topics are explicitly rejected before answer generation.
3. Hybrid retrieval
	 - Semantic + BM25 retrieval improves evidence matching quality.
4. Evidence thresholds
	 - Chunks must pass relevance conditions to be considered valid evidence.
5. Evidence-only prompting
	 - The LLM is instructed to answer only from retrieved evidence.
6. Refusal behavior
	 - If evidence is missing or insufficient, a fixed refusal response is returned.
7. Source citations
	 - Answers are constrained to specification/version/section data present in retrieved evidence.

## 10. Technology Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI |
| Language | Python |
| Frontend | Streamlit |
| Embeddings | FastEmbed |
| Embedding Model | BAAI/bge-small-en-v1.5 |
| Vector Database | Qdrant (local path mode) |
| Lexical Retrieval | rank-bm25 |
| LLM Provider | Groq |
| Data Parsing | python-docx |
| Validation/Settings | Pydantic, pydantic-settings |

## 11. Project Structure

~~~text
3gpp-rag-chatbot/
├── LICENSE
├── README.md
├── requirements.txt
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── evaluate.py
│   │   ├── ingestion.py
│   │   ├── llm.py
│   │   ├── main.py
│   │   ├── rag.py
│   │   ├── retrieval.py
│   │   └── vector_store.py
│   ├── data/
│   │   ├── documents/
│   │   ├── processed/
│   │   └── qdrant/
│   └── tests/
│       └── evaluation_questions.json
└── frontend/
		└── app.py
~~~

Component responsibilities:

- backend/app/ingestion.py
	- Parses the source document and builds structured chunks with metadata.
- backend/app/vector_store.py
	- Embeds chunks and indexes them into Qdrant.
- backend/app/retrieval.py
	- Performs scope detection, hybrid retrieval, scoring, and evidence filtering.
- backend/app/llm.py
	- Builds evidence-only prompts and generates answers with Groq.
- backend/app/rag.py
	- Orchestrates retrieval + generation and refusal behavior.
- backend/app/main.py
	- Exposes API endpoints including POST /chat.
- backend/app/evaluate.py
	- Runs retrieval and LLM evaluation.
- frontend/app.py
	- Streamlit chat UI showing answers and retrieved 3GPP sources.

## 12. Installation

1. Clone the repository and move to the project root.
2. Create and activate a Python virtual environment.
3. Install dependencies.

~~~bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
~~~

## 13. Environment Configuration

Create a .env file in the project root.

~~~bash
cp .env.example .env
~~~

Set the required values (at minimum GROQ_API_KEY). Example safe template:

~~~env
APP_NAME=3GPP Standards RAG Assistant

GROQ_API_KEY=YOUR_GROQ_API_KEY
GROQ_MODEL=llama-3.3-70b-versatile

EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

QDRANT_PATH=./backend/data/qdrant
QDRANT_COLLECTION=3gpp_documents

TOP_K=10
BM25_TOP_K=10
SIMILARITY_THRESHOLD=0.65
~~~

## 14. Running the Backend

Before serving the API, ensure chunks and vector index are prepared:

~~~bash
python -m backend.app.ingestion
python -m backend.app.vector_store
~~~

Start FastAPI:

~~~bash
uvicorn backend.app.main:app --reload
~~~

## 15. Running the Frontend

Run the Streamlit chatbot UI:

~~~bash
streamlit run frontend/app.py
~~~

The frontend calls the backend chat API at:

http://127.0.0.1:8000/chat

## 16. API Usage

Primary endpoint:

- POST /chat

Request body:

~~~json
{
	"question": "What is the purpose of the S1AP Reset procedure?"
}
~~~

Response shape:

~~~json
{
	"answer": "...",
	"evidence": [
		{
			"chunk_id": 0,
			"text": "...",
			"section_path": "...",
			"specification": "TS 36.413",
			"version": "V19.2.0",
			"release": "...",
			"source_file": "...",
			"semantic_score": 0.0,
			"bm25_score": 0.0,
			"lexical_overlap": 0.0,
			"technical_phrase_score": 0.0,
			"hybrid_score": 0.0
		}
	]
}
~~~

## 17. Example Questions

In-scope examples:

- What services does S1AP provide?
- What is E-RAB setup in S1AP?
- What is the purpose of the S1AP Reset procedure?
- Explain the S1AP handover preparation procedure.
- What does the E-RAB SETUP REQUEST message contain?

Out-of-scope examples:

- What is the capital of France?
- Who is the Prime Minister of India?
- Explain Python decorators.
- What is NGAP?
- What is 5G NAS?
- What is the weather in Delhi today?
- Explain TCP congestion control.

Out-of-scope response:

I don't have sufficient evidence in the provided 3GPP standards.

## 18. Evaluation

Evaluation dataset:

- 25 total questions
- 15 in-scope 3GPP questions
- 10 out-of-scope questions

Run retrieval evaluation:

~~~bash
python -m backend.app.evaluate --retrieval-only
~~~

Run LLM spot evaluation (limited sample):

~~~bash
python -m backend.app.evaluate --llm --limit 3
~~~

## 19. Evaluation Results

- Retrieval evaluation: 25/25 tests passed, 100.0%
- LLM spot evaluation: 3/3 on the tested sample

Important interpretation:

- Retrieval results are from the full 25-question set.
- LLM result is a limited spot check and should not be interpreted as full-distribution LLM accuracy.

## 20. Limitations

- Current retrieval scope is tuned to the indexed TS 36.413 content.
- Out-of-scope detection is rule-based and depends on the configured term sets.
- LLM quality still depends on evidence quality and API availability.
- LLM evaluation currently uses a small sample to control API usage and rate limits.

## 21. Future Improvements

- Expand indexed standards coverage beyond the current scope.
- Add broader automated LLM evaluation with controlled cost/rate-limit strategy.
- Add stronger observability for retrieval and generation diagnostics.
- Add API and retrieval tests integrated into CI workflows.

## 22. Security / API Key Handling

- Store secrets only in .env.
- Never commit .env or real API keys to Git.
- Rotate API keys if exposure is suspected.

## 23. Technical Design Decisions

Why RAG:

- Directly grounds responses in standards evidence instead of relying on parametric memory.

Why hybrid retrieval (semantic + BM25):

- Semantic retrieval captures meaning-level similarity.
- BM25 improves lexical precision for protocol terms and exact phrases.
- Combined scoring improves robustness over either method alone.

Why evidence thresholds:

- Prevents weakly related chunks from reaching answer generation.

Why refusal behavior:

- Avoids unsupported answers when evidence is missing or insufficient.

Why source citations:

- Improves traceability and reviewability for technical answers.

Why Groq:

- Provides the hosted LLM endpoint used for answer generation in this implementation.

## 24. Interview Discussion Points

- How scope gating is implemented before retrieval and why this reduces irrelevant generations.
- How semantic, BM25, lexical overlap, and technical phrase features are combined.
- Trade-offs in threshold tuning for precision vs recall in evidence selection.
- Prompt constraints used to enforce evidence-only answering and refusal behavior.
- How to scale from single-standard indexing to multi-standard coverage while preserving grounding.
- How to design broader LLM evaluation without over-consuming API quota.
