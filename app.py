import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, send_from_directory
from rag import get_collection,rag_query,extract_entity_with_llm, add_pdf_to_collection, delete_from_collection
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import fitz
from fpdf import FPDF

load_dotenv()

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
CREDENTIALS_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_PATH")
ADMIN_SECRET = os.getenv("ADMIN_SECRET")

def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE,scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    return sheet

def log_to_sheets(question,answer,source):
    try:
        sheet = get_sheet()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([timestamp,question,answer,source])
        print(f"[sheets] Logged Successfully")
    except Exception as e:
        print(f"[sheets] Failed: {type(e).__name__}: {e}")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,  # Prevents JS from reading the cookie
    SESSION_COOKIE_SAMESITE='Lax', # Security against CSRF
    PERMANENT_SESSION_LIFETIME=1800 # Session expires in 30 mins
)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day","50 per hour"],
    storage_uri="memory://"
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER,exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16*1024*1024

print("Loading knowledge base...")
collection = get_collection()
print("Ready!")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat",methods=["POST"])
def chat():
    data = request.get_json()
    question = data.get("message","").strip()

    if not question:
        return jsonify({"answer":"Please type a question."}), 400
    
    if "memory" not in session:
        session["memory"] = {
            "last_question": "",
            "last_answer": "",
            "current_entity": "",
            "user_name": ""
        }
    
    memory = session.get("memory")

    q_lower = question.lower()

    if "my name is" in q_lower or "i am" in q_lower:
        name = question.split()[-1].capitalize()
        memory["user_name"] = name
        answer = f"Nice to meet you, {name}! I'll remember that. How can i help you today?"
        memory["last_question"] = question
        memory["last_answer"] = answer
        session["memory"] = memory
        session.modified = True

        log_to_sheets(question,answer,"MEMORY")

        return jsonify({"answer":answer})

    answer, source = rag_query(question,collection,memory)
    print(f"[flask] Q:{question[:50]} | Source: {source}")

    memory["last_question"] = question
    memory["last_answer"] = answer

    if(source != "MEMORY"):
        new_entity = extract_entity_with_llm(question,answer)
        if new_entity:
            memory["current_entity"] = new_entity
    
    session["memory"] = memory

    session.modified = True

    print("MEMORY:",memory)
    
    log_to_sheets(question,answer,source)

    return jsonify({"answer":answer})

@app.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json()
    password = data.get("admin_password")
    
    if password == ADMIN_SECRET:
        session.clear()
        session["admin_logged_in"] = True
        session.permanent=True
        return jsonify({"success": True, "message": "Logged in successfully"})
    return jsonify({"error": "Invalid Admin Key"}), 403

# Helper function to check login status in other routes
def is_admin():
    return session.get("admin_logged_in", False)

@app.route("/admin/upload",methods=["GET","POST"])
@limiter.limit("10 per minute")
def admin_upload():
    upload_dir = app.config["UPLOAD_FOLDER"]

    if request.method == "POST":
        # 1. Verify Admin Password
        if not is_admin():
            return jsonify({"error": "Session expired. Please log in again."}), 401
        
        # 2. Get the File from the Form
        file = request.files.get("file")
        if not file or file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        if file and file.filename.endswith('.pdf'):
            # CRITICAL: Use the raw filename to avoid "File Not Found" mismatch
            filename = file.filename 
            filepath = os.path.join(upload_dir, filename)
            
            # 3. Save the Physical File
            file.save(filepath)
            
            # 4. Trigger Vector DB Sync (add_pdf_to_collection)
            # This function wipes old chunks and indexes the new text
            success, message = add_pdf_to_collection(filepath, collection)
            
            if success:
                return jsonify({"success": True, "message": message})
            else:
                return jsonify({"error": message}), 500

        # Use a script redirect to show the message and refresh the page
        return jsonify({"error": "Invalid file format. Please upload a PDF."}), 400

    # GET Request Logic: Prepare file list for the dashboard
    pdf_files = [f for f in os.listdir(upload_dir) if f.endswith('.pdf')]
    
    file_data = []
    for f in pdf_files:
        path = os.path.join(upload_dir, f)
        mtime = os.path.getmtime(path)
        
        # Compare disk time vs. ChromaDB sync_time to set status
        existing = collection.get(where={"source": f}, include=['metadatas'])
        
        status = 'modified' 
        if existing['metadatas'] and len(existing['metadatas'])>0:
            last_sync = existing['metadatas'][0].get('sync_time', 0)
            if mtime <= last_sync:
                status = 'synced'
            else:
                status = 'modified'
        else:
            status = "modified"
        file_data.append({'name': f, 'status': status})

    return render_template("admin.html", files=file_data)

@app.route('/uploads/<filename>')
def serve_uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route("/admin/edit/<path:filename>",methods=['POST'])
@limiter.limit("20 per minute")
def edit_pdf_get(filename):
    if not is_admin():
        return jsonify({"error": "Session expired. Please log in again."}), 401
    
    filepath = os.path.join(app.config["UPLOAD_FOLDER"],filename)
    if not os.path.exists(filepath):
        return jsonify({"error":"File not found"}), 404
    

    try:
        doc = fitz.open(filepath)
        pages = [{"page": i+1, "text": page.get_text()} for i, page in enumerate(doc)]
        doc.close()
        return jsonify({"filename":filename,"pages":pages})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/admin/save/<filename>",methods=["POST"])
@limiter.limit("10 per minute")
def save_pdf(filename):
    
    if not is_admin():
        return jsonify({"error": "Session expired. Please log in again."}), 401
    data = request.get_json()
    pages = data.get("pages")
    if not pages:
        return jsonify({"error": "The file content appears to be empty. No changes made."}), 400
    
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Helvetica",size=11)
        for page_data in pages:
            pdf.add_page()
            text = page_data.get("text","").encode("latin-1","replace").decode("latin-1")
            pdf.multi_cell(0,6,text)

        pdf.output(filepath)

        return jsonify({"success": True, "message": "Saved successfully"})
    
    except Exception as e:
        print(f"[ERROR] Save failed: {str(e)}")
        return jsonify({"error": "An internal server error occurred while generating the PDF. Please check the file permissions."}), 500

@app.route("/admin/sync/<path:filename>",methods=["POST"])
def force_sync(filename):
    if not is_admin():
        return jsonify({"error": "Session expired. Please log in again."}), 401
    filepath = os.path.join(app.config["UPLOAD_FOLDER"],filename)
    success,message = add_pdf_to_collection(filepath,collection)
    if success:
        return jsonify({"success": True, "message": message})
    return jsonify({"error": message}), 500

@app.route("/admin/delete/<path:filename>", methods=["POST"])
@limiter.limit("5 per minute")
def delete_file(filename):
    if not is_admin():
        return jsonify({"error": "Session expired. Please log in again."}), 401

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    try:
        # 1. Remove from ChromaDB
        success, message = delete_from_collection(filename, collection)
        
        # 2. Remove physical file if it exists
        if os.path.exists(filepath):
            os.remove(filepath)
            
        if not success:
            return jsonify({"error": message}), 500
            
        return jsonify({"success": True, "message": f"Successfully deleted {filename}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/logout")
def admin_logout():
    session.clear() # Removes 'admin_logged_in' and 'memory'
    return jsonify({"status": "success", "message": "Logged out"})

@app.route("/clear",methods=["GET"])
def clear():
    session.clear()
    return jsonify({"status":"cleared"})

if __name__ == "__main__":
    app.run(debug=True,port=5000)

