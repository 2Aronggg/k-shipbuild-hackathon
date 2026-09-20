import { useState, useRef, useEffect, useCallback } from 'react';
import type { ChangeEvent, MouseEvent, TouchEvent } from 'react';
import {
  ZoomIn, ZoomOut, RotateCcw, ShieldAlert,
  FileText, ChevronDown, ChevronUp, ChevronRight,
  Check, X, Activity, Image as ImageIcon, AlertTriangle,
  FlipHorizontal, Sparkles, Mountain, Ruler,
} from 'lucide-react';
const CURRENT_RT_IMAGE = '/assets/rt/RT_panel_1.png';

// --- DATA DEFINITIONS (POROSITY ONLY) ---

type WorkerDecision = null | '승인' | '보수' | '재검사';

type ReviewStatus = '정상' | '주의' | '검토 필요' | '보수 검토';

interface PorosityRegion {
  id: string;

  detection: {
    defectType: '기공';
    locationLabel: string;
    weldZone: 'Root' | 'Fill' | 'Cap' | 'Unknown';
    boundingBox: { x: number; y: number };
    aiConfidence: number;
  };

  morphology: {
    shape: '원형' | '타원형' | '불규칙';
    distribution: '단일' | '산재' | '군집' | '선형';
    largestDiameterMm: number;
    averageDiameterMm: number;
    poreCount: number;
    affectedLengthMm: number;
  };

  assessment: {
    status: ReviewStatus;
    severity: 'Low' | 'Medium' | 'High';
    reason: string[];
  };

  workerDecision: WorkerDecision;
}

interface SimilarityBreakdown {
  morphology: number;
  size: number;
  distribution: number;
  location: number;
}

interface SimilarCase {
  id: string;
  caseId: string;
  image: string;
  label: string;

  source: {
    vessel: string;
    inspectionDate: string;
    weldType: string;
    weldZone: string;
  };

  defect: {
    type: '기공';
    shape: string;
    distribution: string;
    largestDiameterMm: number;
    averageDiameterMm: number;
    poreCount: number;
    affectedLengthMm: number;
  };

  similarity: {
    overall: number;
    breakdown: SimilarityBreakdown;
  };

  historicalResult: {
    grade: string;
    decision: '승인' | '보수' | '재검사';
    inspectorAction: string;
  };

  repair: {
    required: boolean;
    method: string | null;
    reinspection: string | null;
    finalResult: string;
  };

  summary: string;
}

const calculateSimilarity = (scores: SimilarityBreakdown): number => {
  return Number(
    (
      scores.morphology * 0.35 +
      scores.size * 0.3 +
      scores.distribution * 0.2 +
      scores.location * 0.15
    ).toFixed(1)
  );
};

const getDecisionColor = (decision: '승인' | '보수' | '재검사'): 'green' | 'amber' | 'red' => {
  switch (decision) {
    case '승인':
      return 'green';
    case '재검사':
      return 'amber';
    case '보수':
      return 'red';
  }
};

const POROSITY_REGION: PorosityRegion = {
  id: 'p1',

  detection: {
    defectType: '기공',
    locationLabel: '577 mm 위치',
    weldZone: 'Root',
    boundingBox: { x: 34.2, y: 48.0 },
    aiConfidence: 94.2,
  },

  morphology: {
    shape: '원형',
    distribution: '단일',
    largestDiameterMm: 3.8,
    averageDiameterMm: 3.8,
    poreCount: 1,
    affectedLengthMm: 4.1,
  },

  assessment: {
    status: '검토 필요',
    severity: 'High',
    reason: [
      '과거 유사 사례 대비 상대적으로 큰 기공이 탐지됨',
      'Root 영역에서 결함이 탐지됨',
      'AI 탐지 신뢰도가 90% 이상임',
      '유사 과거 사례 중 보수 이력이 존재함',
    ],
  },

  workerDecision: null,
};

const SIMILAR_CASES: SimilarCase[] = [
  {
    id: 'sc1',
    caseId: 'CASE-001',
    image: '/assets/rt/RT_panel_2.png',
    label: '사례 #01',
    source: { vessel: 'H-3412 (VLCC)', inspectionDate: '2026-04-18', weldType: 'Butt Weld', weldZone: 'Root' },
    defect: { type: '기공', shape: '원형', distribution: '단일', largestDiameterMm: 3.5, averageDiameterMm: 3.5, poreCount: 1, affectedLengthMm: 3.9 },
    similarity: {
      overall: calculateSimilarity({ morphology: 97, size: 94, distribution: 98, location: 91 }),
      breakdown: { morphology: 97, size: 94, distribution: 98, location: 91 },
    },
    historicalResult: { grade: '2급', decision: '보수', inspectorAction: '결함부 확인 후 국부 보수 결정' },
    repair: { required: true, method: '결함부 제거 후 재용접', reinspection: 'RT 재촬영', finalResult: '재검사 후 승인' },
    summary: '현재 검출부와 크기 및 단일 기공 형상이 가장 유사한 과거 사례.',
  },
  {
    id: 'sc2',
    caseId: 'CASE-002',
    image: '/assets/rt/RT_panel_3.png',
    label: '사례 #02',
    source: { vessel: 'H-3398 (174K LNGC)', inspectionDate: '2026-03-07', weldType: 'Butt Weld', weldZone: 'Root' },
    defect: { type: '기공', shape: '원형', distribution: '단일', largestDiameterMm: 2.4, averageDiameterMm: 2.4, poreCount: 1, affectedLengthMm: 2.7 },
    similarity: {
      overall: calculateSimilarity({ morphology: 96, size: 82, distribution: 98, location: 92 }),
      breakdown: { morphology: 96, size: 82, distribution: 98, location: 92 },
    },
    historicalResult: { grade: '2급', decision: '승인', inspectorAction: '검사원 검토 후 승인' },
    repair: { required: false, method: null, reinspection: null, finalResult: '승인' },
    summary: '위치와 형상은 유사하지만 현재 결함보다 기공 직경이 작은 사례.',
  },
  {
    id: 'sc3',
    caseId: 'CASE-003',
    image: '/assets/rt/RT_panel_4.png',
    label: '사례 #03',
    source: { vessel: 'H-3401 (15K TEU)', inspectionDate: '2026-02-21', weldType: 'Butt Weld', weldZone: 'Fill' },
    defect: { type: '기공', shape: '타원형', distribution: '산재', largestDiameterMm: 3.2, averageDiameterMm: 1.8, poreCount: 3, affectedLengthMm: 12.5 },
    similarity: {
      overall: calculateSimilarity({ morphology: 86, size: 91, distribution: 72, location: 78 }),
      breakdown: { morphology: 86, size: 91, distribution: 72, location: 78 },
    },
    historicalResult: { grade: '3급', decision: '재검사', inspectorAction: '결함부 확인 후 재검사 결정' },
    repair: { required: true, method: '국부 결함 제거 후 보수 용접', reinspection: 'RT 재촬영', finalResult: '재검사 후 승인' },
    summary: '결함 크기는 유사하지만 여러 개의 산재 기공이 존재하는 사례.',
  },
  {
    id: 'sc4',
    caseId: 'CASE-004',
    image: '/assets/rt/RT_panel_5.png',
    label: '사례 #04',
    source: { vessel: 'H-3387 (LPGC)', inspectionDate: '2026-01-29', weldType: 'Butt Weld', weldZone: 'Root' },
    defect: { type: '기공', shape: '원형', distribution: '단일', largestDiameterMm: 2.8, averageDiameterMm: 2.8, poreCount: 1, affectedLengthMm: 3.2 },
    similarity: {
      overall: calculateSimilarity({ morphology: 94, size: 86, distribution: 97, location: 90 }),
      breakdown: { morphology: 94, size: 86, distribution: 97, location: 90 },
    },
    historicalResult: { grade: '2급', decision: '승인', inspectorAction: '현장 검사원 확인 후 승인' },
    repair: { required: false, method: null, reinspection: null, finalResult: '승인' },
    summary: '동일한 Root 영역에서 발견된 단일 원형 기공 사례.',
  },
  {
    id: 'sc5',
    caseId: 'CASE-005',
    image: '/assets/rt/RT_panel_6.png',
    label: '사례 #05',
    source: { vessel: 'H-3420 (Container)', inspectionDate: '2025-12-14', weldType: 'Butt Weld', weldZone: 'Root' },
    defect: { type: '기공', shape: '원형', distribution: '군집', largestDiameterMm: 3.4, averageDiameterMm: 1.7, poreCount: 6, affectedLengthMm: 15.8 },
    similarity: {
      overall: calculateSimilarity({ morphology: 90, size: 92, distribution: 58, location: 88 }),
      breakdown: { morphology: 90, size: 92, distribution: 58, location: 88 },
    },
    historicalResult: { grade: '3급', decision: '보수', inspectorAction: '군집성 결함 확인 후 보수 결정' },
    repair: { required: true, method: '결함 구간 제거 후 재용접', reinspection: 'RT 재촬영', finalResult: '재용접 후 승인' },
    summary: '기공 크기는 유사하지만 단일 기공이 아닌 군집 형태를 보이는 사례.',
  },
];

const SORTED_SIMILAR_CASES = [...SIMILAR_CASES].sort((a, b) => b.similarity.overall - a.similarity.overall);

const decisionColorClasses: Record<'green' | 'amber' | 'red', string> = {
  green: 'bg-teal-950/60 border-teal-800 text-teal-200',
  amber: 'bg-amber-950/60 border-amber-800 text-amber-200',
  red: 'bg-red-950/60 border-red-800 text-red-200',
};

const decisionBarColor: Record<'green' | 'amber' | 'red', string> = {
  green: '#088636',
  amber: '#f0a92c',
  red: '#ef130f',
};

function SimilarityBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs text-[#D2D2D7] mb-1">
        <span>{label}</span>
        <span className="font-mono font-semibold text-[#F4F8FB]">{value}%</span>
      </div>
      <div className="h-2 bg-[#161617] rounded-full overflow-hidden">
        <div className="h-full bg-[#3397D4] rounded-full" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

// Samples grayscale intensity along a line through the image (cross-section),
// used to plot the density/intensity profile through the defect center.
function sampleImageProfile(
  img: HTMLImageElement,
  axis: 'horizontal' | 'vertical',
  centerXPct: number,
  centerYPct: number,
  sampleCount: number
): number[] {
  const canvas = document.createElement('canvas');
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  const ctx = canvas.getContext('2d');
  if (!ctx || canvas.width === 0 || canvas.height === 0) return [];
  ctx.drawImage(img, 0, 0);

  const values: number[] = [];
  if (axis === 'horizontal') {
    const y = Math.round((centerYPct / 100) * canvas.height);
    for (let i = 0; i < sampleCount; i++) {
      const x = Math.round((i / (sampleCount - 1)) * (canvas.width - 1));
      const [r, g, b] = ctx.getImageData(x, y, 1, 1).data;
      values.push(0.299 * r + 0.587 * g + 0.114 * b);
    }
  } else {
    const x = Math.round((centerXPct / 100) * canvas.width);
    for (let i = 0; i < sampleCount; i++) {
      const y = Math.round((i / (sampleCount - 1)) * (canvas.height - 1));
      const [r, g, b] = ctx.getImageData(x, y, 1, 1).data;
      values.push(0.299 * r + 0.587 * g + 0.114 * b);
    }
  }
  return values;
}

function DensityProfileChart({ values, widthMm }: { values: number[]; widthMm: number }) {
  if (values.length === 0) {
    return <div className="h-full flex items-center justify-center text-[11px] text-[#86868B]">단면 데이터를 불러오는 중...</div>;
  }

  const w = 100;
  const h = 100;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 1);

  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(' ');

  // FWHM: half-max width around the deepest dip (defect = dark = low intensity)
  const minIdx = values.indexOf(min);
  const halfLevel = min + range / 2;
  let leftIdx = minIdx;
  while (leftIdx > 0 && values[leftIdx] < halfLevel) leftIdx--;
  let rightIdx = minIdx;
  while (rightIdx < values.length - 1 && values[rightIdx] < halfLevel) rightIdx++;
  const fwhmXLeft = (leftIdx / (values.length - 1)) * w;
  const fwhmXRight = (rightIdx / (values.length - 1)) * w;
  const fwhmMm = ((rightIdx - leftIdx) / (values.length - 1)) * widthMm;
  const fwhmY = h - ((halfLevel - min) / range) * h;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="w-full h-full">
      <line x1={fwhmXLeft} y1={0} x2={fwhmXLeft} y2={h} stroke="#F59E0B" strokeWidth="0.4" strokeDasharray="2,1" />
      <line x1={fwhmXRight} y1={0} x2={fwhmXRight} y2={h} stroke="#F59E0B" strokeWidth="0.4" strokeDasharray="2,1" />
      <line x1={fwhmXLeft} y1={fwhmY} x2={fwhmXRight} y2={fwhmY} stroke="#F59E0B" strokeWidth="0.6" />
      <polyline points={points} fill="none" stroke="#3397D4" strokeWidth="1.2" vectorEffect="non-scaling-stroke" />
      <circle cx={(minIdx / (values.length - 1)) * w} cy={h - ((min - min) / range) * h} r="1.4" fill="#E53935" />
      <text x={(fwhmXLeft + fwhmXRight) / 2} y={fwhmY - 3} fontSize="4" fill="#F59E0B" textAnchor="middle">
        FWHM {fwhmMm.toFixed(1)}mm
      </text>
    </svg>
  );
}

export default function App() {
  // State Management
  const [porosity, setPorosity] = useState<PorosityRegion>(POROSITY_REGION);

  // Custom uploaded RT Image URL
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);

  // RT Viewer Controls
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const [startPan, setStartPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Defect Box & AI Similar Case Matching (worker-triggered)
  const [showDefectBox, setShowDefectBox] = useState<boolean>(false);
  const [activePage, setActivePage] = useState<'inspection' | 'similarity'>('inspection');
  const [selectedCaseId, setSelectedCaseId] = useState<string>(SORTED_SIMILAR_CASES[0].id);

  // Image Adjustment Toolbar (Window Level / Width + Quick Filters)
  const [windowLevel, setWindowLevel] = useState<number>(100); // brightness %
  const [windowWidth, setWindowWidth] = useState<number>(100); // contrast %
  const [invertFilter, setInvertFilter] = useState<boolean>(false);
  const [sharpenFilter, setSharpenFilter] = useState<boolean>(false);
  const [reliefFilter, setReliefFilter] = useState<boolean>(false);
  const [profileAxis, setProfileAxis] = useState<'horizontal' | 'vertical'>('horizontal');
  const [profileValues, setProfileValues] = useState<number[]>([]);

  // Secondary Collapsible Section States
  const [showBasis, setShowBasis] = useState<boolean>(false);
  const [expandedCaseIds, setExpandedCaseIds] = useState<Set<string>>(new Set());
  const [escalated, setEscalated] = useState<boolean>(false);
  const [notice, setNotice] = useState<string | null>(null);

  const viewerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const displayImgRef = useRef<HTMLImageElement>(null);

  // Handle Image Upload
  const handleImageUpload = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setUploadedImage(url);
      showNotification('업로드한 RT 이미지가 적용되었습니다.');
    }
  };

  // Dragging state for the Porosity Marker
  const [isDraggingMarker, setIsDraggingMarker] = useState<boolean>(false);

  // Mouse Pan/Zoom & Drag Handlers
  const handleMouseDown = (e: MouseEvent) => {
    if (!isDraggingMarker) {
      setIsPanning(true);
      setStartPan({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const dragStartPos = useRef<{ x: number; y: number } | null>(null);

  const handleMarkerMouseDown = (e: MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    setIsDraggingMarker(true);
    dragStartPos.current = { x: e.clientX, y: e.clientY };
  };

  const handleMarkerTouchStart = (e: TouchEvent) => {
    e.stopPropagation();
    const touch = e.touches[0];
    if (!touch) return;
    setIsDraggingMarker(true);
    dragStartPos.current = { x: touch.clientX, y: touch.clientY };
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (isDraggingMarker && dragStartPos.current) {
      const deltaX = e.clientX - dragStartPos.current.x;
      const deltaY = e.clientY - dragStartPos.current.y;
      dragStartPos.current = { x: e.clientX, y: e.clientY };

      const imgElem = viewerRef.current?.querySelector('img');
      const rect = imgElem ? imgElem.getBoundingClientRect() : viewerRef.current?.getBoundingClientRect();
      if (rect) {
        const pctX = (deltaX / rect.width) * 100;
        const pctY = (deltaY / rect.height) * 100;

        setPorosity((prev) => {
          const newX = Math.min(Math.max(Math.round((prev.detection.boundingBox.x + pctX) * 10) / 10, 2), 98);
          const newY = Math.min(Math.max(Math.round((prev.detection.boundingBox.y + pctY) * 10) / 10, 2), 98);
          return { ...prev, detection: { ...prev.detection, boundingBox: { ...prev.detection.boundingBox, x: newX, y: newY } } };
        });
      }
      return;
    }

    if (!isPanning) return;
    setPan({ x: e.clientX - startPan.x, y: e.clientY - startPan.y });
  };

  const handleMouseUp = () => {
    setIsPanning(false);
    if (isDraggingMarker) {
      showNotification(`기공 마커 위치가 (${porosity.detection.boundingBox.x}%, ${porosity.detection.boundingBox.y}%)로 이동되었습니다.`);
      setIsDraggingMarker(false);
    }
  };

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const resetImageAdjustment = () => {
    setWindowLevel(100);
    setWindowWidth(100);
    setInvertFilter(false);
    setSharpenFilter(false);
    setReliefFilter(false);
    showNotification('이미지 조정 값이 초기화되었습니다.');
  };

  const handleDecision = (decision: WorkerDecision) => {
    setPorosity((prev) => ({ ...prev, workerDecision: decision }));
    showNotification(`[${decision}] 상태로 기록되었습니다.`);
  };

  const showNotification = (msg: string) => {
    setNotice(msg);
    setTimeout(() => setNotice(null), 3500);
  };

  // brightness = window level, contrast = window width; sharpen/relief are CSS approximations
  const imageFilterStyle = [
    `brightness(${windowLevel}%)`,
    `contrast(${windowWidth}%)`,
    invertFilter ? 'invert(1)' : '',
    sharpenFilter ? 'contrast(135%) saturate(0%)' : '',
    reliefFilter ? 'contrast(160%) brightness(90%) grayscale(1)' : '',
  ].filter(Boolean).join(' ');

  const recomputeProfile = useCallback(() => {
    const img = displayImgRef.current;
    if (!img || !img.complete || img.naturalWidth === 0) return;
    const values = sampleImageProfile(
      img,
      profileAxis,
      porosity.detection.boundingBox.x,
      porosity.detection.boundingBox.y,
      120
    );
    setProfileValues(values);
  }, [profileAxis, porosity.detection.boundingBox.x, porosity.detection.boundingBox.y]);

  useEffect(() => {
    recomputeProfile();
  }, [recomputeProfile, uploadedImage]);

  const markerColor =
    porosity.assessment.severity === 'High' ? '#E53935' : porosity.assessment.severity === 'Medium' ? '#F59E0B' : '#16A34A';
  const selectedCase = SORTED_SIMILAR_CASES.find((item) => item.id === selectedCaseId) ?? SORTED_SIMILAR_CASES[0];

  const openSimilarityPage = (caseId = SORTED_SIMILAR_CASES[0].id) => {
    setSelectedCaseId(caseId);
    setActivePage('similarity');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const openInspectionPage = () => {
    setActivePage('inspection');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="flex flex-col min-h-screen w-full bg-[#F8F7F4] text-[#111111] font-sans select-none text-sm">

      {/* Hidden File Input for User Custom Image Upload */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleImageUpload}
        accept="image/*"
        className="hidden"
      />

      {/* 1. COMPACT ESSENTIAL METADATA HEADER WITH DEMO BADGE */}
      <header className="h-12 bg-[#161617] text-[#F4F8FB] px-4 flex items-center justify-between border-b border-[#333336] shrink-0">
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-2 pr-3 border-r border-[#333336]">
            <span className="w-7 h-7 rounded-[8px] bg-[#3397D4] text-white grid place-items-center font-bold text-xs shadow-sm">W</span>
            <span className="font-semibold tracking-tight text-[#F4F8FB] text-base">WeldScan</span>
            <span className="text-[10px] text-[#86868B] font-mono">WORKER</span>
          </div>

          <div className="flex items-center gap-4 text-[#D2D2D7] text-xs">
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
            <div className="hidden lg:block">
              <span className="text-[#86868B] mr-1">검사자:</span>
              <span className="font-medium text-[#F4F8FB]">김민수 (Level-II), 2년차</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden xl:flex items-center gap-2 px-2.5 h-8 rounded-[5px] border border-[#41626A] bg-[#2B3A37] text-[11px] text-[#D2D2D7]">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            <span>현재 상태</span>
            <strong className="text-[#F4F8FB] font-medium">검토 진행 중</strong>
          </div>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-1.5 h-8 px-2.5 text-[11px] bg-[#333336] hover:bg-[#41626A] text-[#F4F8FB] rounded-[5px] border border-[#41626A] font-medium transition-colors"
            title="실제 촬영된 RT 사진 파일 업로드"
          >
            <ImageIcon className="w-3.5 h-3.5 text-[#3397D4]" />
            <span>{uploadedImage ? '사진 변경' : 'RT 사진 업로드'}</span>
          </button>

          <button
            onClick={() => setShowBasis(!showBasis)}
            className="flex items-center gap-1.5 h-8 px-2.5 text-[11px] bg-[#333336] hover:bg-[#41626A] text-[#D2D2D7] rounded-[5px] border border-[#41626A] font-medium transition-colors"
          >
            <FileText className="w-3.5 h-3.5 text-[#D2D2D7]" />
            <span>검사 기준 보기</span>
            {showBasis ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </header>

      <nav className="h-11 bg-[#1F2022] border-b border-[#41626A] px-4 flex items-end gap-1 shrink-0" aria-label="검사 업무 화면">
        <button
          type="button"
          onClick={openInspectionPage}
          aria-current={activePage === 'inspection' ? 'page' : undefined}
          className={`h-10 px-5 text-xs font-semibold border-b-2 transition-colors ${
            activePage === 'inspection'
              ? 'border-[#3397D4] text-[#F4F8FB] bg-[#2B3A37]'
              : 'border-transparent text-[#86868B] hover:text-[#D2D2D7]'
          }`}
        >
          검사 판정
        </button>
        <button
          type="button"
          onClick={() => openSimilarityPage(selectedCaseId)}
          aria-current={activePage === 'similarity' ? 'page' : undefined}
          className={`h-10 px-5 text-xs font-semibold border-b-2 transition-colors ${
            activePage === 'similarity'
              ? 'border-[#3397D4] text-[#F4F8FB] bg-[#2B3A37]'
              : 'border-transparent text-[#86868B] hover:text-[#D2D2D7]'
          }`}
        >
          유사 매칭 분석
        </button>
      </nav>

      {/* EXPANDABLE SECONDARY SPECIFICATIONS & STANDARDS */}
      {showBasis && (
        <div className="bg-[#2B3A37] border-b border-[#41626A] px-5 py-2.5 text-xs text-[#F4F8FB] grid grid-cols-1 md:grid-cols-3 gap-4 shrink-0 shadow-inner">
          <div>
            <span className="font-medium text-[#9FC6F4] block mb-1 font-mono text-[10px]">적용 규격 (STANDARDS)</span>
            <p className="font-semibold text-sm text-[#F4F8FB]">한국선급규정 KR 2026</p>
            <p className="text-[#D2D2D7] text-[10px] mt-0.5">조선 선체 구조 용접부 방사선 투과 규격</p>
          </div>
          <div>
            <span className="font-medium text-[#9FC6F4] block mb-1 font-mono text-[10px]">기공 허용 기준 (POROSITY LIMITS)</span>
            <p className="text-xs text-[#F4F8FB]">
              단일 기공: <span className="font-mono font-semibold text-[#EA33C0]">Max Ø 2.5mm</span> | 군집 기공: <span className="font-mono font-semibold text-[#EA33C0]">투과 면적 1.5% 이내</span>
            </p>
            <p className="text-[#D2D2D7] text-[10px] mt-0.5">Level B 기준 초과 시 재용접 처리 대상</p>
          </div>
          <div>
            <span className="font-medium text-[#9FC6F4] block mb-1 font-mono text-[10px]">장비 및 투과 조건</span>
            <p className="font-mono text-xs text-[#F4F8FB]">Seifert 200kV DDA 검출기 | 피치 100µm</p>
            <p className="text-[#D2D2D7] text-[10px] mt-0.5">EN 462-1 W10 투과도계 식별 완료</p>
          </div>
        </div>
      )}

      {/* NOTIFICATION BANNER */}
      {notice && (
        <div className="bg-[#3397D4] text-[#F4F8FB] px-5 py-1.5 text-xs font-medium flex items-center justify-between shrink-0 shadow-sm">
          <span>{notice}</span>
          <button onClick={() => setNotice(null)} className="hover:opacity-80 p-1">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* TOP WORKSPACE - RT IMAGE VIEWER (LEFT) / INSPECTION RESULT PANEL (RIGHT), EQUAL HEIGHT */}
      {activePage === 'inspection' && <div className="flex flex-col md:flex-row md:items-stretch">

        {/* LEFT 60–65%: RT IMAGE VIEWER */}
        <div className="w-full md:w-[62%] lg:w-[65%] flex flex-col bg-[#161617] border-r border-[#333336] relative">

          {/* VIEWER CONTROLS TOOLBAR (TOUCH-OPTIMIZED HEIGHT) */}
          <div className="min-h-10 bg-[#333336] border-b border-[#41626A] px-3 py-1.5 flex items-center justify-between gap-3 text-xs text-[#D2D2D7] shrink-0">
            {/* View Mode Toggle */}
            <div className="flex items-center gap-3 min-w-0">
              <div className="min-w-0">
                <div className="text-xs font-semibold text-[#F4F8FB]">현재 검사 영상</div>
                <div className="text-[10px] text-[#86868B] truncate">RT-2026-0910-4082 · 신규 RT 검사</div>
              </div>
              <button
                onClick={() => setShowDefectBox(!showDefectBox)}
                className={`h-7 px-3 rounded-[5px] border text-[11px] font-medium transition-colors flex items-center gap-1.5 ${
                  showDefectBox ? 'bg-[#3397D4] text-[#F4F8FB] border-[#9FC6F4]' : 'bg-[#161617] hover:bg-[#2B3A37] border-[#41626A] text-[#D2D2D7]'
                }`}
              >
                <span className="w-2.5 h-2 rounded-[2px] border border-[#E53935]" style={{ backgroundColor: showDefectBox ? '#E5393533' : 'transparent' }} />
                <span>AI 결함 박스 {showDefectBox ? '숨기기' : '표시'}</span>
              </button>

              <button
                onClick={() => openSimilarityPage()}
                className="h-7 px-3 rounded-[5px] border text-[11px] font-medium transition-colors flex items-center gap-1.5 bg-[#161617] hover:bg-[#2B3A37] border-[#41626A] text-[#D2D2D7]"
              >
                <Activity className="w-3.5 h-3.5" />
                <span>유사 매칭 분석</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Touch-Friendly Zoom Controls */}
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-[#86868B] hidden lg:inline border-r border-[#41626A] pr-2 pt-[3px]">
                💡마커를 마우스로 드래그하여 위치 이동이 가능합니다.
              </span>

              <button onClick={() => setZoom(Math.min(zoom + 0.25, 3))} className="h-7 w-7 bg-[#161617] hover:bg-[#2B3A37] border border-[#41626A] rounded-[5px] flex items-center justify-center text-[#F4F8FB]" title="확대">
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button onClick={() => setZoom(Math.max(zoom - 0.25, 0.75))} className="h-7 w-7 bg-[#161617] hover:bg-[#2B3A37] border border-[#41626A] rounded-[5px] flex items-center justify-center text-[#F4F8FB]" title="축소">
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <button onClick={resetView} className="h-7 w-7 bg-[#161617] hover:bg-[#2B3A37] border border-[#41626A] rounded-[5px] flex items-center justify-center text-[#F4F8FB]" title="초기화">
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
              setIsPanning(true);
              setStartPan({ x: touch.clientX - pan.x, y: touch.clientY - pan.y });
            }}
            onTouchMove={(e) => {
              const touch = e.touches[0];
              if (!touch) return;
              if (isDraggingMarker && dragStartPos.current) {
                const deltaX = touch.clientX - dragStartPos.current.x;
                const deltaY = touch.clientY - dragStartPos.current.y;
                dragStartPos.current = { x: touch.clientX, y: touch.clientY };

                const imgElem = viewerRef.current?.querySelector('img');
                const rect = imgElem ? imgElem.getBoundingClientRect() : viewerRef.current?.getBoundingClientRect();
                if (rect) {
                  const pctX = (deltaX / rect.width) * 100;
                  const pctY = (deltaY / rect.height) * 100;
                  setPorosity((prev) => {
                    const newX = Math.min(Math.max(Math.round((prev.detection.boundingBox.x + pctX) * 10) / 10, 2), 98);
                    const newY = Math.min(Math.max(Math.round((prev.detection.boundingBox.y + pctY) * 10) / 10, 2), 98);
                    return { ...prev, detection: { ...prev.detection, boundingBox: { ...prev.detection.boundingBox, x: newX, y: newY } } };
                  });
                }
                return;
              }
              if (!isPanning) return;
              setPan({ x: touch.clientX - startPan.x, y: touch.clientY - startPan.y });
            }}
            onTouchEnd={handleMouseUp}
            className={`flex-1 min-h-[420px] md:min-h-[560px] max-h-[600px] relative overflow-hidden flex items-center justify-center bg-[#050608] cursor-${isPanning ? 'grabbing' : 'grab'}`}
          >
            {/* Calibration mm Scale Top Overlay */}
            <div className="absolute top-2 left-4 right-4 h-4 flex justify-between items-center text-[10px] font-mono text-[#86868B] border-b border-[#333336] pointer-events-none z-10">
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

                <img
                  ref={displayImgRef}
                  src={uploadedImage || CURRENT_RT_IMAGE}
                  alt="RT Weld Radiograph"
                  crossOrigin="anonymous"
                  onLoad={recomputeProfile}
                  style={{ filter: imageFilterStyle }}
                  className="w-full h-full object-contain pointer-events-none"
                />

                {/* LIGHTWEIGHT ACCURATE POROSITY OVERLAY */}
                {showDefectBox && (
                  <div className="absolute inset-0 pointer-events-auto">
                    <div
                      onMouseDown={handleMarkerMouseDown}
                      onTouchStart={handleMarkerTouchStart}
                      className={`absolute transform -translate-x-1/2 -translate-y-1/2 cursor-grab active:cursor-grabbing z-30 group ${
                        isDraggingMarker ? 'z-50 scale-125' : ''
                      }`}
                      style={{
                        left: `${porosity.detection.boundingBox.x}%`,
                        top: `${porosity.detection.boundingBox.y}%`,
                      }}
                      title="드래그하여 기공 위치 이동 가능"
                    >
                      {/* Wide Rectangular Overlay on Defect (precision bracket style) */}
                      <div
                        className="relative w-52 h-20 rounded-sm transition-all"
                        style={{
                          border: `1px solid ${markerColor}70`,
                          backgroundColor: `${markerColor}14`,
                        }}
                      >
                        {/* Precision corner brackets */}
                        {[
                          'top-0 left-0 border-t-2 border-l-2',
                          'top-0 right-0 border-t-2 border-r-2',
                          'bottom-0 left-0 border-b-2 border-l-2',
                          'bottom-0 right-0 border-b-2 border-r-2',
                        ].map((pos) => (
                          <div
                            key={pos}
                            className={`absolute w-3.5 h-3.5 ${pos}`}
                            style={{ borderColor: markerColor }}
                          />
                        ))}
                        {/* Center crosshair */}
                        <div className="absolute inset-0 grid place-items-center">
                          <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: markerColor }} />
                        </div>
                      </div>

                      {/* Compact Status Chip Immediately Beside the Box */}
                      {porosity.workerDecision && (
                        <div
                          style={{ backgroundColor: markerColor }}
                          className="absolute left-[220px] top-1/2 -translate-y-1/2 text-white font-mono text-sm font-semibold px-2 py-0.5 rounded shadow-lg flex items-center gap-1 whitespace-nowrap scale-110 ring-1 ring-white z-50"
                        >
                          {porosity.workerDecision === '승인' && <Check className="w-3.5 h-3.5 text-green-200" />}
                          {porosity.workerDecision === '보수' && <AlertTriangle className="w-3.5 h-3.5 text-red-200" />}
                          {porosity.workerDecision === '재검사' && <AlertTriangle className="w-3.5 h-3.5 text-amber-200" />}
                        </div>
                      )}
                    </div>
                  </div>
                )}

              </div>
            </div>
          </div>

          {/* IMAGE ADJUSTMENT TOOLBAR & PIXEL DENSITY PROFILE — FILLS THE REMAINING SPACE BELOW THE RT VIEWER */}
          <div className="flex-1 min-h-[230px] bg-zinc-900 border-t border-[#41626A] p-3 grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* LEFT: Image Adjustment Toolbar */}
            <div className="flex flex-col gap-2.5 md:border-r md:border-[#333336] md:pr-3">
              <div className="flex items-center justify-between shrink-0">
                <h2 className="text-xs font-semibold text-[#F4F8FB]">이미지 조정</h2>
                <button
                  type="button"
                  onClick={resetImageAdjustment}
                  className="h-6 px-2 flex items-center gap-1 text-[10px] font-medium text-[#D2D2D7] bg-[#333336] hover:bg-[#41626A] border border-[#41626A] rounded-[4px]"
                >
                  <RotateCcw className="w-3 h-3" /> 초기화
                </button>
              </div>

              {/* Window Level / Width sliders */}
              <div className="space-y-2">
                <div>
                  <div className="flex items-center justify-between text-[10px] text-[#86868B] mb-1">
                    <span>W/L (밝기)</span>
                    <span className="font-mono text-[#F4F8FB]">{windowLevel}%</span>
                  </div>
                  <input
                    type="range"
                    min={40}
                    max={160}
                    value={windowLevel}
                    onChange={(e) => setWindowLevel(Number(e.target.value))}
                    className="w-full h-1.5 accent-[#3397D4]"
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between text-[10px] text-[#86868B] mb-1">
                    <span>W/W (대비)</span>
                    <span className="font-mono text-[#F4F8FB]">{windowWidth}%</span>
                  </div>
                  <input
                    type="range"
                    min={40}
                    max={200}
                    value={windowWidth}
                    onChange={(e) => setWindowWidth(Number(e.target.value))}
                    className="w-full h-1.5 accent-[#3397D4]"
                  />
                </div>
              </div>

              {/* Quick filter toggle buttons */}
              <div className="flex items-center gap-1.5 flex-wrap">
                <button
                  type="button"
                  onClick={() => setInvertFilter((v) => !v)}
                  className={`h-7 px-2.5 rounded-[5px] border text-[11px] font-medium flex items-center gap-1 transition-colors ${
                    invertFilter ? 'bg-[#3397D4] text-[#F4F8FB] border-[#9FC6F4]' : 'bg-[#161617] hover:bg-[#2B3A37] border-[#41626A] text-[#D2D2D7]'
                  }`}
                >
                  <FlipHorizontal className="w-3.5 h-3.5" /> 반전
                </button>
                <button
                  type="button"
                  onClick={() => setSharpenFilter((v) => !v)}
                  className={`h-7 px-2.5 rounded-[5px] border text-[11px] font-medium flex items-center gap-1 transition-colors ${
                    sharpenFilter ? 'bg-[#3397D4] text-[#F4F8FB] border-[#9FC6F4]' : 'bg-[#161617] hover:bg-[#2B3A37] border-[#41626A] text-[#D2D2D7]'
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" /> 선명화
                </button>
                <button
                  type="button"
                  onClick={() => setReliefFilter((v) => !v)}
                  className={`h-7 px-2.5 rounded-[5px] border text-[11px] font-medium flex items-center gap-1 transition-colors ${
                    reliefFilter ? 'bg-[#3397D4] text-[#F4F8FB] border-[#9FC6F4]' : 'bg-[#161617] hover:bg-[#2B3A37] border-[#41626A] text-[#D2D2D7]'
                  }`}
                >
                  <Mountain className="w-3.5 h-3.5" /> 엠보싱
                </button>
              </div>

              {/* Profile axis selector */}
              <div className="flex items-center gap-2 pt-1 border-t border-[#333336]">
                <Ruler className="w-3.5 h-3.5 text-[#9FC6F4] shrink-0" />
                <span className="text-[10px] text-[#86868B] shrink-0">단면 방향</span>
                <div className="flex items-center bg-[#161617] p-0.5 rounded-[5px] border border-[#41626A] gap-0.5">
                  <button
                    type="button"
                    onClick={() => setProfileAxis('horizontal')}
                    className={`h-6 px-2 rounded-[3px] text-[10px] font-medium transition-colors ${
                      profileAxis === 'horizontal' ? 'bg-[#3397D4] text-[#F4F8FB]' : 'text-[#86868B] hover:text-[#F4F8FB]'
                    }`}
                  >
                    가로 단면
                  </button>
                  <button
                    type="button"
                    onClick={() => setProfileAxis('vertical')}
                    className={`h-6 px-2 rounded-[3px] text-[10px] font-medium transition-colors ${
                      profileAxis === 'vertical' ? 'bg-[#3397D4] text-[#F4F8FB]' : 'text-[#86868B] hover:text-[#F4F8FB]'
                    }`}
                  >
                    세로 단면
                  </button>
                </div>
              </div>
            </div>

            {/* RIGHT: Pixel Density / Intensity Profile */}
            <div className="flex flex-col gap-1.5 min-h-0">
              <div className="flex items-center justify-between shrink-0">
                <h2 className="text-xs font-semibold text-[#F4F8FB]">결함 단면 픽셀 밀도 프로파일</h2>
                <span className="text-[9px] whitespace-nowrap text-[#9FC6F4] bg-[#2B3A37] border border-[#41626A] rounded px-2 py-1 font-mono">
                  Intensity Profile
                </span>
              </div>
              <div className="flex-1 min-h-[90px] bg-[#050608] rounded border border-[#333336] p-2">
                <DensityProfileChart values={profileValues} widthMm={porosity.morphology.largestDiameterMm * 2} />
              </div>
              <p className="text-[10px] text-[#86868B] leading-snug shrink-0">
                결함 중심(<span className="font-mono text-[#9FC6F4]">{porosity.detection.boundingBox.x}%, {porosity.detection.boundingBox.y}%</span>)을 지나는 {profileAxis === 'horizontal' ? '가로' : '세로'} 단면의 실제 픽셀 흑도 값입니다. 노란 점선은 반치폭(FWHM) 기준 결함 경계입니다.
              </p>
            </div>
          </div>
        </div>

        {/* RIGHT 35–40%: CLEAN INSPECTION RESULT PANEL (16PX+ TEXT & TOUCH BUTTONS) */}
        <div className="w-full md:w-[38%] lg:w-[35%] bg-[#333336] text-[#F4F8FB] flex flex-col shrink-0 border-l border-[#333336]">

          {/* INSPECTION REVIEW STATUS */}
          <div className="p-3 bg-[#2B3A37] border-b border-[#41626A]">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[#D2D2D7]">기공 검토 상태</span>
              <span className="text-xs font-mono font-bold text-[#F4F8FB] flex items-center gap-1.5">
                {porosity.workerDecision === null && '검토 대기'}
                {porosity.workerDecision === '승인' && (
                  <>
                    <Check className="w-3.5 h-3.5 text-green-400" /> 승인 완료
                  </>
                )}
                {porosity.workerDecision === '보수' && (
                  <>
                    <AlertTriangle className="w-3.5 h-3.5 text-red-400" /> 보수 필요 기록됨
                  </>
                )}
                {porosity.workerDecision === '재검사' && (
                  <>
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> 재검사 요청됨
                  </>
                )}
              </span>
            </div>
          </div>

          {/* AI DETECTION CARD */}
          <div className="p-3 border-b border-[#41626A]">
            <div className={`p-2.5 rounded border flex items-center justify-between mb-2.5 ${
              porosity.assessment.severity === 'High'
                ? 'bg-red-950/60 border-red-800 text-red-200'
                : porosity.assessment.severity === 'Medium'
                ? 'bg-amber-950/60 border-amber-800 text-amber-200'
                : 'bg-teal-950/60 border-teal-800 text-teal-200'
            }`}>
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 shrink-0" />
                <div>
                  <div className="font-bold text-sm leading-none">{porosity.assessment.status}</div>
                  <div className="text-xs mt-1 opacity-80">{porosity.detection.locationLabel} · {porosity.detection.weldZone}</div>
                </div>
              </div>
            </div>

            <div className="text-[10px] font-semibold text-[#9FC6F4] mb-1.5 font-mono">AI DETECTION</div>
            <div className="grid grid-cols-2 gap-1.5 text-xs bg-[#2B3A37] p-2.5 rounded border border-[#41626A] mb-2.5">
              <div><span className="text-[#D2D2D7]">결함 유형</span><div className="font-semibold text-[#F4F8FB]">{porosity.detection.defectType}</div></div>
              <div><span className="text-[#D2D2D7]">Confidence</span><div className="font-semibold text-[#F4F8FB]">{porosity.detection.aiConfidence}%</div></div>
              <div><span className="text-[#D2D2D7]">위치</span><div className="font-semibold text-[#F4F8FB]">{porosity.detection.locationLabel}</div></div>
              <div><span className="text-[#D2D2D7]">용접부</span><div className="font-semibold text-[#F4F8FB]">{porosity.detection.weldZone}</div></div>
            </div>

            <div className="text-[10px] font-semibold text-[#9FC6F4] mb-1.5 font-mono">DETECTED FEATURE</div>
            <div className="space-y-1.5 text-xs bg-[#2B3A37] p-2.5 rounded border border-[#41626A] mb-2.5">
              <div className="flex justify-between border-b border-[#41626A] pb-1.5">
                <span className="text-[#D2D2D7]">형상 / 분포</span>
                <span className="font-semibold text-[#F4F8FB]">{porosity.morphology.shape} · {porosity.morphology.distribution}</span>
              </div>
              <div className="flex justify-between border-b border-[#41626A] pb-1.5">
                <span className="text-[#D2D2D7]">최대 / 평균 직경</span>
                <span className="font-semibold text-[#F4F8FB]">Ø{porosity.morphology.largestDiameterMm} / Ø{porosity.morphology.averageDiameterMm} mm</span>
              </div>
              <div className="flex justify-between border-b border-[#41626A] pb-1.5">
                <span className="text-[#D2D2D7]">기공 개수</span>
                <span className="font-semibold text-[#F4F8FB]">{porosity.morphology.poreCount} 개</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#D2D2D7]">영향 길이</span>
                <span className="font-semibold text-[#F4F8FB]">{porosity.morphology.affectedLengthMm} mm</span>
              </div>
            </div>

            <div className="text-[10px] font-semibold text-[#9FC6F4] mb-1.5 font-mono">검토 근거</div>
            <ul className="space-y-1 text-xs bg-[#2B3A37] p-2.5 rounded border border-[#41626A] mb-2.5">
              {porosity.assessment.reason.map((r, i) => (
                <li key={i} className="text-[#D2D2D7] flex gap-1.5">
                  <span className="text-[#9FC6F4]">•</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>

            {/* Position adjustment UI */}
            <div className="bg-[#2B3A37] p-2.5 rounded border border-[#41626A]">
              <div className="text-[10px] font-semibold text-[#D2D2D7] mb-1">마커 좌표 직접 조정 (%)</div>
              <div className="flex items-center gap-2">
                <div className="flex-1 flex items-center gap-1 bg-[#161617] border border-[#41626A] rounded px-2 py-1">
                  <span className="text-[10px] text-[#86868B] font-bold">X</span>
                  <input
                    type="number"
                    step="0.5"
                    min="2"
                    max="98"
                    value={porosity.detection.boundingBox.x}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value) || 0;
                      setPorosity(prev => ({ ...prev, detection: { ...prev.detection, boundingBox: { ...prev.detection.boundingBox, x: val } } }));
                    }}
                    className="w-full text-xs font-mono font-bold text-[#F4F8FB] bg-transparent outline-none"
                  />
                  <span className="text-[10px] text-[#86868B]">%</span>
                </div>
                <div className="flex-1 flex items-center gap-1 bg-[#161617] border border-[#41626A] rounded px-2 py-1">
                  <span className="text-[10px] text-[#86868B] font-bold">Y</span>
                  <input
                    type="number"
                    step="0.5"
                    min="2"
                    max="98"
                    value={porosity.detection.boundingBox.y}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value) || 0;
                      setPorosity(prev => ({ ...prev, detection: { ...prev.detection, boundingBox: { ...prev.detection.boundingBox, y: val } } }));
                    }}
                    className="w-full text-xs font-mono font-bold text-[#F4F8FB] bg-transparent outline-none"
                  />
                  <span className="text-[10px] text-[#86868B]">%</span>
                </div>
              </div>
            </div>
          </div>

          {/* WORKER DECISION (3 DISPOSITIONS WITH MIN HEIGHT 40PX TOUCH BUTTONS) */}
          <div className="p-3 border-b border-[#41626A]">
            <span className="text-xs font-bold text-[#F4F8FB] block mb-2">
              검사자 판단
            </span>
            <div className="flex flex-col gap-1.5">
              <button
                onClick={() => handleDecision('승인')}
                className={`h-9 py-2 px-3 rounded-[5px] text-xs font-medium flex items-center justify-between transition-colors ${
                  porosity.workerDecision === '승인'
                    ? 'bg-[#3397D4] text-[#F4F8FB] border border-[#9FC6F4]'
                    : 'bg-[#161617] hover:bg-[#2B3A37] text-[#D2D2D7] border border-[#41626A]'
                }`}
              >
                <div className="flex items-center gap-2">
                  <Check className="w-3.5 h-3.5 text-green-400" />
                  <span>승인</span>
                </div>
                <span className="text-[10px] text-[#86868B]">AI 판정 동의</span>
              </button>

              <button
                onClick={() => handleDecision('보수')}
                className={`h-9 py-2 px-3 rounded-[5px] text-xs font-medium flex items-center justify-between transition-colors ${
                  porosity.workerDecision === '보수'
                    ? 'bg-[#3397D4] text-[#F4F8FB] border border-[#9FC6F4]'
                    : 'bg-[#161617] hover:bg-[#2B3A37] text-[#D2D2D7] border border-[#41626A]'
                }`}
              >
                <div className="flex items-center gap-2">
                  <X className="w-3.5 h-3.5 text-red-400" />
                  <span>보수 필요</span>
                </div>
                <span className="text-[10px] text-[#86868B]">국부 제거 후 재용접 권장</span>
              </button>

              <button
                onClick={() => handleDecision('재검사')}
                className={`h-9 py-2 px-3 rounded-[5px] text-xs font-medium flex items-center justify-between transition-colors ${
                  porosity.workerDecision === '재검사'
                    ? 'bg-[#3397D4] text-[#F4F8FB] border border-[#9FC6F4]'
                    : 'bg-[#161617] hover:bg-[#2B3A37] text-[#D2D2D7] border border-[#41626A]'
                }`}
              >
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                  <span>재검사 필요</span>
                </div>
                <span className="text-[10px] text-[#86868B]">초음파(UT) 또는 재촬영</span>
              </button>
            </div>
          </div>

          {/* CONCISE AI SUMMARY */}
          <div className="p-3 border-b border-[#41626A] text-xs leading-relaxed text-[#D2D2D7]">
            <div className="flex items-center gap-1.5 font-bold text-[#3397D4] mb-1.5">
              <Activity className="w-3.5 h-3.5" />
              <span>AI Detection 요약</span>
            </div>
            <p className="text-xs text-[#F4F8FB]">
              {'현재 결함 '}
              <span className="text-[#EA33C0] font-bold">(Ø{porosity.morphology.largestDiameterMm}mm, {porosity.detection.weldZone})</span>
              {'은(는) 유사 과거 사례 대비 크기가 크고 Root 영역에서 탐지되어 '}
              <span className="font-semibold text-[#F4F8FB]">{porosity.assessment.status}</span>
              {'로 분류되었습니다. 최종 판단은 검사원이 결정합니다.'}
            </p>
          </div>

          {/* PERSISTENT BOTTOM ACTIONS (MIN HEIGHT 40PX TOUCH TARGETS) */}
          <div className="p-3 bg-[#161617] space-y-2 mt-auto border-t border-[#41626A]">
            <button
              onClick={() => {
                setEscalated(true);
                showNotification('책임 검사원(Senior Inspector)에게 검사건이 이관되었습니다.');
              }}
              className="w-full h-9 bg-[#333336] hover:bg-[#41626A] text-[#D2D2D7] border border-[#41626A] rounded-[5px] font-medium text-xs flex items-center justify-center gap-2 transition-colors"
            >
              <ShieldAlert className="w-3.5 h-3.5 text-[#9FC6F4]" />
              <span>책임 검사원 이관</span>
            </button>

            <button
              onClick={() => showNotification('판정이 완료되었습니다.')}
              className="w-full h-9 bg-[#3397D4] hover:bg-[#9FC6F4] hover:text-[#161617] text-[#F4F8FB] rounded-[5px] font-medium text-xs transition-colors shadow-sm"
            >
              검사 최종 확인 저장
            </button>
          </div>
        </div>
      </div>}

      {activePage === 'similarity' && (
        <main className="flex-1 bg-[#161617] text-[#F4F8FB] px-4 py-5 md:px-6 md:py-6 overflow-y-auto">
          <div className="max-w-[1380px] mx-auto space-y-5">
            <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
              <div>
                <h1 className="text-xl font-bold tracking-tight">유사 매칭 분석</h1>
                <p className="text-xs text-[#86868B] mt-1">현재 결함과 과거 검사 사례의 형상·크기·분포·위치를 항목별로 비교합니다.</p>
              </div>
              <button type="button" onClick={openInspectionPage} className="h-9 px-4 rounded-[5px] border border-[#41626A] bg-[#2B3A37] hover:bg-[#333336] text-xs font-semibold text-[#D2D2D7]">
                검사 판정으로 돌아가기
              </button>
            </div>

            <section className="bg-[#2B3A37] border border-[#41626A] rounded-[10px] p-3" aria-labelledby="current-target-title">
              <div className="flex items-center gap-3">
                <div className="w-28 h-16 shrink-0 bg-[#050608] border border-[#41626A] rounded-[5px] overflow-hidden">
                  <img src={uploadedImage || CURRENT_RT_IMAGE} alt="현재 검사 RT crop" className="w-full h-full object-cover" />
                </div>
                <div className="min-w-0 flex-1">
                  <h2 id="current-target-title" className="text-xs font-semibold text-[#9FC6F4]">현재 검사 대상</h2>
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5 text-sm font-semibold">
                    <span>{porosity.detection.defectType}</span><span className="text-[#41626A]">/</span>
                    <span className="font-mono">Ø{porosity.morphology.largestDiameterMm} mm</span><span className="text-[#41626A]">/</span>
                    <span>{porosity.detection.weldZone}</span><span className="text-[#41626A]">/</span>
                    <span>{porosity.detection.locationLabel}</span><span className="text-[#41626A]">/</span>
                    <span className="font-mono text-[#9FC6F4]">{porosity.detection.aiConfidence}%</span>
                  </div>
                </div>
              </div>
            </section>

            <section aria-labelledby="similar-case-picker-title">
              <div className="flex items-center justify-between mb-2">
                <h2 id="similar-case-picker-title" className="text-sm font-semibold">유사 사례</h2>
                <span className="text-[10px] font-mono text-[#86868B]">유사도 높은 순</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
                {SORTED_SIMILAR_CASES.map((sc) => {
                  const active = sc.id === selectedCase.id;
                  const color = getDecisionColor(sc.historicalResult.decision);
                  return (
                    <button key={sc.id} type="button" onClick={() => setSelectedCaseId(sc.id)} className={`text-left p-2 rounded-[6px] border transition-colors ${active ? 'bg-[#2B3A37] border-[#3397D4]' : 'bg-[#333336] border-[#41626A] hover:border-[#9FC6F4]'}`}>
                      <div className="h-20 bg-[#050608] rounded-[4px] overflow-hidden border border-[#41626A]">
                        <img src={sc.image} alt={`${sc.caseId} RT 영상`} className="w-full h-full object-cover" />
                      </div>
                      <div className="flex items-center justify-between gap-2 mt-2">
                        <span className="font-mono text-xs font-semibold">{sc.caseId}</span>
                        <span className="font-mono text-xs font-bold text-[#9FC6F4]">{sc.similarity.overall}%</span>
                      </div>
                      <span className={`mt-1.5 inline-flex text-[10px] font-semibold px-1.5 py-0.5 rounded border ${decisionColorClasses[color]}`}>{sc.historicalResult.decision}</span>
                    </button>
                  );
                })}
              </div>
            </section>

            <section className="bg-[#333336] border border-[#41626A] rounded-[10px] overflow-hidden" aria-labelledby="case-comparison-title">
              <div className="px-4 py-3 bg-[#2B3A37] border-b border-[#41626A] flex items-center justify-between gap-3">
                <div>
                  <h2 id="case-comparison-title" className="text-sm font-bold">선택 사례 비교</h2>
                  <p className="text-[11px] text-[#86868B] mt-0.5">현재 검사와 {selectedCase.caseId}의 실제 판독 특성을 나란히 비교합니다.</p>
                </div>
                <span className="font-mono text-lg font-bold text-[#9FC6F4]">{selectedCase.similarity.overall}%</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2">
                <article className="p-4 md:border-r border-[#41626A]">
                  <div className="flex items-center justify-between mb-3"><h3 className="font-semibold">현재 검사</h3><span className="text-[10px] text-[#86868B] font-mono">LIVE</span></div>
                  <div className="h-60 bg-[#050608] rounded-[6px] overflow-hidden border border-[#41626A] mb-4"><img src={uploadedImage || CURRENT_RT_IMAGE} alt="현재 검사 RT 영상" className="w-full h-full object-contain" /></div>
                  <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs">
                    <div className="flex justify-between gap-3"><dt className="text-[#86868B]">형상</dt><dd className="font-semibold">{porosity.morphology.shape}</dd></div>
                    <div className="flex justify-between gap-3"><dt className="text-[#86868B]">분포</dt><dd className="font-semibold">{porosity.morphology.distribution}</dd></div>
                    <div className="flex justify-between gap-3"><dt className="text-[#86868B]">최대 직경</dt><dd className="font-mono font-semibold">{porosity.morphology.largestDiameterMm} mm</dd></div>
                    <div className="flex justify-between gap-3"><dt className="text-[#86868B]">기공 수</dt><dd className="font-mono font-semibold">{porosity.morphology.poreCount}</dd></div>
                    <div className="flex justify-between gap-3"><dt className="text-[#86868B]">위치</dt><dd className="font-semibold">{porosity.detection.weldZone}</dd></div>
                    <div className="flex justify-between gap-3"><dt className="text-[#86868B]">신뢰도</dt><dd className="font-mono font-semibold">{porosity.detection.aiConfidence}%</dd></div>
                  </dl>
                </article>

                <article className="p-4 border-t md:border-t-0 border-[#41626A]">
                  <div className="flex items-center justify-between mb-3"><h3 className="font-semibold">{selectedCase.caseId}</h3><span className="text-[10px] text-[#86868B]">{selectedCase.source.vessel}</span></div>
                  <div className="h-60 bg-[#050608] rounded-[6px] overflow-hidden border border-[#41626A] mb-4"><img src={selectedCase.image} alt={`${selectedCase.caseId} 과거 RT 영상`} className="w-full h-full object-contain" /></div>
                  <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs">
                    <div className="flex justify-between gap-3"><dt className="text-[#86868B]">형상</dt><dd className="font-semibold">{selectedCase.defect.shape}</dd></div>
                    <div className="flex justify-between gap-3"><dt className="text-[#86868B]">분포</dt><dd className="font-semibold">{selectedCase.defect.distribution}</dd></div>
                    <div className="flex justify-between gap-3"><dt className="text-[#86868B]">최대 직경</dt><dd className="font-mono font-semibold">{selectedCase.defect.largestDiameterMm} mm</dd></div>
                    <div className="flex justify-between gap-3"><dt className="text-[#86868B]">기공 수</dt><dd className="font-mono font-semibold">{selectedCase.defect.poreCount}</dd></div>
                    <div className="flex justify-between gap-3"><dt className="text-[#86868B]">위치</dt><dd className="font-semibold">{selectedCase.source.weldZone}</dd></div>
                    <div className="flex justify-between gap-3"><dt className="text-[#86868B]">검사일</dt><dd className="font-mono font-semibold">{selectedCase.source.inspectionDate}</dd></div>
                  </dl>
                </article>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] border-t border-[#41626A]">
                <div className="p-4 lg:border-r border-[#41626A]">
                  <h3 className="text-xs font-semibold text-[#9FC6F4] mb-3 font-mono">SIMILARITY BREAKDOWN</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
                    <SimilarityBar label="형상" value={selectedCase.similarity.breakdown.morphology} />
                    <SimilarityBar label="크기" value={selectedCase.similarity.breakdown.size} />
                    <SimilarityBar label="분포" value={selectedCase.similarity.breakdown.distribution} />
                    <SimilarityBar label="위치" value={selectedCase.similarity.breakdown.location} />
                  </div>
                </div>
                <div className="p-4 bg-[#2B3A37]">
                  <h3 className="text-xs font-semibold text-[#9FC6F4] mb-3 font-mono">과거 검사 결과</h3>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <span className="text-[#86868B]">등급</span><strong className="text-right">{selectedCase.historicalResult.grade}</strong>
                    <span className="text-[#86868B]">판정</span><strong className="text-right">{selectedCase.historicalResult.decision}</strong>
                    <span className="text-[#86868B]">조치</span><strong className="text-right">{selectedCase.historicalResult.inspectorAction}</strong>
                    <span className="text-[#86868B]">최종 결과</span><strong className="text-right text-[#9FC6F4]">{selectedCase.repair.finalResult}</strong>
                  </div>
                  <p className="text-[11px] text-[#D2D2D7] mt-3 pt-3 border-t border-[#41626A] leading-relaxed">{selectedCase.summary}</p>
                </div>
              </div>
            </section>

            <p className="text-[11px] text-[#86868B] leading-relaxed">본 유사도 분석은 검사원의 판정을 지원하는 참고 정보이며, 최종 판정은 한국선급규정 KR 2026과 검사원 검토를 통해 결정됩니다.</p>
          </div>
        </main>
      )}

      {/* SIMILAR HISTORICAL CASES STRIP (CARD-FIRST, NO MODAL) — FULL-WIDTH, BELOW BOTH COLUMNS, SHOWN ONLY AFTER "AI 유사 매칭" IS TRIGGERED */}
      {false && (
        <section className="bg-[#161617] border-t border-[#41626A] p-4 flex flex-col" aria-labelledby="similar-cases-title">
          <div className="flex items-start justify-between gap-3 mb-3 px-0.5 shrink-0">
            <div>
              <h2 id="similar-cases-title" className="text-sm font-semibold text-[#F4F8FB]">유사 사례 (Similar Inspection Cases)</h2>
              <p className="text-xs text-[#86868B] mt-1">현재 결함과 유사했던 과거 RT 검사 사례입니다. 유사도 순으로 정렬됩니다.</p>
            </div>
            <span className="text-[10px] whitespace-nowrap text-[#9FC6F4] bg-[#2B3A37] border border-[#41626A] rounded px-2 py-1 font-mono shrink-0">
              Similarity Search
            </span>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-5 gap-4 items-start">
            {SORTED_SIMILAR_CASES.map((sc) => {
              const decisionColor = getDecisionColor(sc.historicalResult.decision);
              const isExpanded = expandedCaseIds.has(sc.id);
              const toggleExpanded = () => {
                setExpandedCaseIds((prev) => {
                  const next = new Set(prev);
                  if (next.has(sc.id)) next.delete(sc.id);
                  else next.add(sc.id);
                  return next;
                });
              };

              return (
                <div
                  key={sc.id}
                  id={`similar-case-${sc.id}`}
                  className={`bg-[#333336] border rounded-[5px] p-3 flex flex-col transition-colors scroll-mt-4 ${
                    isExpanded ? 'border-[#3397D4] xl:col-span-5' : 'border-[#41626A] hover:border-[#3397D4]'
                  }`}
                >
                  <button
                    type="button"
                    onClick={toggleExpanded}
                    className={`text-left flex gap-2 focus:outline-none ${isExpanded ? 'flex-row items-start' : 'flex-col'}`}
                  >
                    {/* Image-First RT Case Canvas Preview */}
                    <div className={`bg-[#161617] rounded-[3px] relative overflow-hidden border border-[#41626A] flex items-center justify-center shrink-0 ${
                      isExpanded ? 'w-32 h-32' : 'h-[72px]'
                    }`}>
                      <img
                        src={sc.image}
                        alt={`${sc.label} 과거 RT 영상`}
                        className="w-full h-full object-cover"
                      />
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-end justify-between gap-2 text-xs">
                        <div className="min-w-0">
                          <div className="font-mono font-semibold text-[#F4F8FB] truncate">{sc.caseId}</div>
                          <div className="text-[11px] text-[#86868B] mt-0.5 truncate">{sc.source.vessel}</div>
                        </div>
                        <div className="text-right shrink-0">
                          <div className="text-[10px] text-[#86868B]">유사도</div>
                          <div className="font-mono text-base leading-none font-bold text-[#9FC6F4]">{sc.similarity.overall}%</div>
                        </div>
                      </div>

                      <div className="text-[11px] text-[#D2D2D7] mt-1.5">
                        기공 · {sc.defect.distribution} · Ø{sc.defect.largestDiameterMm}mm
                      </div>

                      <div className="mt-2 h-0.5 bg-[#161617] overflow-hidden rounded-full" aria-hidden="true">
                        <div className="h-full" style={{ width: `${sc.similarity.overall}%`, backgroundColor: decisionBarColor[decisionColor] }} />
                      </div>

                      <div className="flex items-center justify-between mt-2">
                        <span className={`text-[11px] font-semibold px-1.5 py-0.5 rounded border ${decisionColorClasses[decisionColor]}`}>
                          과거 판정: {sc.historicalResult.decision}
                        </span>
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5 text-[#86868B]" /> : <ChevronDown className="w-3.5 h-3.5 text-[#86868B]" />}
                      </div>

                      {!isExpanded && (
                        <p className="text-[11px] text-[#86868B] mt-2 leading-snug line-clamp-2">{sc.summary}</p>
                      )}
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-[#41626A] grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-x-6 gap-y-4 text-sm">
                      <div className="min-w-0">
                        <div className="text-xs font-semibold text-[#9FC6F4] mb-2 font-mono">결함 특성</div>
                        <div className="space-y-1.5 text-[#D2D2D7]">
                          <div className="flex justify-between gap-2"><span className="shrink-0">형상</span><span className="text-[#F4F8FB] font-medium text-right">{sc.defect.shape}</span></div>
                          <div className="flex justify-between gap-2"><span className="shrink-0">분포</span><span className="text-[#F4F8FB] font-medium text-right">{sc.defect.distribution}</span></div>
                          <div className="flex justify-between gap-2"><span className="shrink-0">최대 직경</span><span className="text-[#F4F8FB] font-medium text-right">{sc.defect.largestDiameterMm} mm</span></div>
                          <div className="flex justify-between gap-2"><span className="shrink-0">평균 직경</span><span className="text-[#F4F8FB] font-medium text-right">{sc.defect.averageDiameterMm} mm</span></div>
                          <div className="flex justify-between gap-2"><span className="shrink-0">기공 수</span><span className="text-[#F4F8FB] font-medium text-right">{sc.defect.poreCount}</span></div>
                          <div className="flex justify-between gap-2"><span className="shrink-0">영향 길이</span><span className="text-[#F4F8FB] font-medium text-right">{sc.defect.affectedLengthMm} mm</span></div>
                          <div className="flex justify-between gap-2"><span className="shrink-0">검사일</span><span className="text-[#F4F8FB] font-medium text-right">{sc.source.inspectionDate}</span></div>
                          <div className="flex justify-between gap-2"><span className="shrink-0">용접부</span><span className="text-[#F4F8FB] font-medium text-right">{sc.source.weldType} · {sc.source.weldZone}</span></div>
                        </div>
                      </div>

                      <div className="min-w-0">
                        <div className="text-xs font-semibold text-[#9FC6F4] mb-2 font-mono">SIMILARITY BREAKDOWN</div>
                        <div className="space-y-2.5">
                          <SimilarityBar label="형상" value={sc.similarity.breakdown.morphology} />
                          <SimilarityBar label="크기" value={sc.similarity.breakdown.size} />
                          <SimilarityBar label="분포" value={sc.similarity.breakdown.distribution} />
                          <SimilarityBar label="위치" value={sc.similarity.breakdown.location} />
                        </div>
                      </div>

                      <div className="min-w-0">
                        <div className="text-xs font-semibold text-[#9FC6F4] mb-2 font-mono">과거 검사 결과</div>
                        <div className="space-y-1.5 text-[#D2D2D7]">
                          <div className="flex justify-between gap-2"><span className="shrink-0">등급</span><span className="text-[#F4F8FB] font-medium text-right">{sc.historicalResult.grade}</span></div>
                          <div className="flex justify-between gap-2"><span className="shrink-0">판정</span><span className="text-[#F4F8FB] font-medium text-right">{sc.historicalResult.decision}</span></div>
                          <div className="text-[#D2D2D7] mt-2 leading-snug">조치: <span className="text-[#F4F8FB]">{sc.historicalResult.inspectorAction}</span></div>
                          {sc.repair.required && (
                            <>
                              <div className="text-[#D2D2D7] leading-snug">보수 방법: <span className="text-[#F4F8FB]">{sc.repair.method}</span></div>
                              <div className="text-[#D2D2D7] leading-snug">재검사: <span className="text-[#F4F8FB]">{sc.repair.reinspection}</span></div>
                            </>
                          )}
                          <div className="text-[#D2D2D7] leading-snug">최종 결과: <span className="text-[#F4F8FB] font-semibold">{sc.repair.finalResult}</span></div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <p className="text-xs text-[#86868B] mt-4 pt-3 border-t border-[#41626A] leading-relaxed shrink-0">
            ※ 본 분석 결과는 검사원의 판정을 지원하기 위한 참고 정보입니다. 최종 합격·불합격 여부는 적용 검사 규격 및 검사원의 검토를 통해 결정됩니다.
          </p>
        </section>
      )}

      {/* ESCALATED MODAL */}
      {escalated && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg p-5 max-w-md w-full shadow-2xl text-sm">
            <div className="flex items-center gap-2.5 text-red-600 mb-3 font-bold text-base">
              <ShieldAlert className="w-5 h-5" />
              <span>책임 검사원 이관 완료</span>
            </div>
            <p className="text-[#333] mb-4 leading-relaxed">
              RT 사진, 기공 위치, 검사자 판단 내역 및 메모가 선임 검사원 검토 패키지로 이관되었습니다.
            </p>
            <button onClick={() => setEscalated(false)} className="w-full min-h-[44px] bg-[#1A1A1A] text-white py-2.5 rounded font-bold">
              확인
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
