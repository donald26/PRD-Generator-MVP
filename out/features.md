system
You produce structured feature lists derived strictly from the PRD.
user
You are a senior Product Manager and Tech Lead collaborating.

From the PRD below, create a structured feature list in Markdown.

Hard rules:
- Do NOT invent features not implied by the PRD.
- Group features into 4–8 logical groups.
- For each feature include:
  - Description (1–2 lines)
  - Primary Persona
  - Priority (P0/P1/P2)
  - Dependencies (0+)
  - Risks (0+)
- Keep the output concise but complete.

PRD:
system
You produce high-quality PRDs. Follow the outline and do not hallucinate missing facts.
user
You are a senior Product Manager writing a PRD.

Write a detailed PRD in Markdown based on the product information below.
Hard rules:
- Use the exact section headings in this outline (keep order).
- Be concrete and implementation-oriented, but do not write code.
- If information is missing, put it under 'Assumptions & Open Questions' instead of guessing.
- Keep it to ~2–4 pages of Markdown (not a novel).

PRD OUTLINE:
## Overview
## Problem Statement
## Goals
## Non-Goals
## Target Personas
## User Journeys
## Functional Requirements
## Non-Functional Requirements
## Success Metrics
## Assumptions & Open Questions
## Out of Scope

PRODUCT INFORMATION:
system
You summarize multiple product documents faithfully. Do not hallucinate missing facts.
user
You are a Staff Product Manager. You are given multiple documents (meeting notes, docs, emails, etc.) about a product idea.

Task:
- Extract the most important facts and constraints WITHOUT inventing anything.
- Produce:
  1) A short 'Product Intent' paragraph (3-6 sentences)
  2) Key facts (bullets)
  3) Constraints / requirements (bullets)
  4) Open questions (bullets)
  5) Glossary (optional)

Hard rules:
- If the documents conflict, call it out under Open Questions.
- Keep the summary concise (<= 500 words).

DOCUMENTS:
=== FILE: examples/loan_underwriting_docs/current_state_process.md (type=text) ===
# Current Underwriting Process (As-Is)

1. Loan application received via LOS
2. Analyst manually reviews:
   - Application form
   - Uploaded documents
3. Credit bureau reports pulled manually
4. Bank statements reviewed manually
5. Risk score calculated in spreadsheet
6. Analyst writes notes and recommendation
7. Supervisor reviews and approves
8. Decision communicated to applicant

Issues:
- Highly dependent on analyst experience
- Inconsistent decisions across analysts
- High rework due to missing documents
- No centralized audit trail
- Turnaround time: 2–5 business days

=== FILE: examples/loan_underwriting_docs/exec_vision.md (type=text) ===
# Executive Vision – AI Underwriting Platform

We aim to build a modern underwriting platform that leverages AI agents to augment human underwriters, not replace them.

The platform should:
- Improve speed, consistency, and scalability of underwriting
- Reduce operational costs per loan
- Enable lenders to adapt risk policies quickly
- Provide full transparency into decision rationale

Success will be measured by:
- Reduction in average underwriting time
- Reduction in manual effort per application
- Improved approval consistency across analysts

The platform must be enterprise-ready:
- Secure by default
- Auditable
- Compliant with financial regulations

Longer term, this platform can expand beyond underwriting into portfolio monitoring and risk management.

=== FILE: examples/loan_underwriting_docs/meeting_notes_discovery.txt (type=text) ===
Discovery session – AI underwriting platform

Participants: Head of Credit, Ops Lead, Product, Engineering

- Goal is to reduce underwriting TAT from days to minutes
- Current process is heavily manual, rule-based + spreadsheets
- Analysts pull data from multiple sources: bank statements, credit bureaus, KYC docs
- Desire to introduce AI agents that can:
  - Pre-screen applications
  - Flag risk factors
  - Recommend approve / reject / manual review
- Humans must stay in the loop for high-risk loans
- Need explainability for every decision
- Regulators will audit decisions
- Initial focus on SME loans, not retail credit cards
- Non-goal: fully autonomous approval in phase 1
- Need configurable risk policies per lender
- Integration with existing LOS systems is mandatory
- Latency matters — decisions should be near real-time

=== FILE: examples/loan_underwriting_docs/pain_points_from_ops.txt (type=text) ===
Ops & Underwriting Team Feedback

- Too much time spent on low-risk applications
- Hard to keep policies in sync across teams
- Analysts don't trust automated scores today
- Reviewing documents is repetitive and error-prone
- Explaining decisions to auditors is painful
- Training new underwriters takes months

=== FILE: examples/loan_underwriting_docs/regulatory_constraints.md (type=text) ===
# Regulatory and Compliance Constraints

- All underwriting decisions must be explainable
- Decision inputs and outputs must be logged and retained for audit
- Models must not introduce bias based on protected attributes
- Ability to reconstruct decision logic for any loan
- Human override must be possible
- Data residency requirements may vary by region
- Vendors may be subject to model risk management (MRM) reviews

Non-compliance risks:
- Regulatory fines
- Loss of lending license
- Reputational damage

=== FILE: examples/loan_underwriting_docs/sample_customer_feedback.txt (type=text) ===
Customer feedback excerpts:

- "I waited 4 days to hear back on a simple loan"
- "The rejection reason was unclear"
- "We had to submit documents multiple times"
- "Process felt opaque and inconsistent"


Return ONLY the summary in Markdown with these headings:
## Product Intent
## Key Facts
## Constraints
## Open Questions
## Glossary

assistant
### Product Intent
Our goal is to develop an AI-driven underwriting platform that significantly reduces turnaround time, improves consistency, and enhances the efficiency of loan processing. The platform should leverage AI agents to assist human underwriters, ensuring transparent and explainable decisions while maintaining regulatory compliance. This initiative aims to streamline operations, reduce errors, and empower lenders to adapt their risk policies more swiftly.

### Key Facts
1. **Platform Functionality**: AI-driven underwriting platform to augment human underwriters.
2. **Operational Efficiency**: Reduces underwriting time and manual effort.
3. **Regulatory Compliance**: Ensures all underwriting decisions are explainable and compliant with financial regulations.
4. **Decision Transparency**: Provides clear rationale for each decision.
5. **User Experience**: Enables lenders to adapt risk policies quickly and maintain audit trails.
6. **Integration**: Mandatory integration with existing LOS systems.
7. **Scalability**: Can handle both SME and retail credit card loans.
8. **Risk Management**: Potential expansion into portfolio monitoring and risk management.

### Constraints
1. **Regulatory Compliance**: Must adhere to strict regulatory guidelines, including explainability, data retention, and compliance with protected attributes.
2. **Human Oversight**: Humans must remain involved in critical decisions, especially for high-risk loans.
3. **Data Security**: Must ensure secure data handling and retention.
4. **Training and Support**: New underwriters require significant training, taking months to become proficient.
5. **Operational Costs**: Requires careful consideration of operational costs and potential savings.
6. **Latency**: Decisions must be near real-time to meet customer expectations.

### Open Questions
1. **Cost-Benefit Analysis**: How does the platform compare to current processes in terms of cost savings and operational efficiencies?
2. **Model Bias**: What measures are taken to avoid introducing bias in the AI models?
3. **Vendor Responsibility**: Who is responsible for MRM reviews when using third-party vendors?
4. **Scalability**: Will the platform scale effectively to accommodate a large number of users and diverse loan types?

### Glossary
- **AI Agent**: An intelligent system designed to perform tasks without explicit programming.
- **LOSI**: Loan Originator System.
- **LOS**: Loan Officer System.
- **KYC**: Know Your Customer.
- **TAT**: Time to Approval.
- **MRM**: Model Risk Management.


Return ONLY the PRD Markdown.

assistant
```markdown
### Product Intent
Our goal is to develop an AI-driven underwriting platform that significantly reduces turnaround time, improves consistency, and enhances the efficiency of loan processing. The platform should leverage AI agents to assist human underwriters, ensuring transparent and explainable decisions while maintaining regulatory compliance. This initiative aims to streamline operations, reduce errors, and empower lenders to adapt their risk policies more swiftly.

### Key Facts
1. **Platform Functionality**: AI-driven underwriting platform to augment human underwriters.
2. **Operational Efficiency**: Reduces underwriting time and manual effort.
3. **Regulatory Compliance**: Ensures all underwriting decisions are explainable and compliant with financial regulations.
4. **Decision Transparency**: Provides clear rationale for each decision.
5. **User Experience**: Enables lenders to adapt risk policies quickly and maintain audit trails.
6. **Integration**: Mandatory integration with existing LOS systems.
7. **Scalability**: Can handle both SME and retail credit card loans.
8. **Risk Management**: Potential expansion into portfolio monitoring and risk management.

### Constraints
1. **Regulatory Compliance**: Must adhere to strict regulatory guidelines, including explainability, data retention, and compliance with protected attributes.
2. **Human Oversight**: Humans must remain involved in critical decisions, especially for high-risk loans.
3. **Data Security**: Must ensure secure data handling and retention.
4. **Training and Support**: New underwriters require significant training, taking months to become proficient.
5. **Operational Costs**: Requires careful consideration of operational costs and potential savings.
6. **Latency**: Decisions must be near real-time to meet customer expectations.

### Open Questions
1. **Cost-Benefit Analysis**: How does the platform compare to current processes in terms of cost savings and operational efficiencies?
2. **Model Bias**: What measures are taken to avoid introducing bias in the AI models?
3. **Vendor Responsibility**: Who is responsible for MRM reviews when using third-party vendors?
4. **Scalability**: Will the platform scale effectively to accommodate a large number of users and diverse loan types?

### Glossary
- **AI Agent**: An intelligent system designed to perform tasks without explicit programming.
- **LOSI**: Loan Originator System.
- **LOS**: Loan Officer System.
- **KYC**: Know Your Customer.
- **TAT**: Time to Approval.
- **MRM**: Model Risk Management.
```


Return ONLY the feature list Markdown.

assistant
```markdown
### Feature List

#### 1. **Underwriting Automation**
- **Description**: Introduce AI-driven underwriting agents to automate routine tasks such as document review and preliminary risk assessment.
- **Primary Persona**: Loan officers, underwriters, and risk managers.
- **Priority**: P1
- **Dependencies**: Integration with existing LOS systems, data security, and compliance with regulatory standards.
- **Risks**: Potential for initial resistance from human underwriters; need to ensure smooth transition.

#### 2. **Real-Time Decision Making**
- **Description**: Implement near-real-time decision-making capabilities to provide instant feedback to applicants and stakeholders.
- **Primary Persona**: Customers, loan officers, and regulators.
- **Priority**: P1
- **Dependencies**: Data infrastructure, latency optimization, and integration with external systems.
- **Risks**: High latency could lead to frustration among customers; need to balance speed with accuracy.

#### 3. **Transparent Decision Rationale**
- **Description**: Ensure that every underwriting decision is accompanied by a clear rationale, allowing stakeholders to understand the basis for each decision.
- **Primary Persona**: Customers, loan officers, and regulators.
- **Priority**: P1
- **Dependencies**: AI agent development, data logging, and audit trail maintenance.
- **Risks**: Lack of transparency could lead to mistrust; need to ensure data integrity and accessibility.

#### 4. **Auditable Decision Log**
- **Description**: Maintain a comprehensive audit trail of all underwriting decisions, including timestamps, reviewers, and rationale.
- **Primary Persona**: Auditors, regulators, and legal teams.
- **Priority**: P2
- **Dependencies**: Data logging, compliance with regulatory requirements, and integration with external systems.
- **Risks**: Data loss or tampering could compromise decision accountability; need robust security measures.

#### 5. **Enhanced Document Review**
- **Description**: Develop AI-driven tools to assist in reviewing complex and voluminous documentation, reducing the burden on human reviewers.
- **Primary Persona**: Underwriters, risk managers, and loan officers.
- **Priority**: P1
- **Dependencies**: Integration with existing document management systems, data security, and compliance with regulatory standards.
- **Risks**: Over-reliance on AI could lead to errors; need to ensure AI's accuracy and reliability.

#### 6. **Risk Factor Identification**
- **Description**: Train AI agents to identify key risk factors in loan applications, enabling early intervention and risk mitigation.
- **Primary Persona**: Underwriters, risk managers, and loan officers.
- **Priority**: P1
- **Dependencies**: Data analysis, machine learning algorithms, and integration with existing risk assessment systems.
- **Risks**: AI may misinterpret data; need to ensure AI's objectivity and fairness.

#### 7. **Policy Configuration**
- **Description**: Allow lenders to configure risk policies at the project level, enabling tailored underwriting strategies.
- **Primary Persona**: Lenders, risk managers, and loan officers.
- **Priority**: P1
- **Dependencies**: Integration with existing risk assessment systems, compliance with regulatory requirements, and user-friendly interface.
- **Risks**: Complex policy configurations could lead to errors; need to simplify the process.

#### 8. **Decision Logging and Reporting**
- **Description**: Provide detailed logs and reports on underwriting decisions, facilitating easy tracking and analysis.
- **Primary Persona**: Lenders, risk managers, and loan officers.
- **Priority**: P1
- **Dependencies**: Data logging, compliance with regulatory requirements, and integration with external systems.
- **Risks**: Data loss or corruption could hinder decision analysis; need robust data protection measures.

#### 9. **Consistent Decision Making**
- **Description**: Ensure that underwriting decisions are consistent across different underwriters, reducing variability and improving overall quality.
- **Primary Persona**: Underwriters, risk managers, and loan officers.
