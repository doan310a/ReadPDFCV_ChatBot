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
    """Load candidate data from an Excel file where each sheet contains a different candidate's information."""
    excel_data = pd.ExcelFile(file_path)
    candidate_data = {}

    # Iterate over each sheet (representing a candidate)
    for sheet_name in excel_data.sheet_names:
        sheet_data = excel_data.parse(sheet_name)

        # Initialize a dictionary to hold the candidate's information
        candidate_info = {}

        # Assume the candidate's name is in the first row, adjust as needed
        candidate_name = sheet_data.iloc[0, 1]  # Assuming name is in the second column of the first row
        candidate_info["name"] = candidate_name

        # Iterate through each row, starting from row 2, to gather other details
        for index, row in sheet_data.iterrows():
            if index == 0:  # Skip the first row, which contains the candidate's name
                continue
            if pd.isna(row.iloc[0]) or pd.isna(row.iloc[1]):
                continue  # Skip any rows with missing section or content

            section = row.iloc[0]  # Section name from the first column
            content = row.iloc[1]  # Content from the second column
            candidate_info[section] = content  # Store the section and its content dynamically
        
        # Store the candidate's data by their name
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

 
# Function to generate a GPT-4 response based on user message and candidate data
def generate_gpt4_response_with_data(user_message, candidate_data):
    """Generate a GPT-4 response based on the user message and candidate data."""
    try:
        # Attempt to identify the relevant candidate by checking if their name is in the user message
        relevant_candidate = None
        user_message_lower = user_message.lower()  # Normalize user message to lowercase

        for candidate_name, candidate_info in candidate_data.items():
            candidate_name_lower = candidate_name.lower()  # Normalize candidate name to lowercase
            if candidate_name_lower in user_message_lower:  # Check if candidate's name is in the user message
                relevant_candidate = candidate_name
                break

        # If a relevant candidate is found, provide their information
        if relevant_candidate:
            candidate_info = candidate_data[relevant_candidate]
            prompt = f"The user asked about {relevant_candidate}. Provide relevant information from the following data:\n"
            
            for section, content in candidate_info.items():
                if section != "name":
                    prompt += f"{section}: {content}\n"
            
            # Use GPT-4 Chat API
            response = openai.ChatCompletion.create(
                model="gpt-4",  # Ensure you are using the correct model
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that provides information about job candidates."},
                    {"role": "user", "content": user_message},
                    {"role": "system", "content": prompt}
                ],
                max_tokens=500
            )
            
            return response.choices[0].message['content']
        
        # If no relevant candidate is found, return a conversational fallback
        else:
            return "I'm sorry, I couldn't find any information on that candidate. Could you try again, or ask me to list all available candidates?"
    
    except Exception as e:
        print(f"Error generating GPT-4 response: {e}")
        return "Oops, something went wrong on my end. Let me try again!"




# Function to list all available candidates
def list_all_candidates(candidate_data):
    """Return a simple list of all candidate names."""
    if not candidate_data:
        return "No candidates are available at the moment."

    candidate_list = "Here are the candidates we have:\n"
    candidate_list += "\n".join(candidate_data.keys())
    return candidate_list




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
        

# Function to generate a GPT-4 response that handles both general conversation and candidate-related queries
def generate_gpt4_response_with_context(user_message, candidate_data):
    """Generate a GPT-4 response that can handle both general conversation and candidate-related queries."""
    try:
        # Check if the user is asking to list all candidates
        if "list" in user_message.lower() and "candidates" in user_message.lower():
            # Prepare a list of all candidate names
            prompt = "Here is the list of available candidates:\n"
            prompt += "\n".join(candidate_data.keys())
        else:
            # Detect if the user is asking about a specific candidate
            candidate_name = None
            for name in candidate_data.keys():
                if name.lower() in user_message.lower():  # Match candidate name case-insensitively
                    candidate_name = name
                    break

            # If a specific candidate is found, prepare their information
            if candidate_name:
                candidate_info = candidate_data[candidate_name]
                prompt = f"Here is the information about {candidate_name}:\n"
                for section, content in candidate_info.items():
                    prompt += f"{section}: {content}\n"
            else:
                # Fallback for general queries or if no candidate is found
                prompt = "I couldn't find any information on the candidate you're asking about. Please try asking for specific candidates or request a list of available candidates."

        # Prepare the system message explicitly stating the purpose of the bot
        messages = [
            {"role": "system", "content": "You are a helpful assistant with access to preloaded job candidate information. Your job is to answer user queries based on this preloaded information."},
            {"role": "user", "content": user_message},
            {"role": "system", "content": prompt}
        ]

        # Call GPT-4 with the context
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            max_tokens=500
        )

        return response.choices[0].message['content']
    except Exception as e:
        print(f"Error generating GPT-4 response: {e}")
        return "Sorry, I'm having trouble processing that right now. Could you try again?"

        

# Initialize the Flask app
app = Flask(__name__)        
        
# Function to handle webhook
@app.route("/webhook", methods=["POST"])
def handle_webhook():
    """Function to handle incoming webhook messages from Facebook Messenger."""
    try:
        body = request.get_json()
        print(f"Received payload: {body}")  # Log the entire payload for debugging

        if body.get("object") == "page":
            for entry in body["entry"]:
                messaging_event = entry.get("messaging")[0]
                sender_id = messaging_event["sender"]["id"]

                # Handle messages
                if "message" in messaging_event and "text" in messaging_event["message"]:
                    message_text = messaging_event["message"]["text"].lower()  # Normalize to lowercase
                    print(f"Received message: {message_text} from sender {sender_id}")

                    # Check if the user is asking to list all candidates
                    if "list" in message_text and "candidates" in message_text:
                        response_message = list_all_candidates(candidate_data)
                    else:
                        # Send message to GPT-4 for natural processing (greetings, conversations, and candidate queries)
                        response_message = generate_gpt4_response_with_context(message_text, candidate_data)

                    print(f"Response message: {response_message}")  # Debugging
                    send_message_in_chunks(sender_id, response_message)

        return "EVENT_RECEIVED", 200
    except Exception as e:
        print(f"Error in webhook handler: {e}")
        return "Error", 500





# Entry point for running the Flask application, specifying the port, enabling debug mode, and allowing external access.

if __name__ == "__main__":
    app.run(port=3000, debug=True, host="0.0.0.0")
