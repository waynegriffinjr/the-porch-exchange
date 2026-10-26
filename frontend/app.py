# frontend/app.py
import base64
import time
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from api_client import (
    ask_documents_stream,
    create_need,
    create_skill,
    delete_skill,
    get_health,
    get_needs,
    get_skills,
    login,
    reindex_documents,
    update_need_met,
)

# Streamlit frontend for the needs app
st.set_page_config(
    page_title="Needs Manager Dashboard",
    page_icon="🔐",
    layout="wide",
)


@st.cache_resource
def background_css() -> str:
    """Faded community photo behind every page (login and dashboard)."""
    image = Path(__file__).parent / "BlanchesterOH2.JPG"
    if not image.exists():
        return ""
    encoded = base64.b64encode(image.read_bytes()).decode()
    return (
        "<style>.stApp::before{content:'';position:fixed;inset:0;z-index:0;"
        f"background:url(data:image/jpeg;base64,{encoded}) center/cover no-repeat;"
        "opacity:0.18;pointer-events:none;}"
        ".stApp > header{background:transparent;}"
        ".block-container,[data-testid='stSidebar']{position:relative;z-index:1;}</style>"
    )


st.markdown(background_css(), unsafe_allow_html=True)

# Initialize session state for authentication token and username
if "token" not in st.session_state:
    st.session_state["token"] = None
    st.session_state["username"] = None

# --- Auth Gate ---
if st.session_state["token"] is None:
    # Show login form
    st.markdown(
        """
        <style>
        .porch-title{font-family:'Bell MT','Bell MT Std',Baskerville,'Palatino Linotype',Georgia,serif;
            color:#000080;text-align:center;font-size:2.8rem;font-weight:600;margin:1rem 0 1.5rem;}
        [data-testid="stForm"]{background-color:#89CFF0;border:2px solid #000080;border-radius:10px;}
        [data-testid="stForm"] input{background-color:#E3F2FD;}
        </style>
        <div class="porch-title">The Blanchester Porch Exchange</div>
        """,
        unsafe_allow_html=True,
    )
    st.subheader("🔐 Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            try:
                token = login(username, password)
                if token:
                    st.session_state["token"] = token
                    st.session_state["username"] = username
                    st.rerun()
                else:
                    st.error("Invalid credentials")
            except requests.exceptions.Timeout:
                st.error("The API took too long to respond. Please try again.")
            except requests.exceptions.RequestException as error:
                st.error(f"Could not connect to the API: {error}")
            except Exception as error:
                st.error(f"An error occurred: {error}")
    # Stop execution here if not authenticated
    st.stop()


else:
    with st.sidebar:
        # user displayed in sidebar
        st.sidebar.write(f"Logged in as: {st.session_state['username']}")
        # Logout button for the user
        if st.button("Logout"):
            st.session_state["token"] = None
            st.session_state["username"] = None
            st.rerun()

        # Backend / document index status
        st.divider()
        health = get_health()
        if health:
            st.success("API: Connected")
            st.write(f"Ollama: {health.get('ollama', 'unknown')}")
            st.metric("Indexed document chunks", health.get("documents", 0))
        else:
            st.error("API not available")

    # Show the actual app
    st.title("My Dashboard")
    st.header("Be a Neighbor Today.")

    token = st.session_state["token"]
    username = st.session_state["username"]

    st.divider()

    # Display a welcome message to the authenticated user
    st.subheader(f"Welcome, {st.session_state['username']}")

    # Create tabs for different sections of the dashboard
    overview, needs_tab, new_need_tab, skills_tab, ai_tab, docs_tab = st.tabs(
        ["Overview", "Needs", "Add New Need", "Skills I Can Offer", "AI Assistant", "Community Documents"]
    )

    # Fetch needs from the API using the authenticated token
    needs = get_needs(token)
    try:
        if needs == "unauthorized":
            st.error("Session expired. Please log in again.")
            st.session_state["token"] = None
            st.session_state["username"] = None
            st.rerun()
    except Exception as error:
        st.error(f"An error occurred while fetching needs: {error}")

    # Handle the case where no needs are returned from the API
    if needs is None:
        st.info("No need data was returned from the API.")
        needs = []

    # Handle the case where the API returns an error message as a string
    if isinstance(needs, str):
        st.error(needs)

    else:
        with overview:
            st.caption("Want to use the AI Assistant? [Get a free Groq API key](https://console.groq.com/keys)")
            # Metrics row
            stats = {
                "total": len(needs),
                "done": len([need for need in needs if need.get("completed")]),
                "pending": len([need for need in needs if not need.get("completed")]),
            }
            if stats:
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Needs:", stats["total"])
                c2.metric("Needs Met:", stats["done"])
                c3.metric("Open Needs:", stats["pending"])

            # Display the needs in a data table for easier viewing
            st.subheader("Data Table")
            need_df = pd.DataFrame(needs).rename(columns={"completed": "need_met"})
            st.dataframe(need_df, use_container_width=True)

            chart_df = pd.DataFrame(
                {
                    "Status": ["Needs Met", "Open"],
                    "Count": [stats["done"], stats["pending"]],
                }
            ).set_index("Status")  # Sets the row labels to the "Status" column

            st.bar_chart(chart_df)

        with needs_tab:
            st.subheader("Needs Overview:")
            # Display each need in the list of needs

            if needs:
                for need in needs:
                    need_id = need.get("id")
                    need_met = bool(need.get("completed", False))

                    met = st.checkbox(
                        f"Need Met: {need['title']}",
                        value=need_met,
                        key=f"met_{need_id}",
                    )
                    if met != need_met:
                        update_need_met(token, need_id, met)
                        st.rerun()

        with new_need_tab:
            st.subheader("Add New Need")
            if st.session_state.pop("need_added", False):
                st.success("Need added successfully!")
            with st.form("add_need_form", clear_on_submit=True):
                title = st.text_input("Need Title")
                description = st.text_area("Need Description")
                submitted = st.form_submit_button("Add Need")
                if submitted:
                    if not title.strip():
                        st.error("Please enter a title for the need.")
                    else:
                        try:
                            if create_need(token, title.strip(), description):
                                st.session_state["need_added"] = True
                                st.rerun()
                            else:
                                st.error("Failed to add need.")
                        except Exception as error:
                            st.error(f"An error occurred while adding the need: {error}")

        with skills_tab:
            st.subheader("Skills I Can Offer")
            st.caption("Share what you can do to help your neighbors.")
            if st.session_state.pop("skill_added", False):
                st.success("Skill added successfully!")
            with st.form("add_skill_form", clear_on_submit=True):
                skill_name = st.text_input("Skill")
                skill_description = st.text_area("Details (availability, experience, etc.)")
                if st.form_submit_button("Add Skill"):
                    if not skill_name.strip():
                        st.error("Please enter a skill.")
                    else:
                        try:
                            if create_skill(token, skill_name.strip(), skill_description):
                                st.session_state["skill_added"] = True
                                st.rerun()
                            else:
                                st.error("Failed to add skill.")
                        except Exception as error:
                            st.error(f"An error occurred while adding the skill: {error}")
            skills = get_skills(token)
            if isinstance(skills, list) and skills:
                for skill in skills:
                    col_text, col_btn = st.columns([5, 1])
                    with col_text:
                        st.write(f"**{skill['name']}**")
                        if skill.get("description"):
                            st.caption(skill["description"])
                    with col_btn:
                        if st.button("Remove", key=f"skill_del_{skill['id']}"):
                            delete_skill(token, skill["id"])
                            st.rerun()
            else:
                st.info("You haven't listed any skills yet.")

        with ai_tab:
            st.subheader("AI Assistant to help you identify skills you can offer your community")
            # AI assistant content goes here
            # COVERSATION MEMORY: SESSION_STATE
            if "messages" not in st.session_state:
                st.session_state.messages = []

            # SIDEBAR SETUP
            with st.sidebar:
                st.markdown(
                    """
                <style>
                    .sidebar-title {
                        text-align: center;
                        font-size: 24px;
                        font-weight: 600;
                        margin-top: -10px;
                    }
                </style>
                <div class="sidebar-title">⚙️ Customizeable Settings</div>
                """,
                    unsafe_allow_html=True,
                )
                # API KEY OPTIONAL ENTRY
                api_key = st.text_input("Groq API Key", type="password", placeholder="sk-... (optional)")

                use_real_api = api_key and len(api_key) > 10
                if use_real_api:
                    st.success("Using real API key")
                else:
                    st.info("Using default API key")

                st.divider()

                # DISPLAY MESSAGE COUNT
                st.metric("Messages", len(st.session_state["messages"]))

                # COPY CONVERSATION BUTTON
                export_text = ""
                if st.sidebar.button("📋 Copy Conversation"):
                    if st.session_state["messages"]:
                        for msg in st.session_state["messages"]:
                            role = "You" if msg["role"] == "user" else "AI"
                            export_text += f"{role}: {msg['content']}\\n\\n"

                        st.sidebar.code(export_text, language=None)
                        st.sidebar.caption("Select all the text above and copy it (Cmd/Ctrl + C)")
                    else:
                        st.sidebar.info("No messages to export yet.")

                # .TXT DOWNLOAD BUTTON
                if st.session_state["messages"]:
                    export_text = ""
                    for msg in st.session_state["messages"]:
                        role = "You" if msg["role"] == "user" else "AI"
                        export_text += f"{role}: {msg['content']}\\n\\n"

                    st.sidebar.download_button(
                        "💾 Download Chat", data=export_text, file_name="chat_export.txt", mime="text/plain"
                    )

                # SYSTEM PROMPT EDITOR
                system_prompt = st.text_area(
                    "System Prompt",
                    value="You help neighbors identify skills they can offer to meet needs in their community.",
                    help="Edit the system prompt to customize the AI assistant's behavior.",
                )

                # MODEL DISPLAY
                model = st.selectbox("Model", ["openai/gpt-oss-120b"])

                # CONTEXT CHECKBOX
                use_context = st.multiselect(
                    "Include Context",
                    [
                        "Include community needs expertise",
                        "Include skills identification expertise",
                        "Include volunteering expertise",
                    ],
                )

                # CLEAR CHAT AND RESET SESSION STATE, THEN REBUILD THE INTERFACE
                if st.button("CLEAR CHAT"):
                    st.session_state["messages"] = []
                    st.rerun()

            def mock_stream(prompt, contexts):
                """Yield a fake response one word at a time to imitate model streaming."""
                # Keeping responses in a dictionary makes it easy to add prompt-specific
                # canned answers later. This starter example always uses "default".
                context_description = ", ".join(contexts) if contexts else "general knowledge"
                responses = {
                    "default": (
                        f"Based on my {context_description}, here's my take on "
                        f"'{prompt[:50]}'. This is a mock response that verifies your input is being correctly received. In the future, the selected context areas will shape how I "
                        "explain the key ideas and recommend next steps. \nFor now, I recommend heading to groq.com to retrieve a free API key to experience the full capabilities of the platform. Enjoy exploring!"
                    )
                }
                response = responses["default"]

                # A generator pauses at each yield. st.write_stream consumes each string
                # progressively, producing the same visible effect as streamed model text.
                for word in response.split():
                    yield word + " "
                    time.sleep(0.03)

            def real_stream(messages, api_key, model, final_system_prompt):
                """Call Groq and yield each available text chunk for st.write_stream."""
                # Import locally so mock mode still works without installing the optional
                # groq package in the current Python environment.
                from groq import Groq

                # Use the value returned by the password widget, never a placeholder or a
                # hard-coded secret. The key exists only for this browser session unless the
                # user supplies it again after a refresh.
                client = Groq(api_key=api_key)

                # Place the system instruction first, then include every saved message.
                # The current user prompt is already in this list before this function runs.
                stream = client.chat.completions.create(
                    model=model, messages=[{"role": "system", "content": final_system_prompt}] + messages, stream=True
                )

                # Streaming events may contain metadata or role changes without text. Yield
                # only content-bearing chunks because the display expects text strings.
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            # PERSISTENCE: Display all previous messages stored in the session state.
            for message in st.session_state["messages"]:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

            if prompt := st.chat_input("Ask me anything..."):
                st.session_state["user_input"] = prompt
                st.session_state["messages"].append({"role": "user", "content": prompt})

                # Build the instruction that will guide this specific response.
                final_system_prompt = system_prompt
                if "Include community needs expertise" in use_context:
                    final_system_prompt += "\nYou have deep expertise in community needs."
                if "Include skills identification expertise" in use_context:
                    final_system_prompt += "\nYou are highly skilled at helping people identify their skills."
                if "Include volunteering expertise" in use_context:
                    final_system_prompt += "\nYou are an expert in community volunteering."

                with st.chat_message("user"):
                    st.write(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        if use_real_api:
                            try:
                                response = st.write_stream(
                                    real_stream(
                                        st.session_state["messages"],
                                        api_key,
                                        model,
                                        final_system_prompt,
                                    )
                                )
                            except Exception as e:
                                response = st.error(f"API ERROR: {e!s}")
                        else:
                            response = st.write_stream(mock_stream(prompt, use_context))

                # PERSIST WHEN CHAT TURN IS COMPLETED
                st.session_state["messages"].append({"role": "assistant", "content": response})

        with docs_tab:
            st.subheader("Ask Your Documents")
            st.caption("Answers come only from the indexed Blanchester community documents.")

            if "doc_messages" not in st.session_state:
                st.session_state["doc_messages"] = []

            if st.button("🔄 Re-index Documents"):
                with st.spinner("Indexing..."):
                    result = reindex_documents(token)
                if result:
                    st.success(f"Indexed {result.get('ingested', 0)} document(s)")
                else:
                    st.error("Ingestion failed")

            def show_sources(sources, confidence):
                """Render retrieved source chunks inside an expander."""
                if sources:
                    with st.expander(f"Sources ({confidence} confidence)"):
                        for s in sources:
                            st.caption(f"{s['source']} (dist: {s['distance']:.3f})")
                            st.write(s["text"][:200] + "...")

            for msg in st.session_state["doc_messages"]:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
                    show_sources(msg.get("sources"), msg.get("confidence", "unknown"))

            if doc_question := st.chat_input("Ask a question about your documents...", key="doc_chat"):
                st.session_state["doc_messages"].append({"role": "user", "content": doc_question})
                with st.chat_message("user"):
                    st.write(doc_question)

                with st.chat_message("assistant"):
                    try:
                        meta = {}

                        def token_stream():
                            """Capture the meta event, yield only answer text."""
                            with st.spinner("Searching documents..."):
                                events = ask_documents_stream(token, doc_question)
                                first = next(events, None)
                            if first and first[0] == "meta":
                                meta.update(first[1])
                            for kind, value in events:
                                if kind == "token":
                                    yield value

                        answer = st.write_stream(token_stream())
                        show_sources(meta.get("sources", []), meta.get("confidence", "unknown"))
                        st.session_state["doc_messages"].append(
                            {
                                "role": "assistant",
                                "content": answer,
                                "sources": meta.get("sources", []),
                                "confidence": meta.get("confidence", "unknown"),
                            }
                        )
                    except PermissionError as error:
                        st.error(str(error))
                    except Exception as error:
                        st.error(f"Error: {error}")
