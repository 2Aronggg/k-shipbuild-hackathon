"""
WeldScan AI — Streamlit 진입점

로그인
→ 역할 선택
→ 관리자: 기존 HTML 대시보드
→ 작업자/책임 검사원: React(Vite) 작업자 대시보드

실행:
1) worker-ui에서: npm run dev
2) 프로젝트 루트에서: streamlit run app.py
"""

import base64
from pathlib import Path
from urllib.parse import urlencode

import streamlit as st
import streamlit.components.v1 as components


# ══════════════════════════════════════════════════
# 설정
# ══════════════════════════════════════════════════

APP_DIR = Path(__file__).parent
LOGIN_BG_PATH = APP_DIR.parent / "design" / "background.png"
LOGIN_BG_DATA = base64.b64encode(LOGIN_BG_PATH.read_bytes()).decode("ascii")

# 관리자 화면만 기존 HTML 사용
ADMIN_DASHBOARD = APP_DIR / "weldscan_dashboard.html"

# 네 Figma Make → React/Vite 작업자 화면
# npm run dev 실행 시 기본 주소
WORKER_UI_URL = "http://localhost:8443"


# 데모 계정
# 실제 도입 시 LDAP / SSO 등으로 교체 가능
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
    "worker": "작업자 (Worker)",
    "admin": "관리자 (Admin)",
    "senior": "검사자 (Inspector)", # 기존 '책임 검사원'을 이미지에 맞게 변경
}

ROLE_DESC = {
  "worker": "용접부 검사 및 1차 판정",
  "admin": "검사 현황 및 품질 관리",
  "senior": "이관 건 검토 및 최종 판정",
}

# 표시 순서를 이미지와 동일하게 (작업자 -> 관리자 -> 검사자) 맞추려면 아래 순서를 변경하세요.
ROLE_ORDER = ["worker", "admin", "senior"]




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
# 스타일
# ══════════════════════════════════════════════════

st.markdown(
    """
    <style>

      .stApp {
        background:#161617;
      }

      header[data-testid="stHeader"],
      #MainMenu,
      footer {
        display:none;
      }

      .block-container {
        padding:0 !important;
        max-width:none !important;
      }


      /* ──────────────────────────────
         로그인 후 상단 세션바
      ────────────────────────────── */

      .sessionbar {
        display:flex;
        align-items:center;

        gap:12px;
        flex-wrap:wrap;

        padding:10px 20px;
        margin:14px 14px 0;

        border-radius:10px;

        background:#333336;
        border:1px solid #41626A;

        font:400 12.5px/1.5 "IBM Plex Sans KR", system-ui, sans-serif;
        color:#D2D2D7;
      }

      .sessionbar b {
        color:#F4F8FB;
        font-weight:600;
      }

      .sessionbar .tag {
        font:600 11px/1 "IBM Plex Mono", monospace;

        padding:5px 10px;
        border-radius:99px;

        background:#3397D4;
        color:#fff;
        border:1px solid #3397D4;
      }

      .sessionbar .sp {
        flex:1;
      }

      /* ──────────────────────────────
         WeldScan 로그인 셸 (좌 히어로 / 우 로그인 카드)
      ────────────────────────────── */

      .stApp:has(.login-scene) {
        background:#061526;
      }

      .stApp:has(.login-scene) .block-container {
        height:100vh;
        padding:0 !important;
        overflow:hidden;
      }

      .stApp:has(.login-scene) div[data-testid="stHorizontalBlock"] {
        gap:0;
        height:100vh;
      }

      .stApp:has(.login-scene) div[data-testid="column"] {
        display:flex;
        flex-direction:column;
        justify-content:center;
        height:100vh;
        overflow:hidden;
      }

      /* ── 좌측 히어로 (조선소 · 배 이미지) ── */

      .login-scene {
        height:100vh;
        position:relative;
        display:flex;
        flex-direction:column;
        justify-content:flex-end;
        padding:clamp(24px,3vw,44px);
        overflow:hidden;
        background:
          linear-gradient(0deg,rgba(4,10,20,.88) 0%,rgba(4,10,20,.15) 42%,rgba(4,10,20,.05) 60%),
          url("data:image/png;base64,{LOGIN_BG_DATA}") center/cover no-repeat;
      }

      .login-scene::before {
        content:"";
        position:absolute;
        inset:0;
        background-image:
          linear-gradient(rgba(50,214,255,.05) 1px,transparent 1px),
          linear-gradient(90deg,rgba(50,214,255,.05) 1px,transparent 1px);
        background-size:42px 42px;
        mix-blend-mode:screen;
        pointer-events:none;
      }

      .scene-badge {
        position:absolute;
        top:clamp(20px,2.6vw,32px);
        right:clamp(24px,3vw,44px);
        z-index:1;
        text-align:right;
        font:600 10px/1.6 "IBM Plex Mono",monospace;
        letter-spacing:.14em;
        color:rgba(245,249,252,.55);
      }

      .scene-feats {
        position:relative;
        z-index:1;
        display:flex;
        gap:clamp(18px,2.6vw,40px);
        flex-wrap:wrap;
        margin-top:clamp(20px,3vw,32px);
      }

      .scene-feat {display:flex;gap:10px;align-items:flex-start;max-width:200px}
      .scene-feat .ic {
        flex:none;width:34px;height:34px;border-radius:9px;
        background:rgba(50,214,255,.1);border:1px solid rgba(50,214,255,.28);
        display:grid;place-items:center;color:#32D6FF;
      }
      .scene-feat .ic svg {width:17px;height:17px}
      .scene-feat b {display:block;font:600 13px/1.4 "IBM Plex Sans KR",Inter,sans-serif;color:#F5F9FC}
      .scene-feat span {display:block;font:400 11.5px/1.5 "IBM Plex Sans KR",Inter,sans-serif;color:#9FB1C2;margin-top:2px}

      .scene-foot {
        position:relative;
        z-index:1;
        margin-top:clamp(18px,2.4vw,28px);
        padding-top:14px;
        border-top:1px solid rgba(159,177,194,.16);
        font:500 10px/1 "IBM Plex Mono",monospace;
        letter-spacing:.16em;
        color:rgba(159,177,194,.7);
        text-transform:uppercase;
      }

      /* ── 우측 로그인 패널 ── */

      .stApp:has(.login-scene) div[data-testid="column"]:last-child {
        background:#061526;
        padding:clamp(20px,3vw,40px);
      }

      .stApp:has(.login-scene) div[data-testid="column"]:last-child > div {
        width:min(100%,420px);
        margin-inline:auto;
      }

      .st-key-login_card {
        border:1px solid #31516F;
        border-radius:18px;
        background:rgba(10,31,52,.88);
        padding:clamp(22px,2.6vw,30px) clamp(24px,2.8vw,32px);
      }

      .st-key-login_card div[data-testid="stVerticalBlock"] {
        gap:0.5rem !important;
      }

      .login-hero {max-width:none;margin:0 0 20px}
      .login-hero h1 {
        font:700 27px/1.2 Inter,"IBM Plex Sans KR",sans-serif;
        letter-spacing:-.02em;
        margin:0 0 8px;
        background:linear-gradient(90deg,#E6F4FF 0%,#64C7FF 55%,#22D3EE 100%);
        -webkit-background-clip:text;
        background-clip:text;
        -webkit-text-fill-color:transparent;
        color:#F5F9FC;
      }
      .login-hero p {font:400 13px/1.6 "IBM Plex Sans KR",Inter,sans-serif;color:#9FB1C2;margin:0}
      .login-hero .sub2 {font-size:12px;color:#6F8498;margin-top:6px}

      .field-label {
        font:500 12px/1 "IBM Plex Sans KR",Inter,sans-serif;
        color:#9FB1C2;
        margin:16px 0 7px;
      }
      .field-label:first-of-type {margin-top:0}

      div[data-testid="stTextInput"] {position:relative}

      div[data-testid="stTextInput"] label,
      div[data-testid="stWidgetLabel"] {
        display:none !important;
      }

      div[data-testid="stTextInput"] div[data-baseweb="input"] {
        border-radius:9px !important;
        border:1px solid #31516F !important;
        background:rgba(6,21,38,.6) !important;
        overflow:hidden;
      }

      div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {
        border-color:#32D6FF !important;
        box-shadow:0 0 0 3px rgba(50,214,255,.14) !important;
      }

      div[data-testid="stTextInput"] input {
        background:transparent !important;
        border:none !important;
        color:#F5F9FC !important;
        padding:12px 14px 12px 40px !important;
        min-height:46px !important;
        font-size:13.5px !important;
      }

      div[data-testid="stTextInput"] input::placeholder {color:#6F8498 !important}

      /* 입력창 좌측 라인 아이콘 (사번/비밀번호) */
      div[data-testid="stTextInput"]:has(input[aria-label="사번 / ID"])::before,
      div[data-testid="stTextInput"]:has(input[aria-label="비밀번호"])::before {
        content:"";
        position:absolute;
        left:13px;top:50%;
        width:16px;height:16px;
        transform:translateY(-50%);
        z-index:2;
        pointer-events:none;
        background-repeat:no-repeat;background-position:center;background-size:contain;
        opacity:.65;
      }
      div[data-testid="stTextInput"]:has(input[aria-label="사번 / ID"])::before {
        background-image:url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%239FB1C2" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>');
      }
      div[data-testid="stTextInput"]:has(input[aria-label="비밀번호"])::before {
        background-image:url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%239FB1C2" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>');
      }

      /* ── 하단 '사용할 화면' 라디오 버튼 커스텀 ── */

      .st-key-login_card div[data-testid="stRadio"] div[data-baseweb="radio"] > div:first-child {
        display:none !important;
      }

      .st-key-login_card div[data-testid="stRadio"] {
        margin-top:6px;
        margin-bottom:24px;
      }

      .st-key-login_card div[role="radiogroup"] {
        display:flex;
        gap:12px !important;
        flex-direction:row;
      }

      .st-key-login_card div[role="radiogroup"] label {
        flex:1 1 0;
        background:rgba(6,21,38,.6) !important;
        border:1px solid #31516F !important;
        border-radius:9px !important;
        padding:10px 20px !important;
        color:#FFFFFF !important;
        font:500 13px/1 "IBM Plex Sans KR",Inter,sans-serif !important;
        cursor:pointer;
        margin:0 !important;
        transition:all .2s ease;
        display:flex;
        justify-content:center;
        align-items:center;
      }

      .st-key-login_card div[role="radiogroup"] label:hover {
        border-color:rgba(50,214,255,.5) !important;
        color:#F5F9FC !important;
      }

      .st-key-login_card div[role="radiogroup"] label:has(input:checked) {
        background:rgba(50,214,255,.1) !important;
        border-color:#32D6FF !important;
        color:#FFFFFF !important;
        box-shadow:0 0 0 1px rgba(50,214,255,.2) !important;
      }

      .st-key-login_card div[role="radiogroup"] label p,
      .st-key-login_card div[role="radiogroup"] label span {
        color:#FFFFFF !important;
        font:inherit !important;
        margin:0 !important;
      }

      .role-note {
        font:500 12px/1 "IBM Plex Sans KR", Inter, sans-serif;
        color:#9FB1C2;
        margin:16px 0 7px;
      }

      /* ── 로그인 버튼 ── */

      div[data-testid="stForm"] {border:0 !important;padding:0 !important;margin-top:18px}

      .stButton > button,
      div[data-testid="stFormSubmitButton"] > button {
        width:100%;
        min-height:50px;
        border-radius:10px;
        border:1px solid transparent;
        background:linear-gradient(90deg,#2F9BFF,#32D6FF);
        color:#06121F;
        font-weight:700;
        font-size:14.5px;
        padding:12px 18px;
        margin-top:18px;
        transition:filter .15s;
      }

      .stButton > button:hover,
      div[data-testid="stFormSubmitButton"] > button:hover {
        filter:brightness(1.08);
        background:linear-gradient(90deg,#2F9BFF,#32D6FF);
        color:#06121F;
      }

      /* ── 샘플 계정 ── */

      .hintbox {
        margin-top:16px;
        padding-top:14px;

        border-top:1px solid #31516F;
        background:transparent;
        border-radius:0;

        font:400 11.5px/1.7 "IBM Plex Sans KR", sans-serif;
        color:#9FB1C2;
      }

      .hintbox .lbl {color:#6F8498;font-size:11.5px;margin-bottom:9px;display:block}

      .hintbox .chips {display:flex;gap:6px;flex-wrap:wrap}

      .hintbox .chip {
        display:inline-flex;align-items:center;gap:5px;
        padding:6px 10px;
        border-radius:7px;
        border:1px solid #31516F;
        background:rgba(255,255,255,.02);
        font-family:"IBM Plex Mono",monospace;
        font-size:10.5px;
        color:#9FB1C2;
        white-space:nowrap;
      }

      .hintbox .chip b {color:#F5F9FC;font-weight:600;font-family:"IBM Plex Sans KR",sans-serif}

      @keyframes shipDrift {from{transform:translate3d(-6px,2px,0)}to{transform:translate3d(8px,-3px,0)}}
      @media (prefers-reduced-motion:reduce){* {animation:none !important}}

      @media (max-width:900px){
        .stApp:has(.login-scene) div[data-testid="stHorizontalBlock"]{display:block;height:auto}
        .stApp:has(.login-scene) .block-container{height:auto;overflow:visible}
        .stApp:has(.login-scene) div[data-testid="column"]{height:auto}
        .login-scene{height:auto;min-height:38vh}
        .scene-feats{display:none}
        .stApp:has(.login-scene) div[data-testid="column"]:last-child{padding:28px 20px}
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
    left, right = st.columns([1.5, 1])

    with left:
        st.markdown(
            """
            <section class="login-scene" aria-label="WeldScan 브랜드 소개">
              <div class="scene-badge">MARITIME AI<br>FOR A SAFER TOMORROW</div>

              <div class="scene-feats">
                <div class="scene-feat">
                  <div class="ic">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="9"/></svg>
                  </div>
                  <div><b>AI 기반 용접부 판정 보조</b><span>더 정확하고, 더 빠르게</span></div>
                </div>
                <div class="scene-feat">
                  <div class="ic">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/></svg>
                  </div>
                  <div><b>안전한 조선 산업</b><span>사람과 기술의 안전을 생각합니다</span></div>
                </div>
                <div class="scene-feat">
                  <div class="ic">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>
                  </div>
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
                  <p>용접부 비파괴검사 판정 보조 AI 시스템</p>
                  <div class="sub2">AI가 분석하는 정밀한 용접 검사, 더 안전한 조선 산업의 시작입니다.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.form("login", clear_on_submit=False):

                st.markdown('<div class="field-label">사번 / ID</div>', unsafe_allow_html=True)
                user_id = st.text_input(
                    "사번 / ID",
                    value="",
                    placeholder="사번 또는 아이디를 입력하세요",
                    autocomplete="username",
                    label_visibility="collapsed",
                )

                st.markdown('<div class="field-label">비밀번호</div>', unsafe_allow_html=True)
                password = st.text_input(
                    "비밀번호",
                    type="password",
                    value="",
                    placeholder="비밀번호를 입력하세요",
                    autocomplete="current-password",
                    label_visibility="collapsed",
                )


                st.markdown(
                    '<div class="role-note">사용할 화면</div>',
                    unsafe_allow_html=True,
                )


                role_label = st.radio(
                    "역할",

                    options=[
                        ROLE_KO[r]
                        for r in ROLE_ORDER
                    ],

                    label_visibility="collapsed",
                    horizontal=True,
                )


                submitted = st.form_submit_button("로그인 →")










            # ──────────────────────────────
            # 데모 계정 표시
            # ──────────────────────────────

            st.markdown(
                """
                <div class="hintbox">
                  <span class="lbl">샘플 계정으로 체험해 보세요.</span>
                  <div class="chips">
                    <span class="chip"><b>작업자</b> worker01 / 1234</span>
                    <span class="chip"><b>관리자</b> admin / 1234</span>
                    <span class="chip"><b>검사자</b> inspector01 / 1234</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ──────────────────────────────
        # 로그인 처리
        # ──────────────────────────────

        if submitted:

            role = next(
                r
                for r in ROLE_ORDER
                if ROLE_KO[r] == role_label
            )

            account = ACCOUNTS.get(
                user_id.strip()
            )


            if account is None or password != account["pw"]:

                st.error(
                    "아이디 또는 비밀번호가 맞지 않습니다."
                )


            elif role not in account["roles"]:

                st.error(
                    f"이 계정에는 {ROLE_KO[role]} 화면 권한이 없습니다."
                )


            else:

                st.session_state.user = {
                    "id": user_id.strip(),
                    "name": account["name"],
                    "team": account["team"],
                    "role": role,
                }

                st.rerun()


# ══════════════════════════════════════════════════
# 관리자 대시보드
# ══════════════════════════════════════════════════

def render_admin_dashboard() -> None:

    path = ADMIN_DASHBOARD


    if not path.exists():

        st.error(
            f"관리자 대시보드 파일을 찾을 수 없습니다: {path.name}"
        )

        return


    html = path.read_text(
        encoding="utf-8"
    )


    # data.js가 있다면 HTML 내부에 삽입
    # components.html은 srcdoc 기반 iframe이라
    # 일반 상대경로 script가 제대로 안 풀릴 수 있음.

    data_js = path.parent / "data.js"


    if '<script src="data.js"></script>' in html:

        if not data_js.exists():

            st.error(
                "data.js 를 찾을 수 없습니다. "
                "HTML과 같은 폴더에 두세요."
            )

            return


        html = html.replace(
            '<script src="data.js"></script>',

            "<script>"
            + data_js.read_text(
                encoding="utf-8"
            )
            + "</script>",
        )


    components.html(
        html,
        height=4200,
        scrolling=True,
    )


# ══════════════════════════════════════════════════
# 작업자 / 책임 검사원 React 화면
# ══════════════════════════════════════════════════

def render_worker_dashboard(user) -> None:

    role = user["role"]


    # 로그인 정보를 React 화면으로 전달
    #
    # 예:
    #
    # localhost:5173
    # ?role=worker
    # &user_id=worker
    # &name=이수빈
    # &team=비파괴검사팀


    params = urlencode(
        {
            "role": role,
            "user_id": user["id"],
            "name": user["name"],
            "team": user["team"],
        }
    )


    worker_url = (
        f"{WORKER_UI_URL}?{params}"
    )


    # 세션바(약 70px)를 제외한 나머지 브라우저 뷰포트 높이만큼
    # iframe을 꽉 채워서, React 쪽 h-screen 레이아웃이 그대로 맞도록 함
    components.html(
        f"""
        <iframe
          id="worker-frame"
          src="{worker_url}"
          style="display:block; width:100%; border:none;"
          scrolling="no"
        ></iframe>
        <script>
          function resizeWorkerFrame() {{
            const frame = window.frameElement;
            const iframe = document.getElementById('worker-frame');
            if (!frame || !iframe) return;

            const sessionBarHeight = 70;
            const targetHeight = window.parent.innerHeight - sessionBarHeight;

            iframe.style.height = targetHeight + 'px';
            frame.style.height = targetHeight + 'px';
          }}

          resizeWorkerFrame();
          window.parent.addEventListener('resize', resizeWorkerFrame);
        </script>
        """,
        height=900,
    )


# ══════════════════════════════════════════════════
# 로그인 후 역할별 화면
# ══════════════════════════════════════════════════

def render_dashboard() -> None:

    user = st.session_state.user

    role = user["role"]


    # ──────────────────────────────
    # 상단 세션 바
    # ──────────────────────────────

    bar_left, bar_right = st.columns(
        [5, 1]
    )


    with bar_left:

        st.markdown(
            f"""
            <div class="sessionbar">

              <span class="tag">
                {ROLE_KO[role]}
              </span>

              <span>
                <b>{user['name']}</b>
                ·
                {user['team']}
              </span>

              <span class="sp"></span>

              <span>
                {ROLE_DESC[role]}
              </span>

            </div>
            """,
            unsafe_allow_html=True,
        )


    with bar_right:

        st.write("")

        if st.button(
            "로그아웃",
            key="logout",
        ):

            st.session_state.user = None

            st.rerun()


    # ──────────────────────────────
    # 관리자
    # ──────────────────────────────

    if role == "admin":

        render_admin_dashboard()

        return


    # ──────────────────────────────
    # 검사자 / 책임 검사원
    # ──────────────────────────────

    if role in (
        "worker",
        "senior",
    ):

        render_worker_dashboard(user)

        return


    st.error(
        f"지원하지 않는 역할입니다: {role}"
    )


# ══════════════════════════════════════════════════
# 라우팅
# ══════════════════════════════════════════════════

if st.session_state.user is None:

    render_login()

else:

    render_dashboard()
