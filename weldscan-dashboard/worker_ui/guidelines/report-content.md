# Report Content - Tablet-First Interactive RT Weld Inspection Workspace

## Project Identity

```
Report title: Shipyard RT Weld Inspection Field Workspace
Subtitle: NDT Field Inspection & AI-Assisted Defect Diagnostics
Author / organization: HD Hyundai Heavy Industries / NDT Field Division
Date / period covered: 2026-09-10 14:28 UTC
Data source(s): On-site RT Digital Detector Array (DDA) #RT-409, AI Defect Model v3.4 (ISO 5817 Level B)
Version or edition: Field Tablet Edition v2.1
```

## Purpose and Audience

```
What is this workspace for?
An interactive field workspace for tablet-equipped shipyard NDT field inspectors to review RT (Radiographic Testing) weld film scans, verify AI-detected defect regions (porosity, lack of fusion, slag inclusion, cracks), compare with historical similar cases, attach field annotations/pins, and take immediate disposition actions (Confirm Result, Recheck, Retake Image, Escalate to Senior Inspector).

Who will use it?
Shipyard Level-II & Level-III NDT Field Inspectors operating ruggedized tablets in dry docks and block assembly shops.

What should the user accomplish?
Rapidly validate weld soundness, confirm or correct AI findings, compare historical remedies (e.g., carbon arc gouging vs grinding), and save or escalate complete inspection packages with zero data loss.
```

## Inspection Context (Compact Header)

```
- Worker: Kim Min-soo (NDT Level-II Inspector, 8 Yrs Exp)
- Vessel: Hull No. H-3419 (174k LNG Carrier "Arctic Horizon")
- Inspection Area: Block 204 / Inner Bottom Longi. Joint #W-18B (500mm-800mm)
- Inspection ID: RT-2026-0910-4082
- Timestamp: 2026-09-10 14:28:05
- Welding Process: FCAW (Flux Cored Arc Welding) 3G Position
```

## Current Result Summary

```
- Overall Status: High Risk (Action Required)
- Suspected Defect Type: Lack of Fusion (LoF) + Cluster Porosity
- Detected Region Count: 3 Regions (Defect 01, Defect 02, Defect 03)
- Max Risk Level: Level B Defect (ISO 5817 Non-compliant, Depth > 2.5mm)
- AI Summary: AI flagged 3 anomaly regions. Primary concern: Defect 01 (Lack of Fusion near root pass at 620mm mark, length 18mm). Immediate repair or senior escalation recommended.
```

## Defect Markers & Overlays Data

```
Defect 01:
  - Label: Defect 01
  - Type: Lack of Fusion (LoF)
  - Location: 622 mm mark (Root Pass)
  - Dimensions: Length 18.4 mm, Depth 2.8 mm
  - Risk Level: High Risk (Critical)
  - AI Confidence: 94.2%
  - Standard Threshold: ISO 5817 Level B (Limit: 0 mm allowed for LoF)
  - AI Recommendation: Carbon Arc Gouging & Re-weld

Defect 02:
  - Label: Defect 02
  - Type: Cluster Porosity
  - Location: 710 mm mark (Fill Pass)
  - Dimensions: Area 12.2 mm², Pore count 6
  - Risk Level: Needs Review
  - AI Confidence: 81.5%
  - Standard Threshold: ISO 5817 Level C (Limit: Max pore diameter 3mm)
  - AI Recommendation: Grind out fill layer and re-pass

Defect 03:
  - Label: Defect 03
  - Type: Slag Inclusion
  - Location: 545 mm mark (Cap Pass)
  - Dimensions: Length 6.1 mm, Width 1.2 mm
  - Risk Level: Normal / Low Risk (Acceptable under Level C)
  - AI Confidence: 88.0%
  - Standard Threshold: ISO 5817 Level C (Within acceptable limits)
  - AI Recommendation: Monitor in future inspection
```

## Historical Similar Cases Data (5 Cases)

```
Case 1:
  - Case ID: RT-2026-0412-8821
  - Vessel: Hull H-3412 (VLCC)
  - Joint: Block 108 / Shell Plating #W-04
  - Similarity Score: 94%
  - Defect Type: Lack of Fusion (Root Pass)
  - Historical Final Decision: Escalated & Repaired
  - Action Taken: Carbon Arc Gouging 25mm + Back Weld + UT Recheck
  - Status Icon: Escalated / Repaired (High Risk)
  - Note: Root gap was tight (1.5mm), causing incomplete root penetration.

Case 2:
  - Case ID: RT-2025-1104-3019
  - Vessel: Hull H-3398 (174k LNG)
  - Joint: Block 204 / Inner Bottom #W-12A
  - Similarity Score: 89%
  - Defect Type: Lack of Sidewall Fusion
  - Historical Final Decision: Confirmed Defect / Repaired
  - Action Taken: Grind & Reweld (Local 30mm)
  - Status Icon: Confirmed / Repaired

Case 3:
  - Case ID: RT-2026-0118-1290
  - Vessel: Hull H-3401 (Container 15,000 TEU)
  - Joint: Block 302 / Deck Girder #W-08
  - Similarity Score: 85%
  - Defect Type: Heavy Slag + Porosity
  - Historical Final Decision: Recheck Requested
  - Action Taken: Surface Grinding + Secondary UT Inspection -> Pass
  - Status Icon: Rechecked / Passed

Case 4:
  - Case ID: RT-2025-0822-9041
  - Vessel: Hull H-3382 (LPG Carrier)
  - Joint: Block 115 / Tank Top #W-22
  - Similarity Score: 78%
  - Defect Type: Cluster Porosity
  - Historical Final Decision: Accepted (Within Threshold)
  - Action Taken: Verified against ISO 5817 Level C -> Accepted without repair
  - Status Icon: Passed / Acceptable

Case 5:
  - Case ID: RT-2026-0701-5502
  - Vessel: Hull H-3415 (LNG Carrier)
  - Joint: Block 204 / Inner Bottom #W-15B
  - Similarity Score: 72%
  - Defect Type: Incomplete Penetration
  - Historical Final Decision: Retake Image
  - Action Taken: RT Film density was poor (1.2 H&D) -> Re-exposed at 220kV
  - Status Icon: Retaken / Rescanned
```

## Standard & Regulatory Basis (Collapsed View)

```
Applicable Standards:
- ISO 5817:2023 - Welding — Fusion-welded joints in steel, nickel, titanium and their alloys — Quality levels for imperfections
- AWS D1.1/D1.1M:2020 - Structural Welding Code — Steel
- ClassNK / DNV Rules for Classification of Ships - Part 2 Materials and Welding

Level B Acceptance Criteria for Lack of Fusion (Imperfection 100 / 401):
- Imperfection 4011 (Lack of side fusion): Not permitted (Quality Level B)
- Imperfection 4012 (Lack of inter-run fusion): Not permitted (Quality Level B)
- Imperfection 4013 (Lack of root fusion): Not permitted (Quality Level B)

Calibration & Equipment:
- X-Ray Generator: Seifert ERESAS 200kV / DDA Flat Panel Detector
- Pixel Pitch: 100 μm, IQI Wire Indicator: W10 (EN 462-1) visible
```

## Action Decisions & Persistent Controls

```
Actions:
1. Confirm Result (Save field verification)
2. Recheck (Request local UT/MT verification)
3. Retake Image (Re-expose film/DDA due to quality or contrast issues)
4. Escalate to Senior Inspector (Prominent Persistent Action - packages image, defects, worker notes, AI findings, and similar cases for Level-III review)
```
