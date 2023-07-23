from main_img import image_save
from main_text import text_save
from main_ai import PumpDataProcessor
import openai
import os
from dotenv import load_dotenv
import fastapi
from fastapi import FastAPI, File, UploadFile
import datetime

app = FastAPI()

def get_json(FILE_FLDR, FILE_NAME):
    image_save(FILE_FLDR, FILE_NAME)
    text_save(FILE_FLDR, FILE_NAME)

    load_dotenv()
    openai.api_key=os.getenv("OPENAI_API_KEY")
    processor = PumpDataProcessor()
    return processor.process_unique_keys(FILE_FLDR, FILE_NAME)


@app.post("/upload/pdf")
async def upload_pdf_file(file: UploadFile = File(...)):

    c_directory = os.getcwd()
    c_year = datetime.date.year()
    c_date = datetime.date.day()
    fname = c_directory + f"/data/{c_year}/{c_date}/{file.filename}"
    folder_name = c_directory + f"/data/{c_year}/{c_date}"
    with open(fname, "wb") as buffer:
        buffer.write(await file.read())

    data = get_json(folder_name, file.filename)

    return data