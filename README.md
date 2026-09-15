# 66degrees Content Marketing AI Agents Plugin for Gemini / Claude / ChatGPT

> **From marketing brief to campaign-ready content — with AI doing the production work, built-in governance and QA, and a human making the final call.**

An MCP-powered content marketing system for 66degrees.

It connects strategy, event content, blog and white paper creation, optimization, repurposing, brand governance, QA, human approval, and export into one workflow.

---

## What is this?

Most AI content workflows look like this:

**Prompt → AI → Copy**

This project is designed to work more like a **marketing production team**:

**Brief → Strategy → Create → Check → Improve → Approve → Export**

The system is designed for **event content, blogs, and white papers** — with the same governed workflow behind each format.

You give the system a marketing goal or event brief.

It helps turn that input into structured, campaign-ready content while keeping 66degrees messaging, quality checks, and human approval in the workflow.

---

## 🔄 How it works

The workflow has five simple layers:

**1. Input**  
A marketing goal, campaign brief, or event brief.

**2. Skills & MCP tools**  
The system decides which capability is needed — strategy, content creation, refinement, social, repurposing, optimization, QA, approval, or export.

**3. Core & technology**  
The work is grounded in 66degrees brand rules, approved references, content-quality checks, originality checks, and specialist engines such as Emailens.

**4. QA & human review**  
Content can **PASS**, raise a **WARNING**, or require a **REWRITE**. A human reviews the campaign before final export.

**5. Final output**  
An approved campaign kit that can be exported to **DOCX, XLSX, or JSON**.

![Content marketing workflow](assets/content-marketing-flow.svg)

*Illustration of the workflow — every tool and technology layer shown represents a real component in this repository.*

---

## 🤖 11 AI agents working behind the scenes

Think of the system as **11 AI specialists working together for you**. You interact with the workflow naturally; the specialist agents handle strategy, event intelligence, content creation, refinement, social content, repurposing, optimization, QA, approval, and export behind the scenes.

The goal is simple: **less time spent moving content between tools, more time spent on the ideas and decisions that matter.**

## 🧩 Skills

The system brings together the capabilities needed to take a campaign from idea to approved output.

| Skill | What it does |
|---|---|
| **Strategy** | Turns marketing goals into a content strategy |
| **Event Intelligence** | Turns event information into a structured campaign brief |
| **Content Creation** | Creates campaign and content assets |
| **Refinement** | Improves content using feedback |
| **Social** | Turns source content into platform-specific social posts |
| **Repurposing** | Converts one asset into multiple formats |
| **Optimization** | Improves content using QA feedback |
| **Brand Governance** | Keeps content aligned with 66degrees messaging |
| **Quality Assurance** | Checks content before it moves forward |
| **Human Approval** | Keeps a person in control of the final campaign |
| **Export** | Turns approved work into usable campaign files |

---

## 🧠 Built for 66degrees

The system is not designed to generate generic marketing copy.

It uses 66degrees brand and messaging guidance as part of the workflow, including:

- Voice and tone
- Messaging hierarchy
- Strategic pillars
- Approved terminology
- Brand governance
- Approved reference content

The current brand rules enforce terminology such as **Google Cloud Premier Partner**, **Generative AI**, and **SecOps**, while blocking defined forbidden jargon.

The **66degrees Messaging Foundation v17** provides the canonical messaging foundation for positioning and terminology.

---

## 🐴 Built with Ponytail principles

The engineering approach follows the philosophy of **Ponytail**:

> Keep the implementation small. Reuse the standard library and existing dependencies where they already solve the problem. Don't add complexity without a reason.

But simplicity does **not** mean cutting corners.

Validation, error handling, security, and accessibility remain part of the implementation.

This philosophy is reflected in the deliberately small public MCP surface: **11 tools**, with specialist strategies kept internal to the core.

---

## 🛠️ Technology

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| AI interface | MCP |
| Data validation | Pydantic |
| Reference storage | SQLite |
| Semantic retrieval | Optional ChromaDB / sentence-transformers |
| Web intelligence | HTTPX, BeautifulSoup, Playwright |
| Email QA | Emailens |
| Export | DOCX, XLSX, JSON |
| AI clients | Claude, ChatGPT, Gemini |
| Testing | pytest |

---

<details>
<summary><strong>🤖 The 11 AI agents behind the workflow</strong></summary>

| Tool | Purpose |
|---|---|
| `generate_content_strategy` | Generate a content strategy |
| `process_event_brief` | Validate and structure an event brief |
| `generate_campaign_kit` | Generate a campaign kit |
| `generate_content_asset` | Generate a content asset |
| `refine_content_asset` | Refine an existing asset |
| `generate_social_posts` | Generate social posts |
| `repurpose_content_asset` | Repurpose an existing asset |
| `optimize_content_asset` | Optimize content using QA feedback |
| `qa_validate_asset` | Run content QA |
| `approve_campaign_kit` | Apply the human approval gate |
| `export_campaign_kit` | Export an approved campaign kit |

These are the technical interfaces behind the 11 AI agents; specialist strategies remain internal implementation components.

</details>

---

## ⏱️ Approximate time savings

A typical content workflow can involve research, outlining, drafting, editing, brand checks, repurposing, QA, and formatting. By bringing these steps into one workflow, the system is designed to reduce a large amount of repetitive production work.

**Illustrative target:** a task that might take **4–6 hours manually** can be reduced to roughly **1–2 hours of human effort**, depending on the asset, research depth, and review required.

![Approximate content production time savings](assets/content-time-savings.svg)

*Illustrative estimate — actual savings vary by content type, complexity, and human review.*

## 📚 Reference library

The reference library gives the system controlled context instead of relying on generic knowledge alone.

The library is designed to hold approximately **2,000+ competitive advertising examples** alongside approved 66degrees and Google Cloud references. The content is stored in **SQLite** so the AI agents can search for relevant examples and messaging patterns before creating content.

The competitive/reference collection is designed to refresh approximately every **7 days**, while the approved reference sources currently refresh every **2 days**.

Sources are prioritized in this order:

1. 66degrees Brand Guidelines
2. 66degrees approved content
3. Event / Content brief
4. Historical performance and content
5. External open-source methodologies

Approved reference sources currently include 66degrees events, 66degrees success stories, and Google Cloud events.

---

## 👤 Human-in-the-loop

AI does the production work.

Automated QA checks the result.

A human makes the final decision.

```text
Generate
   ↓
QA
   ↓
Refine if needed
   ↓
Human Review
   ↓
Approve
   ↓
Export
```
## License

This project is **for the 66degrees team only** and is not intended for external use or redistribution.
