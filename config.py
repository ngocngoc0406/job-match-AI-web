# -*- coding: utf-8 -*-
"""Configuration settings for NCKH job matching system"""

# USER–JOB MATCHING
TOPK_USER_JOB = 3
W_SKILL = 0.78
W_LOC = 0.22

SIM_THRESHOLD = 0.45
CANDIDATES_TOP = 15
TOPK_SIMILAR = 3

# DRAW
FOCUS_ONLY = True
MAX_SKILLS_DRAW = 10
EDGE_LABEL_MODE = "important"
SHOW_EDGE_SCORES = True
CENTER_MODE = "user"
CENTER_JOB_ID = None
RANDOM_SEED = 42

# CV PDF OCR settings
OCR_LANG = "vie+eng"
OCR_DPI = 300
OCR_MAX_PAGES = 99
FORCE_OCR = True

# Prob skill
MIN_KEEP_PROB = 0.08

# SKILL LEXICON
SKILL_LEXICON = {
    "Python":        ["python", "py", "python3", "python 3"],
    "Java":          ["java", "spring boot", "hibernate"],
    "JavaScript":    ["javascript", "js", "ecmascript"],
    "TypeScript":    ["typescript", "ts"],
    "React":         ["react", "reactjs", "react.js"],
    "NodeJS":        ["nodejs", "node.js", "node", "expressjs"],
    "SQL":           ["sql", "mysql", "postgresql", "postgres", "mssql", "sql server", "sqlite"],
    "Docker":        ["docker", "containerization"],
    "Kubernetes":    ["kubernetes", "k8s"],
    "AWS":           ["aws", "amazon web services", "ec2", "s3", "lambda"],
    "Azure":         ["azure", "microsoft azure"],
    "GCP":           ["gcp", "google cloud platform"],
    "Git":           ["git", "github", "gitlab", "bitbucket"],
    "Excel":         ["excel", "pivot", "vlookup", "power query", "spreadsheet"],
    "Word":          ["word", "ms word", "microsoft word"],
    "PowerPoint":    ["powerpoint", "ms powerpoint", "microsoft powerpoint", "ppt"],
    "Outlook":       ["outlook", "ms outlook", "microsoft outlook"],
    "Power BI":      ["power bi", "pbi", "powerbi"],
    "Tableau":       ["tableau"],
    "SAP":           ["sap", "sap erp", "sap s4"],
    "MISA":          ["misa", "phan mem misa"],
    "QuickBooks":    ["quickbooks", "qb"],
    "VAT":           ["vat", "gtgt", "gia tri gia tang"],
    "Invoice":       ["hoa don", "invoice", "e-invoice", "einvoice", "e invoice"],
    "Tax":           ["thue", "tax", "tndn", "tncn"],
    "Audit":         ["kiem toan", "audit", "auditing"],
    "AR/AP":         ["cong no", "ar/ap", "accounts payable", "accounts receivable"],
    "Bookkeeping":   ["so sach", "bookkeeping", "ghi so"],
    "Financial Reporting": ["bao cao tai chinh", "financial reporting", "financial statement", "financial statements", "bctc"],
    "Tax Finalization": ["quyet toan", "tax finalization", "quyet toan thue"],
    "VAS":           ["vas", "vietnamese accounting standards", "chuan muc ke toan viet nam"],
    "IFRS":          ["ifrs", "international financial reporting standards"],
    "ACCA":          ["acca"],
    "CPA":           ["cpa", "cpa vietnam"],
    "Cost Accounting": ["ke toan gia thanh", "cost accounting", "gia thanh"],
    "Payroll":       ["luong", "payroll", "tinh luong", "bhxh"],
    "Cash Flow":     ["dong tien", "cash flow", "luu chuyen tien te"],
    "Communication": ["giao tiep", "communication", "thuyet trinh", "presentation"],
    "Teamwork":      ["teamwork", "lam viec nhom", "collaboration"],
    "Leadership":    ["leadership", "lanh dao", "quan ly", "management"],
    "Problem Solving": ["giai quyet van de", "problem solving"],
    "English":       ["english", "tieng anh", "ielts", "toeic"],
    "PHP":           ["php", "laravel", "wordpress"],
    "C#":            ["c#", ".net", "dotnet", "asp.net"],
    "C++":           ["c++", "cpp"],
    "Go":            ["go", "golang"],
    "Swift":         ["swift", "ios"],
    "Kotlin":        ["kotlin", "android"],
    "Flutter":       ["flutter", "dart"],
    "Django":        ["django", "fastapi", "flask"],
    "Vue":           ["vue", "vuejs"],
    "Angular":       ["angular"],
    "DevOps":        ["devops", "jenkins", "ci/cd", "terraform", "ansible"],
    "Machine Learning": ["machine learning", "ml", "ai", "deep learning", "nlp", "tensorflow", "pytorch"],
    "Big Data":      ["big data", "hadoop", "spark", "airflow"],
    "SEO":           ["seo", "sem", "google ads", "facebook ads", "digital marketing"],
    "UI/UX":         ["ui/ux", "figma", "sketch", "adobe xd"],
    "Product Management": ["product management", "pm", "product manager"],
    "Business Analysis": ["business analysis", "ba", "requirement gathering"],
    "Logistics": ["logistics", "hau can", "xuat nhap khau", "import", "export", "incoterms"],
    "Supply Chain": ["supply chain", "chuoi cung ung", "inventory", "purchasing", "mua hang"],
    "Customs": ["customs", "hai quan", "khai bao hai quan", "thong quan"],
    "Pedagogy": ["pedagogy", "su pham", "giang day", "teaching skills"],
    "Curriculum": ["curriculum", "giao trinh", "lesson plan", "giao an"],
    "Legal Drafting": ["phap che", "soan thao van ban", "contract drafting", "legal research"],
    "Graphic Design": ["graphic design", "thiet ke do hoa", "photoshop", "illustrator", "indesign", "canva"],
    "Video Editing": ["video editing", "dung phim", "premiere", "after effects", "capcut", "davinci"],
    "Branding": ["branding", "thuong hieu", "nhan dien thuong hieu"],
    "Marketplace": ["shopee", "lazada", "tiki", "tiktok shop", "e-commerce marketplace"],
    "Customer Support": ["customer support", "cskh", "cham soc khach hang", "telesales"],
    "Recruitment": ["recruitment", "tuyen dung", "headhunt", "ta", "talent acquisition"],
    "Event Planning": ["event planning", "to chuc su kien", "event organization"],
    "AutoCAD": ["autocad", "cad", "thiet ke ky thuat"],
    "SolidWorks": ["solidworks", "mechanical design", "thiet ke co khi"],
    "PLC": ["plc", "automation", "tu dong hoa"],
    "Engineering": ["mechanical engineering", "electrical engineering", "civil engineering", "ky thuat"],
    "HVAC": ["hvac", "he thong lanh", "air conditioning"],
    "Credit Analysis": ["credit analysis", "phan tich tin dung", "tham dinh", "loan processing"],
    "Securities": ["securities", "chung khoan", "stock market", "investment"],
    "Risk Management": ["risk management", "quan tri rui ro", "compliance risk"],
    "ISO Standards": ["iso 9001", "iso 14001", "iso 45001", "shql", "tieu chuan iso"],
    "Lean Manufacturing": ["lean", "six sigma", "kaizen", "5s", "production optimization"],
    "Quality Control": ["quality control", "qc", "qa", "kiem-tra-chat-luong"],
    "Property Management": ["property management", "quan ly bat dong san", "toa nha"],
    "Real Estate Valuation": ["real estate valuation", "dinh gia bat dong san", "tham dinh gia"],
    "Land Law": ["land law", "luat dat dai", "phap ly bat dong san"],
    "Chinese": ["chinese", "tieng trung", "hsk"],
    "Japanese": ["japanese", "tieng nhat", "jlpt", "n1", "n2", "n3"],
    "Korean": ["korean", "tieng han", "topik"],
    "French": ["french", "tieng phap", "delf"],
    "German": ["german", "tieng duc"],
    "B2B Sales": ["b2b", "business to business", "ban hang doanh nghiep"],
    "B2C Sales": ["b2c", "retail sales", "ban le"],
    "Kpi Management": ["kpi", "okr", "performance management"],
    "Patient Care": ["cham soc benh nhan", "patient care", "dieu duong", "nursing care"],
    "Vital Signs": ["dau hieu sinh ton", "vital signs", "huyet ap", "nhiet do", "mach"],
    "Wound Care": ["cham soc vet thuong", "wound care", "thay bang", "cat chi"],
    "BLS/ACLS": ["bls", "acls", "cap cuu nguon tuan hoan", "life support"],
    "First Aid": ["so cuu", "first aid", "cap cuu ban dau"],
    "Diagnostics": ["chan doan", "diagnostics", "can lam sang"],
    "Pharmacology": ["duoc ly", "pharmacology", "thuoc", "medical prescription"],
    "Surgery": ["phau thuat", "surgery", "ngoai khoa", "phong mo"],
    "Internal Medicine": ["noi khoa", "internal medicine"],
    "Pediatrics": ["nhi khoa", "pediatrics"],
    "EHR/EMR": ["ehr", "emr", "benh an dien tu", "medical records"],
    "Infection Control": ["kiem soat nhiem khuan", "infection control"],
    "Medical Ethics": ["y duc", "medical ethics"],
    "Generative AI": ["generative ai", "genai", "prompt engineering", "llm", "rag"],
    "Cybersecurity": ["cybersecurity", "an ninh mang", "pentest", "hacking", "grc", "siem"],
    "BIM": ["bim", "revit", "quantity surveying", "structural analysis"],
    "Avionics": ["avionics", "aviation management", "flight safety", "airworthiness"],
    "Naval Engineering": ["naval engineering", "navigation", "marine survey", "shipbuilding"],
    "Dyeing": ["dyeing", "nhuom", "textile chemistry", "fabric testing"],
    "ESG": ["esg", "sustainability", "phat trien ben vung", "corporate social responsibility"],
    "Actuarial": ["actuarial", "dinh phi bao hiem", "mathematical finance"],
    # ===== EXPANDED MEDICAL & NURSING =====

"Patient Monitoring": [
    "patient monitoring", "theo doi benh nhan", "monitoring", "continuous monitoring"
],

"Clinical Skills": [
    "clinical skills", "ky nang lam sang", "lam sang", "clinical practice"
],

"Medication Administration": [
    "medication administration", "administer drugs", "cap phat thuoc", "cho thuoc"
],

"IV Therapy": [
    "iv therapy", "truyen dich", "intravenous", "iv infusion"
],

"Injection Skills": [
    "tiem", "injection", "intramuscular", "subcutaneous", "tiem bap", "tiem duoi da"
],

"Emergency Care": [
    "emergency care", "cap cuu", "emergency response", "xu ly cap cuu"
],

"Triage": [
    "triage", "phan loai benh nhan", "prioritize patients"
],

"ICU Care": [
    "icu", "intensive care", "cham soc hoi suc", "critical care"
],

"Surgical Assistance": [
    "surgical assistance", "ho tro phau thuat", "operating room support"
],

"Postoperative Care": [
    "postoperative care", "cham soc sau phau thuat", "hau phau"
],

"Preoperative Care": [
    "preoperative care", "cham soc truoc phau thuat"
],

"Geriatric Care": [
    "geriatric care", "cham soc nguoi cao tuoi", "elderly care"
],

"Home Care": [
    "home care", "cham soc tai nha", "home nursing"
],

"Rehabilitation": [
    "rehabilitation", "phuc hoi chuc nang", "rehab"
],

"Mental Health Care": [
    "mental health", "tam ly", "psychiatric care", "suc khoe tam than"
],

"Pain Management": [
    "pain management", "quan ly dau", "pain control"
],

"Nutrition Care": [
    "nutrition care", "dinh duong benh nhan", "feeding care"
],

"Patient Education": [
    "patient education", "tu van benh nhan", "health education"
],

"Health Assessment": [
    "health assessment", "danh gia suc khoe", "initial assessment"
],

"Care Planning": [
    "care planning", "lap ke hoach cham soc", "nursing plan"
],

"Documentation": [
    "medical documentation", "ghi chep benh an", "nursing documentation"
],

"Hospital Workflow": [
    "hospital workflow", "quy trinh benh vien", "clinical workflow"
],

"Sterilization": [
    "sterilization", "tiet trung", "vo trung"
],

"Patient Safety": [
    "patient safety", "an toan benh nhan"
],

"Bedside Care": [
    "bedside care", "cham soc tai giuong"
],

"Specimen Collection": [
    "lay mau", "specimen collection", "blood sample", "urine test"
],

"Medical Equipment": [
    "medical equipment", "thiet bi y te", "monitor", "ventilator"
],

"Ventilator Support": [
    "ventilator", "tho may", "respiratory support"
],

"Dialysis": [
    "dialysis", "loc than", "hemodialysis"
],

"Obstetric Care": [
    "obstetric care", "san khoa", "cham soc thai san"
],

"Midwifery": [
    "midwife", "ho sinh", "do de"
],

"Neonatal Care": [
    "neonatal care", "so sinh", "newborn care"
],

"Vaccination": [
    "vaccination", "tiem chung", "immunization"
],

"Infection Prevention": [
    "infection prevention", "phong ngua nhiem trung"
],

"Clinical Procedures": [
    "clinical procedures", "thu thuat y khoa"
],

"Electronic Health Records": [
    "electronic health records", "ehr", "benh an dien tu"
],

"Hospital Information System": [
    "his", "hospital information system", "phan mem benh vien"
],
"Data Analysis": [
    "data analysis", "phan tich du lieu", "data analytics", "data visualization"
],

"Project Management": [
    "project management", "quan ly du an", "scrum", "agile"
],

"Software Engineering": [
    "software engineering", "lap trinh", "coding", "system design"
],

"Cloud Computing": [
    "cloud computing", "cloud", "saas", "iaas", "paas"
],

"Testing": [
    "testing", "unit test", "integration test", "uat"
],
}

CORE_SKILLS_CANON = {
    "Excel", "Tax", "VAT", "Invoice", "Financial Reporting", "Audit", "SAP", "MISA", 
    "AR/AP", "Bookkeeping", "IFRS", "VAS", "ACCA", "CPA", "English", "Communication",
    "Project Management", "Business Analysis", "Software Engineering", "Data Analysis",
    "ISO Standards", "Quality Control", "Risk Management", "AutoCAD", "Japanese", "Chinese",
    "Generative AI", "Cybersecurity", "ESG", "PMP"
}

# LOCATION
VN_CITY_ALIASES = {
    "tp hcm": "Ho Chi Minh City", "tphcm": "Ho Chi Minh City", "hcm": "Ho Chi Minh City", "sai gon": "Ho Chi Minh City", "ho chi minh": "Ho Chi Minh City",
    "ha noi": "Ha Noi", "hanoi": "Ha Noi",
    "da nang": "Da Nang", "danang": "Da Nang",
    "can tho": "Can Tho", "cantho": "Can Tho",
    "hai phong": "Hai Phong", "haiphong": "Hai Phong",
    "an giang": "An Giang", "ba ria vung tau": "Ba Ria - Vung Tau", "vung tau": "Ba Ria - Vung Tau", "vungtau": "Ba Ria - Vung Tau",
    "bac kan": "Bac Kan", "backan": "Bac Kan", "bac lieu": "Bac Lieu", "baclieu": "Bac Lieu",
    "bac ninh": "Bac Ninh", "bacninh": "Bac Ninh", "ben tre": "Ben Tre", "bentre": "Ben Tre",
    "binh dinh": "Binh Dinh", "binhdinh": "Binh Dinh", "qui nhon": "Binh Dinh", "quynhon": "Binh Dinh",
    "binh duong": "Binh Duong", "binhduong": "Binh Duong", "binh phuoc": "Binh Phuoc", "binhphuoc": "Binh Phuoc",
    "binh thuan": "Binh Thuan", "binhthuan": "Binh Thuan", "ca mau": "Ca Mau", "camau": "Ca Mau",
    "cao bang": "Cao Bang", "caobang": "Cao Bang", "dak lak": "Dak Lak", "daklak": "Dak Lak", "buon ma thuot": "Dak Lak", "bmt": "Dak Lak",
    "dak nong": "Dak Nong", "daknong": "Dak Nong", "dien bien": "Dien Bien", "dienbien": "Dien Bien",
    "dong nai": "Dong Nai", "dongnai": "Dong Nai", "dong thap": "Dong Thap", "dongthap": "Dong Thap",
    "gia lai": "Gia Lai", "gialai": "Gia Lai", "pleiku": "Gia Lai", "ha giang": "Ha Giang", "hagiang": "Ha Giang",
    "ha nam": "Ha Nam", "hanam": "Ha Nam", "ha tinh": "Ha Tinh", "hatinh": "Ha Tinh",
    "hai duong": "Hai Duong", "haiduong": "Hai Duong", "hau giang": "Hau Giang", "haugiang": "Hau Giang",
    "hoa binh": "Hoa Binh", "hoabinh": "Hoa Binh", "hung yen": "Hung Yen", "hungyen": "Hung Yen",
    "khanh hoa": "Khanh Hoa", "nha trang": "Khanh Hoa", "nhatrang": "Khanh Hoa", "kien giang": "Kien Giang", "kiengiang": "Kien Giang", "rach gia": "Kien Giang",
    "kon tum": "Kon Tum", "kontum": "Kon Tum", "lai chau": "Lai Chau", "laichau": "Lai Chau",
    "lam dong": "Lam Dong", "da lat": "Lam Dong", "dalat": "Lam Dong", "lang son": "Lang Son", "langson": "Lang Son",
    "lao cai": "Lao Cai", "laocai": "Lao Cai", "long an": "Long An", "longan": "Long An",
    "nam dinh": "Nam Dinh", "namdinh": "Nam Dinh", "nghe an": "Nghe An", "nghean": "Nghe An", "vinh": "Nghe An",
    "ninh binh": "Ninh Binh", "ninhbinh": "Ninh Binh", "ninh thuan": "Ninh Thuan", "ninhthuan": "Ninh Thuan",
    "phu tho": "Phu Tho", "phutho": "Phu Tho", "viet tri": "Phu Tho", "viettri": "Phu Tho",
    "quang binh": "Quang Binh", "quangbinh": "Quang Binh", "quang nam": "Quang Nam", "quangnam": "Quang Nam", "tam ky": "Quang Nam",
    "quang ngai": "Quang Ngai", "quangngai": "Quang Ngai", "quang ninh": "Quang Ninh", "quangninh": "Quang Ninh", "ha long": "Quang Ninh", "halong": "Quang Ninh",
    "quang tri": "Quang Tri", "quangtri": "Quang Tri", "soc trang": "Soc Trang", "soctrang": "Soc Trang",
    "son la": "Son La", "sonla": "Son La", "tay ninh": "Tay Ninh", "tayninh": "Tay Ninh",
    "thai binh": "Thai Binh", "thaibinh": "Thai Binh", "thai nguyen": "Thai Nguyen", "thainguyen": "Thai Nguyen",
    "thanh hoa": "Thanh Hoa", "thanhhoa": "Thanh Hoa", "thua thien hue": "Thua Thien Hue", "hue": "Thua Thien Hue",
    "tien giang": "Tien Giang", "tiengiang": "Tien Giang", "my tho": "Tien Giang", "mytho": "Tien Giang",
    "tra vinh": "Tra Vinh", "travinh": "Tra Vinh", "tuyen quang": "Tuyen Quang", "tuyenquang": "Tuyen Quang",
    "vinh long": "Vinh Long", "vinhlong": "Vinh Long", "vinh phuc": "Vinh Phuc", "vinhphuc": "Vinh Phuc",
    "yen bai": "Yen Bai", "yenbai": "Yen Bai", "phu yen": "Phu Yen", "phuyen": "Phu Yen", "tuy hoa": "Phu Yen", "tuyhoa": "Phu Yen",
    "phu quoc": "Kien Giang", "phuquoc": "Kien Giang", 
    "van don": "Quang Ninh", "vandon": "Quang Ninh",
    "vsip": "Industrial Zone", "amata": "Industrial Zone", "tan thuan": "Industrial Zone",
    "quang trung": "Software Park", "cvpm quang trung": "Software Park",
}

DETAIL_CUES = ["quan","q","huyen","phuong","duong","street","ward","district","tp","thi xa","thi tran"]

# ROLE PATTERNS
ROLE_PATTERNS = [
    (r"\bke toan thue\b|\btax accountant\b", "Tax Accountant"),
    (r"\bke toan tong hop\b|\bgeneral accountant\b", "General Accountant"),
    (r"\bke toan noi bo\b|\binternal accountant\b", "Internal Accountant"),
    (r"\bke toan truong\b|\bchief accountant\b", "Chief Accountant"),
    (r"\btruong phong ke toan\b|\baccounting manager\b", "Accounting Manager"),
    (r"\btruong phong tai chinh\b|\bfinance manager\b", "Finance Manager"),
    (r"\bke toan kho\b|\bwarehouse accountant\b", "Warehouse Accountant"),
    (r"\bke toan gia thanh\b|\bcost accountant\b", "Cost Accountant"),
    (r"\bke toan\b|\baccountant\b", "Accountant"),
    (r"\bkiem toan\b|\baudit\b", "Auditor"),
    (r"\bnhan vien thue\b|\btax consultant\b", "Tax Consultant"),
    (r"\bphan tich tai chinh\b|\bfinancial analyst\b", "Financial Analyst"),
    (r"\bfinance\b|\bfinancial\b", "Finance"),
    (r"\bhr\b|\bnhan su\b", "HR"),
    (r"\bsales\b|\bkinh doanh\b", "Sales"),
    (r"\bdata\b", "Data"),
    (r"\bdeveloper\b|\bengineer\b|\bsoftware\b", "Software Engineer"),
    (r"\bfrontend\b|\bfront-end\b", "Front-end Developer"),
    (r"\bbackend\b|\bback-end\b", "Back-end Developer"),
    (r"\bfullstack\b|\bfull-stack\b", "Full-stack Developer"),
    (r"\bbusiness analyst\b|\bba\b", "Business Analyst"),
    (r"\bproject manager\b|\bpm\b", "Project Manager"),
    (r"\bproduct manager\b|\bpd\b", "Product Manager"),
    (r"\bquality assurance\b|\bqa\b|\bqc\b", "QA/QC"),
    (r"\bmarketing executive\b|\bbranding\b", "Marketing Executive"),
    (r"\bcontent creator\b|\bcopywriter\b", "Content Executive"),
    (r"\brecruiter\b|\btalent acquisition\b", "Recruiter"),
    (r"\blogistics\b|\bxuat nhap khau\b|\bimport export\b", "Logistics Specialist"),
    (r"\bpurchasing\b|\bmua hang\b", "Purchasing Officer"),
    (r"\bsupply chain\b|\bchuoi cung ung\b", "Supply Chain Manager"),
    (r"\bgiao vien\b|\bteacher\b|\btutor\b", "Teacher"),
    (r"\bgiang vien\b|\blecturer\b|\bprofessor\b", "Lecturer"),
    (r"\bluat su\b|\blawyer\b|\blegal\b", "Lawyer"),
    (r"\bphap che\b|\bcompliance\b", "Compliance Officer"),
    (r"\bdesigner\b|\bthiet ke\b", "Graphic Designer"),
    (r"\bui/ux\b|\bproduct designer\b", "UI/UX Designer"),
    (r"\be-commerce\b|\bthuong mai dien tu\b", "E-commerce Specialist"),
    (r"\bcustomer service\b|\bcskh\b", "Customer Service"),
    (r"\bhuyen luyen\b|\btrainer\b", "Corporate Trainer"),
    (r"\bhành chính\b|\badministration\b|\boffice admin\b", "Administrative Officer"),
    (r"\bthu ky\b|\bsecretary\b|\bassistant\b", "Secretary/Assistant"),
    (r"\bquan ly cua hang\b|\bstore manager\b", "Store Manager"),
    (r"\bco khi\b|\bmechanical engineer\b", "Mechanical Engineer"),
    (r"\bdien\b|\belectrical engineer\b", "Electrical Engineer"),
    (r"\bxay dung\b|\bcivil engineer\b", "Civil Engineer"),
    (r"\bkien truc\b|\barchitect\b", "Architect"),
    (r"\bnoi that\b|\binterior designer\b", "Interior Designer"),
    (r"\bchi huy truong\b|\bsite manager\b", "Site Manager"),
    (r"\bkỹ thuật viên\b|\btechnician\b", "Technician"),
    (r"\bbảo trì\b|\bmaintenance\b", "Maintenance Technician"),
    (r"\bqc engineer\b|\bkỹ sư qc\b", "QC Engineer"),
    (r"\bgiam sat san xuat\b|\bproduction supervisor\b", "Production Supervisor"),
    (r"\bgiam doc nha may\b|\bplant manager\b", "Plant Manager"),
    (r"\bbac si\b|\bdoctor\b", "Doctor"),
    (r"\bdieu duong\b|\bnurse\b", "Nurse"),
    (r"\bduoc si\b|\bpharmacist\b", "Pharmacist"),
    (r"\btrinh duoc vien\b|\bmedical representative\b", "Medical Representative"),
    (r"\bdau bep\b|\bchef\b", "Chef"),
    (r"\bquan ly nha hang\b|\brestaurant manager\b", "Restaurant Manager"),
    (r"\ble tan\b|\breceptionist\b", "Receptionist"),
    (r"\bhuong dan vien\b|\btour guide\b", "Tour Guide"),
    (r"\btiep vien hang khong\b|\bflight attendant\b", "Flight Attendant"),
    (r"\bgiao dich vien\b|\bbank teller\b", "Bank Teller"),
    (r"\bnhan vien tin dung\b|\bcredit officer\b", "Credit Officer"),
    (r"\bquan ly quan he\b|\brelationship manager\b", "Relationship Manager"),
    (r"\bphan tich dau tu\b|\binvestment analyst\b", "Investment Analyst"),
    (r"\bquan ly van hanh\b|\boperations manager\b", "Operations Manager"),
    (r"\bgiam doc dieu hanh\b|\bceo\b|\bgeneral manager\b", "General Manager"),
    (r"\btu van viên\b|\bconsultant\b", "Consultant"),
    (r"\bdung phim\b|\bvideo editor\b", "Video Editor"),
    (r"\b3d artist\b|\banimator\b", "3D Artist"),
    (r"\bnhiep anh gia\b|\bphotographer\b", "Photographer"),
    (r"\bseo specialist\b|\bsem\b", "SEO Specialist"),
    (r"\bsocial media\b|\bcommunity manager\b", "Social Media Manager"),
    (r"\btai xe\b|\bdriver\b", "Driver"),
    (r"\bbao ve\b|\bsecurity guard\b", "Security Guard"),
    (r"\bactuary\b|\bdinh phi bao hiem\b", "Actuarial Analyst"),
    (r"\bbiomedical\b|\bky thuat sinh hoc\b", "Biomedical Engineer"),
    (r"\bmedia planner\b|\bdigital media\b", "Media Planner"),
    (r"\baccount manager\b|\bquan ly khach hang\b", "Account Manager"),
    (r"\bpilot\b|\bphi cong\b", "Pilot"),
    (r"\bship captain\b|\bthuyen truong\b", "Ship Captain"),
]

# ROLE SIMILARITY
ROLE_SIM = {
    ("Tax Accountant", "General Accountant"): 0.70,
    ("Internal Accountant", "General Accountant"): 0.60,
    ("Accountant", "General Accountant"): 0.55,
    ("Accountant", "Tax Accountant"): 0.45,
}

# EXPERIENCE SIMILARITY
EXP_NEAR = {
    ("Exp_0_1","Exp_1_3"): 0.6,
    ("Exp_1_3","Exp_3_5"): 0.6,
    ("Exp_3_5","Exp_5_plus"): 0.5,
}

# SECTION HINTS
SECTION_HINTS = {
    "skills":     ["ky nang", "kỹ năng", "skills", "technical skills", "skill set", "core skills", "nang luc"],
    "experience": ["kinh nghiem", "kinh nghiệm", "experience", "work history", "employment", "cong tac"],
    "projects":   ["du an", "dự án", "projects", "project"],
    "education":  ["hoc van", "học vấn", "education", "bang cap", "dao tao"],
    "summary":    ["tom tat", "tóm tắt", "summary", "profile", "about", "muc tieu", "objective", "professional summary"],
    "certs":      ["chung chi", "chứng chỉ", "certifications", "certificate", "awards", "achievement"],
    "languages":  ["ngon ngu", "ngoai ngu", "languages"],
    "interests":  ["so thich", "interests", "activities", "personal interests"],
    "references": ["tham chieu", "references"],
    "socials":    ["social", "links", "portfolio", "github", "linkedin"],
}

SECTION_WEIGHT = {
    "skills": 0.70,
    "experience": 0.45,
    "projects": 0.35,
    "certs": 0.40,
    "summary": 0.30,
    "education": 0.15,
    "unknown": 0.25,
}

# JOB INFO COLUMN MAPPING
COL = {
    "job_id": "JobID",
    "job_url": "URL_Job",
    "job_title": "Title",
    "company": "Name company",
    "location": "Job Address",
    "location_detail": "Job Address detail",
    "requirements": "Job Requirements",
    "salary": "Salary",
    "experience": "Experience",
    "job_desc": "Job description",
    "job_type": "Job type",
    "benefit": "benefit"
}

# RDF CLASSES
RDF_CLASSES = ["User","JobPosting","JobRoleCanonical","JobRoleRaw","Company","Location","ExperienceBucket","SalaryBucket","Skill","SkillRaw","University","Certification","Project","Industry","ContractType"]

# RDF OBJECT PROPERTIES
RDF_OBJ_PROPS = [
    "HAS_ROLE_CANONICAL","HAS_ROLE_RAW","POSTED_BY","LOCATED_IN",
    "REQUIRES_EXP_BUCKET","HAS_SALARY_BUCKET","REQUIRES_SKILL",
    "HAS_SKILL","MATCHES_JOB","SIMILAR_TO","NORMALIZES_TO","MENTIONS_SKILL_RAW",
    "STUDIED_AT", "HAS_CERTIFICATION", "WORKED_ON_PROJECT", "IN_INDUSTRY", "HAS_CONTRACT_TYPE"
]

# EVALUATION SETTINGS
SAMPLE_N = 100
TRIALS = 5
KS = [1, 3, 5, 10]

# Graph visualization helpers (no duplicates)
CENTER_JOB_ID = None
CENTER_MODE = "user"
USER_ID = "user::cv_001"
IMPORTANT_EDGES = ["MATCHES_JOB", "SIMILAR_TO"]
