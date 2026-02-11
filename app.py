from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional
import os
import traceback

# Load Groq API key
load_dotenv()
print("GROQ_API_KEY loaded:", os.getenv("GROQ_API_KEY"))

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Embedding model
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
documents = []
doc_vectors = None

# Groq LLM
llm_model = ChatGroq(temperature=0.5, model_name="llama-3.3-70b-versatile")

# Structured output schema
class ResumeAnalysis(BaseModel):
    extract: str  # Format: <name, email, skills, traits>
    summary: str
    why_selected: str

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/upload', methods=['POST'])
def upload():
    global documents, doc_vectors
    uploaded = request.files.getlist("resumes")
    for file in uploaded:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        loader = PDFPlumberLoader(filepath)
        docs = loader.load()
        for doc in docs:
            doc.metadata["filename"] = filename
            doc.metadata["filepath"] = filepath
        documents.extend(docs)

    doc_vectors = FAISS.from_documents(documents, embeddings)
    return jsonify({"message": f"{len(uploaded)} resume(s) uploaded and processed."})

@app.route('/chatbot', methods=['POST'])
def chatbot():
    global doc_vectors
    data = request.get_json()
    question = data.get("question", "")
    mode = data.get("mode", "chat")

    if mode == "match_resumes":
        if not doc_vectors:
            return jsonify({"matches": [], "message": "No resumes uploaded yet."})

        raw_matches = doc_vectors.similarity_search_with_score(question, k=3)
        seen = set()
        filtered = []

        for match, _ in raw_matches:
            fname = match.metadata["filename"]
            if fname in seen:
                continue
            seen.add(fname)

            resume_text = match.page_content.strip()

            prompt = (
                "You are an HR assistant reviewing a candidate's resume for a job.\n"
                "Please respond in this exact format:\n"
                "Extract: <name, email if available, key skills, traits>\n"
                "Summary: <one-line summary>\n"
                "Why Selected: <one-line reason for selection>\n\n"
                f"Job Description:\n{question}\n\n"
                f"Resume:\n{resume_text}"
            )

            try:
                structured_llm = llm_model.with_structured_output(ResumeAnalysis)
                parsed: ResumeAnalysis = structured_llm.invoke(prompt)

                print(f"\nLLM Structured Output for {fname}:\n{parsed}\n")

                raw = parsed.extract.strip()
                fields = [f.strip() for f in raw.split(",")]

                name = fields[0] if fields else "N/A"
                email = next((f for f in fields if "@" in f), "N/A")
                rest = [f for f in fields if f != name and f != email]

                skills_traits = ", ".join(rest)

                extract = (
                    f"Name: {name}<br>"
                    f"Email: {email}<br>"
                    f"Skills & Traits: {skills_traits}"
                )

                summary = f"Summary: {parsed.summary}"
                reason = f"Why Selected: {parsed.why_selected}"

                print(f"Extracted for {fname}:\n{extract}\n{summary}\n{reason}\n")

            except Exception as e:
                print(f"\nLLM structured output failed for {fname}")
                traceback.print_exc()

                try:
                    fallback_response = llm_model.invoke(prompt)
                    print("Fallback LLM response:\n", fallback_response.content)
                except Exception as fallback_error:
                    print("Fallback also failed:", fallback_error)

                extract = (
                    f"Name: Not available<br>"
                    f"Email: Not available<br>"
                    f"Skills & Traits: Not available"
                )
                summary = "Summary: LLM fallback or parsing error."
                reason = "Why Selected: Resume could not be processed successfully."

            filtered.append({
                "filename": fname,
                "url": f"/download/{fname}",
                "extract": extract,
                "summary": summary,
                "reason": reason
            })

        return jsonify({"matches": filtered})

    else:
        try:
            print("Chatbot received:", question)
            ai_response = llm_model.invoke(question)
            print("Chatbot reply:", ai_response)
            response = ai_response.content
        except Exception as e:
            print("Chatbot Error:", str(e))
            response = "Sorry, I couldn't process your message right now."

        return jsonify({"response": response})

@app.route('/download/<filename>')
def download_resume(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/uploads/<filename>')
def view_pdf(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)

