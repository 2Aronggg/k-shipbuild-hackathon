"""
WeldScan AI — Streamlit 진입점
로그인 → 역할(관리자 / 작업자) 선택 → 역할에 맞는 대시보드 표시.

실행:  streamlit run app.py
"""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# ══════════════════════════════════════════════════ 설정
APP_DIR = Path(__file__).parent
DASHBOARDS = {
    "admin":  APP_DIR / "weldscan_dashboard.html",  # 관리자 · 판정 일관성 관제
    "worker": APP_DIR / "worker_dashboard.html",    # 검사자 · RT 필름 판독
    "senior": APP_DIR / "worker_dashboard.html",    # 책임 검사원 · 같은 판독 화면, 이관 건 목록 추가
}

# 데모 계정. 실제 도입 시 사내 인증(LDAP/SSO)으로 교체할 자리.
ACCOUNTS = {
    "admin":  {"pw": "weldscan", "name": "김성준", "team": "품질관리팀",
               "roles": {"admin", "senior", "worker"}},
    "senior": {"pw": "weldscan", "name": "윤경석", "team": "비파괴검사팀",
               "roles": {"senior", "worker"}},
    "worker": {"pw": "weldscan", "name": "이수빈", "team": "비파괴검사팀",
               "roles": {"worker"}},
}

ROLE_KO = {"admin": "관리자", "senior": "책임 검사원", "worker": "검사자"}
ROLE_DESC = {
    "admin":  "판정 일관성 관제 — 검사자들이 규정대로 판정하고 있는지 채점",
    "senior": "이관 건 최종 확정 — 검사자가 넘긴 애매한 건을 판단",
    "worker": "RT 필름 판독 — AI가 찾은 결함을 확인하고 판정 기록",
}
ROLE_ORDER = ["admin", "senior", "worker"]

st.set_page_config(
    page_title="WeldScan AI",
    page_icon="🔶",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════ 스타일
st.markdown(
    """
    <style>
      .stApp { background:#EFEEEB; }
      header[data-testid="stHeader"], #MainMenu, footer { display:none; }
      .block-container { padding:0 !important; max-width:none !important; }

      /* 로그인 화면 */
      .login-hero { max-width:420px; margin:6vh auto 0; }
      .login-hero .mark {
        width:52px; height:52px; border-radius:17px; background:#FF5A1F; color:#fff;
        display:grid; place-items:center; font:700 22px/1 Inter, system-ui, sans-serif;
        letter-spacing:-.02em; margin-bottom:18px;
      }
      .login-hero h1 {
        font:600 30px/1.2 Inter, "IBM Plex Sans KR", system-ui, sans-serif;
        letter-spacing:-.03em; color:#16161A; margin:0 0 8px;
      }
      .login-hero p {
        font:400 13.5px/1.65 "IBM Plex Sans KR", system-ui, sans-serif;
        color:#5C5C63; margin:0 0 22px;
      }
      .role-note {
        font:400 12px/1.6 "IBM Plex Sans KR", system-ui, sans-serif;
        color:#8B8B92; margin:-6px 0 14px;
      }
      .hintbox {
        margin-top:18px; padding:12px 14px; border-radius:12px;
        border:1px solid #E7E4DF; background:#F5F4F1;
        font:400 11.5px/1.7 "IBM Plex Mono", monospace; color:#5C5C63;
      }
      .hintbox b { color:#16161A; }

      /* 로그인 폼 컨트롤 */
      div[data-testid="stTextInput"] input {
        border-radius:12px !important; border:1px solid #E7E4DF !important;
        background:#fff !important; padding:11px 14px !important; font-size:13.5px !important;
      }
      div[data-testid="stTextInput"] input:focus { border-color:#FF5A1F !important; box-shadow:none !important; }
      div[data-testid="stTextInput"] label, div[data-testid="stRadio"] label {
        font-size:12px !important; color:#5C5C63 !important; font-weight:500 !important;
      }
      div[data-testid="stForm"] { border:0 !important; padding:0 !important; }
      .stButton > button, div[data-testid="stFormSubmitButton"] > button {
        width:100%; border-radius:99px; border:1px solid #FF5A1F; background:#FF5A1F; color:#fff;
        font-weight:600; font-size:13.5px; padding:11px 18px; transition:.15s;
      }
      .stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        background:#EC4A11; border-color:#EC4A11; color:#fff;
      }

      /* 상단 세션 바 */
      .sessionbar {
        display:flex; align-items:center; gap:12px; flex-wrap:wrap;
        padding:10px 20px; margin:14px 14px 0; border-radius:99px;
        background:#fff; border:1px solid #E7E4DF;
        font:400 12.5px/1.5 "IBM Plex Sans KR", system-ui, sans-serif; color:#5C5C63;
      }
      .sessionbar b { color:#16161A; font-weight:600; }
      .sessionbar .tag {
        font:600 11px/1 "IBM Plex Mono", monospace; padding:5px 10px; border-radius:99px;
        background:#FFF3ED; color:#B83E10; border:1px solid #FFD5C2;
      }
      .sessionbar .sp { flex:1; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════ 세션 상태
st.session_state.setdefault("user", None)   # {"id","name","team","role"}


def render_login() -> None:
    st.markdown(
        """
        <div class="login-hero">
          <div class="mark">W</div>
          <h1>WeldScan AI</h1>
          <p>용접부 비파괴검사 판정 보조 시스템입니다.<br>
             계정으로 로그인한 뒤 사용할 화면을 선택해 주세요.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, mid, right = st.columns([1, 1.25, 1])
    with mid:
        with st.form("login", clear_on_submit=False):
            user_id = st.text_input("사번 / 아이디", value="admin", autocomplete="username")
            password = st.text_input("비밀번호", type="password", value="", autocomplete="current-password")

            st.markdown('<div class="role-note">사용할 화면</div>', unsafe_allow_html=True)
            role_label = st.radio(
                "역할",
                options=[ROLE_KO[r] for r in ROLE_ORDER],
                captions=[ROLE_DESC[r] for r in ROLE_ORDER],
                label_visibility="collapsed",
                horizontal=False,
            )
            submitted = st.form_submit_button("로그인")

        if submitted:
            role = next(r for r in ROLE_ORDER if ROLE_KO[r] == role_label)
            account = ACCOUNTS.get(user_id.strip())

            if account is None or password != account["pw"]:
                st.error("아이디 또는 비밀번호가 맞지 않습니다.")
            elif role not in account["roles"]:
                st.error(f"이 계정에는 {ROLE_KO[role]} 화면 권한이 없습니다.")
            else:
                st.session_state.user = {
                    "id": user_id.strip(),
                    "name": account["name"],
                    "team": account["team"],
                    "role": role,
                }
                st.rerun()

        st.markdown(
            """
            <div class="hintbox">
              데모 계정<br>
              <b>admin</b> / weldscan &nbsp;— 세 화면 모두 가능<br>
              <b>senior</b> / weldscan &nbsp;— 책임 검사원 · 검사자<br>
              <b>worker</b> / weldscan &nbsp;— 검사자만
            </div>
            """,
            unsafe_allow_html=True,
        )


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
            """,
            unsafe_allow_html=True,
        )
    with bar_right:
        st.write("")
        if st.button("로그아웃", key="logout"):
            st.session_state.user = None
            st.rerun()

    path = DASHBOARDS[role]
    if not path.exists():
        st.error(f"대시보드 파일을 찾을 수 없습니다: {path.name}")
        st.caption("app.py 와 같은 폴더에 HTML 파일 두 개가 함께 있어야 합니다.")
        return

    # 대시보드 HTML은 편집하기 쉽도록 데이터를 data.js 로 분리해 둠.
    # Streamlit 은 iframe srcdoc 으로 렌더하므로 상대 경로 <script src> 가 풀리지 않음 → 여기서 합쳐 넣음.
    html = path.read_text(encoding="utf-8")
    data_js = path.parent / "data.js"
    if '<script src="data.js"></script>' in html:
        if not data_js.exists():
            st.error("data.js 를 찾을 수 없습니다. HTML 과 같은 폴더에 두세요.")
            return
        html = html.replace(
            '<script src="data.js"></script>',
            "<script>" + data_js.read_text(encoding="utf-8") + "</script>",
        )

    # 검사자와 책임 검사원은 같은 판독 화면을 씀. 역할만 주입해 이관 목록·버튼이 달라지게 함.
    if role in ("worker", "senior"):
        html = html.replace("<body>", f'<body>\n<script>window.WS_ROLE="{role}";</script>', 1)

    height = 4200 if role == "admin" else 2500
    components.html(html, height=height, scrolling=True)


# ══════════════════════════════════════════════════ 라우팅
if st.session_state.user is None:
    render_login()
else:
    render_dashboard()
