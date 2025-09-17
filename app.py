import streamlit as st
import requests
import json

# The URL where your FastAPI backend is running
BACKEND_URL = "http://127.0.0.1:8000/match-resume-job"

# --- Streamlit User Interface ---
st.set_page_config(layout="wide")
st.title("🤖 AI-Powered Resume Matcher")
st.write("Upload a resume and paste a job description to see the match analysis.")

# Create two columns for a cleaner layout
col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 Candidate's Resume")
    resume_file = st.file_uploader("Upload Resume PDF", type=["pdf"])

with col2:
    st.subheader("💼 Job Description")
    job_description = st.text_area("Paste Job Description Here", height=300)

# The button to trigger the analysis
analyze_button = st.button("Analyze Match", type="primary")

if analyze_button:
    # Check if both files are provided
    if resume_file and job_description:
        with st.spinner("Analyzing... The AI is on the case! 🕵️‍♂️"):
            # Prepare the data to be sent to the backend
            # The resume is sent as a file, and the job description is sent as a form field
            files = {'resume_file': (resume_file.name, resume_file, 'application/pdf')}
            data = {'job_description': job_description}

            try:
                # Make the POST request to the FastAPI backend
                response = requests.post(BACKEND_URL, files=files, data=data)

                # If the request was successful
                if response.status_code == 200:
                    st.success("Analysis Complete!")
                    
                    # Get the JSON data from the response
                    results = response.json()
                    
                    # Display the results
                    st.subheader("Parsed Job Description")
                    st.json(results.get("parsed_job", {}))
                    
                    st.subheader("Match Analysis")
                    # The analysis content might be a string-encoded JSON, so we parse it
                    match_analysis = json.loads(results.get("match_analysis", "{}"))
                    st.json(match_analysis)

                    st.info(f"Retrieved {results.get('retrieved_sections', 0)} relevant sections from the resume for analysis.")

                else:
                    # Handle errors from the backend
                    st.error(f"Error from server: {response.status_code} - {response.text}")

            except requests.exceptions.RequestException as e:
                # Handle network-level errors
                st.error(f"Failed to connect to the backend: {e}")
    else:
        # Warning if the user clicks the button without providing inputs
        st.warning("Please upload a resume and provide a job description.")