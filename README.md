# 🏥 DocAssist Clinical Aid v1.0

DocAssist is an AI-powered clinical assistant designed to provide doctors and healthcare professionals with instant access to patient data, slide-based document search, real-time medical guideline updates, and intelligent query assistance.


https://github.com/user-attachments/assets/3db555ee-d6a4-4f91-b073-14571b8ebee1


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


