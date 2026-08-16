import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000/chat"


st.set_page_config(
    page_title="3GPP Standards Assistant",
    page_icon="📡",
    layout="centered",
)

st.title("📡 3GPP Standards Assistant")
st.caption(
    "Ask questions about the indexed 3GPP standards document."
)


if "messages" not in st.session_state:
    st.session_state.messages = []


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant" and message.get("sources"):
            with st.expander("3GPP Sources"):
                for source in message["sources"]:
                    st.markdown(
                        f"**{source['specification']} "
                        f"{source['version']}**  \n"
                        f"Section: {source['section_path']}"
                    )


question = st.chat_input(
    "Ask a question about the 3GPP standard..."
)


if question:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):

        with st.spinner("Searching 3GPP standards..."):

            try:
                response = requests.post(
                    API_URL,
                    json={"question": question},
                    timeout=120,
                )

                response.raise_for_status()

                data = response.json()

                answer = data["answer"]
                evidence = data.get("evidence", [])

                st.markdown(answer)

                if evidence:
                    with st.expander("3GPP Sources"):
                        for source in evidence:
                            st.markdown(
                                f"**{source['specification']} "
                                f"{source['version']}**  \n"
                                f"Section: {source['section_path']}"
                            )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": evidence,
                    }
                )

            except requests.RequestException as exc:

                error = (
                    "Unable to connect to the RAG backend. "
                    "Make sure FastAPI is running."
                )

                st.error(error)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error,
                        "sources": [],
                    }
                )