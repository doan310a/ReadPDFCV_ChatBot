from flask import Flask, request
import os
import openai
import pandas as pd
from fbmessenger import BaseMessenger

app = Flask(__name__)

# Facebook Messenger API credentials
FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')

# OpenAI API credentials
openai.api_key = os.getenv('OPENAI_API_KEY')

# Global variable to store the knowledge base
cv_knowledge_base = {}

# Load CV data from Excel into a knowledge base (dictionary)
def load_cv_data():
    xls = pd.ExcelFile('output.xlsx')
    cv_data = {}
    for sheet_name in xls.sheet_names:
        # Load each candidate's sheet into a DataFrame
        df = pd.read_excel(xls, sheet_name)
        # Convert DataFrame into a dictionary
        candidate_dict = df.to_dict(orient='records')
        cv_data[sheet_name] = candidate_dict
    return cv_data

# Build the knowledge base
cv_knowledge_base = load_cv_data()

# Function to search the knowledge base for candidate-specific queries
def search_cv_data(candidate_name, section=None):
    candidate_info = cv_knowledge_base.get(candidate_name, None)
    if not candidate_info:
        return f"Sorry, I couldn't find any information for the candidate '{candidate_name}'."
    
    if section:
        # Search within the candidate's CV for a specific section (e.g., 'Education')
        for entry in candidate_info:
            if entry.get('Section') and section.lower() in entry['Section'].lower():
                return entry['Details']
        return f"Sorry, I couldn't find the section '{section}' for {candidate_name}."
    
    # If no specific section is provided, return all information for the candidate
    return f"Here is the information I found for {candidate_name}: {candidate_info}"

# Function to generate a dynamic response using OpenAI GPT-4
def generate_gpt4_response(message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        return f"An error occurred while generating a response: {str(e)}"

# Messenger bot logic
class Messenger(BaseMessenger):
    def __init__(self, page_access_token):
        self.page_access_token = page_access_token
        super().__init__(self.page_access_token)

    def message(self, payload):
        print("Received payload:", payload)

        if 'sender' in payload and 'message' in payload:
            sender_id = payload['sender'].get('id', None)
            message_text = payload['message'].get('text', '')

            if sender_id and message_text:
                print(f"Received message: {message_text} from sender {sender_id}")

                candidate_name = None
                section = None

                if "education" in message_text.lower():
                    section = "Education"
                    candidate_name = self.extract_candidate_name(message_text)
                elif "experience" in message_text.lower():
                    section = "Experience"
                    candidate_name = self.extract_candidate_name(message_text)

                if candidate_name and section:
                    response = search_cv_data(candidate_name, section)
                else:
                    # Use GPT-4 for general conversational queries
                    prompt = f"User asked: {message_text}. Respond naturally like ChatGPT."
                    response = generate_gpt4_response(prompt)

                # Send response
                print(f"Sending message to recipient {sender_id}: {response}")
                self.send({
                    'recipient': {'id': sender_id},
                    'message': {'text': response}
                })
            else:
                print("Error: 'sender_id' or 'message' missing.")
        else:
            print("Error: Payload does not contain expected 'sender' or 'message' fields.")

    def send(self, payload):
        try:
            recipient_id = payload['recipient']['id']
            # Payload should include a "recipient" and "message" field at the top level
            response_payload = {
                'recipient': {'id': recipient_id},
                'message': {'text': payload['message']['text']}
            }
            # Sending payload to Messenger API
            response = self.client.send(response_payload, messaging_type='RESPONSE')
            print(f"Message sent successfully to {recipient_id}: {response}")
        except Exception as e:
            print(f"Failed to send message: {str(e)}")


    def extract_candidate_name(self, message):
        # Placeholder function to extract candidate name, improve using NLP if needed
        return "John Doe"

messenger = Messenger(FB_PAGE_ACCESS_TOKEN)

# Endpoint to handle verification of Facebook webhook
@app.route('/webhook', methods=['GET'])
def verify():
    token_sent = request.args.get("hub.verify_token")
    if token_sent == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return 'Invalid verification token'

# Endpoint to receive messages from Facebook
@app.route('/webhook', methods=['POST'])
def webhook():
    output = request.get_json()
    for event in output['entry']:
        messaging = event['messaging']
        for message in messaging:
            if message.get('message'):
                messenger.message(message)
    return "Message Processed"

if __name__ == "__main__":
    app.run(port=3000, debug=True)
