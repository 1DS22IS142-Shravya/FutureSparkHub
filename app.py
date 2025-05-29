# /my_career_portal/app.py
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
import os
import uuid 
from dotenv import load_dotenv

# Load .env file once at the very beginning for all subsequent imports and app config
load_dotenv() 

# Import refactored logic
from resume_builder_logic import generate_resume_pdf_from_data, generate_ai_summary_for_resume
from higher_education_fetcher_logic import search_colleges_globally_api
from career_ai_chatbot_logic import get_chatbot_answer_from_question, initialize_chatbot_components_globally

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'generated_resumes')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Chatbot Initialization ---
# This flag tracks if the chatbot has been initialized for the current app instance/worker.
_chatbot_app_initialized_flag = False

@app.before_request
def ensure_chatbot_is_initialized_for_app():
    global _chatbot_app_initialized_flag
    # Only run initialization for relevant endpoints to avoid unnecessary overhead
    if request.endpoint in ['api_chat', 'career_chatbot']:
        if not _chatbot_app_initialized_flag:
            app.logger.info("Flask App: Initializing chatbot components before first relevant request...")
            if initialize_chatbot_components_globally():
                _chatbot_app_initialized_flag = True
                app.logger.info("Flask App: Chatbot components initialized successfully for this worker.")
            else:
                app.logger.error("Flask App: Chatbot components FAILED to initialize. Chat functionality may be affected.")
    # For other endpoints, or if already initialized, this function does nothing further.

# --- Page Routes ---
@app.route('/')
def home(): return render_template('home.html')

@app.route('/about')
def about(): return render_template('about.html')

@app.route('/resume-builder')
def resume_builder(): return render_template('resume_builder.html')

@app.route('/education-fetcher')
def education_fetcher(): return render_template('education_fetcher.html')

@app.route('/career-chatbot')
def career_chatbot(): return render_template('career_chatbot.html')

# --- API Endpoints ---
@app.route('/api/generate_summary', methods=['POST'])
def api_generate_summary():
    try:
        data = request.get_json()
        keywords = data.get('keywords', []) 
        experience_highlights = data.get('experience_highlights', "")
        
        app.logger.info(f"AI Summary request: Keywords='{keywords}', Highlights='{experience_highlights}'")

        if not keywords and not experience_highlights:
            return jsonify({"error": "Keywords or experience highlights are required for AI summary."}), 400

        summary = generate_ai_summary_for_resume(keywords, experience_highlights)
        
        # Returning 200 OK even for AI-side "errors" allows the frontend to display the message.
        # For a pure API, a 4xx/5xx might be more semantically correct if the AI fails to generate usable content.
        if "Error" in summary or "Could not generate" in summary or "disabled" in summary or "blocked" in summary.lower():
             app.logger.warning(f"AI Summary generation issue: {summary}")
             return jsonify({"summary": summary, "ai_message": summary}), 200 
        return jsonify({"summary": summary})
    except Exception as e:
        app.logger.error(f"Error in /api/generate_summary: {e}", exc_info=True)
        return jsonify({"error": f"An internal server error occurred generating summary: {str(e)}"}), 500

@app.route('/api/build_resume', methods=['POST'])
def api_build_resume():
    try:
        data = request.get_json()
        if not data:
            app.logger.warning("No input data received for resume building.")
            return jsonify({"error": "No input data provided"}), 400
        
        app.logger.info(f"Resume build request for: {data.get('name', 'N/A')}")

        # --- Data Transformations ---
        # This section adapts frontend data to the backend PDF generator's expected format.
        # Ideal future improvement: Align frontend data structure with backend, or use Pydantic models
        # for explicit validation and transformation.

        # 1. Project stack: frontend sends 'stack_str', PDF func needs 'stack' (list)
        if 'projects' in data and isinstance(data['projects'], list):
            for proj in data['projects']:
                if 'stack_str' in proj and isinstance(proj['stack_str'], str):
                    proj['stack'] = [s.strip() for s in proj['stack_str'].split(',') if s.strip()]
        
        # 2. Skills: frontend sends 'skills_input' (comma-separated string), PDF func needs 'skills' (list)
        if 'skills_input' in data and isinstance(data['skills_input'], str):
            data['skills'] = [s.strip() for s in data['skills_input'].split(',') if s.strip()]
        elif 'skills' not in data: # Ensure skills key exists even if empty
            data['skills'] = []

        # 3. Experience/Project descriptions: Frontend JS should already send these as lists of strings.
        #    The resume_builder_logic.py's PDF function expects `description` as a list of bullet points.
        #    No transformation here if frontend handles it.

        # 4. Achievements: PDF function expects `description_str` (newline-separated string).
        #    Frontend JS might send description_list or description_str.
        if 'achievements' in data and isinstance(data['achievements'], list):
            for ach in data['achievements']:
                if 'description_list' in ach and isinstance(ach['description_list'], list): # If JS sent a list
                    ach['description_str'] = "\n".join(ach['description_list'])
                # If 'description_str' is already a string from frontend, it's fine.

        unique_id = uuid.uuid4().hex[:8]
        pdf_filename_base = f"resume_{data.get('name', 'user').replace(' ', '_').replace('.', '')}_{unique_id}.pdf"
        output_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename_base)

        generated_file_path = generate_resume_pdf_from_data(data, output_pdf_path)

        if generated_file_path and os.path.exists(generated_file_path):
            download_url = url_for('download_resume', filename=os.path.basename(generated_file_path), _external=True)
            app.logger.info(f"Resume PDF generated: {os.path.basename(generated_file_path)}")
            return jsonify({"download_url": download_url, "message": "Resume PDF generated successfully."})
        else:
            app.logger.error(f"Failed to generate or locate resume PDF. Expected at: {output_pdf_path}")
            return jsonify({"error": "Failed to generate resume PDF. Check server logs for details."}), 500

    except Exception as e:
        app.logger.error(f"Error in /api/build_resume: {e}", exc_info=True)
        return jsonify({"error": f"An internal server error occurred building resume: {str(e)}"}), 500

@app.route('/downloads/resumes/<filename>')
def download_resume(filename):
    app.logger.info(f"Download request for resume: {filename}")
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/api/search_education', methods=['GET'])
def api_search_education():
    try:
        country = request.args.get('country', '')
        course_type = request.args.get('fieldOfStudy', '') 
        degree_level = request.args.get('degreeLevel') 
        app.logger.info(f"Education search: Country='{country}', Course='{course_type}', Degree='{degree_level}'")
        
        # Prevents overly broad searches
        if not course_type and not country and (not degree_level or degree_level == "Any"):
             app.logger.warning("Education search is too broad. No country, course, or specific degree specified. Returning empty.")
             return jsonify([]), 200 # Return empty list with 200 OK

        results = search_colleges_globally_api(country, course_type, degree_level)
        app.logger.info(f"Edu Fetcher API returned {len(results)} institutions.")
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Error in /api/search_education: {e}", exc_info=True)
        return jsonify({"error": f"An internal server error occurred searching education: {str(e)}"}), 500

@app.route('/api/chat', methods=['POST'])
def api_chat():
    global _chatbot_app_initialized_flag
    if not _chatbot_app_initialized_flag:
        # This case should ideally be rare due to before_request, but acts as a safety net.
        app.logger.error("Chatbot not initialized when /api/chat called. Attempting re-initialization.")
        if not initialize_chatbot_components_globally():
            app.logger.critical("Chatbot re-initialization FAILED in /api/chat. Service unavailable.")
            return jsonify({"error": "Chatbot service is currently unavailable. Please try again later."}), 503
        _chatbot_app_initialized_flag = True 
        app.logger.info("Chatbot re-initialized successfully within /api/chat.")


    try:
        data = request.get_json()
        user_message = data.get('message')
        if not user_message:
            app.logger.warning("No message received for chatbot API.")
            return jsonify({"error": "No message provided"}), 400

        app.logger.info(f"Chat API received user message: '{user_message}'")
        bot_response_text = get_chatbot_answer_from_question(user_message)
        app.logger.info(f"Chat API sending response (first 100 chars): '{bot_response_text[:100]}...'")
        return jsonify({"response": bot_response_text})
    except Exception as e:
        app.logger.error(f"Error in /api/chat: {e}", exc_info=True)
        return jsonify({"error": f"An internal server error occurred in chat: {str(e)}"}), 500

if __name__ == '__main__':
    # For development, debug=True is fine.
    # For production, set debug=False.
    # The @app.before_request handles chatbot initialization per worker if using Gunicorn/uWSGI.
    app.run(debug=True, host='0.0.0.0', port=5000)