import React, { useState, useRef } from 'react';
import { 
  ZoomIn, ZoomOut, RotateCcw, Eye, ShieldAlert, CheckCircle2, 
  ArrowUpRight, Pin, ChevronRight, FileText, ChevronDown, ChevronUp,
  Info, HardHat, Layers, Check, X, Activity, Image as ImageIcon, Sliders, AlertTriangle, Trash2
} from 'lucide-react';
import attachedRtImage from './imports/ChatGPT_Image_2026__9__11_____01_12_32.png';

// --- DATA DEFINITIONS (POROSITY ONLY) ---

type DecisionType = 'confirmed' | 'error' | 'recheck' | null;

interface PorosityRegion {
  id: string;
  label: string; // P1, P2, P3
  location: string;
  x: number; // percentage on image
  y: number;
  width: number;
  height: number;
  diameter: string;
  poreCount: number;
  clusterDensity: string;
  riskLevel: '정상' | '검토 필요' | '위험';
  statusColor: 'green' | 'amber' | 'red';
  aiConfidence: number; // 데모 값
  workerDecision: DecisionType;
}

interface SimilarCase {
  id: string;
  caseId: string;
  vessel: string;
  similarity: number; // 데모 값
  porosityType: string;
  historicalDecision: string;
  actionTaken: string;
  statusColor: 'green' | 'amber' | 'red';
  note: string;
}

interface WorkerAnnotation {
  id: string;
  x: number;
  y: number;
  note: string;
  timestamp: string;
}

const POROSITY_REGIONS: PorosityRegion[] = [
  {
    id: 'p1',
    label: 'P1',
    location: '577mm 위치 (루트 용접부)',
    x: 34.2,
    y: 48.0,
    width: 3.5,
    height: 7.5,
    diameter: 'Ø 3.8 mm (가장 큰 기공)',
    poreCount: 1,
    clusterDensity: '단일 주요 기공 (규격 초과)',
    riskLevel: '고위험',
    statusColor: 'red',
    aiConfidence: 94,
    workerDecision: null,
  },
  {
    id: 'p2',
    label: 'P2',
    location: '559mm 위치 (채움 용접부)',
    x: 27.0,
    y: 44.5,
    width: 3.0,
    height: 6.5,
    diameter: 'Ø 2.1 mm (중간 기공)',
    poreCount: 1,
    clusterDensity: '단일 기공 (주의 요망)',
    riskLevel: '검토 필요',
    statusColor: 'amber',
    aiConfidence: 82,
    workerDecision: null,
  },
  {
    id: 'p3',
    label: 'P3',
    location: '531mm 위치 (표면 용접부)',
    x: 15.5,
    y: 59.1,
    width: 2.5,
    height: 5.5,
    diameter: 'Ø 1.2 mm (가장 작은 기공)',
    poreCount: 1,
    clusterDensity: '미세 기공 (허용 범위 내)',
    riskLevel: '정상',
    statusColor: 'green',
    aiConfidence: 88,
    workerDecision: null,
  },
];

const SIMILAR_CASES: SimilarCase[] = [
  {
    id: 'sc1',
    caseId: 'RT-2026-0412-8821',
    vessel: 'H-3412 (VLCC)',
    similarity: 94,
    porosityType: '루트 용접부 군집 기공',
    historicalDecision: '재용접',
    actionTaken: '가우징 20mm 후 FCAW 재용접',
    statusColor: 'red',
    note: '기공 직경 3.5mm 초과로 규격 미달. 재용접 후 UT 검사 통과.',
  },
  {
    id: 'sc2',
    caseId: 'RT-2025-1104-3019',
    vessel: 'H-3398 (174k LNG)',
    similarity: 88,
    porosityType: '채움 용접부 단일 기공',
    historicalDecision: '합격',
    actionTaken: 'ISO 5817 Level C 기준 충족으로 승인',
    statusColor: 'green',
    note: '기공 직경 2.0mm 이하로 허용 기준 이내.',
  },
  {
    id: 'sc3',
    caseId: 'RT-2026-0118-1290',
    vessel: 'H-3401 (15k TEU)',
    similarity: 81,
    porosityType: '표면 미세 기공',
    historicalDecision: '재확인',
    actionTaken: '표면 그라인딩 후 2차 재검사',
    statusColor: 'amber',
    note: '그라인딩 제거 후 재촬영하여 합격 처리됨.',
  },
];

export default function App() {
  // State Management
  const [porosities, setPorosities] = useState<PorosityRegion[]>(POROSITY_REGIONS);
  const [selectedPId, setSelectedPId] = useState<string>('p1');
  const [viewMode, setViewMode] = useState<'overlay' | 'original' | 'worker'>('overlay');
  
  // Custom uploaded RT Image URL
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);

  // RT Viewer Controls
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const [startPan, setStartPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Worker Pins & Notes
  const [pinMode, setPinMode] = useState<boolean>(false);
  const [annotations, setAnnotations] = useState<WorkerAnnotation[]>([]);
  const [newNoteText, setNewNoteText] = useState<string>('');
  const [activePinPrompt, setActivePinPrompt] = useState<{ x: number; y: number } | null>(null);

  // Secondary Collapsible Section States
  const [showBasis, setShowBasis] = useState<boolean>(false);
  const [comparisonCase, setComparisonCase] = useState<SimilarCase | null>(null);
  const [escalated, setEscalated] = useState<boolean>(false);
  const [notice, setNotice] = useState<string | null>(null);

  const viewerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selectedPorosity = porosities.find((p) => p.id === selectedPId) || porosities[0];

  // Calculate Progress
  const completedCount = porosities.filter((p) => p.workerDecision !== null).length;
  const progressPercent = Math.round((completedCount / porosities.length) * 100);

  // Handle Image Upload
  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setUploadedImage(url);
      showNotification('업로드한 RT 이미지가 적용되었습니다.');
    }
  };

  // Dragging state for Porosity Markers
  const [draggingPId, setDraggingPId] = useState<string | null>(null);

  // Mouse Pan/Zoom, Pin & Drag Handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (pinMode) {
      if (!viewerRef.current) return;
      const rect = viewerRef.current.getBoundingClientRect();
      const x = Math.round(((e.clientX - rect.left) / rect.width) * 1000) / 10;
      const y = Math.round(((e.clientY - rect.top) / rect.height) * 1000) / 10;
      setActivePinPrompt({ x, y });
      setPinMode(false);
      return;
    }
    if (!draggingPId) {
      setIsPanning(true);
      setStartPan({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMarkerDrag = (pId: string, deltaX: number, deltaY: number) => {
    const imgElem = viewerRef.current?.querySelector('img');
    const rect = imgElem ? imgElem.getBoundingClientRect() : viewerRef.current?.getBoundingClientRect();
    if (!rect) return;

    // Convert delta px to percentage
    const pctX = (deltaX / rect.width) * 100;
    const pctY = (deltaY / rect.height) * 100;

    setPorosities((prev) =>
      prev.map((p) => {
        if (p.id !== pId) return p;
        const newX = Math.min(Math.max(Math.round((p.x + pctX) * 10) / 10, 2), 98);
        const newY = Math.min(Math.max(Math.round((p.y + pctY) * 10) / 10, 2), 98);
        return { ...p, x: newX, y: newY };
      })
    );
  };

  const dragStartPos = useRef<{ x: number; y: number } | null>(null);

  const handleMarkerMouseDown = (e: React.MouseEvent, pId: string) => {
    e.stopPropagation();
    e.preventDefault();
    setSelectedPId(pId);
    setDraggingPId(pId);
    dragStartPos.current = { x: e.clientX, y: e.clientY };
  };

  const handleMarkerTouchStart = (e: React.TouchEvent, pId: string) => {
    e.stopPropagation();
    const touch = e.touches[0];
    if (!touch) return;
    setSelectedPId(pId);
    setDraggingPId(pId);
    dragStartPos.current = { x: touch.clientX, y: touch.clientY };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (draggingPId && dragStartPos.current) {
      const deltaX = e.clientX - dragStartPos.current.x;
      const deltaY = e.clientY - dragStartPos.current.y;
      dragStartPos.current = { x: e.clientX, y: e.clientY };

      const imgElem = viewerRef.current?.querySelector('img');
      const rect = imgElem ? imgElem.getBoundingClientRect() : viewerRef.current?.getBoundingClientRect();
      if (rect) {
        const pctX = (deltaX / rect.width) * 100;
        const pctY = (deltaY / rect.height) * 100;

        setPorosities((prev) =>
          prev.map((p) => {
            if (p.id !== draggingPId) return p;
            const newX = Math.min(Math.max(Math.round((p.x + pctX) * 10) / 10, 2), 98);
            const newY = Math.min(Math.max(Math.round((p.y + pctY) * 10) / 10, 2), 98);
            return { ...p, x: newX, y: newY };
          })
        );
      }
      return;
    }

    if (!isPanning) return;
    setPan({ x: e.clientX - startPan.x, y: e.clientY - startPan.y });
  };

  const handleMouseUp = () => {
    setIsPanning(false);
    if (draggingPId) {
      const p = porosities.find((item) => item.id === draggingPId);
      if (p) {
        showNotification(`${p.label} 기공 마커 위치가 (${p.x}%, ${p.y}%)로 이동되었습니다.`);
      }
      setDraggingPId(null);
    }
  };

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const addAnnotation = () => {
    if (!activePinPrompt || !newNoteText.trim()) return;
    setAnnotations([
      ...annotations,
      {
        id: `ann-${Date.now()}`,
        x: activePinPrompt.x,
        y: activePinPrompt.y,
        note: newNoteText.trim(),
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
    setNewNoteText('');
    setActivePinPrompt(null);
    showNotification('현장 관찰 메모가 추가되었습니다.');
  };

  const deleteAnnotation = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setAnnotations((prev) => prev.filter((ann) => ann.id !== id));
    showNotification('현장 관찰 메모 핀이 삭제되었습니다.');
  };

  const handleDecision = (id: string, decision: DecisionType) => {
    setPorosities(
      porosities.map((p) => (p.id === id ? { ...p, workerDecision: decision } : p))
    );
    const label = porosities.find((p) => p.id === id)?.label;
    const descText = decision === 'confirmed' ? '기공 검출 확인' : decision === 'error' ? '검출 오류' : '재검사 필요';
    showNotification(`${label} 영역이 [${descText}] 상태로 기록되었습니다.`);
  };

  const showNotification = (msg: string) => {
    setNotice(msg);
    setTimeout(() => setNotice(null), 3500);
  };

  return (
    <div className="flex flex-col h-screen w-full bg-[#F8F7F4] text-[#111111] overflow-hidden font-sans select-none text-base">
      
      {/* Hidden File Input for User Custom Image Upload */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleImageUpload}
        accept="image/*"
        className="hidden"
      />

      {/* 1. COMPACT ESSENTIAL METADATA HEADER WITH DEMO BADGE */}
      <header className="h-14 bg-[#161617] text-[#F4F8FB] px-4 flex items-center justify-between border-b border-[#333336] shrink-0">
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2 pr-3 border-r border-[#333336]">
            <HardHat className="w-5 h-5 text-[#9FC6F4] shrink-0" />
            <span className="font-semibold tracking-wide text-[#F4F8FB] text-[30px] font-['Amethysta']">RT - 대시보드</span>
          </div>

          <div className="flex items-center gap-4 text-[#D2D2D7] text-sm">
            <div>
              <span className="text-[#86868B] mr-1">선박:</span>
              <span className="font-medium text-[#F4F8FB]">H-3419 (174k LNG)</span>
            </div>
            <div>
              <span className="text-[#86868B] mr-1">검사구역:</span>
              <span className="font-medium text-[#F4F8FB]">Block 204 / Joint #W-18B</span>
            </div>
            <div>
              <span className="text-[#86868B] mr-1">검사 ID:</span>
              <span className="font-mono text-[#9FC6F4] font-medium">RT-2026-0910-4082</span>
            </div>
            <div className="hidden lg:block font-['42dot_Sans']">
              <span className="text-[#86868B] mr-1">검사자:</span>
              <span className="font-medium text-[#F4F8FB]">김민수 (Level-II), 2년차</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-1.5 h-9 px-3 text-xs bg-[#333336] hover:bg-[#41626A] text-[#F4F8FB] rounded-[5px] border border-[#41626A] font-medium transition-colors"
            title="실제 촬영된 RT 사진 파일 업로드"
          >
            <ImageIcon className="w-4 h-4 text-[#3397D4]" />
            <span>{uploadedImage ? '사진 변경' : 'RT 사진 업로드'}</span>
          </button>

          <button
            onClick={() => setShowBasis(!showBasis)}
            className="flex items-center gap-1.5 h-9 px-3 text-xs bg-[#333336] hover:bg-[#41626A] text-[#D2D2D7] rounded-[5px] border border-[#41626A] font-medium transition-colors"
          >
            <FileText className="w-4 h-4 text-[#D2D2D7]" />
            <span>검사 기준 보기</span>
            {showBasis ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </header>

      {/* EXPANDABLE SECONDARY SPECIFICATIONS & STANDARDS */}
      {showBasis && (
        <div className="bg-[#2B3A37] border-b border-[#41626A] px-5 py-3 text-sm text-[#F4F8FB] grid grid-cols-1 md:grid-cols-3 gap-4 shrink-0 shadow-inner">
          <div>
            <span className="font-medium text-[#9FC6F4] block mb-1 font-mono text-xs">적용 규격 (STANDARDS)</span>
            <p className="font-semibold text-base text-[#F4F8FB]">ISO 5817:2023 Level B / AWS D1.1</p>
            <p className="text-[#D2D2D7] text-xs mt-0.5">조선 선체 구조 용접부 방사선 투과 규격</p>
          </div>
          <div>
            <span className="font-medium text-[#9FC6F4] block mb-1 font-mono text-xs">기공 허용 기준 (POROSITY LIMITS)</span>
            <p className="text-sm text-[#F4F8FB]">
              단일 기공: <span className="font-mono font-semibold text-[#EA33C0]">Max Ø 2.5mm</span> | 군집 기공: <span className="font-mono font-semibold text-[#EA33C0]">투과 면적 1.5% 이내</span>
            </p>
            <p className="text-[#D2D2D7] text-xs mt-0.5">Level B 기준 초과 시 재용접 처리 대상</p>
          </div>
          <div>
            <span className="font-medium text-[#9FC6F4] block mb-1 font-mono text-xs">장비 및 투과 조건</span>
            <p className="font-mono text-sm text-[#F4F8FB]">Seifert 200kV DDA 검출기 | 피치 100µm</p>
            <p className="text-[#D2D2D7] text-xs mt-0.5">EN 462-1 W10 투과도계 식별 완료</p>
          </div>
        </div>
      )}

      {/* NOTIFICATION BANNER */}
      {notice && (
        <div className="bg-[#3397D4] text-[#F4F8FB] px-5 py-2 text-sm font-medium flex items-center justify-between shrink-0 shadow-sm">
          <span>{notice}</span>
          <button onClick={() => setNotice(null)} className="hover:opacity-80 p-1">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* MAIN WORKSPACE - TABLET LANDSCAPE SPLIT (65% VIEWER / 35% INSPECTION PANEL) */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
        
        {/* LEFT 60–65%: DOMINANT MAXIMIZED RT IMAGE VIEWER & SIMILAR CASES */}
        <div className="w-full md:w-[62%] lg:w-[65%] flex flex-col bg-[#161617] border-r border-[#333336] relative">
          
          {/* VIEWER CONTROLS TOOLBAR (TOUCH-OPTIMIZED HEIGHT) */}
          <div className="h-12 bg-[#333336] border-b border-[#41626A] px-3 flex items-center justify-between text-sm text-[#D2D2D7] shrink-0">
            {/* View Mode Toggle */}
            <div className="flex items-center bg-[#161617] p-1 rounded-[5px] border border-[#41626A] gap-1 font-['42dot_Sans']">
              <button
                onClick={() => setViewMode('overlay')}
                className={`h-8 px-3 rounded-[3px] text-xs font-medium transition-colors ${
                  viewMode === 'overlay' ? 'bg-[#3397D4] text-[#F4F8FB]' : 'text-[#86868B] hover:text-[#F4F8FB]'
                }`}
              >
                AI 오버레이
              </button>
              <button
                onClick={() => setViewMode('original')}
                className={`h-8 px-3 rounded-[3px] text-xs font-medium transition-colors ${
                  viewMode === 'original' ? 'bg-[#3397D4] text-[#F4F8FB]' : 'text-[#86868B] hover:text-[#F4F8FB]'
                }`}
              >
                원본 RT 사진
              </button>
            </div>

            {/* Touch-Friendly Zoom & Pin Controls */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-[#86868B] hidden lg:inline border-r border-[#41626A] pr-2 pt-[3px] font-['42dot_Sans']">
                💡마커를 마우스로 드래그하여 위치 이동이 가능합니다.
              </span>

              <button
                onClick={() => setPinMode(!pinMode)}
                className={`h-8 px-3 rounded-[5px] border text-xs flex items-center gap-1.5 font-medium transition-colors ${
                  pinMode ? 'bg-[#3397D4] text-[#F4F8FB] border-[#9FC6F4]' : 'bg-[#161617] hover:bg-[#2B3A37] border-[#41626A] text-[#D2D2D7]'
                }`}
              >
                <Pin className="w-3.5 h-3.5" />
                <span>메모 핀 찍기</span>
              </button>

              <div className="h-4 w-px bg-[#41626A] mx-0.5" />

              <button onClick={() => setZoom(Math.min(zoom + 0.25, 3))} className="h-8 w-8 bg-[#161617] hover:bg-[#2B3A37] border border-[#41626A] rounded-[5px] flex items-center justify-center text-[#F4F8FB]" title="확대">
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button onClick={() => setZoom(Math.max(zoom - 0.25, 0.75))} className="h-8 w-8 bg-[#161617] hover:bg-[#2B3A37] border border-[#41626A] rounded-[5px] flex items-center justify-center text-[#F4F8FB]" title="축소">
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <button onClick={resetView} className="h-8 w-8 bg-[#161617] hover:bg-[#2B3A37] border border-[#41626A] rounded-[5px] flex items-center justify-center text-[#F4F8FB]" title="초기화">
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* RT IMAGE DISPLAY CANVAS - MAXIMIZED VIEWPORT WITH ZERO MARGIN FILL */}
          <div
            ref={viewerRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onTouchStart={(e) => {
              const touch = e.touches[0];
              if (!touch) return;
              if (pinMode && viewerRef.current) {
                const rect = viewerRef.current.getBoundingClientRect();
                const x = Math.round(((touch.clientX - rect.left) / rect.width) * 1000) / 10;
                const y = Math.round(((touch.clientY - rect.top) / rect.height) * 1000) / 10;
                setActivePinPrompt({ x, y });
                setPinMode(false);
                return;
              }
              setIsPanning(true);
              setStartPan({ x: touch.clientX - pan.x, y: touch.clientY - pan.y });
            }}
            onTouchMove={(e) => {
              const touch = e.touches[0];
              if (!touch) return;
              if (draggingPId && dragStartPos.current) {
                const deltaX = touch.clientX - dragStartPos.current.x;
                const deltaY = touch.clientY - dragStartPos.current.y;
                dragStartPos.current = { x: touch.clientX, y: touch.clientY };

                const imgElem = viewerRef.current?.querySelector('img');
                const rect = imgElem ? imgElem.getBoundingClientRect() : viewerRef.current?.getBoundingClientRect();
                if (rect) {
                  const pctX = (deltaX / rect.width) * 100;
                  const pctY = (deltaY / rect.height) * 100;
                  setPorosities((prev) =>
                    prev.map((p) => {
                      if (p.id !== draggingPId) return p;
                      const newX = Math.min(Math.max(Math.round((p.x + pctX) * 10) / 10, 2), 98);
                      const newY = Math.min(Math.max(Math.round((p.y + pctY) * 10) / 10, 2), 98);
                      return { ...p, x: newX, y: newY };
                    })
                  );
                }
                return;
              }
              if (!isPanning) return;
              setPan({ x: touch.clientX - startPan.x, y: touch.clientY - startPan.y });
            }}
            onTouchEnd={handleMouseUp}
            className={`flex-1 relative overflow-hidden flex items-center justify-center bg-[#050608] cursor-${pinMode ? 'crosshair' : isPanning ? 'grabbing' : 'grab'}`}
          >
            {/* Calibration mm Scale Top Overlay */}
            <div className="absolute top-2 left-4 right-4 h-4 flex justify-between items-center text-xs font-mono text-[#86868B] border-b border-[#333336] pointer-events-none z-10">
              <span>500mm</span>
              <span>550mm</span>
              <span>600mm</span>
              <span>650mm</span>
              <span>700mm</span>
              <span>750mm</span>
              <span>800mm</span>
            </div>

            {/* Transform Container (Zoom / Pan) - Maximized to Fill Viewport */}
            <div
              className="relative w-full h-full transition-transform duration-75 flex items-center justify-center p-2"
              style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}
            >
              {/* UPLOADED IMAGE OR PRESERVED RADIOGRAPH CANVAS (FITS FULL CONTAINER) */}
              <div className="relative w-full h-full bg-[#161617] rounded border border-[#333336] overflow-hidden flex items-center justify-center shadow-2xl">
                
                {uploadedImage ? (
                  <img
                    src={uploadedImage}
                    alt="RT Weld Radiograph"
                    className="w-full h-full object-contain pointer-events-none"
                  />
                ) : (
                  <img
                    src={attachedRtImage}
                    alt="RT Weld Radiograph"
                    className="w-full h-full object-contain pointer-events-none"
                  />
                )}

                {/* LIGHTWEIGHT ACCURATE POROSITY OVERLAYS */}
                {(viewMode === 'overlay' || viewMode === 'worker') && (
                  <div className="absolute inset-0 pointer-events-auto">
                    {porosities.map((p) => {
                      const isSelected = p.id === selectedPId;
                      const markerColor = p.statusColor === 'red' ? '#E53935' : p.statusColor === 'amber' ? '#F59E0B' : '#16A34A';

                      return (
                        <div
                          key={p.id}
                          onMouseDown={(e) => handleMarkerMouseDown(e, p.id)}
                          onTouchStart={(e) => handleMarkerTouchStart(e, p.id)}
                          className={`absolute transform -translate-x-1/2 -translate-y-1/2 cursor-grab active:cursor-grabbing z-30 group ${
                            draggingPId === p.id ? 'z-50 scale-125' : ''
                          }`}
                          style={{
                            left: `${p.x}%`,
                            top: `${p.y}%`,
                          }}
                          title="드래그하여 기공 위치 이동 가능"
                        >
                          {/* Precise Ring Overlay on Pore */}
                          <div
                            className={`rounded transition-all grid place-items-center font-semibold ${
                              isSelected
                                ? 'w-10 h-10 border-2 ring-2 ring-white ring-offset-2 ring-offset-black scale-125 z-40'
                                : 'w-8 h-8 border-2 opacity-80 hover:opacity-100 hover:scale-110'
                            }`}
                            style={{
                              borderColor: markerColor,
                              backgroundColor: isSelected ? `${markerColor}33` : 'transparent',
                            }}
                          />

                          {/* Compact Label Chip Immediately Beside the Pore */}
                          <div
                            style={{
                              backgroundColor: markerColor,
                              fontFamily: 'ABeeZee, sans-serif'
                            }}
                            className={`absolute left-9 top-1/2 -translate-y-1/2 text-white font-mono text-sm font-semibold px-2 py-0.5 rounded shadow-lg flex items-center gap-1 whitespace-nowrap ${
                              isSelected ? 'scale-110 ring-1 ring-white z-50' : 'opacity-90'
                            }`}
                          >
                            <span className="font-semibold">{p.label}</span>
                            {p.workerDecision === 'confirmed' && <Check className="w-3.5 h-3.5 text-green-200" />}
                            {p.workerDecision === 'error' && <X className="w-3.5 h-3.5 text-red-200" />}
                            {p.workerDecision === 'recheck' && <AlertTriangle className="w-3.5 h-3.5 text-amber-200" />}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* WORKER ANNOTATION PINS */}
                {annotations.map((ann) => (
                  <div
                    key={ann.id}
                    style={{ left: `${ann.x}%`, top: `${ann.y}%` }}
                    className="absolute z-40 transform -translate-x-1/2 -translate-y-1/2 pointer-events-auto group"
                  >
                    <div className="w-6 h-6 bg-[#3397D4] rounded-full border-2 border-white shadow flex items-center justify-center text-white cursor-pointer hover:scale-110 transition-transform">
                      <Pin className="w-3.5 h-3.5 fill-white" />
                    </div>
                    <div className="hidden group-hover:flex flex-col absolute left-7 top-0 bg-[#333336] border border-[#41626A] text-[#F4F8FB] text-xs p-2.5 rounded-[5px] shadow-xl w-56 z-50">
                      <div className="flex items-center justify-between border-b border-[#41626A] pb-1.5 mb-1.5">
                        <span className="text-[#9FC6F4] font-mono">{ann.timestamp}</span>
                        <button
                          onClick={(e) => deleteAnnotation(ann.id, e)}
                          className="text-[#86868B] hover:text-[#EA33C0] p-0.5 rounded transition-colors"
                          title="메모 핀 삭제"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      <p className="text-[#D2D2D7] break-words">{ann.note}</p>
                    </div>
                  </div>
                ))}

                {/* PIN DROP PROMPT */}
                {activePinPrompt && (
                  <div
                    style={{ left: `${activePinPrompt.x}%`, top: `${activePinPrompt.y}%` }}
                    className="absolute z-50 bg-[#1A1A1A] border border-[#2563EB] p-3 rounded shadow-xl w-64 transform -translate-x-1/2 translate-y-2 text-white"
                  >
                    <div className="text-sm font-semibold text-amber-400 mb-1.5 flex items-center gap-1">
                      <Pin className="w-4 h-4" /> 현장 메모 추가
                    </div>
                    <textarea
                      value={newNoteText}
                      onChange={(e) => setNewNoteText(e.target.value)}
                      placeholder="기공 위치 특이사항 또는 육안 관찰 메모..."
                      className="w-full bg-[#0F1115] border border-[#333] text-sm p-2 rounded text-white focus:outline-none h-16 resize-none mb-2"
                      autoFocus
                    />
                    <div className="flex justify-end gap-1.5">
                      <button onClick={() => setActivePinPrompt(null)} className="min-h-[36px] px-3 text-xs bg-[#333] rounded">취소</button>
                      <button onClick={addAnnotation} className="min-h-[36px] px-3 text-xs bg-[#2563EB] text-white rounded font-medium">저장</button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* SIMILAR HISTORICAL CASES STRIP (IMAGE-FIRST WITH COMPARISON ACTION) */}
          <div className="h-[155px] bg-[#161617] border-t border-[#333336] p-2.5 flex flex-col shrink-0">
            <div className="flex items-center justify-between mb-1.5 px-1">
              <span className="text-sm font-semibold text-[#D2D2D7]">
                유사 과거 RT 기공 사례
              </span>
              <span className="text-xs text-[#86868B]">카드 클릭 시 RT 이미지 직접 비교</span>
            </div>

            <div className="flex-1 flex gap-3 overflow-x-auto pb-1">
              {SIMILAR_CASES.map((sc) => (
                <div
                  key={sc.id}
                  onClick={() => setComparisonCase(sc)}
                  className="w-[185px] shrink-0 bg-[#333336] hover:bg-[#2B3A37] border border-[#41626A] hover:border-[#3397D4] rounded p-2 cursor-pointer transition-all flex flex-col justify-between group"
                >
                  {/* Image-First RT Case Canvas Preview */}
                  <div className="h-16 bg-[#161617] rounded relative overflow-hidden border border-[#41626A] flex items-center justify-center mb-1">
                    <img
                      src={uploadedImage || attachedRtImage}
                      alt="Historical RT Case"
                      className="w-full h-full object-cover opacity-70 group-hover:opacity-100 transition-opacity"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
                    <div className="absolute top-1 right-1 bg-[#161617]/90 text-[#9FC6F4] font-mono font-bold text-xs px-1.5 py-0.5 rounded border border-[#41626A]">
                      {sc.similarity}% 일치
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono text-[#D2D2D7] truncate">{sc.caseId}</span>
                    <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                      sc.statusColor === 'red' ? 'text-red-300 bg-red-950' : sc.statusColor === 'amber' ? 'text-amber-300 bg-amber-950' : 'text-teal-300 bg-teal-950'
                    }`}>
                      {sc.historicalDecision.trim()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT 35–40%: CLEAN INSPECTION RESULT PANEL (16PX+ TEXT & TOUCH BUTTONS) */}
        <div className="w-full md:w-[38%] lg:w-[35%] bg-[#333336] text-[#F4F8FB] flex flex-col shrink-0 overflow-y-auto border-l border-[#333336]">
          
          {/* P1~P3 INSPECTION PROGRESS BAR */}
          <div className="p-4 bg-[#2B3A37] border-b border-[#41626A]">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-sm font-semibold text-[#D2D2D7]">기공 영역 검토 진행률</span>
              <span className="text-sm font-mono font-bold text-[#F4F8FB]">
                {completedCount} / {porosities.length} 영역 완료 ({progressPercent}%)
              </span>
            </div>
            
            {/* Progress Bar Visual */}
            <div className="w-full h-2.5 bg-[#161617] rounded-full overflow-hidden mb-3 border border-[#41626A]">
              <div
                className="h-full bg-[#3397D4] transition-all duration-300 rounded-full"
                style={{ width: `${progressPercent}%` }}
              />
            </div>

            {/* P1, P2, P3 Quick Selector Chips */}
            <div className="flex items-center gap-2">
              {porosities.map((p) => {
                const isSel = p.id === selectedPId;
                const dec = p.workerDecision;

                return (
                  <button
                    key={p.id}
                    onClick={() => setSelectedPId(p.id)}
                    className={`flex-1 h-9 px-2 rounded-[5px] border text-sm font-['ABeeZee'] font-medium flex items-center justify-center gap-1 transition-all ${
                      isSel
                        ? 'bg-[#3397D4] text-[#F4F8FB] border-[#9FC6F4]'
                        : 'bg-[#161617] text-[#D2D2D7] border-[#41626A] hover:bg-[#333336]'
                    }`}
                  >
                    <span>{p.label}</span>
                    {dec === 'confirmed' && <Check className="w-3.5 h-3.5 text-green-400 shrink-0" />}
                    {dec === 'error' && <X className="w-3.5 h-3.5 text-red-400 shrink-0" />}
                    {dec === 'recheck' && <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* SELECTED POROSITY DETAIL CARD (TEXT >= 16PX FOR PRIMARY READABILITY) */}
          <div className="p-4 border-b border-[#41626A]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-base font-bold text-[#F4F8FB]">
                선택 영역: <span className="text-[#3397D4]">{selectedPorosity.label}</span>
              </span>
            </div>

            {/* Visual Risk Badge */}
            <div className={`p-3 rounded border flex items-center justify-between mb-3 ${
              selectedPorosity.statusColor === 'red'
                ? 'bg-red-950/60 border-red-800 text-red-200'
                : selectedPorosity.statusColor === 'amber'
                ? 'bg-amber-950/60 border-amber-800 text-amber-200'
                : 'bg-teal-950/60 border-teal-800 text-teal-200'
            }`}>
              <div className="flex items-center gap-2.5">
                <ShieldAlert className="w-6 h-6 shrink-0" />
                <div>
                  <div className="font-bold text-base leading-none">{selectedPorosity.label} - {selectedPorosity.riskLevel}</div>
                  <div className="text-sm mt-1 opacity-80">{selectedPorosity.location}</div>
                </div>
              </div>
            </div>

            {/* Porosity Details Table (Clear Spacing, 16px Main Text) */}
            <div className="space-y-2 text-base bg-[#2B3A37] p-3 rounded border border-[#41626A]">
              <div className="flex justify-between border-b border-[#41626A] pb-1.5">
                <span className="text-[#D2D2D7]">기공 크기 / 직경</span>
                <span className="font-semibold text-[#F4F8FB]">{selectedPorosity.diameter}</span>
              </div>
              <div className="flex justify-between border-b border-[#41626A] pb-1.5">
                <span className="text-[#D2D2D7]">검출 기공 개수</span>
                <span className="font-semibold text-[#F4F8FB]">{selectedPorosity.poreCount} 개</span>
              </div>
              <div className="flex justify-between border-b border-[#41626A] pb-1.5">
                <span className="text-[#D2D2D7]">군집 상태</span>
                <span className="font-semibold text-[#F4F8FB]">{selectedPorosity.clusterDensity}</span>
              </div>
              {/* Position adjustment UI */}
              <div className="pt-1.5">
                <div className="text-xs font-semibold text-[#D2D2D7] mb-1">마커 좌표 직접 조정 (%)</div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 flex items-center gap-1 bg-[#161617] border border-[#41626A] rounded px-2 py-1">
                    <span className="text-xs text-[#86868B] font-bold">X</span>
                    <input
                      type="number"
                      step="0.5"
                      min="2"
                      max="98"
                      value={selectedPorosity.x}
                      onChange={(e) => {
                        const val = parseFloat(e.target.value) || 0;
                        setPorosities(prev => prev.map(p => p.id === selectedPorosity.id ? { ...p, x: val } : p));
                      }}
                      className="w-full text-sm font-mono font-bold text-[#F4F8FB] bg-transparent outline-none"
                    />
                    <span className="text-xs text-[#86868B]">%</span>
                  </div>
                  <div className="flex-1 flex items-center gap-1 bg-[#161617] border border-[#41626A] rounded px-2 py-1">
                    <span className="text-xs text-[#86868B] font-bold">Y</span>
                    <input
                      type="number"
                      step="0.5"
                      min="2"
                      max="98"
                      value={selectedPorosity.y}
                      onChange={(e) => {
                        const val = parseFloat(e.target.value) || 0;
                        setPorosities(prev => prev.map(p => p.id === selectedPorosity.id ? { ...p, x: p.x, y: val } : p));
                      }}
                      className="w-full text-sm font-mono font-bold text-[#F4F8FB] bg-transparent outline-none"
                    />
                    <span className="text-xs text-[#86868B]">%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* WORKER DECISION (3 DISPOSITIONS WITH MIN HEIGHT 48PX TOUCH BUTTONS) */}
          <div className="p-4 border-b border-[#41626A]">
            <span className="text-base font-bold text-[#F4F8FB] block mb-2.5">
              검사자 판단 ({selectedPorosity.label} 영역)
            </span>
            <div className="flex flex-col gap-2">
              <button
                onClick={() => handleDecision(selectedPorosity.id, 'confirmed')}
                className={`h-10 py-2 px-3 rounded-[5px] text-sm font-medium flex items-center justify-between transition-colors ${
                  selectedPorosity.workerDecision === 'confirmed'
                    ? 'bg-[#3397D4] text-[#F4F8FB] border border-[#9FC6F4]'
                    : 'bg-[#161617] hover:bg-[#2B3A37] text-[#D2D2D7] border border-[#41626A]'
                }`}
              >
                <div className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-green-400" />
                  <span>기공 검출 확인</span>
                </div>
                <span className="text-xs text-[#86868B]">AI 판정 동의</span>
              </button>

              <button
                onClick={() => handleDecision(selectedPorosity.id, 'error')}
                className={`h-10 py-2 px-3 rounded-[5px] text-sm font-medium flex items-center justify-between transition-colors ${
                  selectedPorosity.workerDecision === 'error'
                    ? 'bg-[#3397D4] text-[#F4F8FB] border border-[#9FC6F4]'
                    : 'bg-[#161617] hover:bg-[#2B3A37] text-[#D2D2D7] border border-[#41626A]'
                }`}
              >
                <div className="flex items-center gap-2">
                  <X className="w-4 h-4 text-red-400" />
                  <span>검출 오류 (오진)</span>
                </div>
                <span className="text-xs text-[#86868B]">기공 아님 / 필름 노이즈</span>
              </button>

              <button
                onClick={() => handleDecision(selectedPorosity.id, 'recheck')}
                className={`h-10 py-2 px-3 rounded-[5px] text-sm font-medium flex items-center justify-between transition-colors ${
                  selectedPorosity.workerDecision === 'recheck'
                    ? 'bg-[#3397D4] text-[#F4F8FB] border border-[#9FC6F4]'
                    : 'bg-[#161617] hover:bg-[#2B3A37] text-[#D2D2D7] border border-[#41626A]'
                }`}
              >
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <span>재검사 필요</span>
                </div>
                <span className="text-xs text-[#86868B]">초음파(UT) 또는 재촬영</span>
              </button>
            </div>
          </div>

          {/* CONCISE 1-2 SENTENCE AI SUMMARY */}
          <div className="p-4 border-b border-[#41626A] text-base leading-relaxed text-[#D2D2D7]">
            <div className="flex items-center gap-1.5 font-bold text-[#3397D4] mb-1.5">
              <Activity className="w-4 h-4" />
              <span>AI 검사 요약</span>
            </div>
            <p className="text-base text-[#F4F8FB] font-['Alata']">
              {'검출된 3개 기공 중 '}
              <span className="text-[#EA33C0] font-bold">P1 영역(Ø 3.8mm)</span>
              {'이 ISO 5817 Level B 규격을 초과합니다. 작업자 판단 기록 완료 후 책임 검사원 이관을 권장합니다.'}
            </p>
          </div>

          {/* PERSISTENT BOTTOM ACTIONS (MIN HEIGHT 48PX TOUCH TARGETS) */}
          <div className="p-4 bg-[#161617] space-y-2 mt-auto border-t border-[#41626A]">
            <button
              onClick={() => {
                setEscalated(true);
                showNotification('책임 검사원(Senior Inspector)에게 검사건이 이관되었습니다.');
              }}
              className="w-full h-10 bg-[#333336] hover:bg-[#41626A] text-[#D2D2D7] border border-[#41626A] rounded-[5px] font-medium text-sm flex items-center justify-center gap-2 transition-colors"
            >
              <ShieldAlert className="w-4 h-4 text-[#9FC6F4]" />
              <span>책임 검사원 이관</span>
            </button>

            <button
              onClick={() => showNotification('최종 검사 결과가 품질 DB에 저장되었습니다.')}
              className="w-full h-10 bg-[#3397D4] hover:bg-[#9FC6F4] hover:text-[#161617] text-[#F4F8FB] rounded-[5px] font-medium text-sm transition-colors shadow-sm"
            >
              검사 최종 확인 저장
            </button>
          </div>
        </div>
      </div>

      {/* MODAL: SIDE-BY-SIDE HISTORICAL COMPARISON VIEW (IMAGE-FIRST FOCUS) */}
      {comparisonCase && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#333336] rounded-lg shadow-2xl max-w-4xl w-full max-h-[88vh] flex flex-col overflow-hidden text-[#F4F8FB]">
            <div className="bg-[#161617] text-[#F4F8FB] p-4 flex items-center justify-between border-b border-[#41626A]">
              <span className="font-bold text-base">과거 유사 RT 기공 사례 대조 (사례 {comparisonCase.caseId})</span>
              <button onClick={() => setComparisonCase(null)} className="text-[#86868B] hover:text-[#F4F8FB] p-1">
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-5 bg-[#161617] flex-1 overflow-y-auto text-base">
              {/* CURRENT RT CASE */}
              <div className="bg-[#2B3A37] p-4 rounded border border-[#41626A]">
                <span className="font-bold block mb-2 text-[#F4F8FB]">현재 RT 검사 ({selectedPorosity.label} 영역)</span>
                <div className="h-48 bg-[#161617] rounded mb-3 flex items-center justify-center overflow-hidden border border-[#41626A]">
                  <img src={uploadedImage || attachedRtImage} alt="Current RT" className="w-full h-full object-contain" />
                </div>
                <div className="space-y-1">
                  <div>위치: <span className="font-semibold">{selectedPorosity.location}</span></div>
                  <div>상태: <span className="font-semibold text-red-400">{selectedPorosity.riskLevel} ({selectedPorosity.diameter})</span></div>
                </div>
              </div>

              {/* HISTORICAL MATCHED CASE */}
              <div className="bg-[#2B3A37] p-4 rounded border border-[#41626A]">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-[#F4F8FB]">유사 사례 ({comparisonCase.caseId})</span>
                  <span className="text-xs bg-[#161617] text-[#9FC6F4] px-2 py-0.5 rounded border border-[#41626A] font-mono">
                    {comparisonCase.similarity}% AI 매칭
                  </span>
                </div>
                <div className="h-48 bg-[#161617] rounded mb-3 flex items-center justify-center overflow-hidden border border-[#41626A]">
                  <img src={attachedRtImage} alt="Historical Case" className="w-full h-full object-contain opacity-80" />
                </div>
                <div className="space-y-1 text-sm text-[#D2D2D7]">
                  <div>적용 선박: <span className="font-medium text-[#F4F8FB]">{comparisonCase.vessel}</span></div>
                  <div>과거 판정: <span className="font-bold text-amber-300">{comparisonCase.historicalDecision}</span></div>
                  <div>조치 사항: <span className="text-[#F4F8FB]">{comparisonCase.actionTaken}</span></div>
                </div>
              </div>
            </div>

            <div className="p-4 bg-[#161617] border-t border-[#41626A] flex justify-end">
              <button
                onClick={() => setComparisonCase(null)}
                className="min-h-[40px] px-5 bg-[#3397D4] hover:bg-[#9FC6F4] hover:text-[#161617] text-[#F4F8FB] font-semibold rounded text-sm transition-colors"
              >
                창 닫기
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ESCALATED MODAL */}
      {escalated && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg p-6 max-w-md w-full shadow-2xl text-base">
            <div className="flex items-center gap-2.5 text-red-600 mb-3 font-bold text-lg">
              <ShieldAlert className="w-6 h-6" />
              <span>책임 검사원 이관 완료</span>
            </div>
            <p className="text-[#333] mb-4 leading-relaxed">
              RT 사진, 기공 위치(P1~P3), 검사자 판단 내역 및 메모가 선임 검사원 검토 패키지로 이관되었습니다.
            </p>
            <button onClick={() => setEscalated(false)} className="w-full min-h-[48px] bg-[#1A1A1A] text-white py-2.5 rounded font-bold">
              확인
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
