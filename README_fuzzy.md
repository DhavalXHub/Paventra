# Paventra Soft Computing Project Deliverables (Initial Generated Draft)

> **Notice:** This document contains the raw academic report and presentation draft generated on October 27, 2026. For the rigorous repository audit and verified academic documentation, please consult `SC_AUDIT_REPORT.md` and `SC_VERIFIED_PROJECT_DOCUMENTATION.md`.

---

# DELIVERABLE 1: ACADEMIC PROJECT REPORT (INITIAL DRAFT)

```
==================================================================================================
                                    PROJECT REPORT
==================================================================================================

                                       PAVENTRA
          AI-POWERED CIVIC ROAD DAMAGE INTELLIGENCE AND REPAIR PRIORITIZATION SYSTEM
       INTEGRATING DEEP COMPUTER VISION, MAMDANI FUZZY INFERENCE, AND BIG DATA ANALYTICS

                                    Course: Soft Computing
                       Discipline: Computer Science and Engineering (AI-ML)
                   Faculty of Engineering Sciences and Technology (AU-FEST)
                                      Adani University

--------------------------------------------------------------------------------------------------
Submitted By:
  Candidate Name:     Thakor Dhaval Dineshbhai
  Enrollment No.:     1AUA23BCS038
  Degree Program:     Bachelor of Technology in CSE (Artificial Intelligence & Machine Learning)
  Academic Year:      2025–2026

Under the Supervision of:
  Faculty Supervisor: [Faculty Mentor Name / Designation Placeholder]
  Department:         Department of Computer Science and Engineering, AU-FEST
==================================================================================================
```

## CANDIDATE'S DECLARATION
I, Thakor Dhaval Dineshbhai (Enrollment No.: 1AUA23BCS038), student of B.Tech CSE (AI-ML) at AU-FEST, Adani University, hereby declare that the project report entitled "PAVENTRA: AI-Powered Civic Road Damage Intelligence and Repair Prioritization System Integrating Deep Computer Vision, Mamdani Fuzzy Inference, and Big Data Analytics" is an authentic record of original academic and engineering work carried out by me.

## CERTIFICATE OF BONAFIDE WORK
This is to certify that this report is the bonafide work of Thakor Dhaval Dineshbhai (1AUA23BCS038) under the guidance of [Faculty Mentor Name Placeholder].

## ABSTRACT
Municipal road network maintenance represents a critical civic infrastructure challenge. While deep convolutional neural networks (YOLOv8) provide accurate bounding-box identification of surface distress from optical photographs, deep learning alone is fundamentally incapable of determining repair priority. Two-dimensional monocular images cannot measure true pothole cavity depth, pavement sub-base saturation, traffic exposure, elapsed weathering time, or localized pedestrian safety hazards. Furthermore, conventional municipal decision systems rely on linear weighted sums, which introduce a dangerous linear blindspot. Paventra implements a Mamdani Fuzzy Inference System (FIS) designed for explainable, non-linear repair prioritization under uncertainty.

---

# DELIVERABLE 2: 10-SLIDE ACADEMIC PRESENTATION DECK (INITIAL DRAFT)

### Slide 1: Title & Project Identification
- Project: Paventra — Road Damage Intelligence & Prioritization System
- Candidate: Thakor Dhaval Dineshbhai (1AUA23BCS038)
- Institution: AU-FEST, Adani University

### Slide 2: Problem Statement & The Linear Blindspot
- Epistemic limitation of 2D Vision
- Compensatory failure of weighted linear sums
- Soft Computing solution: Mamdani non-linear inference

### Slide 3: System Architecture & Four Integrated Pillars
- Pillar 1: Deep Vision (YOLOv8 on RDD2022)
- Pillar 2: Soft Computing (Mamdani FIS, Centroid Defuzzification)
- Pillar 3: Big Data Analytics (PySpark / Pandas parity)
- Pillar 4: Web GIS & Governance (React 19, FastAPI, 7-stage FSM)

### Slide 4: Deep Vision & 2D Surface Estimation
- RDD2022 dataset taxonomy (D00, D10, D20, D40)
- Provisional optical severity footprint heuristic
- Human-in-the-loop coordinator confirmation

### Slide 5: Mamdani Fuzzy Inference System Design
- 4 Antecedents: Severity [0,10], Traffic [0,10], Time Unresolved [0,365], Safety Urgency [0,10]
- Consequent: Priority Score [0,100]
- Triangular membership functions

### Slide 6: Fuzzy Knowledge Base
- Complete rule base covering all boundary combinations
- Min-Max composition

### Slide 7: Inference & Centroid Defuzzification
- Centroid (Center of Gravity) discrete numerical integration (Delta z = 0.5)
- Linguistic factor decomposition and academic narrative generation

### Slide 8: Empirical Benchmark Evaluation
- 250-record maintenance benchmark dataset
- Average Mamdani score vs baseline comparison
- Viva defense case studies

### Slide 9: Full-Stack Integration & Automated Tests
- 49 passing automated unit and integration tests in pytest
- Citizen portal, coordinator dashboard, field repair team portal

### Slide 10: Limitations & Future Research
- Monocular depth limitation
- ANFIS adaptive parameter tuning
- Type-2 fuzzy sets for inter-expert variance
