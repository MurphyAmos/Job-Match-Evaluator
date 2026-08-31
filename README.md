# Job Match Evaluator

Searches job postings by title and location, then uses an LLM to evaluate each one against a resume with a structured, evidence-based hiring rubric, only surfacing roles that would plausibly pass a real screen.

## What it does

Instead of manually reading through dozens of job postings and guessing whether a resume is actually a fit, this pipeline searches for postings by title, pulls and compresses each job description, and runs it through an LLM acting as a strict, evidence-only hiring manager. Every evaluation is scored, broken down requirement by requirement, and saved as structured JSON, and postings the model would reject outright are filtered out automatically instead of cluttering the results.

## How it works

1. **Job search.** An async browser session searches for postings matching a given job title and location, collecting a batch of listing URLs.
2. **Job description extraction.** Each posting's page is fetched and parsed with BeautifulSoup, stripping scripts, styles, and other non-content tags down to plain text.
3. **Compression.** The extracted text is passed through a local compression model (Bonsai-1.7B) to cut it down to a target token count before it ever reaches the evaluation model, keeping prompts small without truncating mid-sentence.
5. **Embedding and semantic filtering.** The compressed job description and full resume are embedded using Gemini's embedding model. Their cosine similarity is calculated. Postings below the configured similarity threshold (`0.45` by default) are skipped. This acts as a semantic retrieval gate: only postings meaningfully related to the applicant's experience move forward.
6. **LLM evaluation.** Qualifying job descriptions and the full resume are sent to Gemini with a detailed system prompt enforcing evidence-only evaluation. The model cannot invent skills, technologies, or experience; each important requirement is scored as **Strong Match**, **Partial Match**, or **Not Demonstrated**.
7. **Structured output.** The model returns out a strict JSON schema: match percentage, confidence level, a verdict (INTERVIEW / MAYBE INTERVIEW / REJECT), and itemized requirement-by-requirement breakdowns.
8. **Filtering & saving.** Postings that come back as REJECT are logged and skipped. Everything else is written to disk as its own JSON file, one per job posting, organized by job title.

# Retrieval-Augmented Evaluation Design

This project uses a lightweight RAG-style workflow:

- **Retrieve:** Embed the resume and each job description, then use cosine similarity to identify semantically relevant postings.
- **Augment:** Provide the retrieved job description alongside the applicant's resume.
- **Generate/Evaluate:** Use an LLM to produce a detailed, structured hiring assessment grounded only in those two inputs.

The embedding stage is not the final decision-maker. It is a low-cost semantic filter that prevents irrelevant postings from being sent to the more expensive LLM evaluation stage.


## Tech stack

- Python
- `linkedin_scraper` by joeyism for job-board scraping
- BeautifulSoup for HTML-to-text extraction
- LiteLLM with Bonsai-1.7B for job-description compression
- Google Gemini API for embeddings and structured hiring evaluation
- NumPy for vector operations and cosine similarity
- `python-docx` for resume parsing
- JSON for structured evaluation outpu
## Setup

Install dependencies:

```
pip install -r requirements.txt
```

Set your API key by replacing the `{Enter Key Here}` placeholder in the `genai.Client()` initialization at the top of the script.

The job search scraper also needs a `session.json` file to authenticate, generated as follows:

1. Run the session-creation script (a small Playwright script that opens a browser, lets you log in manually, then saves the resulting cookies and localStorage).
   ```
   python create_session.py
   ```
2. A browser window will open to the login page. Log in manually.
3. Return to the terminal and press Enter once you're logged in. The script will save your session to `session.json` in the working directory and close the browser.


## Usage

Update the following in `main.py`:

- `job_titles` with the roles you want to search.
- `resume_docx` with the path to the applicant's `.docx` resume.
- `location` with the target city or area.
- The similarity threshold if you want a stricter or broader first-pass filter.
Then Run:
```
python main.py
```

Results are written to the `outputs/` directory as one JSON file per non-rejected posting, named by job title and index.

## Known limitations & Next Fixes
- **Single-vector similarity.** The current version compares one full-resume vector to one full-job-description vector. A strong match can occasionally be missed if relevant skills are diluted by unrelated text. 
- **Fixed similarity threshold.** The `0.45` threshold is a practical starting point, not a universally correct value. 
- **No retry logic on JSON parse failures.** If the model's output isn't valid JSON, that posting isn't retried, but it isn't lost either, the raw response is still saved to disk as a `.text` file for debugging instead of the usual `.json` output.
- **Compression model is fixed.** The compression step always targets the same token count regardless of how information-dense the original posting is, which can occasionally cut relevant detail from very long listings.
- **Scraping is subject to platform Terms of Service.** This is built for personal, individual job-search use, not for redistribution or commercial use of scraped listing data.
-**No UI.** This runs entirely from the command line. Functional, but every job title, resume path, and setting has to be edited directly in the script, there's no interface for adjusting a run without touching the code.

## Fixed & Updates
- Added RAG implementation using Gemini embeddings and cosine similarity to prefilter job postings before LLM evaluation.

## Motivation

After manually comparing my resume against dozens of postings by hand and realizing most of that time was spent re-reading the same kind of requirement over and over, the next step was obvious: let a model do the repetitive evaluation, evidence-only and consistent every time, and only bring me the postings actually worth my attention.
