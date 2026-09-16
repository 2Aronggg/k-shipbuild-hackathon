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

from pathlib import Path
from urllib.parse import urlencode

import streamlit as st
import streamlit.components.v1 as components


# ══════════════════════════════════════════════════
# 설정
# ══════════════════════════════════════════════════

APP_DIR = Path(__file__).parent

# 관리자 화면만 기존 HTML 사용
ADMIN_DASHBOARD = APP_DIR / "weldscan_dashboard.html"

# 네 Figma Make → React/Vite 작업자 화면
# npm run dev 실행 시 기본 주소
WORKER_UI_URL = "http://localhost:5173"


# 데모 계정
# 실제 도입 시 LDAP / SSO 등으로 교체 가능
ACCOUNTS = {
    "admin": {
        "pw": "weldscan",
        "name": "김성준",
        "team": "품질관리팀",
        "roles": {"admin", "senior", "worker"},
    },
    "senior": {
        "pw": "weldscan",
        "name": "윤경석",
        "team": "비파괴검사팀",
        "roles": {"senior", "worker"},
    },
    "worker": {
        "pw": "weldscan",
        "name": "이수빈",
        "team": "비파괴검사팀",
        "roles": {"worker"},
    },
}


ROLE_KO = {
    "admin": "관리자",
    "senior": "책임 검사원",
    "worker": "검사자",
}

ROLE_DESC = {
    "admin": "판정 일관성 관제 — 검사자들이 규정대로 판정하고 있는지 채점",
    "senior": "이관 건 최종 확정 — 검사자가 넘긴 애매한 건을 판단",
    "worker": "RT 필름 판독 — AI가 찾은 결함을 확인하고 판정 기록",
}

ROLE_ORDER = ["admin", "senior", "worker"]


# ══════════════════════════════════════════════════
# Streamlit 기본 설정
# ══════════════════════════════════════════════════

st.set_page_config(
    page_title="WeldScan AI",
    page_icon="🔶",
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
        background:#EFEEEB;
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
         로그인 화면
      ────────────────────────────── */

      .login-hero {
        max-width:420px;
        margin:6vh auto 0;
      }

      .login-hero .mark {
        width:52px;
        height:52px;
        border-radius:17px;

        background:#FF5A1F;
        color:#fff;

        display:grid;
        place-items:center;

        font:700 22px/1 Inter, system-ui, sans-serif;
        letter-spacing:-.02em;

        margin-bottom:18px;
      }

      .login-hero h1 {
        font:600 30px/1.2 Inter, "IBM Plex Sans KR", system-ui, sans-serif;
        letter-spacing:-.03em;
        color:#16161A;

        margin:0 0 8px;
      }

      .login-hero p {
        font:400 13.5px/1.65 "IBM Plex Sans KR", system-ui, sans-serif;
        color:#5C5C63;

        margin:0 0 22px;
      }

      .role-note {
        font:400 12px/1.6 "IBM Plex Sans KR", system-ui, sans-serif;
        color:#8B8B92;

        margin:-6px 0 14px;
      }

      .hintbox {
        margin-top:18px;
        padding:12px 14px;

        border-radius:12px;
        border:1px solid #E7E4DF;
        background:#F5F4F1;

        font:400 11.5px/1.7 "IBM Plex Mono", monospace;
        color:#5C5C63;
      }

      .hintbox b {
        color:#16161A;
      }


      /* ──────────────────────────────
         로그인 폼
      ────────────────────────────── */

      div[data-testid="stTextInput"] input {
        border-radius:12px !important;
        border:1px solid #E7E4DF !important;
        background:#fff !important;

        padding:11px 14px !important;
        font-size:13.5px !important;
      }

      div[data-testid="stTextInput"] input:focus {
        border-color:#FF5A1F !important;
        box-shadow:none !important;
      }

      div[data-testid="stTextInput"] label,
      div[data-testid="stRadio"] label {
        font-size:12px !important;
        color:#5C5C63 !important;
        font-weight:500 !important;
      }

      div[data-testid="stForm"] {
        border:0 !important;
        padding:0 !important;
      }

      .stButton > button,
      div[data-testid="stFormSubmitButton"] > button {
        width:100%;

        border-radius:99px;
        border:1px solid #FF5A1F;

        background:#FF5A1F;
        color:#fff;

        font-weight:600;
        font-size:13.5px;

        padding:11px 18px;

        transition:.15s;
      }

      .stButton > button:hover,
      div[data-testid="stFormSubmitButton"] > button:hover {
        background:#EC4A11;
        border-color:#EC4A11;
        color:#fff;
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

        border-radius:99px;

        background:#fff;
        border:1px solid #E7E4DF;

        font:400 12.5px/1.5 "IBM Plex Sans KR", system-ui, sans-serif;
        color:#5C5C63;
      }

      .sessionbar b {
        color:#16161A;
        font-weight:600;
      }

      .sessionbar .tag {
        font:600 11px/1 "IBM Plex Mono", monospace;

        padding:5px 10px;
        border-radius:99px;

        background:#FFF3ED;
        color:#B83E10;
        border:1px solid #FFD5C2;
      }

      .sessionbar .sp {
        flex:1;
      }

    </style>
    """,
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

    st.markdown(
        """
        <div class="login-hero">

          <div class="mark">W</div>

          <h1>WeldScan AI</h1>

          <p>
            용접부 비파괴검사 판정 보조 시스템입니다.<br>
            계정으로 로그인한 뒤 사용할 화면을 선택해 주세요.
          </p>

        </div>
        """,
        unsafe_allow_html=True,
    )


    left, mid, right = st.columns([1, 1.25, 1])


    with mid:

        with st.form("login", clear_on_submit=False):

            user_id = st.text_input(
                "사번 / 아이디",
                value="admin",
                autocomplete="username",
            )

            password = st.text_input(
                "비밀번호",
                type="password",
                value="",
                autocomplete="current-password",
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

                captions=[
                    ROLE_DESC[r]
                    for r in ROLE_ORDER
                ],

                label_visibility="collapsed",
                horizontal=False,
            )


            submitted = st.form_submit_button("로그인")


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


        # 데모 계정 표시

        st.markdown(
            """
            <div class="hintbox">

              데모 계정<br>

              <b>admin</b> / weldscan
              &nbsp;— 세 화면 모두 가능<br>

              <b>senior</b> / weldscan
              &nbsp;— 책임 검사원 · 검사자<br>

              <b>worker</b> / weldscan
              &nbsp;— 검사자만

            </div>
            """,
            unsafe_allow_html=True,
        )


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