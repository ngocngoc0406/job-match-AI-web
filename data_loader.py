# -*- coding: utf-8 -*-
"""Data loading functions for Excel and PDF"""

import os
import glob
import pandas as pd
import numpy as np

try:
    import fitz
    HAS_FITZ = True
except:
    HAS_FITZ = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except:
    HAS_PDFPLUMBER = False

try:
    import pytesseract
    HAS_OCR = True
except:
    HAS_OCR = False

from config import COL, OCR_DPI, OCR_LANG, FORCE_OCR

print(f"HAS_FITZ: {HAS_FITZ}")
print(f"HAS_PDFPLUMBER: {HAS_PDFPLUMBER}")
print(f"HAS_OCR: {HAS_OCR}")

def load_excel_file(file_path=None):
    """Load job data from Excel file"""
    if file_path is None:
        cand = []
        cand += glob.glob("*.xlsx")
        cand += glob.glob("/mnt/data/*.xlsx")
        cand += glob.glob("/kaggle/working/*.xlsx")
        if not cand:
            raise FileNotFoundError("No .xlsx file found. Place file in working directory.")
        file_path = cand[0]

    df_raw = pd.read_excel(file_path, engine='openpyxl').fillna("")
    df_raw.columns = [str(c).strip() for c in df_raw.columns]
    
    missing = [v for v in COL.values() if v not in df_raw.columns]
    if missing:
        raise ValueError(f"Missing columns in job file: {missing}")

    df = pd.DataFrame({
        "job_id": df_raw[COL["job_id"]].astype(str),
        "job_url": df_raw[COL["job_url"]].astype(str),
        "job_title": df_raw[COL["job_title"]].astype(str),
        "company": df_raw[COL["company"]].astype(str),
        "location": df_raw[COL["location"]].astype(str),
        "location_detail": df_raw[COL["location_detail"]].astype(str),
        "requirements": df_raw[COL["requirements"]].astype(str),
        "salary": df_raw[COL["salary"]].astype(str),
        "experience": df_raw[COL["experience"]].astype(str),
        "job_desc": df_raw[COL["job_desc"]].astype(str),
        "job_type": df_raw[COL["job_type"]].astype(str),
        "benefit": df_raw[COL["benefit"]].astype(str),
    }).reset_index(drop=True)

    return file_path, df

def extract_text_pymupdf(pdf_path, verbose=True):
    """Extract text from PDF using PyMuPDF"""
    if not HAS_FITZ:
        if verbose:
            print("PyMuPDF (fitz) not available")
        return ""

    try:
        doc = fitz.open(pdf_path)
        all_text = []

        for page_num, page in enumerate(doc):
            text1 = page.get_text("text")
            blocks = page.get_text("blocks")
            text3 = "\n".join([b[4] for b in blocks if b[6] == 0])

            page_texts = [text1, text3]
            best_text = max(page_texts, key=len) if page_texts else ""

            if best_text.strip():
                all_text.append(f"--- Page {page_num + 1} ---\n{best_text}")

        doc.close()
        result = "\n\n".join(all_text).strip()
        if verbose:
            print(f"PyMuPDF extracted {len(result)} characters from {len(doc)} pages")
        return result
    except Exception as e:
        if verbose:
            print(f"PyMuPDF error: {e}")
        return ""

def extract_text_pdfplumber(pdf_path, verbose=True):
    """Extract text from PDF using pdfplumber"""
    if not HAS_PDFPLUMBER:
        if verbose:
            print("pdfplumber not available")
        return ""

    try:
        all_text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                tables = page.extract_tables()
                table_text = ""
                for table in tables:
                    for row in table:
                        row_text = " | ".join([str(cell) if cell else "" for cell in row])
                        table_text += row_text + "\n"

                combined = text + "\n" + table_text
                if combined.strip():
                    all_text.append(combined)

        result = "\n\n".join(all_text).strip()
        if verbose:
            print(f"pdfplumber extracted {len(result)} characters")
        return result
    except Exception as e:
        if verbose:
            print(f"pdfplumber error: {e}")
        return ""

def ocr_pdf_all_pages(pdf_path, dpi=300, lang="vie+eng", verbose=True):
    """OCR all pages of PDF"""
    if not HAS_PDFPLUMBER or not HAS_OCR:
        if verbose:
            print("OCR requires pdfplumber and pytesseract")
        return ""

    out = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            if verbose:
                print(f"OCR scanning {total_pages} pages at {dpi} DPI...")

            for i, page in enumerate(pdf.pages):
                img = page.to_image(resolution=dpi).original
                pil = img.convert("RGB")

                try:
                    t = pytesseract.image_to_string(pil, lang=lang)
                except:
                    try:
                        t = pytesseract.image_to_string(pil, lang="eng")
                    except:
                        t = ""

                if t.strip():
                    out.append(f"--- OCR Page {i + 1} ---\n{t}")

                if verbose and (i + 1) % 5 == 0:
                    print(f"  Processed {i + 1}/{total_pages} pages...")

    except Exception as e:
        if verbose:
            print(f"OCR error: {e}")

    result = "\n\n".join(out).strip()
    if verbose:
        print(f"OCR extracted {len(result)} characters")
    return result

def extract_all_text_from_pdf(pdf_path, verbose=True):
    """Master function to extract text from PDF"""
    if verbose:
        print(f"\nExtracting text from: {pdf_path}")

    results = {}
    results['pymupdf'] = extract_text_pymupdf(pdf_path, verbose=verbose)
    results['pdfplumber'] = extract_text_pdfplumber(pdf_path, verbose=verbose)

    text_results = [results['pymupdf'], results['pdfplumber']]
    best_text = max(text_results, key=len) if text_results else ""

    MIN_TEXT_THRESHOLD = 100

    if len(best_text) < MIN_TEXT_THRESHOLD:
        if verbose:
            print(f"Text extraction got only {len(best_text)} chars. Trying OCR...")
        results['ocr'] = ocr_pdf_all_pages(pdf_path, dpi=OCR_DPI, lang=OCR_LANG, verbose=verbose)

        if len(results['ocr']) > len(best_text):
            best_text = results['ocr']

    if verbose:
        print(f"\nFINAL: Extracted {len(best_text)} characters total")
        print(f"   Methods tried: PyMuPDF ({len(results.get('pymupdf', ''))}), "
              f"pdfplumber ({len(results.get('pdfplumber', ''))}), "
              f"OCR ({len(results.get('ocr', ''))})")

    return best_text

def load_pdf_file(file_path=None):
    """Load CV from PDF file"""
    if file_path is None:
        cand = []
        cand += glob.glob("*.pdf")
        cand += glob.glob("/mnt/data/*.pdf")
        cand += glob.glob("/kaggle/working/*.pdf")
        if not cand:
            raise FileNotFoundError("No CV .pdf file found. Place file in working directory.")
        file_path = cand[0]

    return file_path
