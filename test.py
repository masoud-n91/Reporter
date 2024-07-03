import pdfplumber
import google.generativeai as genai
from dotenv import load_dotenv
import os



# load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

genai.configure(api_key=GOOGLE_API_KEY)

# Path to the PDF file
pdf_path = "uploads/book.pdf"

# Initialize an empty string to hold the text
full_text = []

# Open the PDF file
with pdfplumber.open(pdf_path) as pdf:
    # Iterate through each page in the PDF
    for page in pdf.pages:
        # Extract text from the page
        text = page.extract_text()
        # Append the text to the full_text variable
        if text:
            full_text.append(text)



generation_config = {
    "temperature": 0.6,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 4096,
    # "response_mime_type": "application/json",
}

safety_settings = [
    {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_NONE",
    },
    {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_NONE",
    },
    {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_NONE",
    },
    {
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_NONE",
    },
]


sys_prompt = f"""
You are an expert in Pathology and Genetics of the digestive system.
I will give you a book and ask you questions about it.
Answer them in the most appropriate way according to the book.
You have to explain your answer, too. Use the information in the book, give the most correct answer then explain the answer in your own words.

Book: {full_text}
"""

model = genai.GenerativeModel(
        model_name="gemini-1.5-pro-latest",
        safety_settings=safety_settings,
        generation_config=generation_config,
        system_instruction=sys_prompt,
    )


chat_session = model.start_chat(history=[])

while True:
    query = input("Question: ")

    if query == "exit":
        break

    response = chat_session.send_message(query)

    print(response.text)


