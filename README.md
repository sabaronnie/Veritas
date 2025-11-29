#Veritas - Lebanese News Fact-Checker
Veritas is a client-server application that fact-checks Lebanese news articles by comparing claims across multiple sources using AI analysis.
#Complete Project Documentation
Built by: Tracy Ghosn, Ronnie Saba, Joey Saade
Project Idea: Misinformation Detection for Lebanese News Media
Final Approach: API-based fact-checking using OpenAI GPT-3.5
What We Built
In today's rapidly evolving digital landscape, the proliferation of news sources and the exponential spread of information have created a critical challenge: distinguishing factual reporting from misinformation. This problem is particularly acute in regions like Lebanon, where multiple media outlets often present conflicting narratives about the same events, leaving citizens confused and struggling to identify objective truth. 

Our solution addresses this pressing issue through an AI-powered fact-checking system that analyzes news articles against multiple sources from the same time period as the article being examined. By leveraging GPT-3.5's advanced natural language processing capabilities, the system extracts key factual claims from any given article and cross-references them against similar reporting from other outlets, providing clear verification scores and confidence levels for each claim. This approach delivers rapid, cost-effective fact-checking at approximately $0.06 per analysis, empowering readers to make informed decisions about the news they consume while combating the spread of misinformation at scale.

#Installation Instrunctions:
- Go to secrets.env.example and fill out the API links provided by email
- 

#Evolution of Approaches
Our Original Three-Model Architecture
3 different ML models:
├── Babelscape (Transformer-based model for claim extraction)
├── Mpnet-Base-v2 (semantic similarity)
└── NLTK Vader (for bias detection)

3 models codes: https://colab.research.google.com/drive/1QGZW5_RWmaWQ9PTqlHhRW3h0Nosb2UIT#scrollTo=0TMOLn8iONkx&uniqifier=2 
Model 1: Claim Extraction System

Purpose
This model transforms raw news articles into structured factual claims, preparing them for fact-checking analysis. 

Claim Generation
- Uses a specialized T5 transformer model trained specifically for claim extraction
- Handles long articles through intelligent sentence-based chunking
- Produces clear, individual claims 
Entity Role Extraction
- Employs spaCy's natural language processing to identify entities and relationships
- Categorizes information into five key dimensions:
  - WHO: People and groups involved
  - WHAT: Core actions and events described
  - WHEN: Timeframes and dates mentioned
  - WHERE: Locations and places referenced
  - HOW MUCH: Quantities, percentages, and numerical data

Intelligent Scoring & Filtering
- Evaluates claim quality based on completeness of information
- Prioritizes claims with clear WHO-WHAT-WHEN structure
- Ranks claims by salience score to focus on most significant facts

Model 2: Hybrid Similarity System

Purpose
This model identifies similar and contradictory claims across different news sources by comparing newly extracted claims against a database of previously verified statements. It determines whether claims are supported, contradicted, or unrelated to existing reporting.

Multi-Dimensional Similarity Analysis
- Vector Embedding Search: Uses claim embeddings to find semantically similar statements across the entire database
- Time-Based Filtering: Focuses on articles published within ±3 days to ensure relevant temporal context
- Multi-Level Comparison: Evaluates claims across multiple similarity dimensions

Four-Layer Comparison Approach
1. Semantic Similarity: 
   - Compares claim embeddings using cosine similarity
   - Identifies conceptually related statements regardless of exact wording

2. Text-Based Similarity:
   - Token-Level: Jaccard similarity, overlap coefficients, and bag-of-words cosine
   - Character-Level: Levenshtein distance and trigram matching
   - Captures both exact and fuzzy text matches

3. Structured Entity Matching:
   - Compares extracted entities from model 1 (who, what, when, where, how much)
   - Uses weighted scoring with emphasis on key entities (who: 30%, where: 25%)
   - Handles partial matches and related entities

4. Logical Relationship Detection:
   - Employs Natural Language Inference (NLI) to detect contradictions
   - Classifies relationships as entailment, neutral, or contradiction
   - Uses RoBERTa-large model trained on MNLI dataset

Intelligent Scoring & Classification
- Hybrid Scoring: Combines all similarity metrics with weighted importance
- Relationship Classification: Categorizes claims as:
  - SAME: Highly similar claims
  - RELATED: Partially similar context
  - CONTRADICTION: Directly opposing statements
  - UNRELATED: No meaningful connection

The hybrid approach ensures robust claim verification by combining multiple similarity techniques, reducing false positives/negatives while maintaining contextual relevance through time-aware filtering.
Problems with Three-Model Approach:
•	Complex Integration: Three different models to manage
•	High Cost: Three separate models to accommodate
•	Slow Performance: Sequential processing creates bottlenecks
Evolved Current Approach
Phase 1: Continuous Data Collection
•	Background Scraper runs daily for fresh articles
•	Collects articles from different Lebanese news resources
•	Stores in MongoDB database to prevent throttling with intelligent rate limiting
Importance of MongoDB:
•	avoids throttling
•	limited to last week and updates every 24 hours to preserve usefulness
•	avoids the need to demand scrape all similar articles, augmenting time efficiency

We initially tried not using a database, but real-time scraping for each user request proved unsustainable, requiring 45-60 seconds per analysis as the system sequentially scraped multiple news sources for every URL submitted to compare as some website exceeded their respective rate limit. This created long user wait times and scalability limitations. 
We then pivoted to a database-driven strategy where a background scraper continuously collects articles from Lebanese news sources daily, maintaining a fresh repository of recent content. When users submit URLs, the system now performs fast comparisons against similar articles in pre-scraped database based on a +-1 window to ensure temporal relevance while delivering results in just 3-8 seconds. 
This approach maintains comprehensive coverage of the Lebanese news landscape while providing instant fact-checking through intelligent time-based filtering and optimized database queries.
Phase 2: User Request Processing
•	User submits any news article URL for verification
•	System scrapes the target article on-demand
•	Converts both user article and similar database articles into structured JSON
•	How it works:
Upon receiving a user-submitted URL, the system scrapes the article to extract its text, title, and publication metadata. This scraped article is then used to initiate the event-matching pipeline:
(1) the system loads potentially related articles from the MongoDB database using a time-based filter,
(2) filters those articles using TF-IDF topical similarity,
(3) ranks the remaining candidates using a custom event-relevance score, and
(4) returns the top N most relevant articles.
Both the scraped article and the database results are serialized into structured JSON objects, ensuring a clean, standardized data package for downstream processing.
Phase 3: AI Analysis
•	GPT-3.5 processes structured JSON data containing both the user's article and similar comparison articles
•	Performs semantic matching for supporting, contradicting and unrelated
•	Performs bias analysis and assigns overall bias score
Key Advantages:
•	Single API call replaces complex multi-model usage
•	Faster processing than our previous integration
•	Accuracy through advanced prompt engineering
•	Scalability as modular architecture allows easy expansion 
•	Daily scraping and database upgrading ensure fresh data and recent time-based comparison
•	Cost-effective design suitable for high-volume usage
•	Modified approach: few seconds in comparison to the 10 minutes 3-models approach

System Architecture Overview 
Our fact-checking platform employs a modern client-server architecture that separates frontend presentation from backend processing, enabling scalable and maintainable development.
•	Frontend Specialization: Focuses on user experience and responsive design
•	Backend Specialization: Handles data processing and AI integration
Data Flow Architecture
The system processes requests through a structured pipeline:
The user workflow begins when they access the frontend interface and input a news article URL for verification. The frontend immediately transmits this URL to the backend API, which then scrapes the target article and gathers relevant comparison articles. This collected data is forwarded to the GPT-4.1 model for comprehensive analysis, where it extracts key claims and identifies matching evidence across sources. After processing through backend, AI's output is organized, showing verified claims, source matches, and bias assessment.