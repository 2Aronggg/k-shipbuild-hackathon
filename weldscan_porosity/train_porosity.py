"""
train_porosity.py
==================
노트북 안에서 직접 학습을 돌리면(Windows + Jupyter) DataLoader 멀티프로세싱
워커가 __main__ 재실행 문제로 hang되거나(workers>0), 억지로 workers=0으로
돌리면 GPU가 데이터를 기다리며 노는(GPU 사용률 30%대) 문제가 생긴다.

이 스크립트는 진짜 .py 엔트리포인트 + `if __name__ == "__main__":` 가드를
갖춰서 workers>0을 안전하게 쓸 수 있게 한 것. 노트북에서 이렇게 실행한다:

    !python train_porosity.py

또는 별도 Anaconda Prompt / cmd에서:

    cd C:\\Users\\user\\weldscan\\weldscan_porosity
    python train_porosity.py

학습이 끝나면 best.pt 경로를 stdout에 출력하고, 노트북의 평가 셀들이
그 경로를 그대로 이어받을 수 있도록 run_dir을 JSON으로도 남긴다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# --- 노트북 0번 셀과 동일한 환경변수. 값이 다르면 여기만 고치면 된다 ---
os.environ.setdefault("WELDSCAN_ROOT", r"C:\Users\user\weldscan\weld_db")
os.environ.setdefault("WELDSCAN_WORK", r"C:\Users\user\weldscan\work")

# Windows에서 torch/ultralytics의 하위 의존성들이 각자 Intel OpenMP 런타임
# (libiomp5md.dll)을 중복 로드해 즉시 크래시하는 흔한 충돌 우회.
# (OMP Error #15) 성능/정확도에 영향 없음 - 단일 프로세스 학습 스크립트라 안전.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

SRC = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC))


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--quick", action="store_true",
        help=(
            "가장 작은 스모크 테스트. 파이프라인이 정상 동작하고 GPU를 제대로 "
            "쓰는지만 확인 (nano 모델, 양성/음성 각 300+300장, 8에폭). "
            "여기서 나오는 mAP/loss 수치는 정확도 판단에 쓰지 말 것."
        ),
    )
    p.add_argument(
        "--demo", action="store_true",
        help=(
            "발표/데모 영상용 실전 학습. 전체 43,068장/60에폭 대신, "
            "양성/음성 균형 잡힌 중간 규모 서브셋(기본 각 4,000+4,000장)으로 "
            "yolov8s-seg를 적은 에폭(기본 25)만 돌려 합리적인 시간 안에 "
            "쓸만한 성능을 얻는다. --n-pos-train 등으로 규모 조절 가능."
        ),
    )
    p.add_argument("--n-pos-train", type=int, default=4000)
    p.add_argument("--n-neg-train", type=int, default=4000)
    p.add_argument("--n-pos-val", type=int, default=600)
    p.add_argument("--n-neg-val", type=int, default=600)
    p.add_argument("--epochs", type=int, default=None,
                   help="에폭 수 직접 지정 (기본: --quick=8, --demo=25, 전체=config 값)")
    args = p.parse_args()
    if args.quick and args.demo:
        p.error("--quick과 --demo는 동시에 쓸 수 없다")
    return args


def main() -> None:
    args = parse_args()
    from ultralytics import YOLO
    from ultralytics import settings as ul_settings

    from porosity import config as cfg
    from porosity import data_prep as D

    cfg.PATHS.ensure()
    ul_settings.update({"datasets_dir": str(cfg.PATHS.yolo_root.parent)})

    T = cfg.TRAIN
    if T.workers == 0:
        T.workers = 4
        print(f"[train_porosity] workers=0 -> {T.workers} 로 상향 "
              f"(별도 프로세스라 안전함)")

    # Ultralytics의 fraction=N은 무작위 샘플링이 아니라
    # sorted(im_files)[:count] 로 앞부분만 자른다 (실제 소스 확인).
    # 우리 파일명이 "RT_ST_00_*"(정상)/"RT_ST_02_*"(기공)로 클래스별로
    # 뭉쳐 있어서 fraction을 쓰면 정상 이미지로만 채워진 서브셋이 뽑히는
    # 사고가 난다 (실제 재현됨: 전 에폭 loss가 0으로 찍힘).
    # --quick/--demo 둘 다 fraction 대신 균형 잡힌 별도 서브셋을 만든다.
    if args.quick:
        T.model = "yolov8n-seg.pt"
        T.epochs = args.epochs or 8
        T.patience = max(3, T.epochs // 2)
        data_yaml = D.build_quick_subset(
            cfg.PATHS, variant="quick",
            n_pos_train=300, n_neg_train=300, n_pos_val=60, n_neg_val=60,
        )
        print(f"[train_porosity] QUICK 모드: model={T.model} epochs={T.epochs} "
              f"data={data_yaml} (스모크 테스트 - 정확도는 참고 금지)")
    elif args.demo:
        # 기본 모델은 config의 yolov8s-seg 그대로 사용 - 데모 영상엔
        # nano보다 실제 타겟 모델을 쓰는 게 신뢰도 면에서 낫다.
        T.epochs = args.epochs or 25
        T.patience = max(5, T.epochs // 3)
        data_yaml = D.build_quick_subset(
            cfg.PATHS, variant="demo",
            n_pos_train=args.n_pos_train, n_neg_train=args.n_neg_train,
            n_pos_val=args.n_pos_val, n_neg_val=args.n_neg_val,
        )
        print(f"[train_porosity] DEMO 모드: model={T.model} epochs={T.epochs} "
              f"data={data_yaml}")
    else:
        data_yaml = cfg.PATHS.dataset_yaml
        if args.epochs is not None:
            T.epochs = args.epochs

    print(f"[train_porosity] model={T.model} imgsz={T.imgsz} batch={T.batch} "
          f"workers={T.workers} device={T.device} epochs={T.epochs} "
          f"data={data_yaml}")

    model = YOLO(T.model)
    run_name = T.project_name + ("_quick" if args.quick else "_demo" if args.demo else "")
    results = model.train(
        data=str(data_yaml),
        imgsz=T.imgsz, epochs=T.epochs, batch=T.batch, device=T.device,
        workers=T.workers, optimizer=T.optimizer, patience=T.patience,
        cos_lr=T.cos_lr, amp=T.amp, seed=T.seed, deterministic=True,
        project=str(cfg.PATHS.runs_dir), name=run_name, exist_ok=True,
        hsv_h=T.hsv_h, hsv_s=T.hsv_s, hsv_v=T.hsv_v,
        degrees=T.degrees, translate=T.translate, scale=T.scale,
        shear=T.shear, perspective=T.perspective,
        flipud=T.flipud, fliplr=T.fliplr,
        mosaic=T.mosaic, close_mosaic=T.close_mosaic,
        mixup=T.mixup, copy_paste=T.copy_paste,
        overlap_mask=T.overlap_mask, mask_ratio=T.mask_ratio,
        plots=True, val=True,
    )

    run_dir = Path(results.save_dir)
    best_pt = run_dir / "weights" / "best.pt"
    print("[train_porosity] best:", best_pt)

    # 노트북이 이어받을 수 있도록 실행 결과를 파일로도 남긴다.
    handoff = cfg.PATHS.work_root / (
        "last_train_run_quick.json" if args.quick else
        "last_train_run_demo.json" if args.demo else
        "last_train_run.json"
    )
    handoff.write_text(json.dumps({
        "run_dir": str(run_dir), "best_pt": str(best_pt),
        "workers_used": T.workers, "quick": args.quick, "demo": args.demo,
        "data_yaml": str(data_yaml),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[train_porosity] handoff written:", handoff)


if __name__ == "__main__":
    main()
