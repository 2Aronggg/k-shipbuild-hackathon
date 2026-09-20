"""
WeldScan AI — Streamlit 진입점

로그인
→ 역할 선택
→ 관리자: 기존 HTML 대시보드
→ 작업자/책임 검사원: React(Vite) 작업자 대시보드
"""

import base64
import io
from pathlib import Path
from urllib.parse import urlencode

import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image


# ══════════════════════════════════════════════════
# 설정
# ══════════════════════════════════════════════════

APP_DIR = Path(__file__).parent
LOGIN_BG_PATH = APP_DIR.parent / "design" / "background2.png"
# 파일이 없을 경우 빈 문자열 반환 (오류 방지)
LOGIN_BG_DATA = base64.b64encode(LOGIN_BG_PATH.read_bytes()).decode("ascii") if LOGIN_BG_PATH.exists() else ""

# 공모전 기관 로고 (흰 배경 → 투명 배경으로 변환 후 인라인)
LOGO_DIR = APP_DIR.parent / "design" / "logo"


def _logo_data_uri(filename: str, threshold: int = 245) -> str:
    """흰 배경 PNG 로고를 투명 배경 PNG data URI로 변환."""
    path = LOGO_DIR / filename
    if not path.exists():
        return ""
    img = Image.open(path).convert("RGBA")

    arr = np.array(img)
    is_white = np.all(arr[:, :, :3] >= threshold, axis=-1)
    arr[is_white, 3] = 0
    img = Image.fromarray(arr, mode="RGBA")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")

    return f"data:image/png;base64,{encoded}"


ORG_LOGOS = {
    "motie": _logo_data_uri("motie.png"),
    "kiat": _logo_data_uri("kiat.png"),
    "koshipa": _logo_data_uri("koshipa.png"),
    "hd_ksoe": _logo_data_uri("hd_ksoe.png"),
    "hanwha_ocean": _logo_data_uri("hanwha_ocean.png"),
    "samsung_heavy": _logo_data_uri("samsung_heavy.png"),
    "snak": _logo_data_uri("대한조선학회.jpg"),
    "kriso": _logo_data_uri("kriso.png"),
}

# 관리자 화면만 기존 HTML 사용
ADMIN_DASHBOARD = APP_DIR / "weldscan_dashboard.html"
WORKER_UI_URL = "http://localhost:8443"

# 로그인 계정
ACCOUNTS = {
    "admin": {
        "pw": "1234",
        "name": "김성준",
        "team": "품질관리팀",
        "roles": {"admin", "senior", "worker"},
    },
    "inspector01": {
        "pw": "1234",
        "name": "윤경석",
        "team": "비파괴검사팀",
        "roles": {"senior", "worker"},
    },
    "worker01": {
        "pw": "1234",
        "name": "이수빈",
        "team": "비파괴검사팀",
        "roles": {"worker"},
    },
}

ROLE_KO = {
    "worker": "작업자",
    "admin": "관리자 (Admin)",
    "senior": "검사자",
}

ROLE_DESC = {
  "worker": "용접부 검사 및 1차 판정",
  "admin": "검사 현황 및 품질 관리",
  "senior": "이관 건 검토 및 최종 판정",
}

ROLE_ORDER = ["worker", "senior"]


# ══════════════════════════════════════════════════
# Streamlit 기본 설정
# ══════════════════════════════════════════════════

st.set_page_config(
    page_title="WeldScan AI",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ══════════════════════════════════════════════════
# 스타일 (디자인 수정 적용 완료)
# ══════════════════════════════════════════════════

st.markdown(
    """
    <style>

      @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital,wght@0,400;1,400&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
      @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');

      .stApp { background:#161617; }
      header[data-testid="stHeader"], #MainMenu, footer { display:none; }
      .block-container { padding:0 !important; max-width:none !important; }

      /* 세션바 */
      .sessionbar {
        display:flex; align-items:center; gap:12px; flex-wrap:wrap;
        padding:10px 20px; margin:14px 14px 0; border-radius:10px;
        background:#333336; border:1px solid #41626A;
        font:400 12.5px/1.5 "IBM Plex Sans KR", system-ui, sans-serif; color:#D2D2D7;
      }
      .sessionbar b { color:#F4F8FB; font-weight:600; }
      .sessionbar .tag {
        font:600 11px/1 "IBM Plex Mono", monospace; padding:5px 10px;
        border-radius:99px; background:#3397D4; color:#fff; border:1px solid #3397D4;
      }
      .sessionbar .sp { flex:1; }

      /* 로그인 셸 */
      .stApp:has(.login-scene) { background:#061526; }
      .stApp:has(.login-scene) .block-container { height:100vh; padding:0 !important; overflow:hidden; }
      .stApp:has(.login-scene) div[data-testid="stHorizontalBlock"] { gap:0; height:100vh; }
      .stApp:has(.login-scene) div[data-testid="column"] {
        display:flex; flex-direction:column; justify-content:center; height:100vh; overflow:hidden;
      }

      /* 좌측 히어로 */
      .login-scene {
        height:100vh; position:relative; display:flex; flex-direction:column;
        justify-content:flex-end; padding:clamp(24px,3vw,44px); overflow:hidden;
        background: linear-gradient(0deg,rgba(4,10,20,.88) 0%,rgba(4,10,20,.15) 42%,rgba(4,10,20,.05) 60%),
                    url("data:image/png;base64,{LOGIN_BG_DATA}") center/cover no-repeat;
      }
      .login-scene::before {
        content:""; position:absolute; inset:0;
        background-image: linear-gradient(rgba(50,214,255,.05) 1px,transparent 1px),
                          linear-gradient(90deg,rgba(50,214,255,.05) 1px,transparent 1px);
        background-size:42px 42px; mix-blend-mode:screen; pointer-events:none;
      }

      .scene-feats {
        position:relative; z-index:1; display:flex; gap:clamp(18px,2.6vw,40px);
        flex-wrap:wrap; margin-top:clamp(20px,3vw,32px);
        justify-content:center; width:100%;
      }
      .scene-feat {display:flex;gap:14px;align-items:flex-start;max-width:240px}
      .scene-feat.wide {max-width:none}
      .scene-feat.wide b,
      .scene-feat.wide span {white-space:nowrap}
      .scene-feat .ic {
        flex:none;width:46px;height:46px;border-radius:12px;
        background:rgba(50,214,255,.1);border:1px solid rgba(50,214,255,.28);
        display:grid;place-items:center;color:#32D6FF;
      }
      .scene-feat .ic svg {width:23px;height:23px}
      .scene-feat b {display:block;font:600 16px/1.4 "IBM Plex Sans KR",Inter,sans-serif;color:#F5F9FC}
      .scene-feat span {display:block;font:400 13.5px/1.5 "IBM Plex Sans KR",Inter,sans-serif;color:#9FB1C2;margin-top:3px}
      .scene-foot {
        position:relative; z-index:1; margin-top:clamp(18px,2.4vw,28px); padding-top:14px;
        border-top:1px solid rgba(159,177,194,.16); font:500 10px/1 "IBM Plex Mono",monospace;
        letter-spacing:.16em; color:rgba(159,177,194,.7); text-transform:uppercase;
      }

      /* 우측 로그인 패널 */
      .stApp:has(.login-scene) div[data-testid="column"]:last-child {
        background:#061526; padding:clamp(20px,3vw,40px);
      }
      .stApp:has(.login-scene) div[data-testid="column"]:last-child > div {
        width:min(100%,440px);
        margin-inline:auto;
      }

      .st-key-login_card {
        border:1px solid rgba(255,255,255,.24); border-radius:20px; background:rgba(255,255,255,.08);
        backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px);
        padding:clamp(22px,2.4vw,28px) clamp(22px,2.4vw,28px);
        box-shadow:0 24px 60px -20px rgba(1,8,18,.65), 0 1px 0 rgba(255,255,255,.04) inset;
      }
      .st-key-login_card div[data-testid="stVerticalBlock"] { gap:0.5rem !important; }

      .login-hero {max-width:none;margin:0 0 20px;text-align:center}
      .login-hero h1 {
        font:400 64px/1 "Instrument Serif",serif; font-style:italic; letter-spacing:-.01em; margin:0;
        background:linear-gradient(90deg,#E6F4FF 0%,#64C7FF 55%,#22D3EE 100%);
        -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; color:#F5F9FC;
      }
      .login-hero p {font:400 13px/1.6 "Inter",sans-serif;color:#9FB1C2;margin:0}
      .login-hero .sub2 {
        font:500 11.5px/1.35 "Inter",sans-serif; letter-spacing:.14em; color:#7FA8C9; margin-top:-5px;
      }

      .field-label { font:500 12px/1 "Inter",sans-serif; color:#F5F9FC; margin:18px 0 14px; }
      .field-label:first-of-type {margin-top:0}

      div[data-testid="stTextInput"] {position:relative; width:100%}
      div[data-testid="stTextInput"] label, div[data-testid="stWidgetLabel"] { display:none !important; }
      div[data-testid="stTextInput"] div[data-baseweb="input"] {
        width:100%; min-height:46px; box-sizing:border-box;
        border-radius:9px !important; border:1px solid #31516F !important;
        background:rgba(255,255,255,.05) !important; overflow:hidden;
      }
      div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {
        border-color:#32D6FF !important; box-shadow:0 0 0 3px rgba(50,214,255,.14) !important;
        background:rgba(255,255,255,.08) !important;
      }
      div[data-testid="stTextInput"] input {
        background:transparent !important; border:none !important; color:#25282D !important;
        -webkit-text-fill-color:#25282D !important; caret-color:#25282D !important;
        padding:10px 13px 10px 40px !important; min-height:46px !important;
        font-family:"Inter",sans-serif !important; font-size:13px !important;
      }
      div[data-testid="stTextInput"] input::placeholder {color:#6F8498 !important}

      /* 입력창 좌측 라인 아이콘 */
      div[data-testid="stTextInput"]:has(input[aria-label="사번 / ID"])::before {
        content:""; position:absolute; left:14px; top:50%; width:18px; height:18px;
        transform:translateY(-50%); z-index:2; pointer-events:none;
        background-repeat:no-repeat; background-position:center; background-size:contain; opacity:.8;
      }
      div[data-testid="stTextInput"]:has(input[aria-label="사번 / ID"])::before {
        background-image:url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%239FB1C2" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>');
      }
      div[data-testid="stTextInput"]:has(input[aria-label="비밀번호"]) input {
        padding-left:14px !important; padding-right:14px !important;
      }
      div[data-testid="stTextInput"]:has(input[aria-label="비밀번호"]) button {
        display:none !important;
      }

      /* 하단 '사용할 화면' 선택 버튼 */
      .st-key-login_card div[data-testid="stRadio"] input[type="radio"],
      .st-key-login_card div[data-testid="stRadio"] div[data-baseweb="radio"] > div:first-child {
        position:absolute !important; opacity:0 !important; width:0 !important; height:0 !important;
        margin:0 !important; padding:0 !important; pointer-events:none !important;
      }
      .st-key-login_card div[data-testid="stRadio"] > div,
      .st-key-login_card div[data-testid="stRadio"] > div > div {
        width:100% !important; max-width:none !important;
      }
      .st-key-login_card div[data-testid="stRadio"] { margin-top:8px; margin-bottom:28px; }
      .st-key-login_card div[role="radiogroup"] {
        display:grid !important; grid-template-columns:repeat(3,minmax(0,1fr)) !important;
        width:100% !important; max-width:none !important; gap:6px !important;
        box-sizing:border-box;
      }
      .st-key-login_card div[role="radiogroup"] label {
        position:relative; width:100% !important; min-width:0 !important;
        max-width:none !important; background:rgba(255,255,255,.03) !important;
        border:1px solid #31516F !important; border-radius:9px !important;
        min-width:0; height:46px; box-sizing:border-box; padding:12px 14px !important; color:#FFFFFF !important;
        font:500 13px/1.3 "Inter",sans-serif !important; letter-spacing:.02em; cursor:pointer;
        margin:0 !important; transition:all .2s ease; display:flex; justify-content:center; align-items:center; text-align:center;
      }
      .st-key-login_card div[role="radiogroup"] label:hover {
        border-color:rgba(50,214,255,.5) !important; background:rgba(255,255,255,.06) !important;
      }
      .st-key-login_card div[role="radiogroup"] label:has(input:focus-visible) {
        outline:none; box-shadow:0 0 0 3px rgba(50,214,255,.35) !important; border-color:#32D6FF !important;
      }
      .st-key-login_card div[role="radiogroup"] label:has(input:checked) {
        background:rgba(50,214,255,.08) !important; border-color:#32D6FF !important;
        box-shadow:0 0 0 1px rgba(50,214,255,.25), 0 0 16px -4px rgba(50,214,255,.2) !important;
      }
      .st-key-login_card div[role="radiogroup"] label p,
      .st-key-login_card div[role="radiogroup"] label span { color:#FFFFFF !important; font:inherit !important; margin:0 !important; }
      .role-note { font:500 12px/1 "Inter",sans-serif; color:#F5F9FC; margin:18px 0 8px; }

      .st-key-role_actions,
      .st-key-role_actions > div,
      .st-key-role_actions div[data-testid="stVerticalBlock"],
      .st-key-role_actions div[data-testid="stElementContainer"],
      .st-key-role_actions div[data-testid="stRadio"],
      .st-key-role_actions div[data-testid="stFormSubmitButton"] {
        width:100% !important; max-width:none !important; box-sizing:border-box;
      }
      .st-key-role_actions div[data-testid="stRadio"] { margin-bottom:0; }
      .st-key-role_actions div[data-testid="stFormSubmitButton"] > button {
        width:100% !important; min-height:46px; height:46px; box-sizing:border-box;
        margin-top:10px; border-radius:9px;
      }

      /* 로그인 버튼 */
      div[data-testid="stForm"] {border:0 !important;padding:0 !important;margin-top:24px}
      .stButton > button, div[data-testid="stFormSubmitButton"] > button {
        width:100%; min-height:54px; border-radius:10px; border:1px solid transparent;
        background:linear-gradient(90deg,#2F9BFF,#32D6FF); color:#06121F;
        font-family:"Inter",sans-serif; font-weight:700; font-size:14px;
        padding:12px 18px; margin-top:24px; transition:filter .15s, box-shadow .15s, transform .1s;
        display:inline-flex; align-items:center; justify-content:center; gap:8px;
        box-shadow: 0 4px 14px 0 rgba(50,214,255,.3);
      }
      .stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        filter:brightness(1.1); transform:translateY(-1px); box-shadow: 0 6px 20px rgba(50,214,255,.4);
      }
      .stButton > button:focus-visible, div[data-testid="stFormSubmitButton"] > button:focus-visible {
        outline:none; box-shadow:0 0 0 3px rgba(50,214,255,.35);
      }
      div[data-testid="stFormSubmitButton"] > button::after {
        content:""; width:18px; height:18px; margin-left: 6px;
        background-repeat:no-repeat; background-position:center; background-size:contain;
        background-image:url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%2306121F" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M13 6l6 6-6 6"/></svg>');
      }

      /* ── 하단 공모전 기관 로고 footer (가장 중요한 부분) ── */
      .org-footer {
        width:100%; margin:18px 0 0; padding:16px 0 0 0;
        border-top:1px solid rgba(159,177,194,.15); display:flex; flex-direction:column; gap:14px;
      }
      .org-footer .org-row { display:flex; flex-direction: column; align-items:flex-start; gap: 10px; }

      /* 주최/주관을 나란히 배치하기 위한 래퍼 */
      .org-footer-top {
          display: flex; justify-content: space-between; align-items: flex-start; width: 100%; gap: 20px;
      }
      .org-footer-top .org-row { flex: 1; }
      .org-footer .org-caption { font:600 13px/1 "Inter", sans-serif; color:#FFFFFF; margin-bottom: 5px; }

      .org-footer .org-logos { display:flex; align-items:center; gap:18px; flex-wrap:wrap; width:100%; }
      .org-footer .org-logos img {
        display:block; height:30px; max-height:30px; width:auto; max-width:130px;
        object-fit:contain; opacity:.75; transition: all 0.3s ease;
      }
      .org-footer .org-logos img:hover { opacity: 1; }
      .org-footer .org-logos img.emblem { height:34px; max-height:34px; }

      @media (max-width:900px){
        .stApp:has(.login-scene) div[data-testid="stHorizontalBlock"]{display:block;height:auto}
        .stApp:has(.login-scene) .block-container{height:auto;overflow:visible}
        .stApp:has(.login-scene) div[data-testid="column"]{height:auto}
        .login-scene{height:auto;min-height:38vh}
        .scene-feats{display:none}
        .stApp:has(.login-scene) div[data-testid="column"]:last-child{padding:28px 20px}
      }
      @media (max-width:480px){
        .org-footer-top { flex-direction: column; gap: 24px; }
        .org-footer .org-logos{gap:16px}
        .org-footer .org-logos img{height:28px;max-height:28px}
        .org-footer .org-logos img.emblem{height:32px;max-height:32px}
      }

    </style>
    """.replace("{LOGIN_BG_DATA}", LOGIN_BG_DATA),
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════
# 세션 상태
# ══════════════════════════════════════════════════
st.session_state.setdefault("user", None)


# ══════════════════════════════════════════════════
# 로그인 화면
# ══════════════════════════════════════════════════
def render_login() -> None:
    left, right = st.columns([6.5, 3.5])

    with left:
        st.markdown(
            """
            <section class="login-scene" aria-label="WeldScan 브랜드 소개">
              <div class="scene-feats">
                <div class="scene-feat">
                  <div class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="9"/></svg></div>
                  <div><b>AI 기반 용접부 판정 보조</b><span>더 정확하고, 더 빠르게</span></div>
                </div>
                <div class="scene-feat wide">
                  <div class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/></svg></div>
                  <div><b>안전한 조선 산업</b><span>사람과 기술의 안전을 생각합니다</span></div>
                </div>
                <div class="scene-feat wide">
                  <div class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg></div>
                  <div><b>데이터로 만드는 더 나은 미래</b><span>지속 가능한 미래를 위해</span></div>
                </div>
              </div>
              <div class="scene-foot">SMART INSPECTION · SAFER SHIPS · A BRIGHTER TOMORROW</div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    with right:
        card = st.container(key="login_card")

        with card:
            st.markdown(
                """
                <div class="login-hero">
                  <h1>WeldScan AI</h1>
                  <p class="sub2">조선산업 지능화·자동화를 위한 AX 솔루션</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.form("login", clear_on_submit=False):
                st.markdown('<div class="field-label">사번 / ID</div>', unsafe_allow_html=True)
                user_id = st.text_input(
                    "사번 / ID", value="", placeholder="사번 또는 아이디를 입력하세요",
                    autocomplete="username", label_visibility="collapsed",
                )

                st.markdown('<div class="field-label">비밀번호</div>', unsafe_allow_html=True)
                password = st.text_input(
                    "비밀번호", type="password", value="", placeholder="비밀번호를 입력하세요",
                    autocomplete="current-password", label_visibility="collapsed",
                )

                st.markdown('<div class="role-note">사용할 화면</div>', unsafe_allow_html=True)
                with st.container(key="role_actions"):
                    role_label = st.radio(
                        "역할", options=[ROLE_KO[r] for r in ROLE_ORDER],
                        label_visibility="collapsed", horizontal=True,
                    )
                    submitted = st.form_submit_button("로그인", use_container_width=True)

            # ──────────────────────────────
            # 기관 로고 (카드 안, 주최·주관 1줄 + 참여 1줄)
            # ──────────────────────────────

            st.markdown(
                f"""
                <div class="org-footer">
                  <div class="org-footer-top">
                      <div class="org-row">
                        <span class="org-caption">주최</span>
                        <div class="org-logos">
                          <img src="{ORG_LOGOS.get('motie', '')}" alt="산업통상부">
                        </div>
                      </div>
                      <div class="org-row">
                        <span class="org-caption">주관</span>
                        <div class="org-logos">
                          <img src="{ORG_LOGOS.get('kiat', '')}" alt="KIAT">
                          <img src="{ORG_LOGOS.get('koshipa', '')}" alt="한국조선해양플랜트협회">
                        </div>
                      </div>
                  </div>
                  <div class="org-row" style="margin-top: 12px;">
                    <span class="org-caption">참여</span>
                    <div class="org-logos">
                      <img src="{ORG_LOGOS.get('hd_ksoe', '')}" alt="HD한국조선해양">
                      <img src="{ORG_LOGOS.get('hanwha_ocean', '')}" alt="한화오션">
                      <img src="{ORG_LOGOS.get('samsung_heavy', '')}" alt="삼성중공업">
                      <img src="{ORG_LOGOS.get('snak', '')}" alt="대한조선학회" class="emblem">
                      <img src="{ORG_LOGOS.get('kriso', '')}" alt="KRISO">
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if submitted:
            role = next(r for r in ROLE_ORDER if ROLE_KO[r] == role_label)
            account = ACCOUNTS.get(user_id.strip())

            if account is None or password != account["pw"]:
                st.error("아이디 또는 비밀번호가 맞지 않습니다.")
            elif role not in account["roles"]:
                st.error(f"이 계정에는 {ROLE_KO[role]} 화면 권한이 없습니다.")
            else:
                st.session_state.user = {
                    "id": user_id.strip(), "name": account["name"],
                    "team": account["team"], "role": role,
                }
                st.rerun()


# ══════════════════════════════════════════════════
# 관리자 & 작업자 대시보드 렌더링 함수 유지
# ══════════════════════════════════════════════════
def render_admin_dashboard() -> None:
    path = ADMIN_DASHBOARD
    if not path.exists():
        st.error(f"관리자 대시보드 파일을 찾을 수 없습니다: {path.name}")
        return

    html = path.read_text(encoding="utf-8")
    data_js = path.parent / "data.js"

    if '<script src="data.js"></script>' in html:
        if not data_js.exists():
            st.error("data.js 를 찾을 수 없습니다. HTML과 같은 폴더에 두세요.")
            return
        html = html.replace('<script src="data.js"></script>', "<script>" + data_js.read_text(encoding="utf-8") + "</script>")

    components.html(html, height=4200, scrolling=True)


def render_worker_dashboard(user) -> None:
    role = user["role"]
    params = urlencode({"role": role, "user_id": user["id"], "name": user["name"], "team": user["team"]})
    worker_url = f"{WORKER_UI_URL}?{params}"

    # Streamlit 컴포넌트 안에 iframe을 한 번 더 중첩하면 두 스크롤 영역이
    # 휠 입력을 번갈아 가져가므로, Vite 화면을 단일 iframe으로 직접 렌더링한다.
    components.iframe(worker_url, height=900, scrolling=True)


def render_dashboard() -> None:
    user = st.session_state.user
    role = user["role"]
    bar_left, bar_right = st.columns([5, 1])

    with bar_left:
        st.markdown(
            f"""
            <div class="sessionbar">
              <span class="tag">{ROLE_KO[role]}</span>
              <span><b>{user['name']}</b> · {user['team']}</span>
              <span class="sp"></span>
              <span>{ROLE_DESC[role]}</span>
            </div>
            """, unsafe_allow_html=True,
        )

    with bar_right:
        st.write("")
        if st.button("로그아웃", key="logout"):
            st.session_state.user = None
            st.rerun()

    if role in ("admin", "senior"):
        render_admin_dashboard()
        return
    if role == "worker":
        render_worker_dashboard(user)
        return

    st.error(f"지원하지 않는 역할입니다: {role}")


# ══════════════════════════════════════════════════
# 라우팅
# ══════════════════════════════════════════════════
if st.session_state.user is None:
    render_login()
else:
    render_dashboard()
