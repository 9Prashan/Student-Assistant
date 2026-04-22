"""
app.py  —  EduBot Streamlit UI
Run with:  streamlit run app.py
"""
 
import streamlit as st
from EduBot import Bot
from parser import parse_bot_response, parse_content, render_mentor_message
 
# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EduBot — AI Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)
 
# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS  (clean academic look + chat bubbles)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Global ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
 
/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #0f172a 0%, #1e293b 100%);
    color: #f1f5f9;
}
section[data-testid="stSidebar"] * { color: #f1f5f9 !important; }
section[data-testid="stSidebar"] .stTextArea textarea {
    background: #1e293b;
    border: 1px solid #334155;
    color: #f1f5f9 !important;
    border-radius: 8px;
}
section[data-testid="stSidebar"] label { color: #94a3b8 !important; }
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
}
 
/* ── Main area ── */
.main .block-container { padding-top: 1.5rem; max-width: 900px; }
 
/* ── Problem / Solution cards ── */
.problem-card {
    background: linear-gradient(135deg, #eff6ff, #dbeafe);
    border-left: 4px solid #3b82f6;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
}
.solution-card {
    background: linear-gradient(135deg, #f0fdf4, #dcfce7);
    border-left: 4px solid #22c55e;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
}
.card-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
    opacity: 0.6;
}
 
/* ── Chat bubbles ── */
.chat-wrapper { display: flex; flex-direction: column; gap: 1rem; padding: 0.5rem 0; }
 
.bot-bubble-wrap  { display: flex; justify-content: flex-start; }
.user-bubble-wrap { display: flex; justify-content: flex-end; }
 
.bot-bubble {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 4px 18px 18px 18px;
    padding: 1rem 1.2rem;
    max-width: 82%;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07);
}
.user-bubble {
    background: linear-gradient(135deg, #6366f1, #818cf8);
    color: #ffffff !important;
    border-radius: 18px 4px 18px 18px;
    padding: 0.75rem 1.1rem;
    max-width: 70%;
    box-shadow: 0 1px 4px rgba(99,102,241,0.3);
}
.user-bubble * { color: #ffffff !important; }
.bubble-avatar {
    font-size: 1.4rem;
    margin-right: 0.5rem;
    align-self: flex-start;
    margin-top: 0.2rem;
}
 
/* ── Info panels inside bot bubble ── */
.info-panel {
    border-radius: 8px;
    padding: 0.5rem 0.8rem;
    margin-bottom: 0.5rem;
    font-size: 0.82rem;
}
.panel-checker  { background: #fef9c3; border-left: 3px solid #eab308; }
.panel-tracker  { background: #e0f2fe; border-left: 3px solid #0ea5e9; }
.panel-label    { font-weight: 700; font-size: 0.7rem; letter-spacing: 0.08em;
                  text-transform: uppercase; margin-bottom: 0.2rem; opacity: 0.65; }
 
/* ── Conclude banner ── */
.conclude-banner {
    background: linear-gradient(135deg, #f0fdf4, #dcfce7);
    border: 1px solid #86efac;
    border-radius: 12px;
    padding: 1rem 1.4rem;
    text-align: center;
    font-weight: 600;
    color: #15803d;
    margin-top: 0.5rem;
}
 
/* ── Status badge ── */
.status-badge {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 99px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.badge-active   { background: #dcfce7; color: #15803d; }
.badge-done     { background: #e0f2fe; color: #0369a1; }
.badge-idle     { background: #f1f5f9; color: #64748b; }
 
/* ── Input area ── */
.stChatInput > div { border-radius: 12px !important; border: 2px solid #6366f1 !important; }
 
/* ── Buttons ── */
.stButton > button {
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.2s;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
</style>
""", unsafe_allow_html=True)
 
 
# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "bot": None,
        "messages": [],          # LLM conversation history
        "chat_display": [],      # [{"role":"bot"|"user", "content":str, "parsed":dict|None}]
        "session_active": False,
        "session_done": False,
        "language": "English",
        "problem_formatted": "",
        "solution_formatted": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
 
init_state()
 
 
# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def get_bot() -> Bot:
    if st.session_state.bot is None:
        st.session_state.bot = Bot()
    return st.session_state.bot
 
 
def render_bot_bubble(parsed: dict):
    """Render a structured bot message inside a chat bubble."""
    sc   = parsed.get("solution_checker")
    pt   = parsed.get("progress_tracker")
    mentor_raw = parsed.get("mentor", "")
    mentor_text = render_mentor_message(mentor_raw)
    is_conclude = parsed.get("is_conclude", False)
 
    html_parts = ['<div class="bot-bubble">']
 
    if sc:
        html_parts.append(
            f'<div class="info-panel panel-checker">'
            f'<div class="panel-label">✅ Solution Checker</div>{sc}</div>'
        )
    if pt:
        html_parts.append(
            f'<div class="info-panel panel-tracker">'
            f'<div class="panel-label">📊 Progress Tracker</div>{pt}</div>'
        )
 
    html_parts.append("</div>")  # close bot-bubble before markdown (markdown won't render inside html)
    st.markdown(
        f'<div class="bot-bubble-wrap"><span class="bubble-avatar">🎓</span>'
        + "".join(html_parts),
        unsafe_allow_html=True,
    )
 
    # Render mentor message as proper markdown (supports LaTeX via st.markdown)
    with st.container():
        col = st.columns([0.05, 0.95])[1]
        with col:
            st.markdown(
                f'<div class="bot-bubble" style="margin-top:-0.5rem">',
                unsafe_allow_html=True,
            )
            st.markdown(mentor_text)
            if is_conclude:
                st.markdown(
                    '<div class="conclude-banner">🎉 Great work! You\'ve mastered this problem!</div>',
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)
 
 
def render_user_bubble(text: str):
    st.markdown(
        f'<div class="user-bubble-wrap">'
        f'<div class="user-bubble">{text}</div>'
        f'<span class="bubble-avatar" style="margin-left:0.5rem;margin-right:0">🧑‍🎓</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
 
 
def render_content_card(label: str, content: str, card_class: str):
    parsed = parse_content(content)
    st.markdown(
        f'<div class="{card_class}"><div class="card-label">{label}</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(parsed)
 
 
# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — Problem / Solution input
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 EduBot")
    st.markdown("*AI-powered adaptive tutor*")
    st.divider()
 
    st.markdown("### 📝 Problem")
    problem_input = st.text_area(
        "Enter the problem statement",
        height=160,
        placeholder="Paste the problem here…",
        label_visibility="collapsed",
    )
 
    st.markdown("### 💡 Solution")
    solution_input = st.text_area(
        "Enter the reference solution",
        height=200,
        placeholder="Paste the solution here…",
        label_visibility="collapsed",
    )
 
    st.markdown("### 🌐 Language")
    language = st.selectbox(
        "Response language",
        ["English", "Hindi", "Spanish", "French", "German", "Arabic", "Bengali", "Tamil"],
        label_visibility="collapsed",
    )
    st.session_state.language = language
 
    st.divider()
 
    start_col, reset_col = st.columns(2)
    with start_col:
        start_btn = st.button("▶ Start Session", use_container_width=True, type="primary")
    with reset_col:
        reset_btn = st.button("↺ Reset", use_container_width=True)
 
    if reset_btn:
        for key in ["messages", "chat_display", "session_active",
                    "session_done", "problem_formatted", "solution_formatted"]:
            st.session_state[key] = [] if key in ("messages", "chat_display") else False if "active" in key or "done" in key else ""
        st.rerun()
 
    # Session status
    st.divider()
    if st.session_state.session_done:
        st.markdown('<span class="status-badge badge-done">✔ Session Complete</span>', unsafe_allow_html=True)
    elif st.session_state.session_active:
        st.markdown('<span class="status-badge badge-active">● Active</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-badge badge-idle">○ Idle</span>', unsafe_allow_html=True)
 
 
# ─────────────────────────────────────────────────────────────────────────────
# MAIN AREA
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("## 🎓 EduBot — Adaptive Learning Assistant")
 
# ── Start session ──
if start_btn:
    if not problem_input.strip() or not solution_input.strip():
        st.error("Please enter both a problem and a solution in the sidebar.")
    else:
        bot = get_bot()
        with st.spinner("📚 Formatting content and initialising session…"):
            prob_fmt  = bot.format_content_sync(problem_input)
            soln_fmt  = bot.format_content_sync(solution_input)
            st.session_state.problem_formatted  = prob_fmt
            st.session_state.solution_formatted = soln_fmt
 
            # Build initial messages and get first bot response
            msgs = bot.build_initial_messages(prob_fmt, soln_fmt)
            raw_response = bot.get_bot_response_sync(msgs)
 
            # Translate if needed
            display_response = raw_response
            if language != "English":
                display_response = bot.translate_sync(raw_response, language)
 
            # Update state
            msgs.append({"role": "assistant", "content": raw_response})
            st.session_state.messages    = msgs
            st.session_state.session_active = True
            st.session_state.session_done   = False
            st.session_state.chat_display   = [{
                "role":    "bot",
                "content": display_response,
                "parsed":  parse_bot_response(display_response),
            }]
            if "@conclude" in raw_response:
                st.session_state.session_done   = True
                st.session_state.session_active = False
        st.rerun()
 
# ── Show problem / solution cards ──
if st.session_state.problem_formatted:
    with st.expander("📌 Problem & Solution", expanded=False):
        render_content_card("Problem", st.session_state.problem_formatted, "problem-card")
        render_content_card("Reference Solution", st.session_state.solution_formatted, "solution-card")
 
st.divider()
 
# ── Chat history ──
if st.session_state.chat_display:
    for entry in st.session_state.chat_display:
        if entry["role"] == "bot":
            render_bot_bubble(entry["parsed"])
        else:
            render_user_bubble(entry["content"])
else:
    if not st.session_state.session_active:
        st.markdown(
            """
            <div style="text-align:center; padding: 3rem; color:#94a3b8;">
                <div style="font-size:3rem;">🎓</div>
                <h3 style="color:#64748b;">Ready to learn?</h3>
                <p>Enter your problem and solution in the sidebar,<br>then click <strong>▶ Start Session</strong>.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
 
# ── Chat input (only when session is active) ──
if st.session_state.session_active and not st.session_state.session_done:
    user_input = st.chat_input("Type your answer or question here…")
 
    if user_input:
        bot = get_bot()
        lang = st.session_state.language
 
        # Translate user input to English for the model if needed
        input_for_model = user_input
        if lang != "English":
            with st.spinner("Translating…"):
                input_for_model = bot.translate_sync(user_input, "English")
 
        # Add to display and LLM history
        st.session_state.chat_display.append({
            "role": "user", "content": user_input, "parsed": None
        })
        st.session_state.messages.append({
            "role": "user",
            "content": "STUDENT_RESPONSE:\n" + input_for_model,
        })
 
        with st.spinner("🤔 Thinking…"):
            raw_response = bot.get_bot_response_sync(st.session_state.messages)
 
        display_response = raw_response
        if lang != "English":
            with st.spinner("Translating response…"):
                display_response = bot.translate_sync(raw_response, lang)
 
        st.session_state.messages.append({"role": "assistant", "content": raw_response})
        parsed = parse_bot_response(display_response)
        st.session_state.chat_display.append({
            "role": "bot", "content": display_response, "parsed": parsed,
        })
 
        if "@conclude" in raw_response:
            st.session_state.session_done   = True
            st.session_state.session_active = False
 
        st.rerun()
 
elif st.session_state.session_done:
    st.success("🎉 Session complete! Reset to start a new problem.")