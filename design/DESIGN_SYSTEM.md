# WeldScan Design System

이 문서는 로그인, Worker UI, WeldScan 관리자 화면에 공통으로 적용하는 단일 디자인 기준입니다.

## 적용 화면

| 화면 | 구현 위치 | 기술 |
| --- | --- | --- |
| 로그인 | `weldscan-dashboard/app.py`의 `render_login()` | Streamlit + HTML/CSS |
| Worker | `weldscan-dashboard/worker_ui/src/App.tsx` | React + Tailwind CSS |
| 관리자 | `weldscan-dashboard/weldscan_dashboard.html` | HTML/CSS/JavaScript |

## 브랜드 원칙

- 조선·RT 검사 환경에 어울리는 딥 네이비와 전기 블루를 사용한다.
- 정보 전달을 장식보다 우선하며 과도한 그라데이션과 광원 효과를 피한다.
- 로그인, Worker, 관리자 화면은 동일한 `W` 마크와 WeldScan 이름을 사용한다.
- 실제 구현 값의 단일 원본은 `brand/brand-tokens.json`이다.

## 색상

- 브랜드 네이비: `#071426`
- 브랜드 블루: `#3397D4`
- 블루 Hover: `#60B7EA`
- 밝은 배경: `#F4F7FA`
- 어두운 표면: `#161617`
- 성공 / 주의 / 위험: `#16A34A` / `#F59E0B` / `#E53935`
- RT 결함 마커(P1/P2/P3)는 `color.semanticDefect`로 별도 고정되며, 위 브랜드 팔레트가 바뀌어도 함께 바뀌지 않는다.

## 타이포그래피

- 본문: Inter, IBM Plex Sans KR, system-ui
- 숫자와 ID: IBM Plex Mono, JetBrains Mono
- 화면 제목보다 검사 데이터와 상태값의 가독성을 우선한다.

## 간격과 형태

- 기본 모서리: 5px, 카드: 10px, 큰 로그인 카드: 16px
- 테두리는 1px을 기본으로 하고 그림자는 로그인 카드와 최상위 패널에만 제한한다.
- 기본 간격 단위는 4px이며 주요 패널 간격은 12~16px을 사용한다.

## 공통 컴포넌트

### 버튼

- Primary는 브랜드 블루, Secondary는 중립 표면과 얇은 테두리를 사용한다.
- 모든 버튼은 hover, focus-visible, disabled 상태를 구분한다.

### 카드

- 카드 선택은 블루 테두리로 표시하며 과도한 그림자를 사용하지 않는다.

### 입력창

- Focus는 브랜드 블루 테두리와 약한 focus ring으로 표시한다.
- 오류는 해당 입력창과 인접 메시지에만 표시하며 카드 전체 shake는 금지한다.

### Badge

- 상태색과 텍스트를 함께 사용해 색상만으로 의미를 전달하지 않는다.

### Modal / Drawer

- 기존 화면 맥락을 유지하며 Esc, 닫기 버튼, 배경 클릭 정책을 명확히 한다.

## 모션

- UI 피드백은 150~220ms 범위로 제한한다.
- 로그인 선박 비주얼은 느리고 미세한 움직임만 허용한다.
- `prefers-reduced-motion`에서는 장식 모션을 제거한다.

## 접근성

- 키보드 focus를 숨기지 않으며 주요 터치 영역은 최소 40px 이상으로 유지한다.
- 이미지에는 역할을 설명하는 대체 텍스트를 제공한다.
