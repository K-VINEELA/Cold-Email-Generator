from flask import Flask, request, render_template
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from langchain_groq import ChatGroq

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate_email', methods=['POST'])
def generate_email():
    try:
        # Get user inputs
        job_link = request.form['job_link']
        user_name = request.form['user_name']
        user_role = request.form['user_role']
        user_expertise = request.form['user_expertise']
        tone_choice = request.form['tone_choice']
        language_choice = request.form['language_choice']

        # Load job posting data
        loader = WebBaseLoader(job_link)
        page_data = loader.load().pop().page_content

        # Extract job postings
        prompt_extract = PromptTemplate.from_template(
            """
            ### SCRAPED TEXT FROM WEBSITE:
            {page_data}
            ### INSTRUCTION:
            Extract the job postings from the above text and return them in JSON format with the following keys:
            `role`, `experience`, `skills`, and `description`. Only return the valid JSON.
            """
        )
        llm = ChatGroq(
            temperature=0,
            groq_api_key='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',
            model_name="llama-3.1-70b-versatile"
        )
        response_extract = llm.invoke(prompt_extract.format(page_data=page_data))
        json_parser = JsonOutputParser()
        job_details = json_parser.parse(response_extract.content)

        # Skill matching score
        def calculate_skill_match(user_skills, job_skills):
            if isinstance(job_skills, list):
                job_skills = " ".join(job_skills)
            vectorizer = CountVectorizer().fit_transform([user_skills, job_skills])
            vectors = vectorizer.toarray()
            return round(cosine_similarity(vectors)[0][1] * 100, 2)

        skill_match_score = calculate_skill_match(user_expertise, job_details.get("skills", ""))

        # Email tones and language options
        email_tones = {
            "1": "Write a professional and formal email.",
            "2": "Write a friendly and casual email.",
            "3": "Write a persuasive email highlighting why the applicant is the best fit."
        }
        language_options = {
            "1": "Write the email in English.",
            "2": "Write the email in Spanish.",
            "3": "Write the email in French."
        }

        # Generate the email
        prompt_email = PromptTemplate.from_template(
            f"""
            ### JOB DESCRIPTION:
            {{job_details}}

            ### USER DETAILS:
            Name: {{user_name}}
            Role Applied For: {{user_role}}
            Expertise: {{user_expertise}}

            ### INSTRUCTION:
            {email_tones[tone_choice]} {language_options[language_choice]}
            Ensure the email is concise and enthusiastic.
            """
        )
        response_email = llm.invoke(prompt_email.format(
            job_details=job_details,
            user_name=user_name,
            user_role=user_role,
            user_expertise=user_expertise,
            skill_match_score=skill_match_score
        ))

        # Render the generated email in email_display.html
        return render_template('email_display.html', email_content=response_email.content)

    except Exception as e:
        return render_template('email_display.html', email_content=f"Error: {str(e)}")

if __name__ == "__main__":
    app.run(debug=True)
