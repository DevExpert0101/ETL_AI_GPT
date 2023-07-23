import os
import fitz
from PyPDF2 import PdfReader

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