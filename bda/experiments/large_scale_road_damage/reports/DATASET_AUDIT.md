# RDD2022 Dataset Audit Report

**Date of Audit:** 2026-11-15  
**Platform:** Paventra Large-Scale Road Damage Analytics  
**Official Source:** CRDDC 2022 (Crowdsensing-based Road Damage Detection Challenge 2022)  
**FigShare Citation:** [https://figshare.com/articles/dataset/RDD2022_-_The_multi-national_Road_Damage_Dataset_released_through_CRDDC_2022/21431547](https://figshare.com/articles/dataset/RDD2022_-_The_multi-national_Road_Damage_Dataset_released_through_CRDDC_2022/21431547)

---

## 1. Storage & Volume Breakdown

| Storage Scope | Files / Entries | Size (Bytes) | Size (MB / GB) |
|---|---|---|---|
| **Compressed CRDDC2022 Archive** | 7 Country Archives | 13,264,172,619 bytes | **12.353 GB** |
| **Extracted India Train Images** | 7,706 images | 519,665,922 bytes | 495.59 MB |
| **Extracted India Test Images** | 1,959 images | 132,775,501 bytes | 126.62 MB |
| **Extracted India XML Annotations**| 7,706 files | 3,275,918 bytes | 3.12 MB |
| **Total Extracted Working Dataset**| **9,665 images** | **655,717,341 bytes** | **625.34 MB** |

> **Scientific Honesty Note on Dataset Size:**  
> The complete archive present in the project repository (`RDD2022_released_through_CRDDC2022.zip`) comprises **13.26 GB** containing road damage datasets across 7 countries (India, Japan, Czech, Norway, United States, China Drone, China Motorbike).  
> The working local extraction deployed for the Indian road damage experiment contains **9,665 total images** (7,706 training + 1,959 test) occupying **625.34 MB** uncompressed.

---

## 2. Annotations & Label Taxonomy Audit

- **Total Pascal VOC XML Files:** 7,706
- **Malformed XML Files:** 0
- **Missing Image/XML Mismatches:** 0
- **Images with Detected Damage:** 3,785 (49.12%)
- **Images without Damage (Clean Pavement / Negative Samples):** 3,921 (50.88%)
- **Total Ground-Truth Annotated Objects:** 8,203
- **Invalid Bounding Boxes:** 0

### Ground-Truth Damage Class Distribution

| Class Code | Damage Description | Object Count | Percentage |
|---|---|---|---|
| **D00** | Longitudinal Crack | 1,555 | 18.96% |
| **D10** | Transverse Crack | 68 | 0.83% |
| **D20** | Alligator Crack (Fatigue) | 2,021 | 24.64% |
| **D40** | Pothole | 3,187 | 38.85% |
| **Other / Unknown** | Miscellaneous | 1,372 | - |
| **Total** | | **8,203** | **100.00%** |

---

## 3. Data Integrity & Quality Verification

- **Image Readability Check:** 500 randomly sampled images across train and test splits were decoded and verified using PIL image integrity headers. Corrupted files found: **0**.
- **Duplicate Detection:** MD5 checksum auditing across 1,000 images found **0** duplicate files.
- **Test Split Labeling Status:** The 1,959 test images in `India/test/images` are unlabelled, which aligns with the CRDDC 2022 competition design where test labels are held by competition organizers. Consequently, supervised evaluation and bounding box metrics use the fully labeled 7,706 image set.
