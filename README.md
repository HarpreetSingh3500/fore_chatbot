# Fore Solutions RAG Chatbot

An intelligent AI-powered chatbot built with Flask, ChromaDB, and Ollama (Llama 3.2) that provides contextual answers about Fore Solutions using Retrieval-Augmented Generation (RAG).

## 🌟 Features

- **RAG-Powered Responses**: Combines vector search with LLM generation for accurate, context-aware answers
- **PDF Knowledge Base Management**: Admin panel for uploading, editing, and syncing PDF documents
- **Conversational Memory**: Maintains context across the conversation using Flask sessions
- **Web Search Fallback**: Automatically searches the web when local knowledge is insufficient
- **Google Sheets Logging**: Tracks all interactions for analytics and improvement
- **Smart Query Classification**: Routes queries to appropriate handlers (greetings, company info, out-of-scope, etc.)
- **Rate Limiting**: Protection against abuse with configurable limits
- **Real-time PDF Editing**: Edit PDF content directly in the browser and sync to vector database

## 🏗️ Architecture

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│         Flask Web App               │
│  ┌──────────────┐  ┌──────────────┐│
│  │   Frontend   │  │  Admin Panel ││
│  │  (Chat UI)   │  │ (PDF Manager)││
│  └──────────────┘  └──────────────┘│
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│         RAG Pipeline                │
│  ┌────────────────────────────────┐ │
│  │  1. Query Classification       │ │
│  │  2. Memory Enrichment          │ │
│  │  3. Vector Search (ChromaDB)   │ │
│  │  4. LLM Generation (Ollama)    │ │
│  │  5. Web Fallback (DuckDuckGo)  │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│     Data Storage Layer              │
│  ┌──────────┐  ┌──────────────────┐│
│  │ChromaDB  │  │  Google Sheets   ││
│  │(Vectors) │  │    (Logging)     ││
│  └──────────┘  └──────────────────┘│
└─────────────────────────────────────┘
```

## 📋 Prerequisites

- **Python 3.10+**
- **Ollama** with Llama 3.2 model installed
- **Google Cloud Service Account** (for Sheets logging)
- **Git** (for version control)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Harpreet-Singh-lks/fore-solutions-chatbot.git
cd fore-solutions-chatbot
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r req.txt
```

### 4. Install Ollama and Llama 3.2

```bash
# Install Ollama (visit https://ollama.ai for OS-specific instructions)
# Then pull the Llama 3.2 model
ollama pull llama3.2
```

### 5. Set Up Google Sheets API

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Google Sheets API and Google Drive API
3. Create a Service Account and download the JSON credentials
4. Share your target Google Sheet with the service account email
5. Save credentials as `fore-solutions-chatbot-f6c1565df71d.json` (or your chosen name)

### 6. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Flask Configuration
FLASK_SECRET_KEY=your-super-secret-key-here-change-this

# Admin Panel Security
ADMIN_SECRET=your-admin-password-here

# Google Sheets Integration
GOOGLE_SHEET_ID=your-google-sheet-id-here
GOOGLE_APPLICATION_CREDENTIALS_PATH=fore-solutions-chatbot-f6c1565df71d.json
```

**🔐 Security Note**: Never commit the `.env` file to version control!

### 7. Prepare Initial Data

1. Create an `uploads/` directory:
   ```bash
   mkdir uploads
   ```

2. Add your initial PDF documents to the `uploads/` folder

3. (Optional) Create a `team.json` file for structured team data:
   ```json
   [
     {
       "name": "John Doe",
       "role": "CEO",
       "linkedin": "https://linkedin.com/in/johndoe"
     }
   ]
   ```

## 🎯 Usage

### Start the Application

```bash
python app.py
```

The app will be available at: `http://localhost:5000`

### User Chat Interface

1. Navigate to `http://localhost:5000`
2. Start asking questions about Fore Solutions
3. The chatbot maintains conversation context automatically

### Admin Panel

1. Navigate to `http://localhost:5000/admin/upload`
2. Login with your `ADMIN_SECRET` password
3. Upload, edit, or sync PDF documents
4. Changes sync automatically to the vector database

## 🔧 Configuration

### Rate Limiting

Adjust in `app.py`:

```python
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)
```

### Chunking Strategy

Modify in `rag.py`:

```python
def chunk_text(text, chunk_size=200, overlap=50):
    # Adjust chunk_size and overlap for your use case
```

### LLM Model

Change the model in `rag.py`:

```python
response = ollama.chat(
    model="llama3.2",  # Change to llama3.1, mistral, etc.
    messages=[{"role": "user", "content": prompt}]
)
```

## 📁 Project Structure

```
fore-solutions-chatbot/
├── app.py                    # Flask application & routes
├── rag.py                    # RAG logic, query processing
├── .env                      # Environment variables (NOT in git)
├── .gitignore               # Git ignore rules
├── requirements.txt         # Python dependencies
├── team.json                # Structured team data (optional)
├── uploads/                 # PDF documents (NOT in git)
├── vector_db/               # ChromaDB storage (NOT in git)
├── templates/
│   ├── index.html          # Chat interface
│   └── admin.html          # Admin dashboard
└── static/                  # (Optional) Static assets
```

## 🛡️ Security Best Practices

1. **Always use HTTPS in production** (configure reverse proxy)
2. **Rotate secrets regularly** (ADMIN_SECRET, FLASK_SECRET_KEY)
3. **Restrict admin panel access** by IP if possible
4. **Review uploaded PDFs** for sensitive information before syncing
5. **Monitor Google Sheets logs** for suspicious activity
6. **Keep dependencies updated**: `pip install --upgrade -r requirements.txt`

## 🔍 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main chat interface |
| `/chat` | POST | Process user query |
| `/admin/login` | POST | Admin authentication |
| `/admin/upload` | GET/POST | Admin dashboard & PDF upload |
| `/admin/edit/<filename>` | POST | Load PDF for editing |
| `/admin/save/<filename>` | POST | Save edited PDF |
| `/admin/sync/<filename>` | POST | Force vector DB sync |
| `/admin/delete/<filename>` | POST | Delete PDF and embeddings |
| `/admin/logout` | GET | Clear admin session |
| `/clear` | GET | Clear user session |

## 🐛 Troubleshooting

### Issue: "Ollama connection refused"
**Solution**: Ensure Ollama is running: `ollama serve`

### Issue: "ChromaDB database locked"
**Solution**: Close any other processes accessing `vector_db/`

### Issue: "Google Sheets permission denied"
**Solution**: Verify service account email has edit access to the sheet

### Issue: "PDF upload fails"
**Solution**: Check file size < 16MB and format is valid PDF

### Issue: "Web search not working"
**Solution**: DuckDuckGo might be rate-limiting; reduce `num_results` parameter

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -m "Add feature"`
4. Push to branch: `git push origin feature-name`
5. Submit a Pull Request

## 📝 License

This project is proprietary and confidential. Unauthorized copying or distribution is prohibited.

## 👨‍💻 Author

**Harpreet Singh**  
- GitHub: [@Harpreet-Singh](https://github.com/HarpreetSingh3500/)  
- LinkedIn: [Connect with me](https://www.linkedin.com/in/harpreet-singh-3500am/)

## 🙏 Acknowledgments

- **Anthropic** for Claude AI assistance during development
- **Ollama** for local LLM inference
- **ChromaDB** for vector database
- **DuckDuckGo** for web search API

## 📊 Performance Metrics

- Average response time: 2-3 seconds (PDF only)
- Average response time: 5-7 seconds (with web search)
- ChromaDB query time: <100ms for 5000+ chunks
- Concurrent users supported: 20-30 (with current rate limits)

## 🔮 Future Enhancements

- [ ] Multi-model support (GPT-4, Claude API)
- [ ] Real-time streaming responses
- [ ] Voice input/output
- [ ] Multi-language support
- [ ] Advanced analytics dashboard
- [ ] Automated PDF extraction from URLs
- [ ] Integration with Slack/Discord
- [ ] User authentication & role-based access
- [ ] Conversation export (PDF, JSON)
- [ ] A/B testing for prompt variations

---

**Made with ❤️ for Fore Solutions**
