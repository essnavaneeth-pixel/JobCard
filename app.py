import re
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

import streamlit as st

from google import genai
from google.genai import types

from prompts import (
    SUMMARY_REQUEST_PROMPT,
    SYSTEM_PROMPT,
    WELCOME_MESSAGE_TEMPLATE,
)

# --------------------------------
# Configuration & Theme
# --------------------------------

MODEL_NAME = "gemini-3.5-flash"

st.set_page_config(
    page_title="JobCard",
    page_icon="🔧",
    layout="centered",
)

# Clean, modern, eye-catching styling with crystal clear contrast
st.markdown(
    """
    <style>
    /* Fonts & Typography */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    /* Headings */
    h1 {
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        color: #f8fafc !important;
        margin-bottom: 4px !important;
    }

    /* Subtitle & captions */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: #94a3b8 !important;
        font-size: 0.95rem !important;
    }

    /* Form card */
    [data-testid="stForm"] {
        background-color: #131b2e !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 14px !important;
        padding: 24px !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25) !important;
    }

    /* Form labels & inputs */
    [data-testid="stTextInput"] label {
        color: #e2e8f0 !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        margin-bottom: 6px !important;
    }

    [data-testid="stTextInput"] input {
        background-color: #0b1120 !important;
        color: #ffffff !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        font-size: 0.98rem !important;
        padding: 10px 14px !important;
    }

    [data-testid="stTextInput"] input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25) !important;
    }

    /* Eye-catching Buttons */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 8px 18px !important;
        transition: all 0.2s ease-in-out !important;
        background: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid #334155 !important;
    }

    .stButton > button:hover:not(:disabled) {
        border-color: #3b82f6 !important;
        color: #38bdf8 !important;
        transform: translateY(-1px) !important;
    }

    /* Submit & Primary action buttons */
    .stFormSubmitButton > button {
        background: linear-gradient(135deg, #2563eb, #3b82f6) !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
    }

    .stFormSubmitButton > button:hover {
        background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
        box-shadow: 0 6px 18px rgba(37, 99, 235, 0.5) !important;
        transform: translateY(-1px) !important;
    }

    /* Chat Messages */
    [data-testid="stChatMessage"] {
        background-color: #131b2e !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 14px 18px !important;
        margin-bottom: 12px !important;
        color: #f1f5f9 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
    }

    /* Chat Input Bar */
    [data-testid="stChatInput"] {
        border-radius: 12px !important;
        border-color: #334155 !important;
        background: #131b2e !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
GMAIL_ADDRESS = st.secrets["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]


@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)


gemini_client = get_gemini_client()


def send_email(to_address, subject, body, sender_name="sri navaneeth"):
    try:
        message = MIMEText(body)

        message["Subject"] = subject
        message["From"] = formataddr((sender_name, GMAIL_ADDRESS))
        message["To"] = to_address

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(
                GMAIL_ADDRESS,
                GMAIL_APP_PASSWORD
            )

            server.send_message(message)

        return True, "Email sent successfully."

    except Exception as error:
        return False, str(error)


def render_message(message):
    avatar = "🔧" if message["role"] == "assistant" else "👤"
    with st.chat_message(message["role"], avatar=avatar):
        if message["kind"] == "text":
            st.write(message["content"])
        elif message["kind"] == "image":
            st.image(message["content"], use_container_width=True)


def add_message(role, kind, content):
    st.session_state.messages.append(
        {
            "role": role,
            "kind": kind,
            "content": content,
        }
    )

    render_message(
        st.session_state.messages[-1]
    )


def ask_gemini(parts):
    try:
        return st.session_state.chat.send_message(
            parts
        ).text
    except Exception as error:
        return f"Sorry, something went wrong: {error}"


def clean_email_text(text, sender_name="sri navaneeth"):
    if not text:
        return "No service update available."

    # Remove or clean greeting placeholders like "Dear [Customer Name]," or "Dear [Customer]," -> "Hello,"
    text = re.sub(r'(?i)Dear\s+\[.*?\]\s*,?', 'Hello,', text)
    # Remove any generic bracketed customer placeholders
    text = re.sub(r'(?i)\[\s*customer(?:\s+name)?\s*\]', '', text)

    # Replace sign-off placeholders
    text = re.sub(r'(?i)\[\s*(?:your|technician|service\s*technician|provider)?\s*name\s*\]', sender_name, text)
    text = re.sub(r'(?i)\[\s*your\s*company\s*\]', 'JobCard Service', text)

    # Strip any remaining bracketed placeholders
    text = re.sub(r'\[[A-Za-z\s]+\]', '', text)

    # Ensure clean sign-off with "Best regards,\n{sender_name}"
    closing_pattern = r'(?i)(best\s+regards|regards|sincerely|warm\s+regards)[,\s]*.*$'
    if re.search(closing_pattern, text):
        text = re.sub(closing_pattern, f'Best regards,\n{sender_name}', text).strip()
    else:
        text = text.strip() + f'\n\nBest regards,\n{sender_name}'

    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines).strip()
    text = re.sub(r'\n{3,}', '\n\n', text)

    return (
        text[:5000] + "..."
        if len(text) > 5000
        else text
    )


# --------------------------------
# Step 1: Onboarding
# --------------------------------

if "onboarded" not in st.session_state:

    st.title("🔧 JobCard")

    st.caption(
        "Turn repair photos and notes into clear customer updates."
    )

    with st.form("onboarding_form"):

        name = st.text_input(
            "Your name",
            value="sri navaneeth",
        )

        email_address = st.text_input(
            "Customer email address",
            placeholder="customer@example.com",
        )

        submitted = st.form_submit_button(
            "Let's go 🚀",
            use_container_width=True,
        )

    if submitted:

        if (
            not name.strip()
            or not email_address.strip()
        ):

            st.warning(
                "Please fill in both your name "
                "and the customer email."
            )

        else:

            st.session_state.name = name.strip()

            st.session_state.email_address = (
                email_address.strip()
            )

            st.session_state.chat = (
                gemini_client.chats.create(
                    model=MODEL_NAME,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT
                    ),
                )
            )

            st.session_state.messages = []

            st.session_state.onboarded = True

            st.rerun()

    st.stop()


# --------------------------------
# Step 2: Header
# --------------------------------

header_col, button_col = st.columns(
    [5, 2],
    vertical_alignment="center",
)


with header_col:

    st.title("🔧 JobCard")


with button_col:

    send_disabled = (
        len(st.session_state.messages) <= 1
    )

    if st.button(
        "📧 Send Customer Update",
        disabled=send_disabled,
        use_container_width=True,
    ):

        with st.spinner(
            "Preparing customer update..."
        ):

            sender_name = st.session_state.get("name", "sri navaneeth")
            summary = ask_gemini(
                [SUMMARY_REQUEST_PROMPT.format(name=sender_name)]
            )

        cleaned_email = clean_email_text(summary, sender_name=sender_name)

        success, info = send_email(
            st.session_state.email_address,
            "Service Update",
            cleaned_email,
            sender_name=sender_name,
        )

        if success:

            st.success(
                "Customer update sent! 📧"
            )

        else:

            st.error(
                f"Couldn't send the email: {info}"
            )


st.caption(
    f"Logged in as {st.session_state.name} "
    f"- updates go to "
    f"{st.session_state.email_address}"
)


# --------------------------------
# Step 3: Chat history
# --------------------------------

if not st.session_state.messages:

    add_message(
        "assistant",
        "text",
        WELCOME_MESSAGE_TEMPLATE.format(
            name=st.session_state.name
        ),
    )

else:

    for message in st.session_state.messages:

        render_message(message)


# --------------------------------
# Step 4: Photo / text input
# --------------------------------

user_input = st.chat_input(
    "Describe the repair problem, or attach a photo",
    accept_file=True,
    file_type=[
        "jpg",
        "jpeg",
        "png",
    ],
)


if user_input:

    photo = (
        user_input.files[0]
        if hasattr(user_input, "files") and user_input.files
        else (user_input.get("files", [None])[0] if isinstance(user_input, dict) and user_input.get("files") else None)
    )

    text = (
        user_input.text
        if hasattr(user_input, "text")
        else (user_input.get("text", "") if isinstance(user_input, dict) else str(user_input))
    )

    parts = []

    if photo is not None:

        photo_bytes = photo.getvalue()

        add_message(
            "user",
            "image",
            photo_bytes,
        )

        parts.append(
            types.Part.from_bytes(
                data=photo_bytes,
                mime_type=photo.type,
            )
        )

    if text:

        add_message(
            "user",
            "text",
            text,
        )

        parts.append(text)

    elif photo is not None:

        parts.append(
            "Analyze this repair/service photo. "
            "Describe what can be visibly observed "
            "and explain what information would be "
            "useful for the service job."
        )

    with st.spinner(
        "Analyzing the job..."
    ):

        answer = ask_gemini(parts)

    add_message(
        "assistant",
        "text",
        answer,
    )
