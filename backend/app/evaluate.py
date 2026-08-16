import argparse
import json
import requests

from backend.app.retrieval import get_relevant_evidence


API_URL = "http://127.0.0.1:8000/chat"
TEST_FILE = "backend/tests/evaluation_questions.json"

REFUSAL = (
    "I don't have sufficient evidence in the provided "
    "3GPP standards."
)


def load_tests():
    with open(TEST_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def evaluate_retrieval(tests):
    passed = 0

    print("=" * 80)
    print("3GPP RAG — RETRIEVAL EVALUATION")
    print("=" * 80)

    for i, test in enumerate(tests, 1):
        question = test["question"]
        expected = test["expected"]

        try:
            evidence = get_relevant_evidence(
                question,
                limit=5,
            )

            if expected == "answer":
                success = len(evidence) > 0
            else:
                success = len(evidence) == 0

            status = "PASS" if success else "FAIL"

            if success:
                passed += 1

            print(f"\n[{status}] Test {i}")
            print(f"Question: {question}")
            print(f"Expected: {expected}")
            print(f"Evidence: {len(evidence)}")

        except Exception as exc:
            print(f"\n[ERROR] Test {i}")
            print(f"Question: {question}")
            print(f"Error: {exc}")

    total = len(tests)
    accuracy = (passed / total) * 100 if total else 0

    print("\n" + "=" * 80)
    print(f"RESULT: {passed}/{total} tests passed")
    print(f"Retrieval Accuracy: {accuracy:.1f}%")
    print("=" * 80)


def evaluate_llm(tests):
    passed = 0

    print("=" * 80)
    print("3GPP RAG — LLM EVALUATION")
    print("=" * 80)

    for i, test in enumerate(tests, 1):
        question = test["question"]
        expected = test["expected"]

        try:
            response = requests.post(
                API_URL,
                json={"question": question},
                timeout=120,
            )
            response.raise_for_status()

            data = response.json()

            answer = data.get("answer", "").strip()
            evidence = data.get("evidence", [])

            if expected == "answer":
                success = (
                    len(evidence) > 0
                    and bool(answer)
                    and answer != REFUSAL
                    and "Groq API rate limit" not in answer
                    and "Groq API" not in answer
                )
            else:
                success = answer == REFUSAL

            status = "PASS" if success else "FAIL"

            if success:
                passed += 1

            print(f"\n[{status}] Test {i}")
            print(f"Question: {question}")
            print(f"Expected: {expected}")
            print(f"Evidence: {len(evidence)}")
            print(f"Answer: {answer}")

        except Exception as exc:
            print(f"\n[ERROR] Test {i}")
            print(f"Question: {question}")
            print(f"Error: {exc}")

    total = len(tests)
    accuracy = (passed / total) * 100 if total else 0

    print("\n" + "=" * 80)
    print(f"RESULT: {passed}/{total} tests passed")
    print(f"LLM Accuracy: {accuracy:.1f}%")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate the 3GPP RAG system."
    )

    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="Evaluate retrieval without calling the LLM.",
    )

    parser.add_argument(
        "--llm",
        action="store_true",
        help="Evaluate the API and LLM responses.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of tests for LLM evaluation.",
    )

    args = parser.parse_args()

    tests = load_tests()

    if args.retrieval_only:
        evaluate_retrieval(tests)
        return

    if args.llm:
        selected_tests = (
            tests[:args.limit]
            if args.limit
            else tests
        )
        evaluate_llm(selected_tests)
        return

    evaluate_retrieval(tests)


if __name__ == "__main__":
    main()