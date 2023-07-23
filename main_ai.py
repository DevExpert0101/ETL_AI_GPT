import os
import openai
import json 
from dotenv import load_dotenv

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
