import random
import time
import uuid
import pandas as pd
import requests
import streamlit as st
from google import genai
from google.genai import types

# =========================================================
# 1. Google Forms & スプレッドシート設定
# =========================================================
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSf-_jdLcfiNzS-EvIhOocAQnLSV9B6fGkWjOplTeaNhqgtLpA/formResponse"
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1XqOK9luQstWCKa8fkZDfbJgsloPqbTt7sDlvHrILW6k/export?format=csv"

ENTRY_SESSION_ID = "entry.1763471419"
ENTRY_PATTERN_ID = "entry.885379734"
ENTRY_NATIVE_LANG = "entry.1042619836"
ENTRY_NATIONALITY = "entry.415113020"
ENTRY_AGE_GROUP = "entry.1825534113"
ENTRY_SECURITY = "entry.627623479"
ENTRY_CONTINUE = "entry.582426341"
ENTRY_NATURAL = "entry.226172863"
ENTRY_RELIABLE = "entry.1043924285"

ALL_PATTERNS = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]


def get_least_tested_pattern(tested_by_user=[]):
  """スプレッドシートを参照し、現在最も回答数が少ないパターンを優先して割り当てる"""
  try:
    df = pd.read_csv(SHEET_CSV_URL)
    counts = df["pattern_id"].value_counts().to_dict()
  except Exception:
    counts = {}

  pattern_counts = {p: counts.get(p, 0) for p in ALL_PATTERNS}
  available_patterns = [p for p in ALL_PATTERNS if p not in tested_by_user]
  if not available_patterns:
    available_patterns = ALL_PATTERNS

  min_count = min(pattern_counts[p] for p in available_patterns)
  candidates = [p for p in available_patterns if pattern_counts[p] == min_count]
  return random.choice(candidates)


def send_to_google_forms(answers):
  """Google Formsへデータ送信"""
  data = {
      ENTRY_SESSION_ID: str(st.session_state.session_id),
      ENTRY_PATTERN_ID: str(st.session_state.current_pattern),
      ENTRY_NATIVE_LANG: str(
          st.session_state.user_info.get("native_lang", "Prefer not to say")
      ),
      ENTRY_NATIONALITY: str(
          st.session_state.user_info.get("nationality", "Prefer not to say")
      ),
      ENTRY_AGE_GROUP: str(
          st.session_state.user_info.get("age_group", "Prefer not to say")
      ),
      ENTRY_SECURITY: str(answers["security"]),
      ENTRY_CONTINUE: str(answers["continue"]),
      ENTRY_NATURAL: str(answers["natural"]),
      ENTRY_RELIABLE: str(answers["reliable"]),
  }

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
          "AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/120.0.0.0 Safari/537.36"
      ),
      "Content-Type": "application/x-www-form-urlencoded",
  }

  try:
    res = requests.post(FORM_URL, data=data, headers=headers)
    if res.status_code in [200, 302]:
      return True
    else:
      st.error(f"Forms submission failed. Status code: {res.status_code}")
      return False
  except Exception as e:
    st.error(f"Error sending data: {e}")
    return False


# =========================================================
# 2. システム初期化 & 設定
# =========================================================
st.set_page_config(page_title="AI Research Study in Toronto", page_icon="🤖")

if "session_id" not in st.session_state:
  st.session_state.session_id = f"TRT-{uuid.uuid4().hex[:6].upper()}"

if "tested_patterns" not in st.session_state:
  st.session_state.tested_patterns = []

if "current_pattern" not in st.session_state:
  st.session_state.current_pattern = get_least_tested_pattern(
      st.session_state.tested_patterns
  )

if "phase" not in st.session_state:
  st.session_state.phase = (
      "setup"  # setup -> chat -> prompt_rate -> survey -> next_prompt -> finished
  )

if "user_info" not in st.session_state:
  st.session_state.user_info = {}

if "turn_count" not in st.session_state:
  st.session_state.turn_count = 0

PATTERN_CONFIG = {
    "P1": {"speed": 0.0, "char": "robot", "indicator": None},
    "P2": {"speed": 0.0, "char": "empathic", "indicator": None},
    "P3": {"speed": 1.5, "char": "robot", "indicator": "AI is thinking..."},
    "P4": {"speed": 1.5, "char": "empathic", "indicator": "AI is thinking..."},
    "P5": {
        "speed": 3.0,
        "char": "robot",
        "indicator": "AI is deeply considering...",
    },
    "P6": {
        "speed": 3.0,
        "char": "empathic",
        "indicator": "AI is deeply considering...",
    },
    "P7": {"speed": 3.0, "char": "robot", "indicator": None},
    "P8": {"speed": 3.0, "char": "empathic", "indicator": None},
}

SYSTEM_PROMPTS = {
    "robot": (
        "You are a factual, concise AI assistant. Provide objective facts"
        " without emotional words, warm greetings, or emojis. Keep responses"
        " short."
    ),
    "empathic": (
        "You are a warm, highly empathetic conversation partner. Show deep"
        " sympathy, use warm language, and kindly encourage the user."
    ),
}

client = genai.Client()

# =========================================================
# 3. サイドバー
# =========================================================
with st.sidebar:
  st.header("📌 Progress")
  st.caption(f"Session: {st.session_state.session_id}")

  # 評価済みパターンの進捗を表示 (例: 3/8 Patterns)
  completed_count = len(set(st.session_state.tested_patterns))
  st.progress(completed_count / len(ALL_PATTERNS))
  st.write(f"**Tested Patterns:** {completed_count} / {len(ALL_PATTERNS)}")

  if st.session_state.phase in ["chat", "prompt_rate"]:
    st.info("Ready to share your feedback?")
    if st.button("⭐ Rate this AI now", use_container_width=True, type="primary"):
      st.session_state.phase = "survey"
      st.rerun()

  st.divider()
  st.markdown("### ℹ️ About Study")
  st.write(
      "Please chat with the AI and rate your experience when you are ready."
  )

# =========================================================
# 4. ヘッダー & 研究詳細表示
# =========================================================
st.title("Interactive AI Conversation Study")

with st.expander("ℹ️ About This Research Study (Click to read details)"):
  st.markdown("""
    **Research Objective:**  
    This study investigates how response speed, conversational persona, and visual feedback affect psychological safety and comfort during AI-human interaction.

    **What You Will Do:**  
    1. Chat with an AI assistant about general topics (e.g., Japanese culture, food, travel).
    2. Complete a short 4-question survey about your experience.
    3. You can test multiple AI variations!

    **Data Privacy:**  
    All responses are completely anonymous. No personally identifiable information (PII) is collected or stored.
    """)

# =========================================================
# PHASE 1: 初期属性入力
# =========================================================
if st.session_state.phase == "setup":
  st.markdown(
      "## 🚀 Please chat with the AI a few times, and then rate your"
      " experience!"
  )

  st.info("""
    🌟 **We have prepared 8 different AI variations** (differing in response speed, personality, and visual feedback). 
    To help our research, we kindly encourage you to **test and rate as many different AI patterns as possible** during your session!
    """)

  st.subheader("Welcome! Please tell us a little about yourself")
  st.write(
      "💡 Answering these questions is optional. You can select 'Prefer not to"
      " say' for any item."
  )

  with st.form("user_info_form"):
    native_lang = st.text_input(
        "First Language / Native Language (e.g., English, Spanish, Japanese)",
        value="",
    )
    nationality = st.text_input(
        "Nationality / Region (e.g., Canada, Japan)", value=""
    )
    age_group = st.selectbox(
        "Age Group",
        [
            "Select...",
            "Under 18",
            "18-24",
            "25-34",
            "35-44",
            "45-54",
            "55+",
            "Prefer not to say",
        ],
    )

    submit_setup = st.form_submit_button("Start Conversation")

    if submit_setup:
      st.session_state.user_info = {
          "native_lang": (
              native_lang.strip() if native_lang.strip() else "Prefer not to say"
          ),
          "nationality": (
              nationality.strip() if nationality.strip() else "Prefer not to say"
          ),
          "age_group": (
              age_group if age_group != "Select..." else "Prefer not to say"
          ),
      }
      st.session_state.messages = []
      st.session_state.turn_count = 0
      st.session_state.phase = "chat"
      st.rerun()

# =========================================================
# PHASE 2: チャット会話
# =========================================================
elif st.session_state.phase in ["chat", "prompt_rate"]:
  config = PATTERN_CONFIG[st.session_state.current_pattern]

  for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
      st.write(msg["content"])

  if prompt := st.chat_input(
      "Type a message (e.g., 'Tell me about Japanese food')..."
  ):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
      st.write(prompt)

    st.session_state.turn_count += 1

    with st.chat_message("assistant"):
      if config["speed"] > 0:
        if config["indicator"]:
          with st.spinner(config["indicator"]):
            time.sleep(config["speed"])
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPTS[config["char"]]
                ),
            )
            reply = response.text
        else:
          time.sleep(config["speed"])
          response = client.models.generate_content(
              model="gemini-3.5-flash-lite",
              contents=prompt,
              config=types.GenerateContentConfig(
                  system_instruction=SYSTEM_PROMPTS[config["char"]]
              ),
          )
          reply = response.text
      else:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPTS[config["char"]]
            ),
        )
        reply = response.text

      st.write(reply)
      st.session_state.messages.append({"role": "assistant", "content": reply})

    time.sleep(3.0)

    if st.session_state.turn_count >= 2:
      st.session_state.phase = "prompt_rate"
    else:
      st.session_state.phase = "chat"

    st.rerun()

  if st.session_state.phase == "prompt_rate":

    @st.dialog("Finished chatting with this AI?")
    def show_rate_prompt():
      st.write(
          "How was your experience with this AI assistant so far? You can"
          " submit your rating now, or continue chatting with it."
      )

      col1, col2 = st.columns(2)
      with col1:
        if st.button("⭐ Rate this AI now", type="primary"):
          st.session_state.phase = "survey"
          st.rerun()

      with col2:
        if st.button("💬 Continue chatting"):
          st.session_state.phase = "chat"
          st.rerun()

    show_rate_prompt()

# =========================================================
# PHASE 3: アンケート回答 (8パターン評価完了の判定処理を追加)
# =========================================================
elif st.session_state.phase == "survey":
  st.divider()
  st.subheader("📝 Rate This AI Assistant (1 = Very Low, 5 = Very High)")
  st.write("Please rate your experience with this specific AI configuration:")

  q1 = st.slider(
      "1. Did you feel safe and comfortable (no anxiety/rush) during the chat?",
      1,
      5,
      3,
  )
  q2 = st.slider(
      "2. Would you like to continue chatting with this AI in daily life?",
      1,
      5,
      3,
  )
  q3 = st.slider(
      "3. Was the timing and pacing of the AI's responses natural?", 1, 5, 3
  )
  q4 = st.slider(
      "4. Did you feel the system was reliable (no freezes/errors)?", 1, 5, 3
  )

  if st.button("Submit Rating"):
    answers = {"security": q1, "continue": q2, "natural": q3, "reliable": q4}

    success = send_to_google_forms(answers)

    if success:
      st.success("Responses successfully sent!")
      if (
          st.session_state.current_pattern
          not in st.session_state.tested_patterns
      ):
        st.session_state.tested_patterns.append(
            st.session_state.current_pattern
        )

      # ★ 全8パターンを全て評価し終えたかチェック
      unique_tested = set(st.session_state.tested_patterns)
      if len(unique_tested) >= len(ALL_PATTERNS):
        st.session_state.phase = "finished"  # 全8パターン達成で終了画面へ
      else:
        st.session_state.phase = "next_prompt"  # まだ残っていれば次のパターン提案へ

      st.rerun()

# =========================================================
# PHASE 4: ダイアログ (別パターン挑戦の案内)
# =========================================================
elif st.session_state.phase == "next_prompt":

  @st.dialog("Try Another AI Pattern?")
  def show_next_option():
    st.write("Thank you for submitting your feedback!")
    st.write(
        "To help us get balanced data, would you like to try a **different AI"
        " pattern** next? (Takes about 1 minute)"
    )

    col1, col2 = st.columns(2)
    with col1:
      if st.button("YES, try another!", type="primary"):
        st.session_state.current_pattern = get_least_tested_pattern(
            st.session_state.tested_patterns
        )
        st.session_state.messages = []
        st.session_state.turn_count = 0
        st.session_state.phase = "chat"
        st.rerun()

    with col2:
      if st.button("NO, finish study"):
        st.session_state.phase = "finished"
        st.rerun()

  show_next_option()

# =========================================================
# PHASE 5: 完全終了画面
# =========================================================
elif st.session_state.phase == "finished":
  st.balloons()
  st.success(
      "🎉 Outstanding! You have evaluated all 8 AI patterns! Thank you very"
      " much for your time and contribution to our research!"
  )
  st.write("Your responses have been recorded. You can now close this window.")
