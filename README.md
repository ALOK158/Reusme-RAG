# 📄 Resume-RAG: Your Personal AI Career Copilot

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> An intelligent agent designed to optimize your resume for any job description, significantly increasing your chances of passing automated screening and landing an interview.

---

<p align="center">
  <img src="URL_TO_YOUR_PROJECT_DEMO.gif" alt="Project Demo" width="800"/>
</p>

---

## The Problem This Solves

Applying for jobs often feels like sending your resume into a black box. You don't know why you get rejected or what you could have done better. This tool demystifies the process by providing **data-driven feedback**, showing you exactly where your resume aligns with a job's requirements and where it falls short.

## ✨ Core Features

* 📄 **Dynamic Resume Parsing**: Ingests and understands your resume in PDF format.
* 🤖 **AI-Powered Gap Analysis**: Intelligently structures job descriptions and compares them against your resume to identify key missing skills and experience.
* 💡 **Actionable Optimization**: Provides a clear breakdown of matching qualifications, gaps, and an estimated match score to help you tailor your application effectively.

---

## 🛠️ Technical Architecture

This project is built on a modern RAG (Retrieval-Augmented Generation) pipeline to ensure accurate, context-aware analysis.

<p align="center">
<pre>
+----------------------+      +-----------------------------+
|   Resume (PDF)       |      | Job Description (Raw Text)  |
+----------------------+      +-----------------------------+
           |                             |
           v                             v
+----------------------+      +-----------------------------+
|  PDFMinerLoader      |      |   LLM (Gemini) for JSON     |
|  Semantic Chunker    |      |   Extraction & Structuring  |
+----------------------+      +-----------------------------+
           |                             |
           v                             v
+----------------------+      +-----------------------------+
| Embeddings           |      | Structured Job Data (JSON)  |
| (Google Generative AI) |      |   - Required Skills         |
+----------------------+      |   - Responsibilities        |
           |                  +-----------------------------+
           v                             |
+----------------------+                 |
| FAISS Vector Store   | <---------------+
| (Resume Knowledge    |                 |
| Base)                | <---------------+--- Multi-Query Retriever
+----------------------+
           |
           v
+----------------------+
|  Final Analysis      |
|  - Match Score       |
|  - Gap Report        |
+----------------------+
</pre>
</p>

1.  **Resume Ingestion**: The resume PDF is loaded and parsed. It's then split into semantic chunks, embedded into vectors using Google's models, and stored in a **FAISS** vector database. This creates a searchable knowledge base of the user's experience.
2.  **Job Description Structuring**: A raw job description is passed to an LLM (Gemini) which extracts key information (`required_skills`, `responsibilities`, etc.) into a structured JSON format.
3.  **RAG Analysis**: A **Multi-Query Retriever** uses the structured job data to generate multiple, precise questions to query the resume vector store. The retrieved results are synthesized to produce the final, detailed comparison report.

---

## 💡 Skills Showcased

This project demonstrates proficiency in:
* **AI/ML**: Retrieval-Augmented Generation (RAG), Large Language Models (LLM), Vector Databases, Semantic Search.
* **Prompt Engineering**: Designing effective prompts for LLM-based data extraction and structuring.
* **Python & Core Libraries**: Python, LangChain, FAISS, PDFMiner.
* **Software Architecture**: Designing and implementing a multi-step data processing pipeline.
* **Version Control**: Git & GitHub for project management.

---

## 🚀 Getting Started

Follow these steps to get the project running on your local machine.

### Prerequisites
* Python 3.9+
* A Google API Key

### Installation
1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/ALOK158/Reusme-RAG.git](https://github.com/ALOK158/Reusme-RAG.git)
    cd Reusme-RAG
    ```
2.  **Create and Activate a Virtual Environment**
    ```bash
    # For Windows
    python -m venv venv
    venv\Scripts\activate
    
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install Dependencies**
    *(Ensure you have a `requirements.txt` file in your repository)*
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set Up Environment Variables**
    Create a file named `.env` in the root directory and add your API key:
    ```
    # .env file
    GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY_HERE"
    ```

### Running the Application
```bash
python your_main_script.py