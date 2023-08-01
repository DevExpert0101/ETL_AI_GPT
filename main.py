import os
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import datetime
import openai
import json 
import fitz
import time
from PyPDF2 import PdfReader
import pymongo
import base64


app = FastAPI()

# Set up CORS middleware to allow all origins (*)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PumpDataProcessor:
    def __init__(self):
        self.sample_data_keys = [
            'name', 'Maximum temperature', 'Maximum temperature (with flush)', 'Maximum suction pressure',
            'Maximum head', 'Maximum speed', 'Maximum flow', 'Maximum horsepower', 'Rotor',
            'Rotor cover', 'Manifold', 'Endbell', 'Pick-up tube*', 'Shaft'
        ]
        self.sample_data_value=[
            'Roto-Jet API-R11', '180F, 82C', '250F 121C', '200PSI 14BAR',
            '1500Ft', '150GPM 34m3/hr', '75HP 55KW', '380Ibs. 159kg', '316 St. Steel',
            '316 St. Steel', '316 St. Steel', 'Ductile Iron', '17-4 PH', 'AISI 4140'
        ]
    def get_pump_info(self, pump_data):
        try:
            prompt = f"{pump_data}This is pump description. {self.sample_data_keys, self.sample_data_value} This is sample data. Give me {', '.join(self.sample_data_keys)}. Provide the response in JSON format, with keys in lowercase without spaces or symbols."
            response = openai.Completion.create(
                engine='text-davinci-003',
                prompt=prompt,
                max_tokens=500,
                temperature=0.8,
                top_p=0.9,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                n=1
            )
            return json.loads(response.choices[0].text.strip())
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return {"":""}
    def process_unique_keys(self, FILE_FLDR, FILE_NAME):
                folder_name = os.path.splitext(FILE_NAME)[0]
                pdf_folder_path = os.path.join(FILE_FLDR, folder_name)
                text_file_path = os.path.join(pdf_folder_path, folder_name+".txt")
                json_file_path = os.path.join(pdf_folder_path, "json.txt")
                with open(text_file_path, "r") as text_file:
                    pump_data=text_file.read()
                    pump_info=self.get_pump_info(pump_data)
                    print(pump_info)
                    with open(json_file_path, "w") as json_file:
                        json_file.write(str(pump_info))
                    return pump_info

DIMENSION_LIMIT = 0
RELATIVE_SIZE = 0
ABSOLUTE_SIZE = 0
IMG_DIR = "output"
def recover_pix(doc, item):
    xref = item[0]  # xref of PDF image
    smask = item[1]  # xref of its /SMask
    # special case: /SMask or /Mask exists
    if smask > 0:
        pix0 = fitz.Pixmap(doc.extract_image(xref)["image"])
        if pix0.alpha:  # catch irregular situation
            pix0 = fitz.Pixmap(pix0, 0)  # remove alpha channel
        mask = fitz.Pixmap(doc.extract_image(smask)["image"])
        try:
            pix = fitz.Pixmap(pix0, mask)
        except:  # fallback to original base image in case of problems
            pix = fitz.Pixmap(doc.extract_image(xref)["image"])
        if pix0.n > 3:
            ext = "pam"
        else:
            ext = "png"
        return {  # create dictionary expected by caller
            "ext": ext,
            "colorspace": pix.colorspace.n,
            "image": pix.tobytes(ext),
        }
    # special case: /ColorSpace definition exists
    # to be sure, we convert these cases to RGB PNG images
    if "/ColorSpace" in doc.xref_object(xref, compressed=True):
        pix = fitz.Pixmap(doc, xref)
        pix = fitz.Pixmap(fitz.csRGB, pix)
        return {  # create dictionary expected by caller
            "ext": "png",
            "colorspace": 3,
            "image": pix.tobytes("png"),
        }
    return doc.extract_image(xref)

def extract_images_from_pdf(pdf_file_path, pdf_folder_path):
    """Extract images from the given PDF file."""
    doc = fitz.open(pdf_file_path)
    page_count = doc.page_count
    xreflist = []
    imglist = []
    for pno in range(page_count):
        il = doc.get_page_images(pno)
        imglist.extend([x[0] for x in il])
        for img in il:
            xref = img[0]
            if xref in xreflist:
                continue
            width, height = img[2], img[3]
            if min(width, height) <= DIMENSION_LIMIT:
                continue
            image = recover_pix(doc, img)
            n = image["colorspace"]
            imgdata = image["image"]
            if len(imgdata) <= ABSOLUTE_SIZE:
                continue
            if len(imgdata) / (width * height * n) <= RELATIVE_SIZE:
                continue
            imgfile = os.path.join(pdf_folder_path, f"img{xref:05}.{image['ext']}")
            with open(imgfile, "wb") as fout:
                fout.write(imgdata)
            xreflist.append(xref)
    return imglist, xreflist

def image_save(FILE_FLDR, FILE_NAME):
        pdf_file_path = os.path.join(FILE_FLDR, FILE_NAME)
        folder_name = os.path.splitext(FILE_NAME)[0]
        pdf_folder_path = os.path.join(FILE_FLDR, folder_name)
        os.makedirs(pdf_folder_path, exist_ok=True)
        print(f"Created folder '{folder_name}'.")
        t0 = time.time()
        imglist, xreflist = extract_images_from_pdf(pdf_file_path, pdf_folder_path)
        t1 = time.time()
        print(f"{len(set(imglist))} images in total")
        print(f"{len(xreflist)} images extracted")
        print(f"total time {t1 - t0} sec")

def get_json(FILE_FLDR, FILE_NAME):
    image_save(FILE_FLDR, FILE_NAME)
    text_save(FILE_FLDR, FILE_NAME)

    load_dotenv()
    openai.api_key=os.getenv("OPENAI_API_KEY")
    processor = PumpDataProcessor()
    return processor.process_unique_keys(FILE_FLDR, FILE_NAME)

def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PdfReader(file)
        num_pages = len(reader.pages)
        text_content = ""
        for page_num in range(num_pages):
            page = reader.pages[page_num]
            text_content += page.extract_text()
    return text_content

def text_save(FILE_FLDR, FILE_NAME):
        pdf_file_path = os.path.join(FILE_FLDR, FILE_NAME)
        folder_name = os.path.splitext(FILE_NAME)[0]
        pdf_folder_path = os.path.join(FILE_FLDR, folder_name)
        os.makedirs(pdf_folder_path, exist_ok=True)
        print(f"Created folder '{folder_name}'.")
        text_file_path = os.path.join(pdf_folder_path, folder_name+".txt")
        with open(text_file_path, "w") as text_file:
            text_file.write(extract_text_from_pdf(pdf_file_path))
        print(f"Created text file '{folder_name}.txt' in the folder.")
        pdf_file = fitz.open(pdf_file_path)

@app.post("/upload/pdf/")
async def upload_pdf_file(file: UploadFile = File(...)):

    c_directory = os.getcwd()
    
    c_year = str(datetime.date.today().year)
    c_date = str(datetime.date.today().month) + '-' + str(datetime.date.today().day)
    fname = c_directory + f"/data/{c_year}/{c_date}/{file.filename}"
    folder_name = c_directory + f"/data/{c_year}/{c_date}"

    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    with open(fname, "wb") as buffer:
        buffer.write(await file.read())

    client = pymongo.MongoClient("mongodb+srv://KellyForPDFScraper:wKceyRadQErXNc92@enp.ocrp5.mongodb.net/?retryWrites=true&w=majority")
    database = client["stgsupplier"]
    pdf_collection = database["pdfcatalogue"]
    # Read the PDF file
    # Ensure pdf file size is < 11MB
    with open(fname, "rb") as pdf_file:
        pdf_data = pdf_file.read()

    # Encode the binary PDF data as Base64
    encoded_pdf_data = base64.b64encode(pdf_data)
    pdf_document = {
        "filename": file.filename,  # Set the desired filename for the PDF
        "pdf_data": encoded_pdf_data.decode()  # Convert binary to string before inserting
    }

    # Insert the document into the MongoDB collection
    pdf_collection.insert_one(pdf_document)

    data = get_json(folder_name, file.filename)

    return data