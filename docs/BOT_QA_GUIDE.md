# StartupIntel Bot Q&A Guide with Artifacts

Complete guide for interacting with each of the 8 specialized ML bots, including example questions, responses, and sample output artifacts.

---

## 🤖 Bot Overview

| Bot | Purpose | Primary Users | Key Signals |
|-----|---------|---------------|-------------|
| **RunwayBot** | Financial stress detection | Founders, CFOs | Headcount, funding, domain expiry |
| **ObituaryBot** | Failure pattern matching | Founders, Investors | Historical failures, risk taxonomy |
| **PMFBot** | Product-market fit analysis | Product, Growth | Reviews, GitHub, search trends |
| **PivotBot** | Strategic pivot detection | Founders, Strategy | Wayback, messaging changes |
| **AcquiBot** | Acqui-hire probability | Founders, M&A | Team quality, tech stack, network |
| **InvestorBot** | Investor network analysis | Founders, VCs | Centrality, betweenness, value-add |
| **AcceleratorBot** | Accelerator ROI ranking | Founders | Cohort outcomes, follow-on rates |
| **TermBot** | Term sheet analysis | Founders, Legal | Red flags, founder-friendliness |

---

## 1. 🏃 RunwayBot - Financial Stress Detection

### Example Questions

**Basic Queries:**
- "What's my startup's runway looking like?"
- "Analyze financial stress for [Startup Name]"
- "How many months of runway do we have left?"
- "Should I be worried about our burn rate?"
- "Compare our runway to similar Series A companies"

**Advanced Queries:**
- "Runway analysis with headcount trends and job posting velocity"
- "Stress test: what if we lose our biggest customer?"
- "Show me the signal breakdown for runway health"
- "Which runway indicator is most concerning?"
- "Predict runway in 3 months if we keep hiring"

### Example Response

```
📊 Runway Analysis for TechFlow AI

OVERALL SCORE: 67/100 (MODERATE STRESS)
Risk Level: 🟡 CAUTION

📈 SIGNAL BREAKDOWN:
├── Headcount Trend: 78/100 (-12% vs 6mo ago)
├── Job Posting Velocity: 45/100 (↓ 67% drop)
├── Founder Sentiment: 82/100 (Positive in recent tweets)
├── Domain Renewal: 95/100 (Expires 2027-03-15)
└── Funding Recency: 42/100 (Last round: 14 months ago)

⚠️ KEY FINDINGS:
1. Job postings dropped 67% in last 90 days
   → Hiring freeze or caution mode detected
   
2. Headcount down 12% from peak (42 → 37 employees)
   → 5 departures, 0 new hires in Q4
   
3. Days since funding: 427 days
   → Typical runway exhaustion warning at 18 months

💡 SIMILAR CASES:
• DataSync (2022) - Score 64, survived via bridge round
• CloudPath (2021) - Score 71, acqui-hired by Microsoft
• NexStream (2023) - Score 58, shut down after 8 months

🤖 AI DIAGNOSIS:
"TechFlow shows classic Series A squeeze patterns. The combination
of reduced hiring velocity and headcount contraction suggests 
management is actively managing burn. Domain renewal through 2027 
indicates long-term intent. Recommend: accelerate revenue 
conversations or initiate bridge round discussions within 60 days."

📋 RECOMMENDED ACTIONS:
□ Project cash position with 10% revenue haircut
□ Identify non-essential spend for potential cuts
□ Reach out to existing investors for signal check
□ Consider acqui-hire conversations as backup plan
```

### Output Artifact

```json
{
  "bot_name": "runway",
  "startup_id": "uuid-here",
  "score": 67.0,
  "risk_level": "caution",
  "signal_breakdown": {
    "headcount": 78.0,
    "job_postings": 45.0,
    "sentiment": 82.0,
    "domain_renewal": 95.0,
    "funding_recency": 42.0
  },
  "raw_signals": {
    "current_headcount": 37,
    "headcount_6mo_ago": 42,
    "headcount_delta_pct": -11.9,
    "job_postings_current": 3,
    "job_postings_6mo_ago": 12,
    "job_posting_delta_pct": -75.0,
    "founder_sentiment": 0.72,
    "domain_expiry_days": 825,
    "last_funding_date": "2023-08-15",
    "days_since_funding": 427,
    "total_funding_usd": 8500000
  },
  "similar_cases": [
    {
      "name": "DataSync",
      "outcome": "survived_bridge_round",
      "score": 64,
      "match_confidence": 0.87
    },
    {
      "name": "CloudPath",
      "outcome": "acqui_hired",
      "score": 71,
      "match_confidence": 0.82
    },
    {
      "name": "NexStream",
      "outcome": "shutdown",
      "score": 58,
      "match_confidence": 0.78
    }
  ],
  "llm_diagnosis": "TechFlow shows classic Series A squeeze patterns...",
  "computed_at": "2024-12-19T12:30:00Z"
}
```

---

## 2. ⚰️ ObituaryBot - Failure Pattern Analysis

### Example Questions

**Basic Queries:**
- "What could kill this startup?"
- "Analyze failure risks for [Startup Name]"
- "Are we showing any death spiral signals?"
- "What killed startups like ours?"
- "Failure pattern analysis"

**Advanced Queries:**
- "Compare our failure risk to postmortem database"
- "What's our top failure pattern match?"
- "Show me the failure taxonomy breakdown"
- "Which historical failure are we most similar to?"
- "Early warning indicators we're missing"

### Example Response

```
⚰️ Failure Risk Analysis for CloudSync Pro

OVERALL SCORE: 73/100 (HIGH RISK)
Risk Level: 🔴 HIGH

🎯 TOP FAILURE PATTERN:
"Premature Scaling Before Product-Market Fit"
Match Confidence: 84%
Cases in Database: 127 similar failures

📊 FAILURE TAXONOMY BREAKDOWN:
├── Product-Market Fit Issues: 31% (39 cases)
├── Team/Execution Problems: 24% (30 cases)
├── Market Timing: 18% (23 cases)
├── Running Out of Cash: 15% (19 cases)
└── Competitive Pressure: 12% (15 cases)

💀 SIMILAR FAILURES (Top 3):

1. StreamVault (2022) - 91% match
   Raised $12M Series A, hired 50 people in 6 months
   Product couldn't scale, churn hit 40%
   Shutdown after 18 months
   Key Lesson: "Don't hire sales before product works"

2. DataBridge (2021) - 87% match
   Similar TAM assumptions, similar burn rate
   Customer acquisition cost 3x projections
   Acqui-hired by competitor for $2M (vs $8M raised)
   Key Lesson: "Unit economics matter more than growth"

3. SyncFlow (2023) - 82% match
   Nearly identical feature set
   Same target customer segment (mid-market)
   Failed due to enterprise security requirements
   Key Lesson: "Enterprise needs > SMB simplicity"

🚨 RED FLAGS DETECTED:
⚠️ Employee growth (140%) outpaces revenue growth (45%)
⚠️ Glassdoor sentiment dropped 23% in 6 months
⚠️ 4 senior departures in engineering
⚠️ Customer support tickets up 180% (quality issues)
⚠️ Negative NPS trend: +12 → -3

✅ POSITIVE INDICATORS:
✓ Domain renewed through 2028
✓ Founder still actively posting about vision
✓ Core team retention > 85%
✓ Product usage engagement stable

🤖 AI DIAGNOSIS:
"CloudSync exhibits classic 'building the airplane while flying it'
patterns. The 3.1x employee-to-revenue growth ratio is the primary
concern - you're scaling operations before the product can support
the cost structure. Historical matches suggest 65% probability of
significant downsizing or shutdown within 12 months without course
correction.

Immediate actions: (1) Freeze non-essential hiring, (2) Segment
customers by profitability, (3) Consider technical debt investment
before new features."

📋 SURVIVAL RECOMMENDATIONS:
□ Emergency board meeting within 7 days
□ Implement zero-based budgeting for Q1
□ Identify top 20% customers by profitability
□ Technical audit of scaling bottlenecks
□ Prepare bridge round materials (defensive)
□ Begin acqui-hire conversations as backup
```

### Output Artifact

```json
{
  "bot_name": "obituary",
  "startup_id": "uuid-here",
  "score": 73.0,
  "risk_level": "high",
  "top_failure_pattern": "Premature Scaling Before PMF",
  "pattern_confidence": 0.84,
  "failure_taxonomy_breakdown": {
    "product_market_fit": 31,
    "team_execution": 24,
    "market_timing": 18,
    "cash_burn": 15,
    "competition": 12
  },
  "similar_failures": [
    {
      "name": "StreamVault",
      "year": 2022,
      "match_score": 91,
      "funding_raised": 12000000,
      "outcome": "shutdown",
      "key_lesson": "Don't hire sales before product works"
    },
    {
      "name": "DataBridge",
      "year": 2021,
      "match_score": 87,
      "funding_raised": 8000000,
      "outcome": "acqui_hired_2m",
      "key_lesson": "Unit economics matter more than growth"
    }
  ],
  "red_flags": [
    {
      "indicator": "employee_growth_vs_revenue",
      "severity": "high",
      "value": "140% vs 45%",
      "description": "Headcount growing 3.1x faster than revenue"
    },
    {
      "indicator": "glassdoor_sentiment",
      "severity": "medium",
      "value": -23,
      "description": "Employee satisfaction declining"
    }
  ],
  "llm_diagnosis": "CloudSync exhibits classic 'building the airplane...",
  "survival_probability_12mo": 0.35,
  "computed_at": "2024-12-19T12:30:00Z"
}
```

---

## 3. 🎯 PMFBot - Product-Market Fit Analysis

### Example Questions

**Basic Queries:**
- "Do we have product-market fit?"
- "How's our PMF looking?"
- "Analyze product-market fit for [Startup Name]"
- "Are users loving our product?"
- "What's our strongest PMF signal?"

**Advanced Queries:**
- "Show me PMF score breakdown by signal"
- "Detect any changepoints in PMF metrics"
- "Compare our PMF to competitors"
- "Which PMF signal should we focus on?"
- "Predict PMF trajectory for next quarter"

### Example Response

```
🎯 Product-Market Fit Analysis for DevCollab

OVERALL PMF SCORE: 71/100 (STRONG INDICATIONS)
Status: 🟢 PMF INFLECTION DETECTED

📈 SIGNAL BREAKDOWN:
├── App Store Reviews: 78/100 (↑ 340% vs 6mo ago)
├── G2/Capterra Ratings: 72/100 (4.3★ avg, 127 reviews)
├── GitHub Activity: 85/100 (2,400 stars, 340 forks)
├── Search Trends: 68/100 ("devcollab" queries ↑ 180%)
├── StackOverflow Mentions: 61/100 (45 tagged questions)
├── Reddit Discussions: 55/100 (r/webdev, r/programming)
├── ProductHunt: 82/100 (#2 Product of Day, 890 upvotes)
└── Twitter Sentiment: 74/100 (Positive developer buzz)

📊 CHANGPOINT ANALYSIS:
🚨 PMF INFLECTION DETECTED: 2024-08-15

Pre-August (6mo avg): PMF Score 42/100
Post-August (6mo avg): PMF Score 68/100

Change Drivers:
• Launched AI code review feature (+156% GitHub mentions)
• GitHub integration went viral on Twitter (+890% impressions)
• Featured in Fireship YouTube video (2.4M views)
• Organic search traffic 4x'd in 60 days

🏆 STRONGEST SIGNALS:
1. GitHub Stars Velocity (85/100)
   2,400 stars in 8 months (300/mo avg)
   Comparable to: Figma (early), Linear, Raycast
   
2. App Store Reviews Sentiment (78/100)
   4.7★ average, "game changer" mentioned 47x
   Review keywords: "intuitive", "saves time", "essential"

⚠️ WEAKEST SIGNALS:
1. Reddit Engagement (55/100)
   Organic mentions limited to 3 subreddits
   Opportunity: Target r/webdev more actively
   
2. StackOverflow Presence (61/100)
   Only 45 questions tagged (vs 400+ for competitors)
   Opportunity: Technical SEO for error messages

💡 SIMILAR SUCCESS CASES:
• Linear (2020) - Score 74 at same stage, now $1B+ valuation
• Figma (2018) - Score 68, viral designer adoption
• Raycast (2021) - Score 71, developer tool breakout

🤖 AI DIAGNOSIS:
"DevCollab is experiencing a genuine PMF inflection event. The 
August 2024 acceleration pattern matches successful developer
tool breakouts like Linear and Raycast. The GitHub star velocity
and organic Twitter mentions are particularly strong leading
indicators.

Key insight: Your AI code review feature created a 'wow moment'
that transformed users into evangelists. The Fireship video 
catalyzed awareness but product quality drove retention.

Recommendation: Double down on the features driving this 
momentum (AI review, GitHub integration). Avoid premature 
enterprise features - you have 6-9 months of organic growth
runway before needing paid acquisition."

📋 GROWTH RECOMMENDATIONS:
□ Launch "DevCollab Pro" tier to capture value from power users
□ Create YouTube tutorial series (ride the wave)
□ Implement referral program (organic + incentivized)
□ Add team collaboration features (expand use case)
□ Begin enterprise pilot conversations (but don't build yet)
□ Monitor for competitor responses (retention defense)
```

### Output Artifact

```json
{
  "bot_name": "pmf",
  "startup_id": "uuid-here",
  "score": 71.0,
  "pmf_status": "strong_indications",
  "changepoint_detected": true,
  "changepoint_date": "2024-08-15",
  "pre_changepoint_score": 42.0,
  "post_changepoint_score": 68.0,
  "strongest_signal": {
    "type": "github_activity",
    "score": 85.0,
    "metric": "stars_velocity",
    "value": 2400,
    "growth_rate": 340
  },
  "weakest_signal": {
    "type": "reddit_discussions",
    "score": 55.0,
    "metric": "subreddit_mentions",
    "value": 12,
    "opportunity": "Expand to r/webdev community"
  },
  "signal_breakdown": {
    "app_store_reviews": 78,
    "g2_capterra": 72,
    "github_activity": 85,
    "search_trends": 68,
    "stackoverflow": 61,
    "reddit": 55,
    "producthunt": 82,
    "twitter": 74
  },
  "similar_success_cases": [
    {
      "name": "Linear",
      "pmf_score_at_stage": 74,
      "current_valuation": "1B+",
      "key_pattern_match": "Developer tool viral adoption"
    }
  ],
  "llm_diagnosis": "DevCollab is experiencing a genuine PMF inflection event...",
  "computed_at": "2024-12-19T12:30:00Z"
}
```

---

## 4. 🔄 PivotBot - Strategic Pivot Detection

### Example Questions

**Basic Queries:**
- "Has this startup pivoted?"
- "Show me pivot history for [Startup Name]"
- "Detect any strategic pivots"
- "What direction changes have they made?"
- "Analyze website evolution for pivots"

**Advanced Queries:**
- "Compare current positioning to 2 years ago"
- "What triggered their last pivot?"
- "Detect messaging changes over time"
- "Show pivot confidence scores"
- "Analyze Wayback history for pivot signals"

### Example Response

```
🔄 Pivot Analysis for ShopAI (formerly ChatCommerce)

OVERALL SCORE: 58/100 (MODERATE PIVOT ACTIVITY)
Pivot Count: 3 detected pivots
Primary Pivot Type: 🎯 Market Segment Pivot

📅 PIVOT TIMELINE:

Pivot #1: August 2022 (Confidence: 92%)
├─ Type: Technology Pivot
├─ From: Rule-based chatbot for e-commerce
├─ To: AI-powered shopping assistant
├─ Evidence:
│  • Website copy changed: "chatbot" → "AI assistant"
│  • Tech stack mentions added: "GPT", "transformers"
│  • Pricing changed from per-conversation to per-result
│
├─ Trigger: ChatGPT launch (Nov 2022, anticipated)
└─ Outcome: Successful - enabled by tech breakthrough

Pivot #2: March 2023 (Confidence: 87%)
├─ Type: Market Segment Pivot  
├─ From: SMB e-commerce (Shopify stores)
├─ To: Enterprise retail (Fortune 500)
├─ Evidence:
│  • Case studies: "Boutique store" → "Major retailer"
│  • Pricing: $99/mo → "Contact sales"
│  • Features: Basic recommendations → Enterprise analytics
│  • Team: Hired enterprise sales VP from Salesforce
│
├─ Trigger: SMB churn at 40%, enterprise interest inbound
└─ Outcome: Mixed - 6mo transition, now 3 enterprise customers

Pivot #3: September 2024 (Confidence: 78%)
├─ Type: Use Case Pivot
├─ From: Product recommendations
├─ To: Visual search / "Shop by photo"
├─ Evidence:
│  • Homepage hero: "AI recommendations" → "Snap to shop"
│  • New landing page: /visual-search (Oct 2024)
│  • API docs: New image recognition endpoints
│  • Blog: "The future of shopping is visual"
│
├─ Trigger: Product recommendation market crowded
└─ Outcome: Too early to tell - 3 months post-pivot

📊 PIVOT CONFIDENCE METRICS:
├── Average Confidence: 86% (High confidence detections)
├── Avg Time Between Pivots: 7.5 months
├── Messaging Consistency: 64% (declining trend)
└── Strategic Coherence: 71% (pivots build on each other)

🎯 PIVOT PATTERN ANALYSIS:

Strengths:
✓ Pivots are data-driven (customer feedback, market signals)
✓ Team has adapted successfully to previous pivots
✓ Core technology (AI shopping) remains consistent
✓ Pivots are additive, not abandoning previous work

Concerns:
⚠ High pivot frequency (3 in 27 months)
⚠ May indicate unclear initial vision
⚠ Latest pivot (visual search) = new market, new risks
⚠ Customer confusion possible with rapid changes

💡 SIMILAR PIVOT PATTERNS:

• Slack (2013-2014): Gaming → Enterprise comms
  Pattern match: 81% - Successfully navigated major pivot
  
• Instagram (2010-2012): Check-ins → Photo sharing
  Pattern match: 74% - Use case pivot success
  
• Twitter (2006-2007): Podcasting → Microblogging
  Pattern match: 69% - Complete vision change

🤖 AI DIAGNOSIS:
"ShopAI exhibits an adaptive but potentially concerning pivot
pattern. The 7.5-month average between pivots suggests either
exceptional market responsiveness OR lack of strategic conviction.

The good news: Each pivot has been technically additive. The 
company hasn't abandoned core AI shopping technology, just 
repackaged it for different markets.

The risk: The September 2024 visual search pivot is the third
direction change. Enterprise customers may question long-term
commitment to their specific use case.

Recommendation: Stabilize for 12-18 months on current direction.
The visual search angle has genuine differentiation potential
and the enterprise pivot showed traction."

📋 STRATEGIC RECOMMENDATIONS:
□ Commit to visual search direction for 18 months minimum
□ Create "pivot communication playbook" for enterprise customers
□ Document lessons from each pivot (avoid repeating)
□ Identify 2-3 use cases to maintain simultaneously (not pivot)
□ Build team confidence: share pivot success stories
□ Monitor for "pivot fatigue" in customer conversations
```

### Output Artifact

```json
{
  "bot_name": "pivot",
  "startup_id": "uuid-here",
  "score": 58.0,
  "pivot_count": 3,
  "primary_pivot_type": "market_segment",
  "pivot_events": [
    {
      "date": "2022-08-15",
      "pivot_type": "technology",
      "confidence": 0.92,
      "from_positioning": "Rule-based chatbot for e-commerce",
      "to_positioning": "AI-powered shopping assistant",
      "evidence": [
        "Website copy: 'chatbot' → 'AI assistant'",
        "Tech mentions: Added 'GPT', 'transformers'",
        "Pricing model changed from per-convo to per-result"
      ],
      "trigger": "ChatGPT launch anticipation",
      "outcome": "successful"
    },
    {
      "date": "2023-03-01",
      "pivot_type": "market_segment",
      "confidence": 0.87,
      "from_positioning": "SMB e-commerce (Shopify)",
      "to_positioning": "Enterprise retail (Fortune 500)",
      "evidence": [
        "Case study change: 'Boutique' → 'Major retailer'",
        "Pricing: $99/mo → 'Contact sales'",
        "New hire: Enterprise sales VP from Salesforce"
      ],
      "trigger": "SMB churn 40%, enterprise inbound",
      "outcome": "mixed_success"
    },
    {
      "date": "2024-09-01",
      "pivot_type": "use_case",
      "confidence": 0.78,
      "from_positioning": "Product recommendations",
      "to_positioning": "Visual search / 'Shop by photo'",
      "evidence": [
        "Homepage hero: 'AI recommendations' → 'Snap to shop'",
        "New landing page: /visual-search",
        "API docs: New image recognition endpoints"
      ],
      "trigger": "Recommendation market crowded",
      "outcome": "early"
    }
  ],
  "avg_confidence": 0.86,
  "avg_time_between_pivots_months": 7.5,
  "messaging_consistency": 64,
  "strategic_coherence": 71,
  "similar_patterns": [
    {
      "company": "Slack",
      "pattern_match": 0.81,
      "description": "Gaming → Enterprise comms"
    }
  ],
  "llm_diagnosis": "ShopAI exhibits an adaptive but potentially concerning...",
  "computed_at": "2024-12-19T12:30:00Z"
}
```

---

## 5. 💰 AcquiBot - Acqui-Hire Prediction

### Example Questions

**Basic Queries:**
- "What's our acqui-hire probability?"
- "Calculate acquisition probability for [Startup Name]"
- "Are we acqui-hire material?"
- "Who might acquire us?"
- "What's our acquihire score?"

**Advanced Queries:**
- "Show acquisition probability by acquirer type"
- "Which big tech companies are most likely to buy us?"
- "Analyze our team, tech, and network for acquisition"
- "Compare our acqui profile to successful exits"
- "Feature importance for acqui-hire prediction"

### Example Response

```
💰 Acqui-Hire Analysis for MLFlow (ML infrastructure startup)

OVERALL SCORE: 74/100 (HIGH ACQUI-HIRE PROBABILITY)
Probability: 74% within 24 months

📊 GROUP SCORES:
├── Team Quality: 82/100 (A+ grade)
├── Technology Assets: 71/100 (B+ grade)
├── Network Position: 68/100 (B grade)
└── Financial Situation: 76/100 (B+ grade)

🎯 LIKELY ACQUIRERS (Ranked by Fit Score):

1. 🏆 DataBricks
   Fit Score: 91/100
   ├── Tech Overlap: 94% (ML pipelines, experiment tracking)
   ├── Team Fit: 88% (互补 skill sets)
   ├── Network Overlap: 87% (3 mutual investors)
   └── Rationale: "MLFlow fills gap in Databricks' MLOps stack"
   Estimated Deal Size: $150-250M

2. 🥈 Snowflake
   Fit Score: 84/100
   ├── Tech Overlap: 79% (Data + ML convergence)
   ├── Team Fit: 85% (Cloud-native expertise)
   ├── Network Overlap: 82% (2 mutual board members)
   └── Rationale: "MLFlow extends Snowflake into ML workloads"
   Estimated Deal Size: $120-200M

3. 🥉 Microsoft (Azure ML)
   Fit Score: 79/100
   ├── Tech Overlap: 86% (Azure integration potential)
   ├── Team Fit: 76% (Microsoft alumni on team)
   ├── Network Overlap: 71% ( indirect through GitHub)
   └── Rationale: "Strengthens Azure ML vs AWS SageMaker"
   Estimated Deal Size: $180-300M

4. Amazon (SageMaker)
   Fit Score: 71/100
   Estimated Deal Size: $150-250M

5. Google (Vertex AI)
   Fit Score: 68/100
   Estimated Deal Size: $140-240M

📈 FEATURE IMPORTANCES:

Top Acqui-Hire Drivers:
1. Engineering team quality (0.28) - PhDs from top schools
2. Open source community (0.24) - 4.2M downloads, 890 contributors
3. GitHub stars velocity (0.19) - 18K stars, trending
4. Technical IP (0.16) - 3 patents, proprietary algorithms
5. Recruiting difficulty (0.13) - High signal in ML talent

⚠️ Acqui-Hire Risks:
• Team size (12 people) = small for big tech aquihire threshold
• Revenue ($2.1M ARR) = not enough for standalone valuation
• Competitive pressure = 3 similar tools launched in 2024

✅ Acqui-Hire Strengths:
✓ Founders are ex-Google Brain (proven talent)
✓ Core maintainers = essential knowledge
✓ MLFlow is industry standard (hard to replicate)
✓ GitHub integration = strategic for Microsoft

💡 SIMILAR ACQUI-HIRES:
• Comet.ml → DataRobot (2022, $110M, score 78)
• Weights & Biases → Stayed independent (score 71, said no)
• Algorithmia → DataRobot (2021, $85M, score 69)

🤖 AI DIAGNOSIS:
"MLFlow represents a textbook acqui-hire opportunity. The team
quality is exceptional (ex-Google Brain, PhDs) and the open
source traction creates strategic value for acquirers looking to
own the ML infrastructure narrative.

The primary risk is the team size - 12 people is below typical
big tech acqui-hire thresholds (usually 20-50). However, the 
quality and the 'industry standard' position of MLFlow may
justify a premium.

Most likely outcome: DataBricks acquisition within 12-18 months.
They've already partnered on integrations and the cultural fit
is strong (both Apache Spark ecosystem companies).

Alternative: Microsoft could acquire to block Databricks and
strengthen Azure ML's position vs AWS."

📋 EXIT STRATEGY RECOMMENDATIONS:
□ Begin informal conversations with Databricks partnership team
□ Engage with Microsoft Azure ML product team
□ Document IP and proprietary algorithms (valuation support)
□ Secure key employee retention agreements
□ Prepare for 18-24 month integration period post-acquisition
□ Consider if independent path is viable (need 5x revenue growth)
```

### Output Artifact

```json
{
  "bot_name": "acqui",
  "startup_id": "uuid-here",
  "score": 74.0,
  "probability": 0.74,
  "timeframe": "24_months",
  "group_scores": {
    "team_quality": 82,
    "technology_assets": 71,
    "network_position": 68,
    "financial_situation": 76
  },
  "likely_acquirers": [
    {
      "acquirer_id": "databricks",
      "name": "DataBricks",
      "domain": "databricks.com",
      "fit_score": 91,
      "tech_overlap": 94,
      "team_fit": 88,
      "network_overlap": 87,
      "estimated_deal_range": [150000000, 250000000],
      "rationale": "MLFlow fills gap in Databricks MLOps stack"
    },
    {
      "acquirer_id": "snowflake",
      "name": "Snowflake",
      "domain": "snowflake.com",
      "fit_score": 84,
      "tech_overlap": 79,
      "team_fit": 85,
      "network_overlap": 82,
      "estimated_deal_range": [120000000, 200000000],
      "rationale": "MLFlow extends Snowflake into ML workloads"
    },
    {
      "acquirer_id": "microsoft",
      "name": "Microsoft (Azure ML)",
      "domain": "microsoft.com",
      "fit_score": 79,
      "tech_overlap": 86,
      "team_fit": 76,
      "network_overlap": 71,
      "estimated_deal_range": [180000000, 300000000],
      "rationale": "Strengthens Azure ML vs AWS SageMaker"
    }
  ],
  "feature_importances": {
    "engineering_team_quality": 0.28,
    "open_source_community": 0.24,
    "github_stars_velocity": 0.19,
    "technical_ip": 0.16,
    "recruiting_difficulty": 0.13
  },
  "similar_acqui_hires": [
    {
      "company": "Comet.ml",
      "acquirer": "DataRobot",
      "year": 2022,
      "deal_size": 110000000,
      "score_at_time": 78
    }
  ],
  "llm_diagnosis": "MLFlow represents a textbook acqui-hire opportunity...",
  "computed_at": "2024-12-19T12:30:00Z"
}
```

---

## 6. 💼 InvestorBot - Investor Network Analysis

### Example Questions

**Basic Queries:**
- "Analyze my investor network"
- "Who are my most valuable investors?"
- "Show me investor centrality scores"
- "Which investors should I prioritize?"
- "What's my investor network quality?"

**Advanced Queries:**
- "Calculate betweenness centrality for my cap table"
- "Show co-investor graph and connections"
- "Analyze investor value-add beyond money"
- "Compare my investor network to competitors"
- "Identify introduction opportunities through investors"

### Example Response

```
💼 Investor Network Analysis for Quantum Health

OVERALL SCORE: 78/100 (STRONG INVESTOR NETWORK)
Network Health: 🟢 EXCELLENT

📊 NETWORK METRICS:
├── Betweenness Centrality: 82/100 (High connectivity)
├── Eigenvector Centrality: 79/100 (Connected to important nodes)
├── Network Diversity: 71/100 (Good sector spread)
└── Value-Add Score: 76/100 (Strong operational support)

🕸️ CO-INVESTOR GRAPH:

Seed Round (2021):
├─ Andreessen Horowitz (Lead) ──┬── General Catalyst
├─ General Catalyst ────────────┼── Lux Capital
├─ Lux Capital ───────────────┼── Andreessen Horowitz
└─ Village Global ──────────────┴── (Isolated node)

Series A (2023):
├─ Andreessen Horowitz (Lead) ──┬── GV
├─ GV ────────────────────────┼── Lux Capital
├─ Lux Capital ───────────────┼── Obvious Ventures
└─ Obvious Ventures ────────────┴── (New addition)

🔗 HIGH-VALUE CONNECTIONS:

1. Andreessen Horowitz ↔ General Catalyst
   Connection Strength: 0.94
   Shared Deals: 23 (including Figma, Slack, Coinbase)
   Opportunity: Introduction to GC portfolio for partnerships

2. Lux Capital ↔ GV  
   Connection Strength: 0.87
   Shared Deals: 17 (biotech focus overlap)
   Opportunity: Scientific advisory network access

3. Andreessen Horowitz ↔ GV
   Connection Strength: 0.82
   Shared Deals: 31 (Alphabet connection)
   Opportunity: Potential Google partnership/acquisition path

🏆 INVESTOR VALUE-ADD RANKING:

1. Andreessen Horowitz - Score: 94/100
   ├── Network Access: 98/100 (Top-tier connections)
   ├── Operational Support: 91/100 (Talent, GTM)
   ├── Follow-on Capacity: 95/100 (Deep pockets)
   └── Brand Halo: 92/100 (Signal to market)
   
2. Lux Capital - Score: 87/100
   ├── Network Access: 89/100 (Deep tech ecosystem)
   ├── Operational Support: 85/100 (Scientific expertise)
   ├── Follow-on Capacity: 88/100 (Fund size: $1.1B)
   └── Brand Halo: 86/100 (Hard tech credibility)

3. GV - Score: 81/100
   ├── Network Access: 94/100 (Google ecosystem)
   ├── Operational Support: 78/100 (Technical resources)
   ├── Follow-on Capacity: 82/100 (Alphabet backing)
   └── Brand Halo: 80/100 (Corporate VC signal)

4. General Catalyst - Score: 79/100
5. Obvious Ventures - Score: 71/100
6. Village Global - Score: 64/100

📈 NETWORK EVOLUTION:

2021 (Seed): Network Density: 0.62
2023 (Series A): Network Density: 0.74
2024 (Current): Network Density: 0.81

Trend: ⬆️ Network is becoming more interconnected (good for 
       introductions, warm outreach, deal flow)

💡 INTRODUCTION OPPORTUNITIES:

Through Andreessen Horowitz:
□ Intro to Figma design team (UX research partnership)
□ Intro to Databricks (data infrastructure evaluation)
□ Intro to Modern Treasury (payments integration)

Through Lux Capital:
□ Intro to Recursion Pharma (clinical data partnership)
□ Intro to Sakana AI (Japanese market entry)
□ Intro to Isomorphic Labs (competitive intelligence)

Through GV:
□ Intro to Google Health (regulatory pathways)
□ Intro to Verily (sensor technology partnership)
□ Intro to Fitbit (consumer health data)

🤖 AI DIAGNOSIS:
"Quantum Health has assembled a textbook tier-1 investor network
for a deep tech healthcare startup. The combination of Andreessen
Horowitz (brand + growth), Lux Capital (deep tech expertise), and
GV (Google ecosystem) provides exceptional coverage across all
dimensions a quantum sensing company needs.

The network density score of 0.81 is excellent - your investors
co-invest frequently, which means warm introductions are readily
available and investor alignment is high.

Key strategic insight: The Andreessen Horowitz ↔ GV connection
(31 shared deals) provides a potential path to Google acquisition
or partnership. Both firms have strong Alphabet relationships.

One gap: No dedicated healthcare/biotech specialist at the table.
Consider adding an investor like Arch Venture or 8VC for sector
expertise in future rounds."

📋 NETWORK OPTIMIZATION:
□ Schedule quarterly "investor network mapping" session
□ Request specific introductions from top 3 investors
□ Attend portfolio events for each major investor
□ Map competitor investor networks (for intelligence)
□ Identify gaps: Healthcare specialist, International (EU/Asia)
□ Prepare Series B target list based on network synergies
```

### Output Artifact

```json
{
  "bot_name": "investor",
  "startup_id": "uuid-here",
  "score": 78.0,
  "network_metrics": {
    "betweenness": 82.0,
    "eigenvector": 79.0,
    "diversity": 71.0,
    "value_add": 76.0
  },
  "co_investor_graph": {
    "nodes": [
      {"id": "a16z", "name": "Andreessen Horowitz", "centrality": 0.94},
      {"id": "gc", "name": "General Catalyst", "centrality": 0.79},
      {"id": "lux", "name": "Lux Capital", "centrality": 0.87},
      {"id": "gv", "name": "GV", "centrality": 0.81},
      {"id": "obvious", "name": "Obvious Ventures", "centrality": 0.71},
      {"id": "village", "name": "Village Global", "centrality": 0.64}
    ],
    "edges": [
      {"source": "a16z", "target": "gc", "weight": 23, "strength": 0.94},
      {"source": "lux", "target": "gv", "weight": 17, "strength": 0.87},
      {"source": "a16z", "target": "gv", "weight": 31, "strength": 0.82}
    ]
  },
  "investor_rankings": [
    {
      "investor_id": "a16z",
      "name": "Andreessen Horowitz",
      "value_add_score": 94,
      "network_access": 98,
      "operational_support": 91,
      "follow_on_capacity": 95,
      "brand_halo": 92
    },
    {
      "investor_id": "lux",
      "name": "Lux Capital",
      "value_add_score": 87,
      "network_access": 89,
      "operational_support": 85,
      "follow_on_capacity": 88,
      "brand_halo": 86
    }
  ],
  "network_density": 0.81,
  "density_trend": "increasing",
  "introduction_opportunities": [
    {
      "through_investor": "a16z",
      "target_company": "Figma",
      "potential_value": "UX research partnership",
      "warmth_score": 0.92
    },
    {
      "through_investor": "gv",
      "target_company": "Google Health",
      "potential_value": "Regulatory pathway guidance",
      "warmth_score": 0.88
    }
  ],
  "network_gaps": [
    "Healthcare/biotech specialist investor",
    "EU-based investor for international expansion",
    "Corporate strategic investor (pharma)"
  ],
  "llm_diagnosis": "Quantum Health has assembled a textbook tier-1 investor network...",
  "computed_at": "2024-12-19T12:30:00Z"
}
```

---

## 7. 🎓 AcceleratorBot - Accelerator ROI Ranking

### Example Questions

**Basic Queries:**
- "Which accelerator should I apply to?"
- "Compare accelerators for my startup"
- "What's the ROI of Y Combinator vs Techstars?"
- "Rank accelerators by outcomes"
- "Best accelerator for Series A success?"

**Advanced Queries:**
- "Show accelerator survival rates by cohort"
- "Compare follow-on rates across programs"
- "Which accelerators have best unicorn production?"
- "Analyze time-to-Series-A by accelerator"
- "Rank accelerators for my industry/stage"

### Example Response

```
🎓 Accelerator ROI Analysis for AI/ML Startups (Seed Stage)

OVERALL ANALYSIS: Top 10 Programs Ranked

🏆 GLOBAL RANKINGS (for AI/ML Seed Stage):

Rank  Program         ROI Score  Follow-on  Time to A  Survival
────────────────────────────────────────────────────────────────
 1    Y Combinator      94/100      89%        8.2mo      94%
 2    AI2 Incubator     89/100      85%        9.1mo      91%
 3    Techstars AI      84/100      78%        11.4mo     87%
 4    Entrepreneur F.   82/100      81%        10.2mo     85%
 5    500 Startups      78/100      72%        12.8mo     82%
 6    Alchemist Acc.    76/100      74%        13.1mo     79%
 7    Plug and Play     73/100      69%        14.2mo     76%
 8    SOSV (HAX)        71/100      68%        15.3mo     74%
 9    MassChallenge     68/100      64%        16.7mo     71%
10    Founder Inst.     66/100      61%        17.9mo     69%

📊 DETAILED ANALYSIS: Top 3

🥇 #1: Y Combinator
ROI Score: 94/100 | Global Rank: #1 | AI/ML Rank: #1

Normalized Metrics (vs AI/ML peer group):
├── Follow-on Rate: 89% (vs 73% avg) - TOP 5%
├── Median Time to Series A: 8.2 months (vs 12.4 avg) - FASTEST
├── 3-Year Survival Rate: 94% (vs 81% avg) - TOP 1%
├── Unicorn Rate: 8.2% (vs 1.8% avg) - 4.6x baseline
└── Shutdown Rate: 6% (vs 19% avg) - LOWEST RISK

Confidence Interval: [91, 97] (High confidence)

Peer Comparison:
• vs AI2: +5 points (network effects)
• vs Techstars: +10 points (follow-on speed)
• vs 500: +16 points (survival rate)

Best For:
✓ Founders who can relocate to Mountain View
✓ Ambitious, high-growth mindset
✓ Willing to give up 7% equity
✓ Can handle intense pace (3 months)

Not Ideal For:
✗ Non-full-time founders
✗ Lifestyle businesses
✗ Founders needing gradual ramp

---

🥈 #2: AI2 Incubator (Allen Institute for AI)
ROI Score: 89/100 | Global Rank: #3 | AI/ML Rank: #2

Normalized Metrics:
├── Follow-on Rate: 85% (vs 73% avg) - TOP 10%
├── Median Time to Series A: 9.1 months (vs 12.4 avg) - TOP 10%
├── 3-Year Survival Rate: 91% (vs 81% avg) - TOP 5%
├── Unicorn Rate: 4.7% (vs 1.8% avg) - 2.6x baseline
└── Shutdown Rate: 9% (vs 19% avg) - LOW RISK

Unique Advantages:
• AI research credibility (Allen Institute backing)
• No equity taken (grant-based)
• Deep technical mentorship
• Access to AI2 research/tools

Best For:
✓ Technical founders (PhDs, researchers)
✓ Research-heavy AI products
✓ Seattle-based or willing to relocate
✓ Want to keep full equity

Trade-offs:
⚠ Smaller network than YC
⚠ Less focus on commercialization
⚠ Fewer unicorn outcomes (but higher survival)

---

🥉 #3: Techstars AI (Any Location)
ROI Score: 84/100 | Global Rank: #7 | AI/ML Rank: #3

Normalized Metrics:
├── Follow-on Rate: 78% (vs 73% avg) - Above average
├── Median Time to Series A: 11.4 months (vs 12.4 avg) - Faster
├── 3-Year Survival Rate: 87% (vs 81% avg) - Above average
├── Unicorn Rate: 2.1% (vs 1.8% avg) - Baseline
└── Shutdown Rate: 13% (vs 19% avg) - Lower risk

Unique Advantages:
• Multiple locations (choose your market)
• Strong corporate partnerships
• Mentor-driven model
• Good for B2B AI startups

Best For:
✓ Want accelerator without relocating to SV
✓ Industry-specific AI (healthcare, fintech, etc.)
✓ B2B sales-focused founders
✓ Value mentorship over network

---

📈 PROGRAM-SPECIFIC RECOMMENDATIONS:

For Your Startup Profile (AI/ML, Seed, B2B):

Primary Recommendation: 🥇 Y Combinator
Match Score: 91/100
Reason: Fastest time-to-Series-A, highest follow-on rate, and 
       strongest investor network for AI companies.

Secondary: 🥈 AI2 Incubator  
Match Score: 87/100
Reason: If technical depth > commercial urgency. No equity cost.
       Strong for research-heavy products.

Tertiary: 🥉 Techstars AI (Industry vertical)
Match Score: 82/100
Reason: If you have strong industry domain and want local program.
       Good corporate partnership opportunities.

💡 ALTERNATIVE PATHWAYS:

Don't need an accelerator? Consider:
• AI Grant (Nat Friedman/Daniel Gross) - $250K no-strings funding
• Sequoia Arc - Pre-seed program, no equity
• OpenAI Fund - If using GPT models heavily

🤖 AI DIAGNOSIS:
"For an AI/ML startup at seed stage, Y Combinator offers the 
highest probability of successful Series A (89% follow-on, 8.2mo 
median). The network effects compound significantly - YC alumni
invest in each other, hire each other, and provide warm 
introductions at scale.

However, the AI2 Incubator is the hidden gem for technical 
founders. No equity cost and the Allen Institute credibility 
opens doors in research-heavy fields (biotech AI, scientific 
computing, etc.).

Consider applying to both - YC for the network, AI2 as backup
if you want to keep equity and have technical depth."

📋 APPLICATION STRATEGY:
□ Apply to Y Combinator (next batch deadline: check ycombinator.com)
□ Apply to AI2 Incubator (rolling admissions)
□ Research Techstars vertical programs (healthcare, fintech, etc.)
□ Consider AI Grant as non-dilutive alternative
□ Prepare demo that shows technical feasibility
□ Highlight team technical credentials (critical for AI2)
```

### Output Artifact

```json
{
  "bot_name": "accelerator",
  "analysis_type": "ai_ml_seed_stage",
  "accelerator_id": "y-combinator",
  "name": "Y Combinator",
  "roi_score": 94,
  "global_rank": 1,
  "category_rank": 1,
  "normalized_metrics": {
    "follow_on_rate": 89,
    "median_time_to_series_a_months": 8.2,
    "survival_rate_3yr": 94,
    "unicorn_rate": 8.2,
    "shutdown_rate": 6
  },
  "confidence_interval": [91, 97],
  "peer_comparison": {
    "vs_ai2": 5,
    "vs_techstars": 10,
    "vs_500_startups": 16
  },
  "industry_focus": "generalist_with_ai_ml_strength",
  "stage_focus": "seed",
  "location": "Mountain View, CA (remote options available)",
  "equity_taken": "7%",
  "cohort_size": "250-300 companies",
  "program_duration": "3 months",
  "top_alumni": ["Airbnb", "Stripe", "Dropbox", "Coinbase", "Instacart"],
  "recommendation_match_score": 91,
  "best_for": [
    "Ambitious high-growth founders",
    "Willing to relocate to Mountain View",
    "Accept 7% equity cost"
  ],
  "llm_diagnosis": "Y Combinator offers the highest probability of successful Series A...",
  "computed_at": "2024-12-19T12:30:00Z"
}
```

---

## 8. 📄 TermBot - Term Sheet Analysis

### Example Questions

**Basic Queries:**
- "Analyze this term sheet"
- "Is this term sheet founder-friendly?"
- "What red flags should I watch for?"
- "Show me term sheet clause analysis"
- "How does this compare to market?"

**Advanced Queries:**
- "Calculate founder-friendliness score"
- "Show liquidation preference waterfall"
- "Analyze anti-dilution provisions"
- "Compare to YC standard terms"
- "Identify most negotiable clauses"

### Example Response

```
📄 Term Sheet Analysis for Series A - CloudSecure

OVERALL SCORE: 67/100 (MODERATELY FOUNDER-FRIENDLY)
Risk Level: 🟡 CAUTION - Some concerning provisions

📊 CLAUSE-BY-CLAUSE ANALYSIS:

1️⃣ VALUATION & ECONOMICS
├── Pre-Money Valuation: $28M
├── Post-Money Valuation: $35M
├── Investment Amount: $7M
├── Price Per Share: $2.34
└── Founder-Friendly Score: 72/100 ✅

Market Comparison:
• Your valuation: $28M pre
• Market median (similar companies): $22-32M pre
• Your position: 75th percentile (strong) 💪

2️⃣ LIQUIDATION PREFERENCES ⚠️
├── Type: 1x NON-PARTICIPATING ✅
├── Score: 85/100 (Standard, reasonable)
├── Waterfall Analysis:
│   Exit at $50M → Investors get $7M, Founders get $43M
│   Exit at $100M → Investors get $7M, Founders get $93M
│   Exit at $35M (return of capital) → Investors get $7M
└── Risk: LOW - Standard 1x non-participating is market

3️⃣ ANTI-DILUTION PROTECTIONS 🔴
├── Type: BROAD-BASED WEIGHTED AVERAGE ⚠️
├── Score: 45/100 (Concerning)
├── Market Standard: Narrow-based weighted average (better for founders)
├── Impact Example:
│   If you raise at $20M pre in down round (from $28M):
│   • Broad-based: Investor conversion price drops to $1.87
│   • Narrow-based: Investor conversion price drops to $2.01
│   • Difference: Founders diluted ~7% more with broad-based
└── Recommendation: 🔴 NEGOTIATE to narrow-based

4️⃣ BOARD COMPOSITION ⚠️
├── Total Seats: 5
├── Founder Seats: 2 (40%)
├── Investor Seats: 2 (40%)
├── Independent Seats: 1 (20%)
├── Score: 68/100 (Acceptable but not ideal)
└── Market Standard: 3-2-0 or 2-2-1 (you have 2-2-1)

Risk: Deadlock possible (2-2 split on all issues)
Recommendation: Push for 3 founder seats OR veto rights

5️⃣ PROTECTIVE PROVISIONS 🔴
├── Investor Consent Required For:
│   ✅ New debt >$1M (reasonable)
│   ✅ Sale of company (standard)
│   ⚠️ Change in business model (broad)
│   ⚠️ Hiring/firing executives (excessive control)
│   🔴 Budget changes >10% (micromanagement)
│   🔴 Any IP licensing (overly broad)
├── Score: 52/100 (Too many veto rights)
└── Recommendation: Remove business model, hiring, budget provisions

6️⃣ FOUNDER VESTING ✅
├── Current: 75% vested, 25% unvested (4-year)
├── New Terms: 4-year vesting, 1-year cliff (restart)
├── Acceleration: Single trigger only (not double)
├── Score: 78/100 (Reasonable)
└── Market Standard: 4-year vest, double trigger accel (you're close)

7️⃣ RIGHT OF FIRST REFUSAL (ROFR) ⚠️
├── Transfer ROFR: Yes (standard)
├── Pro Rata ROFR: Yes (standard)
├── Pay-to-Play: NO 🔴 (concerning omission)
├── Score: 58/100
└── Risk: Without pay-to-play, investors may not participate in down rounds

8️⃣ NO-SHOP / EXCLUSIVITY ✅
├── Duration: 30 days
├── Score: 85/100 (Standard, not excessive)
└── Note: 30 days is reasonable; >45 days would be excessive

📈 RED FLAGS SUMMARY:
🔴 HIGH CONCERN (Fix before signing):
• Broad-based weighted average anti-dilution (-12 points)
• Excessive protective provisions (budget, hiring, business model)
• Missing pay-to-play clause

🟡 MEDIUM CONCERN (Try to negotiate):
• Board composition creates deadlock risk
• Founder vesting restart (push for credit for time served)
• ROFR without pay-to-play protection

✅ ACCEPTABLE (Market standard):
• 1x non-participating liquidation preference
• 30-day no-shop
• General governance provisions
• Valuation at 75th percentile

💡 MARKET BENCHMARKS:

Clause                    Your Terms      Market Standard    Grade
───────────────────────────────────────────────────────────────
Liquidation Preference    1x Non-Part.    1x Non-Part.       ✅ A
Anti-Dilution           Broad-Based     Narrow-Based       🔴 D
Board Control           40% Founders    50%+ Founders      🟡 C
Protective Provisions   8 items         4-5 items          🔴 D
Vesting                 4yr restart     4yr w/ credit        🟡 B-

🤖 AI DIAGNOSIS:
"This term sheet has a 'Trojan horse' structure - attractive 
valuation ($28M is strong) but concerning control provisions.

The anti-dilution clause is the biggest concern. Broad-based
weighted average can cost you 5-10% additional dilution in a
down round compared to narrow-based. For a $7M round, that's
potentially $2-3M in value transfer.

The protective provisions are also excessive. Budget and hiring
vetoes give investors operational control that should remain with
founders. These provisions can paralyze decision-making.

The good news: The valuation is fair and liquidation preference
is standard. These are the hardest terms to negotiate, so you're
starting from a reasonable base.

Negotiation priority: Fix anti-dilution and protective provisions.
Consider giving on board composition if needed to win these."

📋 NEGOTIATION PLAYBOOK:

Priority 1 - Must Fix (Don't sign without these):
□ Anti-dilution: Broad-based → Narrow-based weighted average
□ Remove protective provisions: Budget, hiring, business model
□ Add pay-to-play clause

Priority 2 - Strongly Prefer:
□ Board: 3 founder seats OR supermajority founder veto
□ Vesting: Credit for time served (don't restart 4-year clock)
□ Double-trigger acceleration on founder vesting

Priority 3 - Nice to Have:
□ Information rights: Quarterly (not monthly) reporting
□ Preemptive rights: Limit to next round only
□ Registration rights: Cut back (expensive to implement)

Acceptable as-is:
✓ Valuation at $28M pre
✓ 1x non-participating liquidation preference
✓ 30-day no-shop provision
✓ General governance framework

🎯 NEGOTIATION TACTICS:

For Anti-Dilution:
"We're aligned on valuation, but the anti-dilution mechanism needs
to be narrow-based. Broad-based penalizes us for option pool 
fluctuations that don't reflect true down rounds. Let's use the 
NVCA standard narrow-based formula."

For Protective Provisions:
"We're happy to include standard protective provisions for major
corporate actions - sale, IPO, new debt. But day-to-day operations
like hiring and budgeting need to remain with management. Trust
is a two-way street."

For Board Composition:
"We need a board that can make decisions. Either 3-2 founder 
majority or a supermajority provision requiring founder consent.
This protects both sides from deadlock."
```

### Output Artifact

```json
{
  "bot_name": "term",
  "term_sheet_id": "uuid-here",
  "startup_id": "uuid-here",
  "founder_friendliness_score": 67,
  "risk_level": "caution",
  "clause_scores": {
    "valuation_economics": {
      "score": 72,
      "pre_money": 28000000,
      "post_money": 35000000,
      "investment_amount": 7000000,
      "price_per_share": 2.34,
      "market_percentile": 75
    },
    "liquidation_preference": {
      "score": 85,
      "type": "1x_non_participating",
      "multiple": 1,
      "participating": false,
      "waterfall_examples": {
        "exit_50m": {
          "investors": 7000000,
          "founders": 43000000
        },
        "exit_100m": {
          "investors": 7000000,
          "founders": 93000000
        }
      }
    },
    "anti_dilution": {
      "score": 45,
      "type": "broad_based_weighted_average",
      "market_standard": "narrow_based_weighted_average",
      "impact": "5-10% additional dilution in down round",
      "recommendation": "NEGOTIATE - Switch to narrow-based"
    },
    "board_composition": {
      "score": 68,
      "total_seats": 5,
      "founder_seats": 2,
      "investor_seats": 2,
      "independent_seats": 1,
      "deadlock_risk": true
    },
    "protective_provisions": {
      "score": 52,
      "total_items": 8,
      "market_standard_items": 4,
      "concerning_items": [
        "change_in_business_model",
        "hiring_firing_executives",
        "budget_changes_gt_10pct",
        "any_ip_licensing"
      ]
    },
    "founder_vesting": {
      "score": 78,
      "vesting_schedule": "4_year",
      "cliff": "1_year",
      "acceleration": "single_trigger",
      "restart": true
    },
    "rofr": {
      "score": 58,
      "transfer_rofr": true,
      "pro_rata_rofr": true,
      "pay_to_play": false
    },
    "no_shop": {
      "score": 85,
      "duration_days": 30,
      "market_standard_days": 30
    }
  },
  "red_flags": [
    {
      "severity": "high",
      "clause": "anti_dilution",
      "issue": "Broad-based weighted average instead of narrow-based",
      "impact": "5-10% additional dilution in down rounds"
    },
    {
      "severity": "high",
      "clause": "protective_provisions",
      "issue": "Excessive investor veto rights over operations",
      "impact": "Potential management paralysis"
    },
    {
      "severity": "high",
      "clause": "pay_to_play",
      "issue": "Missing pay-to-play clause",
      "impact": "No protection if investors don't participate in future rounds"
    }
  ],
  "market_benchmarks": {
    "liquidation_preference": {"grade": "A", "status": "acceptable"},
    "anti_dilution": {"grade": "D", "status": "red_flag"},
    "board_control": {"grade": "C", "status": "caution"},
    "protective_provisions": {"grade": "D", "status": "red_flag"},
    "vesting": {"grade": "B-", "status": "caution"}
  },
  "negotiation_priority": [
    {
      "priority": 1,
      "must_fix": true,
      "item": "Switch anti-dilution to narrow-based weighted average",
      "tactic": "Reference NVCA standard template"
    },
    {
      "priority": 1,
      "must_fix": true,
      "item": "Remove operational protective provisions (budget, hiring, business model)",
      "tactic": "Emphasize trust and founder autonomy"
    },
    {
      "priority": 2,
      "strongly_prefer": true,
      "item": "Fix board deadlock risk",
      "tactic": "Propose 3-2 founder majority or supermajority veto"
    }
  ],
  "llm_diagnosis": "This term sheet has a 'Trojan horse' structure...",
  "analyzed_at": "2024-12-19T12:30:00Z"
}
```

---

## 📋 Quick Reference Card

| Bot | Best Question | Expected Score Range | Action Triggers |
|-----|-------------|---------------------|-----------------|
| **Runway** | "How's my runway?" | 40-100 | < 65 = stress warning |
| **Obituary** | "What could kill us?" | 0-100 | > 70 = high risk |
| **PMF** | "Do we have PMF?" | 0-100 | > 60 = inflection detected |
| **Pivot** | "Any pivot signals?" | 0-100 | Multiple pivots = pattern |
| **Acqui** | "Acqui probability?" | 0-100 | > 60 = likely target |
| **Investor** | "Network quality?" | 0-100 | > 75 = excellent |
| **Accelerator** | "Which program?" | 0-100 | Compare multiple |
| **Term** | "Analyze term sheet" | 0-100 | > 70 = founder-friendly |

---

## 🎯 Pro Tips for Maximum Value

1. **Cross-Bot Analysis**: Ask about the same startup across multiple bots for comprehensive intelligence
2. **Comparative Questions**: "Compare my runway to [Competitor]" for competitive intelligence
3. **Trend Analysis**: "How has my PMF changed over the last 6 months?"
4. **Scenario Planning**: "What if I cut 20% of headcount?" (RunwayBot)
5. **Investor Prep**: Run all 8 bots before investor meetings for complete picture

---

*Generated by StartupIntel v0.3.0 - 8 Specialized ML Bots for Startup Intelligence*
