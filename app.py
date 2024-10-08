from flask import Flask, request
import requests
import json
import openai
import os
import pandas as pd


# Facebook Page Access Token for authenticating API requests to the Facebook Messenger platform
PAGE_ACCESS_TOKEN = "EAAQmzH9J2CUBOxdKClR2QIg2JhfNswpQU0oZCwXpvPAeFh3DEvhnxrVjpOVBfP1bEuP9VBddFmE3vVcIQAukhwMelq2al5it5vP8xiCuZB4RDmZA4xS7QZAJvjvKs2GpqYJcCJM2W7rRcl4750lnHk9bs3tsG8Exe4ZC4jaLiHpc3NQQEvZA0uuKYrWUgETfsZD"

# Verification token to validate requests received from Facebook Messenger webhook
VERIFY_TOKEN = "doan_secure_verify_token_for_vu_job"


#To run program, you need copy my OpenAI key from the MS Word file (I sent via email) and paste it to the following line of code.
# API key for authenticating requests to OpenAI's API for language model operations
openai.api_key = ""

 
# Function to load candidate data
def load_candidate_data(file_path):
    excel_data = pd.ExcelFile(file_path)
    candidate_data = {}

    # Iterate over each sheet (representing a CV) and dynamically parse its content
    for sheet_name in excel_data.sheet_names:
        sheet_data = excel_data.parse(sheet_name)

        # Initialize a dictionary to hold the candidate's information
        candidate_info = {}

        # Iterate through each row, where the first column is the section name, and the second column is the content
        for index, row in sheet_data.iterrows():
            if pd.isna(row.iloc[0]) or pd.isna(row.iloc[1]):
                continue  # Skip any rows with missing section or content

            section = row.iloc[0]  # Section name from the first column
            content = row.iloc[1]  # Content from the second column
            candidate_info[section] = content  # Store the section and its content dynamically
        
        # Use the sheet name as the candidate's identifier
        candidate_name = f"Candidate_{sheet_name}"
        
        # Store the candidate's data
        candidate_data[candidate_name] = candidate_info

    return candidate_data

# Load data 
candidate_data = load_candidate_data('output.xlsx')


# Function to find candidate info dynamic
def find_candidate_info_dynamic(candidate_name, question, candidate_data):
    if candidate_name in candidate_data:
        cv_data = candidate_data[candidate_name]
        relevant_info = []

        # Search through all available sections dynamically
        for section, content in cv_data.items():
            if any(keyword in section.lower() for keyword in ['education', 'experience', 'summary']):
                relevant_info.append(f"{section}: {content}")

        return relevant_info
    else:
        return None


# Function to generate response with cv dynamic
def generate_response_with_cv_dynamic(question, candidate_name, candidate_data):
    info = find_candidate_info_dynamic(candidate_name, question, candidate_data)

    if info:
        # Convert the relevant information into a natural language response
        response = "".join(info)
        return response
    else:
        return f"Sorry, I couldn't find any information about {candidate_name}."




# Function to generate response with cv
def generate_response_with_cv(question, candidate_name, candidate_data):
    info = find_candidate_info_dynamic(candidate_name, question, candidate_data)

    if info:
        # Convert the relevant information into a natural language response
        response = "\n".join(info)
        return response
    else:
        return "Sorry, I couldn't find any information about that candidate."


# Function to generate gpt4 response with data
def generate_gpt4_response_with_data(question, relevant_info):
    if relevant_info:
        relevant_data_str = "\n".join([f"{info}" for info in relevant_info])

        prompt = (f"You are a helpful chatbot that is analyzing candidate CVs. "
                  f"The user asked: '{question}'. Here is relevant information from the CVs:\n"
                  f"{relevant_data_str}\n"
                  f"Generate a natural response that answers the user's query based on this data.")

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=150,
            temperature=0.7
        )
        
        # Debugging: print the generated response
        answer = response['choices'][0]['message']['content'].strip()
        print(f"Generated GPT-4 response: {answer}")
        return answer
    else:
        return generate_gpt4_response(question)



# Default GPT-4 response when no data is found
# Function to generate gpt4 response
def generate_gpt4_response(question):
    messages = [
        {"role": "system", "content": "You are a helpful chatbot that answers general questions."},
        {"role": "user", "content": question}
    ]
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        max_tokens=150,
        temperature=0.7
    )
    return response['choices'][0]['message']['content'].strip()



# Function to send a long message in chunks
def send_message_in_chunks(recipient_id, message_text, chunk_size=2000):
    """Splits a long message into chunks and sends each part sequentially."""
    for i in range(0, len(message_text), chunk_size):
        chunk = message_text[i:i + chunk_size]
        send_message(recipient_id, chunk)

# Existing function to send a single message
def send_message(recipient_id, message_text):
    try:
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "recipient": {"id": recipient_id},
            "message": {"text": message_text}
        }
        params = {'access_token': PAGE_ACCESS_TOKEN}

        print(f"Sending message to recipient {recipient_id}: {message_text}")

        response = requests.post('https://graph.facebook.com/v8.0/me/messages',
                                 params=params, headers=headers, json=data)

        if response.status_code != 200:
            print(f"Error sending message: {response.status_code}, {response.text}")
        return response
    except Exception as e:
        print(f"Error sending message: {e}")

 
        

# Initialize the Flask app
app = Flask(__name__)        
        

@app.route("/webhook", methods=["POST"])
# Function to handle webhook
def handle_webhook():
    try:
        body = request.get_json()
        print(f"Received payload: {body}")  # Log the entire payload for debugging

        if body.get("object") == "page":
            for entry in body["entry"]:
                messaging_event = entry.get("messaging")[0]
                sender_id = messaging_event["sender"]["id"]

                # Handle messages
                if "message" in messaging_event and "text" in messaging_event["message"]:
                    message_text = messaging_event["message"]["text"]
                    print(f"Received message: {message_text} from sender {sender_id}")

                    # Find relevant data based on the user's question
                    candidate_name = list(candidate_data.keys())[0]
                    relevant_info = find_candidate_info_dynamic(candidate_name, message_text, candidate_data)
                    print(f"Relevant info: {relevant_info}")  # Debugging

                    # Generate a natural response using GPT-4 and the relevant data
                    response_message = generate_gpt4_response_with_data(message_text, relevant_info)
                    print(f"Response message: {response_message}")  # Debugging

                    send_message_in_chunks(sender_id, response_message)
                

        return "EVENT_RECEIVED", 200
    except Exception as e:
        print(f"Error in webhook handler: {e}")
        return "Error", 500



# Entry point for running the Flask application, specifying the port, enabling debug mode, and allowing external access.

if __name__ == "__main__":
    app.run(port=3000, debug=True, host="0.0.0.0")
