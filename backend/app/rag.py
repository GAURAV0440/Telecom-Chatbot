from backend.app.retrieval import get_relevant_evidence
from backend.app.llm import generate_answer


def ask(question: str) -> dict:
    evidence = get_relevant_evidence(
        question,
        limit=5,
    )

    if not evidence:
        return {
            "answer": (
                "I don't have sufficient evidence in the provided "
                "3GPP standards."
            ),
            "evidence": [],
        }

    answer = generate_answer(
        question=question,
        evidence=evidence,
    )

    return {
        "answer": answer,
        "evidence": evidence,
    }


if __name__ == "__main__":

    question = "Explain the S1AP handover preparation procedure."

    result = ask(question)

    print("\nQUESTION:")
    print(question)

    print("\nANSWER:")
    print(result["answer"])

    print("\nSOURCES:")

    for item in result["evidence"]:
        print(
            f"- {item['specification']} "
            f"{item['version']} | "
            f"{item['section_path']}"
        )