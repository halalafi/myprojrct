from fastapi import FastAPI, HTTPException
import logging
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import arabic_reshaper
from bidi.algorithm import get_display
from googlesearch import search
from fpdf import FPDF
from io import BytesIO
from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi import FastAPI, File, UploadFile
from typing import List, Optional
import fitz  # PyMuPDF
from fastapi import FastAPI, File, UploadFile


app = FastAPI()

# دالة لاستخراج النص من ملف PDF
def extract_text_from_pdf(file_path: str) -> str:
    try:
        doc = fitz.open(file_path)
        text = ""
        for page_num, page in enumerate(doc):
            page_text = page.get_text()
            if not page_text.strip():
                print(f"تحذير: لم يتم العثور على نص في الصفحة {page_num + 1}")
            text += page_text
        doc.close()
        if text.strip():
            return text
        else:
            print("تحذير: النص المستخرج فارغ.")
            return ""
    except Exception as e:
        print(f"حدث خطأ أثناء قراءة ملف PDF: {e}")
        return ""

# استخراج التخصص والمهارات من النص
def extract_specialization_and_skills(text: str) -> tuple:
    specialization = None
    skills = []

    # استخراج التخصص (Specialization)
    if "Specialization:" in text:
        specialization_start = text.find("Specialization:") + len("Specialization:")
        specialization_end = text.find("\n", specialization_start)
        specialization = text[specialization_start:specialization_end].strip()

    # استخراج المهارات (Skills)
    if "Skills:" in text:
        skills_start = text.find("Skills:") + len("Skills:")
        skills_text = text[skills_start:].strip()  # باقي النص بعد Skills:

        # تقسيم المهارات باستخدام السطر الجديد أو الفواصل
        skills = [skill.strip() for skill in skills_text.split('\n') if skill.strip() and skill.startswith('-')]

    return specialization, skills

# دالة للبحث عن الوظائف باستخدام التخصص والمهارات
def search_jobs(specialization: str, skills: List[str]) -> List[str]:
    search_query = f"{specialization} job vacancies {' '.join(skills)}"
    search_results = search(search_query, num_results=5)
    
    job_links = []
    for result in search_results:
        job_links.append(result)
    
    return job_links

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # حفظ الملف المرفوع مؤقتًا
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # استخراج النص من ملف PDF
        text = extract_text_from_pdf(file_path)

        if not text:
            return {"error": "لم يتم استخراج النص من الملف"}

        # استخراج التخصص والمهارات
        specialization, skills = extract_specialization_and_skills(text)

        if specialization or skills:
            # البحث عن الوظائف
            job_links = search_jobs(specialization, skills)
            return {
                "specialization": specialization,
                "skills": skills,
                "job_links": job_links
            }
        else:
            return {"error": "لم أتمكن من استخراج التخصص أو المهارات من النص."}
    except Exception as e:
        return {"error": f"حدث خطأ أثناء معالجة الملف: {e}"}
    finally:
        # حذف الملف المؤقت بعد المعالجة
        if os.path.exists(file_path):
            os.remove(file_path)

# إعداد logging لعرض الأخطاء
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# تقديم صفحة HTML عند الوصول إلى المسار الجذري "/"
@app.get("/", response_class=HTMLResponse)
async def get_index():
    html_path = r"job.html"
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as file:
            return file.read()
    else:
        logger.warning("الملف job.html غير موجود.")
        return "الملف غير موجود."

# إعدادات CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # السماح لأي أصل
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Path to store generated PDFs
PDF_DIR = "pdfs"
os.makedirs(PDF_DIR, exist_ok=True)


@app.get("/")
async def serve_home():
    return FileResponse("pdf.html")

@app.post("/create_cv/")
async def create_cv(
    name: str = Form(...),
    specialization: str = Form(...),
    skills: str = Form(...),
    education: str = Form(...),
    experience: str = Form(...),
    contact_info: str = Form(...)
):
    
    try:
        # إنشاء الـ PDF
        pdf = FPDF()
        pdf.add_page()
        
        # تحديد حجم الخط واللون
        pdf.set_font("Helvetica", style='B', size=16)  # تغيير الخط إلى Helvetica مع حجم 16 واستخدام خط غامق
        pdf.set_text_color(0, 0, 0)  # تغيير اللون إلى الأسود
        
        # العنوان الأول
        pdf.cell(200, 10, txt=f"{name} - CV", ln=True, align="C")
        pdf.ln(10)
        
        # العودة إلى الخط العادي
        pdf.set_font("Helvetica", size=12)
        
        pdf.cell(200, 10, txt=f"Name: {name}", ln=True)
        pdf.cell(200, 10, txt=f"Specialization: {specialization}", ln=True)
        pdf.cell(200, 10, txt="Skills:", ln=True)
        for skill in skills.split(","):
            pdf.cell(200, 10, txt=f"- {skill.strip()}", ln=True)
        pdf.cell(200, 10, txt="Education:", ln=True)
        pdf.multi_cell(0, 10, txt=education)
        pdf.cell(200, 10, txt="Experience:", ln=True)
        pdf.multi_cell(0, 10, txt=experience)
        pdf.cell(200, 10, txt="Contact Info:", ln=True)
        pdf.multi_cell(0, 10, txt=contact_info)

        # حفظ الـ PDF
        
        # Save PDF
        pdf_path = os.path.join(PDF_DIR, f"{name}_CV.pdf")
        pdf.output(pdf_path)

        # Check if PDF was created successfully
        if os.path.exists(pdf_path):
            return FileResponse(pdf_path, media_type="application/pdf", filename=f"{name}_CV.pdf")
        else:
            return {"error": "Failed to create PDF file"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}



# دالة لتحسين عرض النصوص العربية
def fix_arabic_display(text: str) -> str:
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

# دالة عامة لتحميل البيانات من ملف نصي
def load_data(file_path: str, fields: dict):
    if not os.path.exists(file_path):
        logger.error(f"الملف '{file_path}' غير موجود.")
        raise HTTPException(status_code=404, detail=f"الملف '{file_path}' غير موجود.")

    current_item = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            for field, prefix in fields.items():
                if line.startswith(prefix):
                    if current_item and field == list(fields.keys())[0]:  # عند العثور على بداية عنصر جديد
                        yield current_item
                        current_item = {}
                    current_item[field] = line.replace(prefix, "").strip()
                    break
            else:
                # إذا كانت سطراً تابعاً للوصف
                if "description" in current_item:
                    current_item["description"] += f" {line}"
        if current_item:
            yield current_item

# دالة للبحث عن وظائف أو شركات
def search_items(query: str, items: list, fields_to_search: list) -> list:
    query = query.lower()
    matched_items = [
        item for item in items
        if any(query in item.get(field, "").lower() for field in fields_to_search)
    ]
    if not matched_items:
        logger.info("لم يتم العثور على نتائج تطابق الاستفسار.")
        raise HTTPException(status_code=404, detail="لم أتمكن من العثور على نتائج تطابق هذا الاستفسار.")
    return matched_items

# دوال البحث باستخدام Google
def search_google(query: str, num_results: int = 5) -> list:
    try:
        return list(search(query, num_results=num_results))
    except Exception as e:
        logger.error(f"خطأ أثناء البحث في Google: {str(e)}")
        raise HTTPException(status_code=500, detail=f"خطأ أثناء البحث في Google: {str(e)}")

   
@app.get("/files/{file_name}")
async def get_file(file_name: str):
    file_path = f"/tmp/{file_name}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        logger.warning(f"File '{file_name}' not found.")
        raise HTTPException(status_code=404, detail="File not found")

class JobQuery(BaseModel):
    query: str

class CompanyQuery(BaseModel):
    city: str
    specialization: str

@app.get("/jobs")
def get_jobs(query: str):
    jobs_file_path = r'C:\Users\lenovo\OneDrive\Desktop\-\jobs.txt'
    fields = {"title": "Job Title:", "description": "Description:"}
    jobs = list(load_data(jobs_file_path, fields))
    return search_items(query, jobs, ["title", "description"])

@app.get("/search_jobs_google")
def search_jobs_google(specialty: str, skills: str):
    query = f"{specialty} {skills} job vacancies"
    job_links = search_google(query)  # دالة البحث
    return {"job_links": job_links}

@app.get("/search_companies_google")
def search_companies_google(city: str, specialization: str):
    query = f"companies in {city} specializing in {specialization}"
    return {"company_links": search_google(query)}

@app.post("/search_companies")
def search_companies_api(company_query: CompanyQuery):
    companies_file_path = r'C:\Users\lenovo\OneDrive\Desktop\-\companies.txt'
    fields = {"company": "Company Name:", "location": "Location:", "specialization": "Specialization:"}
    companies = list(load_data(companies_file_path, fields))
    return search_items(company_query.specialization, companies, ["specialization"])


logger.info("API is ready.")
