from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import os
import requests
import logging
import json
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '../frontend')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

# Create uploads folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def serve_frontend():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(FRONTEND_DIR, path)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({"error": "No message provided"}), 400

        user_message = data["message"].strip()
        if not user_message:
            return jsonify({"error": "Empty message"}), 400

        logger.info(f"User message: {user_message}")

        # System prompt for Indian Judiciary chatbot
        system_prompt = """
        **You are an AI assistant designed to provide information and guidance related to the Indian Judiciary system.**
        - **Scope:** Only answer questions related to Indian laws, court procedures, legal rights, case filing, and related topics.
        - **Response Rules:**
          1. **Be informative and accurate:** Provide clear and accurate information based on Indian laws and judicial procedures.
          2. **Avoid legal advice:** Do NOT provide legal advice or act as a substitute for professional legal counsel. Encourage users to consult a qualified lawyer for specific legal issues.
          3. **Provide resources:** Offer helpful resources such as links to legal acts, court services, and legal aid organizations.
          4. **No internal monologue:** Do NOT generate `<think>`, `</think>`, or any reasoning steps.
          5. **Direct answers:** Provide clear, concise responses without unnecessary explanations.

        **Examples:**
        - User: "How do I file a case in India?"
          Assistant: "To file a case in India, you need to visit your local court or use the e-Courts portal for online filing. You will need to submit the required documents and pay the applicable fees. For more details, visit https://services.ecourts.gov.in/."

        - User: "What are my rights if I am arrested?"
          Assistant: "If you are arrested in India, you have the right to know the grounds of arrest, the right to legal representation, and the right to be produced before a magistrate within 24 hours. You can also seek legal aid through NALSA if you cannot afford a lawyer. For more information, visit https://nalsa.gov.in/."

        If the question is unrelated to the Indian Judiciary system, respond: "This question is outside my area of expertise. I'm here to help with information related to the Indian Judiciary system."
        """
        full_prompt = f"{system_prompt}\n\nUser: {user_message}\nAssistant:"

        # Call Ollama API
        ollama_response = requests.post(
            "http://localhost:11435/api/generate",
            json={"model": "llama3.1", "prompt": full_prompt, "stream": True},
            stream=True
        )

        if ollama_response.status_code != 200:
            logger.error(f"Ollama error: {ollama_response.text}")
            return jsonify({"error": "Failed to connect to the AI model"}), 500

        def generate():
            for chunk in ollama_response.iter_lines():
                if chunk:
                    decoded_chunk = chunk.decode('utf-8')
                    try:
                        chunk_json = json.loads(decoded_chunk)
                        response_text = chunk_json.get("response", "")
                        
                        # Remove <think> content (including cases with missing closing tags)
                        response_text = re.sub(r'<think>.*?(</think>|$)', '', response_text, flags=re.DOTALL)
                        
                        # Clean residual whitespace
                        response_text = re.sub(r'\s+', ' ', response_text).strip()
                        
                        yield response_text
                    except json.JSONDecodeError:
                        yield ""

        return Response(generate(), content_type='text/plain')

    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/upload_document', methods=['POST'])
def upload_document():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            logger.info(f"Document uploaded: {filename}")
            
            # You would normally extract text from the document here based on file type
            # For simplicity, we're just grabbing the filename and asking model to summarize
            
            # System prompt for document summarization
            system_prompt = """
            **You are an AI assistant designed to summarize legal documents related to the Indian Judiciary system.**
            - **Task:** Summarize the uploaded document in a clear and concise manner.
            - **Response Rules:**
              1. **Be informative and accurate:** Extract key information from the document.
              2. **Legal context:** Focus on legal implications and context within Indian law.
              3. **No internal monologue:** Do NOT generate `<think>`, `</think>`, or any reasoning steps.
              4. **Structure:** Provide a structured summary with key points.
              5. **Disclaimer:** Include a disclaimer that this is not legal advice.
            """
            
            full_prompt = f"{system_prompt}\n\nUser uploaded document: {filename}\nPlease summarize this document.\n\nAssistant:"
            
            # Call Ollama API
            ollama_response = requests.post(
                "http://localhost:11436/api/generate",
                json={"model": "llama3.1", "prompt": full_prompt, "stream": True},
                stream=True
            )
            
            if ollama_response.status_code != 200:
                logger.error(f"Ollama error: {ollama_response.text}")
                return jsonify({"error": "Failed to process the document"}), 500
            
            def generate():
                for chunk in ollama_response.iter_lines():
                    if chunk:
                        decoded_chunk = chunk.decode('utf-8')
                        try:
                            chunk_json = json.loads(decoded_chunk)
                            response_text = chunk_json.get("response", "")
                            
                            # Remove <think> content
                            response_text = re.sub(r'<think>.*?(</think>|$)', '', response_text, flags=re.DOTALL)
                            
                            # Clean residual whitespace
                            response_text = re.sub(r'\s+', ' ', response_text).strip()
                            
                            yield response_text
                        except json.JSONDecodeError:
                            yield ""
            
            return Response(generate(), content_type='text/plain')
        else:
            return jsonify({"error": "File type not allowed"}), 400
            
    except Exception as e:
        logger.error(f"Error in document upload: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)