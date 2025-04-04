# 🏥 DocAssist Clinical Aid v1.0

DocAssist RAG is an AI-powered clinical assistant designed to provide doctors and healthcare professionals with instant access to patient data, slide-based document search, real-time medical guideline updates, and intelligent query assistance using Retrieval-Augmented Generation (RAG).

📌 Features

1. Real-Time Medical Knowledge & Second Opinions

2. Smart Data Sync & Pathway Integration

3. AI-Powered Decision Support

4. Developer-Friendly API & UI


https://github.com/user-attachments/assets/f7827b3d-9467-449d-a3e9-5a18ea6128e2




## 📌 Features

- **👨⚕ Patient Management**: View, update, and analyze patient vitals and medications.
- **🔍 Query Assistant**: Ask clinical questions and get RAG-based document-grounded answers using slide metadata.
- **📚 Update Center**: See live updates to medical guidelines and monitor document statistics.
- **🖼 Slide Search**: Visual preview of pages from indexed medical PDFs with support for slide navigation.

## 🧠 Tech Stack

| Component          | Tech Used            |
|--------------------|----------------------|
| Frontend           | Streamlit            |
| Backend API        | FastAPI              |
| Vector Search      | Pathway RAG Client   |
| Styling            | Custom CSS (Streamlit) |
| PDF/Slide Viewer   | Image+PDF URL Preview |
| Data Storage       | Environment Variables / JSON |
| Live Data Fetching | `requests` module    |

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Docker (optional for Pathway and NGINX services)
- Virtual environment (recommended)

### 1. Clone the repository

```bash
git clone https://github.com/992manav/DocAssist.git

docker-compose up --build -d

