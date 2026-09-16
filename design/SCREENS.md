# WeldScan Screen Specifications

화면별 레이아웃과 동작을 정의한다. 공통 색상, 서체, 컴포넌트 규칙은 `DESIGN_SYSTEM.md`를 따른다.

## 1. 로그인

- 구현: `weldscan-dashboard/app.py`의 `render_login()`
- 역할: 사용자 인증과 역할별 화면 진입

### 화면 구조

- 좌측: 야간 선박 이미지와 짧은 브랜드 메시지
- 우측: 로고, 시스템 이름, ID, 비밀번호, 역할, 로그인 버튼, 안내 문구
- 로그인 카드가 항상 가장 중요한 요소가 되도록 배경 대비를 조절한다.

### 상태

- 기본: 입력 가능
- 입력: Focus border 표시
- 오류: 해당 입력창과 오류 메시지 표시, 카드 전체 shake 금지
- 로딩: 버튼 로딩 및 중복 클릭 방지
- 완료: 계정 역할에 따라 Worker 또는 관리자 화면 진입

## 2. Worker UI

- 구현: `weldscan-dashboard/worker_ui/src/App.tsx`
- 역할: RT 영상 확인, 기공 검토, 유사 사례 참고, 작업자 판정

### 화면 구조

- Header: 검사 ID, 작업자, 현재 작업 상태
- RT Viewer: 화면에서 가장 큰 영역이며 영상, 확대/축소, Pan, 기공 위치 표시 제공
- AI 결과 패널: 결함 종류, 탐지 개수, 현재 상태만 간결하게 표시
- 유사 사례: RT Viewer 아래 Top 5 카드로 이미지, 유사도, 과거 판정 표시
- 작업자 판정: 프로젝트 상태에 따른 최종 판정 저장

### 주요 상호작용

- RT Viewer 확대/축소/Pan
- Marker hover 및 선택 정보 표시
- 유사 사례 카드 선택 후 확대 비교
- 판정 저장 및 다음 검사 흐름

## 3. WeldScan 관리자 화면

- 구현: `weldscan-dashboard/weldscan_dashboard.html`
- 역할: 검사 현황과 품질 정보 관리

### 화면 구조

- Sidebar/상단 탭: 운영, 품질, 검사자 관제 화면 이동
- 상단 KPI: 검사, 탐지, 재검, 완료 등 핵심 현황
- Dashboard: 검사 추이, 결함 종류, 작업량, 품질 통계
- Table: 검사 목록, 검색, 정렬, 필터
- Detail: RT 이미지, AI 결과, 작업자 판정, 검사 이력

### 주요 상호작용

- 실시간 검색
- 기간, 검사자, 결함 종류, 상태 필터
- 표 열 정렬
- 행 선택 후 상세 정보 확인

## 공통 반응형 원칙

- Desktop `1920×1080`: 정보를 최대한 표시한다.
- Laptop: Sidebar 축소, 차트는 2열에서 1열로 전환할 수 있다.
- Tablet: 카드 그리드를 축소하고 RT Viewer를 우선한다.
- Mobile: 관리자는 읽기 중심, Worker는 RT Viewer 중심으로 단순화한다.

## 화면 우선순위

- 로그인: 로그인 → 브랜드 → 배경
- Worker: RT Viewer → AI 결과 → 유사 사례 → 작업자 판정
- 관리자: KPI → Chart → Table → Detail
