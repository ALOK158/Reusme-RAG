from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from langchain_community.document_loaders import PDFMinerLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS

from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain.output_parsers.json import SimpleJsonOutputParser
import os
import tempfile
from fastapi import Form
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="RAG Resume Matcher", description="AI-powered resume and job matching")

# Initialize your models (same as in notebook)
embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)

class JobDescription(BaseModel):
    description: str

class MatchRequest(BaseModel):
    job_description: str

@app.get("/")
def health_check():
    return {"message": "RAG Resume Matcher API is running!", "status": "healthy"}

@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """Process uploaded resume PDF and return structured data"""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Process with your existing logic
        loader = PDFMinerLoader(temp_file_path, mode="single")
        docs = loader.load()
        
        # Clean up temp file
        os.unlink(temp_file_path)
        
        return {"resume_content": docs[0].page_content, "filename": file.filename}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/match-resume-job")
async def match_resume_job(job_description: str = Form(...), resume_file: UploadFile = File(...)):
    """Complete resume-job matching pipeline"""
    try:
        # Process resume (same as upload_resume)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            content = await resume_file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        loader = PDFMinerLoader(temp_file_path, mode="single")
        docs = loader.load()
        resume_text = docs[0].page_content
        
        # Text splitting and vectorization
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
        texts = text_splitter.split_text(resume_text)
        vector_store = FAISS.from_texts(texts, embedding_model)
        
        # Job description extraction (your existing logic)
        job_extraction_prompt = """Extract structured data from job descriptions.
        Return ONLY valid JSON with these keys: title, company, location, summary, 
        responsibilities, required_skills, preferred_skills, education_requirements, 
        experience_level, Else"""
        
        # Parse job description
        job_chain = ChatPromptTemplate.from_template(job_extraction_prompt) | llm | SimpleJsonOutputParser()
        # New, corrected line
        parsed_job = job_chain.invoke({"description": job_description})
        
        # Multi-query retrieval
        base_retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 7})
        multi_query_retriever = MultiQueryRetriever.from_llm(retriever=base_retriever, llm=llm)
        
        # Build search query and retrieve
        search_terms = []
        for key in ["responsibilities", "required_skills", "preferred_skills"]:
            if key in parsed_job and parsed_job[key]:
                search_terms.extend(parsed_job[key])
        
        search_query = ", ".join(search_terms[:10])  # Limit to avoid too long queries
        retrieved_docs = multi_query_retriever.get_relevant_documents(search_query)
        
        # Comparison analysis
        comparison_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a career-matching assistant. Use ONLY the resume snippets provided to judge the fit."),
            ("user", "Job description (JSON):\n{job_json}"),
            ("user", "Resume snippets:\n{snippets}"),
            ("user", "Return a JSON with keys: matches, gaps, overall_fit")
        ])
        
        comparison_chain = comparison_prompt | llm
        snippets = "\n---\n".join(doc.page_content for doc in retrieved_docs)
        
        match_result = comparison_chain.invoke({
            "job_json": parsed_job,
            "snippets": snippets
        })
        
        # Clean up
        os.unlink(temp_file_path)
        
        return {
            "parsed_job": parsed_job,
            "match_analysis": match_result.content,
            "retrieved_sections": len(retrieved_docs)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
