from groq import APIConnectionError, APIStatusError, Groq, RateLimitError

from backend.app.config import settings


INSUFFICIENT_EVIDENCE = (
    "I don't have sufficient evidence in the provided "
    "3GPP standards."
)


client = Groq(
    api_key=settings.groq_api_key
)


SYSTEM_INSTRUCTION = """
You are a 3GPP Telecom Standards Assistant.

Use ONLY the 3GPP evidence supplied in the user message.

Rules:

1. Answer ONLY from the supplied evidence.
2. Do not use outside knowledge.
3. Do not invent, assume, or infer unsupported technical facts.
4. Give a complete answer when the supplied evidence supports it.
5. Answer exactly what the user asked.
6. Prioritize evidence that directly addresses the question.
7. Use supporting evidence only when it is necessary to make the answer
   complete.
8. Do not discuss related procedures, messages, timers, causes, or functions
   unless they are directly relevant to answering the question.
9. Do not add unrelated information.
10. Preserve the terminology used in the 3GPP specification.
11. Every factual claim must be supported by the supplied evidence.
12. Use only specification, version, and section information present in the
    supplied evidence.
13. Never invent, modify, or guess a citation or section number.
14. Cite important factual statements using:
    [Specification Version, Section X]
15. If the supplied evidence does not sufficiently answer the question,
    return exactly:

I don't have sufficient evidence in the provided 3GPP standards.

16. Do not mention retrieval, embeddings, BM25, Qdrant, Groq, prompts, or
    internal system details.
17. Keep the answer concise, technically accurate, and well structured.
"""


def generate_answer(
    question: str,
    evidence: list[dict],
) -> str:

    question = (question or "").strip()

    if not question or not evidence:
        return INSUFFICIENT_EVIDENCE

    evidence_parts = []

    for index, item in enumerate(evidence, start=1):

        text = str(
            item.get("text", "")
        ).strip()

        specification = str(
            item.get("specification", "")
        ).strip()

        version = str(
            item.get("version", "")
        ).strip()

        section = str(
            item.get("section_path", "")
        ).strip()

        if not text or not specification or not version or not section:
            continue

        evidence_parts.append(
            f"[Evidence {index}]\n"
            f"Specification: {specification} {version}\n"
            f"Section: {section}\n"
            f"Content:\n{text}"
        )

    if not evidence_parts:
        return INSUFFICIENT_EVIDENCE

    evidence_text = "\n\n".join(evidence_parts)

    prompt = f"""
Question:
{question}

3GPP Evidence:
{"\n\n".join(evidence_parts)}

Answer the question using ONLY the evidence above.

Follow these requirements:

- First identify the evidence that directly answers the question.
- Use the most directly relevant evidence as the primary basis of the answer.
- Use other evidence only when it provides necessary supporting details.
- Give a complete answer, but do not unnecessarily expand into related
  procedures or topics.
- Do not include information merely because it appears in the evidence.
- Do not use outside knowledge.
- Do not speculate or fill missing information.
- Preserve 3GPP terminology.
- Cite important factual claims using the exact specification, version,
  and section provided in the evidence.
- Never invent a citation.
- If the evidence does not sufficiently answer the question, return exactly:

{INSUFFICIENT_EVIDENCE}
"""

    try:
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0,
            max_completion_tokens=2048,
        )

        if not response.choices:
            return INSUFFICIENT_EVIDENCE

        answer = response.choices[0].message.content

        if not answer or not answer.strip():
            return INSUFFICIENT_EVIDENCE

        answer = answer.strip()

        # Prevent mixed responses such as:
        # "Here is the answer..." + refusal message.
        if INSUFFICIENT_EVIDENCE in answer:
            return INSUFFICIENT_EVIDENCE

        return answer

    except RateLimitError:
        return (
            "The Groq API rate limit has been exceeded. "
            "Please retry later."
        )

    except APIStatusError as exc:

        if exc.status_code in (401, 403):
            return (
                "The Groq API authentication failed. "
                "Please check the configured API key."
            )

        if exc.status_code == 404:
            return (
                "The configured Groq model is unavailable. "
                "Please check the GROQ_MODEL setting."
            )

        if exc.status_code == 400:
            return (
                "The Groq API rejected the request. "
                "Please check the model configuration."
            )

        return (
            "The Groq API request could not be completed. "
            "Please retry later."
        )

    except APIConnectionError:
        return (
            "The Groq API could not be reached. "
            "Please check the network connection and retry."
        )

    except Exception:
        return (
            "The answer generation service encountered an unexpected error. "
            "Please retry later."
        )