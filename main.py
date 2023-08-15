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
import uuid
import uvicorn


app = FastAPI()

# Set up CORS middleware to allow all origins (*)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# client = pymongo.MongoClient(
#     "mongodb+srv://KellyForPDFScraper:wKceyRadQErXNc92@enp.ocrp5.mongodb.net/?retryWrites=true&w=majority")
# database = client["stgsupplier"]
# pdf_collection = database["pdfcatalogue"]
# img_collection = database["pdfimages"]


class PumpDataProcessor:
    def __init__(self):
        self.category="Pump"
        self.sample_data_keys = {"Pump": [
            'name', 'Maximum temperature', 'Maximum temperature (with flush)', 'Maximum suction pressure',
            'Maximum head', 'Maximum speed', 'Maximum flow', 'Maximum horsepower', 'Rotor',
            'Rotor cover', 'Manifold', 'Endbell', 'Pick-up tube*', 'Shaft'],

            "Electrical Motor": [
                "Frame Size", "Make", "Model", "Manufacturer",
                "Product ID/ SKU", "Description", "Brand/ Label", "Country of Origin", "Certification Agency", "Dimensions",
                "Weight", "Enclosure Type", "Enclosure Material", "Electrical Data (I)", "Electrical Data (Freq)", "Electrical Data (P)",
                "Electrical Data (Speed)", "Electrical Data (V)", "Motor Base", "Motor Frame Size", "NEMA Design Code", "No of Phase",
                "No of Speeds", "Shaft Diameter", "Standards", "UNSPC", "HS/ Custom Tarrif Code"],

            "Tank" : [
                "Frame Size", "Make", "Model", "Manufacturer", "Product ID/ SKU", "Description", "Brand/ Label", "Certification Agency","Country of Origin",
                    "Dimensions", "Weight", "Temperature", "Pressure", "Volume", "Body", "Shell", "Bladder","System Connection" ],
                    
            "Heat Exchanger" :  ["Frame Size","Make","Model","Manufacturer","Product ID/ SKU","Description","Brand/ Label",
                    "Certification Agency","Country of Origin","Dimensions","Weight","Temperature","Pressure","Volume","Body","Heat exchanged"]       
            }
        self.sample_data_value = {"Pump":[
            'Roto-Jet API-R11', '180F, 82C', '250F 121C', '200PSI 14BAR',
            '1500Ft', '150GPM 34m3/hr', '75HP 55KW', '380Ibs. 159kg', '316 St. Steel',
            '316 St. Steel', '316 St. Steel', 'Ductile Iron', '17-4 PH', 'AISI 4140'],

            "Electrical Motor": [
                "449TS","Baldor-Reliance", "EM44304TS-4","ABB","7BEM44304TS-4","General Purpose Motor 300 Hp 460 V (EM44304TS-4)","Baldor-Reliance","United States (US)"
                ,"CCSA USCSA EEV","61 in x 29.5 in x 44 in","1253.729 kg","TEFC","Iron","327","60 Hz","300 Hp","1780 r/min","460 V","Foot Mounted","449TS","B"
                ,"3","Single Speed","2.375 in","NEMA","26101112","85015381"],

            "Tank": [ 
                "30(762)IN * 65(1651)IN", "", "1060BP-600", "Aurora", "1060BP-600", "For Domestic Potable Water Systems", "Aurora", "ASME", "30IN*65IN", "360 lbs", "200°F",
                "125 psi", "158 gal", "", "Steel", "Heavy Duty Butyl - FDA approved", "Bronze" ],

            "Heat Exchanger" :  [
                "", "", "DNA 159.10.S24", "Hexonic", "DNA 159.10.S24", "", "Hexonic", "PED, ASME, EAC, China ML", "", "140mm,850mm,1260mm,159mm", "92.9 lb", "392°F, -4°F",
                "145 psi, 232 psi", "1.8 gal, 3.5 gal", "AISI 316L / 1.4404", "" ]
            }
        


    def get_pump_info(self, pump_data):
        try:
                        
            data_keys = self.sample_data_keys[self.category]            
            data_value = self.sample_data_value[self.category]
            
            prompt = f"{pump_data}This is equipment description. Please give me attributes {', '.join(data_keys)}. Provide the response in JSON format, with keys in lowercase without spaces or symbols."
            
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
            return {"": ""}

    def process_unique_keys(self, FILE_FLDR, FILE_NAME):
        
        if "motor" in FILE_NAME.lower():
            self.category = "Electrical Motor"
        elif "tank" in FILE_NAME.lower():
            self.category = "Tank"
        else:
            self.category = "Heat Exchanger"

        

        folder_name = os.path.splitext(FILE_NAME)[0]
        pdf_folder_path = os.path.join(FILE_FLDR, folder_name)
        text_file_path = os.path.join(pdf_folder_path, folder_name+".txt")
        json_file_path = os.path.join(pdf_folder_path, "json.txt")

        
        with open(text_file_path, "r", encoding="utf-8") as text_file:
        
            pump_data = text_file.read()
        
            pump_info = self.get_pump_info(pump_data)
        
            with open(json_file_path, "w") as json_file:
        
                json_file.write(str(pump_info))
        
            print(pump_info)
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
    img_ids = []
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
            imgfile = os.path.join(
                pdf_folder_path, f"img{xref:05}.{image['ext']}")
            with open(imgfile, "wb") as fout:
                fout.write(imgdata)
                        
            uid = str(uuid.uuid4())
            img_document = {
                "img_id": uid,
                "img_data": imgdata
            }

            # img_collection.insert_one(img_document)
            img_ids.append(uid)

            xreflist.append(xref)
    return imglist, xreflist, img_ids


def image_save(FILE_FLDR, FILE_NAME):
    pdf_file_path = os.path.join(FILE_FLDR, FILE_NAME)
    folder_name = os.path.splitext(FILE_NAME)[0]
    pdf_folder_path = os.path.join(FILE_FLDR, folder_name)
    os.makedirs(pdf_folder_path, exist_ok=True)

    print(f"Created folder '{folder_name}'.")

    t0 = time.time()
    imglist, xreflist, img_ids = extract_images_from_pdf(
        pdf_file_path, pdf_folder_path)
    t1 = time.time()

    print(f"{len(set(imglist))} images in total")
    print(f"{len(xreflist)} images extracted")
    print(f"total time {t1 - t0} sec")

    return img_ids


def get_json(FILE_FLDR, FILE_NAME):
    img_ids = image_save(FILE_FLDR, FILE_NAME)
    text_save(FILE_FLDR, FILE_NAME)

    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")
    processor = PumpDataProcessor()
    return processor.process_unique_keys(FILE_FLDR, FILE_NAME), img_ids


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
    with open(text_file_path, "w", encoding="utf-8") as text_file:
        text_file.write(extract_text_from_pdf(pdf_file_path))
    
    
    print(f"Created text file '{folder_name}.txt' in the folder.")
    pdf_file = fitz.open(pdf_file_path)


@app.post("/upload/pdf/")
async def upload_pdf_file(file: UploadFile = File(...)):

    c_directory = os.getcwd()

    c_year = str(datetime.date.today().year)
    c_date = str(datetime.date.today().month) + \
        '-' + str(datetime.date.today().day)
    fname = c_directory + f"/data/{c_year}/{c_date}/{file.filename}"
    folder_name = c_directory + f"/data/{c_year}/{c_date}"

    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    with open(fname, "wb") as buffer:
        buffer.write(await file.read())

    # Read the PDF file
    # Ensure pdf file size is < 11MB
    with open(fname, "rb") as pdf_file:
        pdf_data = pdf_file.read()

    # Encode the binary PDF data as Base64
    encoded_pdf_data = base64.b64encode(pdf_data)
    pdf_document = {
        "filename": file.filename,  # Set the desired filename for the PDF
        # Convert binary to string before inserting
        "pdf_data": encoded_pdf_data.decode()
    }

    # Insert the document into the MongoDB collection
    # pdf_collection.insert_one(pdf_document)

    data, img_ids = get_json(folder_name, file.filename)

    return data, img_ids

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
