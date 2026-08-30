import os, requests, json
os.makedirs("outputs", exist_ok=True)

from google import genai
from google.genai import types
from google.genai.types import Tool, GoogleSearch, GenerateContentConfig
client = genai.Client(api_key="{Enter Key Here}")

from docx import Document

import asyncio
from linkedin_scraper import BrowserManager, PersonScraper ,CompanyScraper, JobSearchScraper

import litellm
from litellm.types.utils import CallTypes

from bs4 import BeautifulSoup

link_holder = []
def get_job_details(url):
    ##take jobposting url remove unwanted data 
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    ##strip text and feeed parsed/stripped text into prompt compressor 
    text = soup.get_text(" ", strip=True)
    messages = [
    {"role": "user", "content": text}
    ]
    #anything above 5000 tokens will triger a compression
    compressed = litellm.compress(
        messages=messages,
        model="hf.co/prism-ml/Bonsai-1.7B-gguf",
        call_type=CallTypes.completion,
        compression_trigger=5000,
        compression_target=2000,
    )
    compressed_text = compressed["messages"][-1]["content"]
    #we will then feed the compressed text into the model inputs for comparison
    return compressed_text

found_job_links = [] 
async def search_jobs(title,location):
    ##load session data 
    async with BrowserManager(headless=True) as browser:
        await browser.load_session("session.json")
        ##open headless browser to run in background 
        scraper = JobSearchScraper(browser.page)
        #scrape based on job title, location, and number of postings limit
        jobs = await scraper.search(
            keywords=title,
            location=location,
            limit=10
        )
        ##if the job is not link holder add it 
        for job in jobs:
            if job not in link_holder:
                found_job_links.append(job)

def read_docx(filePath):
    ##check document ext and if it exist 
    if not filePath.endswith('.docx'):
        print("Please provide a valid .docx file.")
        raise ValueError("The provided file is not a DOCX.")
    if not os.path.exists(filePath):
        print(f"The file {filePath} does not exist.")
        raise FileNotFoundError(f"The file {filePath} was not found.")
    #pull document 
    doc = Document(filePath)
    #return text data 
    data = {"paragraphs": []}
    text = ""
    # Iterate through doc paragraphs and return out stripped text
    try:
        for para in doc.paragraphs:
            if para.text.strip():
                data["paragraphs"].append({
                    "text": para.text,
                    "style": para.style.name
                })
                text += para.text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error occurred while reading DOCX file: {e}")

def main(job_title, resume_docx=None, location = None):
    global found_job_links
    #pull job listings
    asyncio.run(search_jobs(job_title,location))
    if len(found_job_links) != 0:
        #remove any empty strings we find 
        found_job_links = [x for x in found_job_links if x != ""]
        #take each job link and compare against resume
        for i,link in enumerate(found_job_links):
            website = str(link)
            # Execute the text generation request using a Gemma 3 model variant
            response = client.interactions.create(
                    model="gemini-3.5-flash-lite",
                    system_instruction=f"""
                        ROLE

                        You are a Senior Engineering Hiring Manager with 15 years of experience evaluating candidates for:

                        Software Engineering
                        AI / Machine Learning
                        Robotics
                        Computer Vision
                        Embedded Systems
                        Automation
                        Applied AI

                        Evaluate candidates as you would during a real hiring process in 2026.

                        You are strict, evidence-based, and fair.


                        OBJECTIVE

                        Compare the applicant's resume against the specific job description provided.

                        Determine:

                        How closely the applicant's demonstrated qualifications match the position.
                        Whether the applicant is likely to receive an interview.
                        The applicant's strongest qualifications.
                        The applicant's biggest gaps.
                        Whether the application should be prioritized.


                        EVIDENCE RULES

                        Use ONLY information contained in the provided Job Description and Applicant Resume.

                        Never invent:

                        Skills
                        Technologies
                        Programming languages
                        Projects
                        Responsibilities
                        Years of experience
                        Certifications
                        Education
                        Employment history
                        Achievements
                        Domain experience

                        If the resume does not provide evidence for a requirement, classify it as "Not Demonstrated."

                        Do not infer specific technologies from related technologies.

                        Examples:

                        Python does NOT automatically mean Django.
                        Computer vision does NOT automatically mean deep learning.
                        Machine learning does NOT automatically mean PyTorch.
                        Software engineering does NOT automatically mean distributed systems.

                        EVALUATION

                        TECHNICAL MATCH

                        Identify the most important technical requirements from the job description.

                        For each requirement, determine:

                        "Strong Match"
                        "Partial Match"
                        "Not Demonstrated"

                        Prioritize explicitly required qualifications over preferred qualifications.


                        RELEVANT EXPERIENCE

                        Evaluate:

                        Professional experience
                        Responsibility overlap
                        Technical depth
                        Domain relevance
                        Production experience
                        Ownership
                        Recency


                        PROJECTS

                        Evaluate projects based on their relevance to the actual position.

                        Prioritize directly relevant projects over unrelated projects.


                        EDUCATION

                        Evaluate:

                        Degree requirements
                        Field of study
                        Graduation requirements
                        Relevant coursework
                        Other explicit educational requirements

                        Identify potential eligibility blockers separately from competitive weaknesses.


                        ATS ALIGNMENT

                        Identify important technologies, terminology, and qualifications from the job description.

                        Determine whether they appear explicitly in the resume.

                        Do not recommend adding keywords unless the applicant's actual experience supports them.


                        SCORING

                        MATCH PERCENTAGE

                        Estimate how closely the applicant's demonstrated qualifications align with the job requirements.

                        This is NOT a probability of being hired.

                        Use:

                        90-100: Exceptional alignment
                        80-89: Strong alignment
                        70-79: Good alignment
                        60-69: Moderate alignment
                        50-59: Weak alignment
                        Below 50: Poor alignment



                        Consider:

                        Minimum qualifications
                        Technical alignment
                        Relevant experience
                        Project relevance
                        Education
                        Resume clarity
                        ATS alignment
                        Missing requirements
                        Eligibility issues

                        Do not assign a high match chance if a clear hard requirement is missing.


                        CONFIDENCE

                        Use:

                        "High" — Requirements and qualifications are clearly described.
                        "Medium" — Some important information is missing or ambiguous.
                        "Low" — There is insufficient information for a reliable comparison.


                        VERDICT

                        Choose exactly one:

                        "INTERVIEW"
                        "MAYBE INTERVIEW"
                        "REJECT"

                        Use these general guidelines:

                        INTERVIEW:

                        The applicant demonstrates strong alignment with the core requirements and has sufficient evidence to justify advancing them.

                        MAYBE INTERVIEW:

                        The applicant has meaningful relevant qualifications but has notable gaps, uncertainty, or competition concerns.

                        REJECT:

                        The applicant lacks one or more critical qualifications or has insufficient relevant evidence to justify advancing them.


                        OUTPUT

                        Return ONLY valid JSON.

                        Do not include Markdown.

                        Do not include code fences.

                        Do not include explanations outside the JSON.

                        Use exactly this structure:

                        {{
                            "position": "string",
                            "company": "string",
                            "job_url": "{link}",

                            "match_percentage": 0,

                            "confidence": "High",

                            "verdict": "INTERVIEW",

                            "core_requirements": [
                                {{
                                    "requirement": "string",
                                    "importance": "Required",
                                    "match": "Strong Match",
                                    "resume_evidence": "string"
                                }}
                            ],

                            "technical_skills": {{
                                "strong_matches": [
                                    "string"
                                ],
                                "partial_matches": [
                                    "string"
                                ],
                                "not_demonstrated": [
                                    "string"
                                ]
                            }},

                            "relevant_experience": [
                                {{
                                    "experience": "string",
                                    "relevance": "string"
                                }}
                            ],

                            "relevant_projects": [
                                {{
                                    "project": "string",
                                    "relevance": "string"
                                }}
                            ],

                            "education": {{
                                "match": "string",
                                "potential_blocker": false,
                                "details": "string"
                            }},

                            "ats_alignment": {{
                                "matched_keywords": [
                                    "string"
                                ],
                                "missing_keywords": [
                                    "string"
                                ]
                            }},

                            "strengths": [
                                "string"
                            ],

                            "weaknesses": [
                                "string"
                            ],

                            "missing_requirements": [
                                "string"
                            ],

                            "highest_impact_improvements": [
                                "string"
                            ],

                            "hiring_manager_verdict": "string",

                            "priority": "High"
                        }}


                        FIELD RULES

                        "match_percentage":

                        Integer from 0 to 100.

                        "confidence":

                        Must be exactly:

                        "High"
                        "Medium"
                        "Low"

                        "verdict":

                        Must be exactly:

                        "INTERVIEW"
                        "MAYBE INTERVIEW"
                        "REJECT"

                        "priority":

                        Use:

                        "High" = strong candidate worth applying to immediately.

                        "Medium" = potentially worthwhile but has meaningful gaps.

                        "Low" = weak match or significant qualification problems.


                        "core_requirements":

                        Include only the most important requirements from the job posting.


                        "resume_evidence":

                        State the specific evidence from the resume supporting the match.

                        If there is no evidence, use:

                        "Not demonstrated in resume."


                        "missing_requirements":

                        Only include meaningful requirements that are required or strongly relevant.


                        "highest_impact_improvements":

                        Provide no more than 5 improvements.

                        Only recommend improvements that are supported by the applicant's actual background.

                        All arrays may contain zero items when appropriate.


                        CONSISTENCY REQUIREMENTS

                        The numerical scores and verdict must agree.

                        Do not produce:

                        A 90% match with a REJECT verdict unless there is a clear hard eligibility blocker.
                        A 40% match with an INTERVIEW verdict.
                        A low confidence score when both inputs clearly contain sufficient information.

                        Do not inflate scores because the applicant has many projects.

                        Prioritize relevance, evidence, and required qualifications over quantity.

                        Return ONLY the JSON object.

                        CRITICAL: Limit lists (like core_requirements) to the top 5-7 most impactful items to ensure the entire payload fits within token limits. Do not truncate the JSON.
                        """,
                    input = f"""
                        INPUTS

                        JOB DESCRIPTION

                        {get_job_details(website)}

                        APPLICANT RESUME

                        {read_docx(resume_docx)}
                        Evaluate the candidate against the job description.

                    """,
                )
            ##take current response into json 
            y = response.output_text

            try:
                ##if the verdict is not reject, write output for review
                json_y = json.loads(y.strip())
                if json_y["verdict"] != "REJECT":
                    with open(f"outputs/{job_title}_Comparison_{i+1}.json", "w") as f:
                        f.write(y)
                    continue
                else:
                    #if theres no match print what job did not make it. 
                    print(f"{job_title}: {website} does not match requirements")
            #if theres a problem with json output, write gemini response as text file for review 
            except json.JSONDecodeError as e:
                print("\n========== JSON ERROR ==========")
                print(f"Error: {e}")
                print(f"Line: {e.lineno}")
                print(f"Column: {e.colno}")
                print(f"Position: {e.pos}")

                with open(f"outputs/{job_title}_Comparison_{i}.text", "w") as f:
                    f.write(y)

                continue
        ##add all found links to link holder for later checks 
        link_holder.extend(found_job_links)
        ##clear the found jobs links for next job type application
        found_job_links.clear()
job_titles = [
    "Application Analyst",
    "Systems Analyst",
    "Solutions Analyst",
    "Technology Solutions Analyst",
    "Functional Analyst",
    "Digital Analyst",
    "Technology Associate",
    "IT Associate",
    "Engineering Associate",
    "Software Development Associate",
    "Application Development Associate",
    "Computer Analyst",
    "Information Systems Analyst",
]
#loop through list, find and compare postings to resume 
for job in job_titles:
    print(f"Searching for {str(job)} positions")
    main(job, resume_docx="{docx resume file here}",location = "{Enter location Here}")
