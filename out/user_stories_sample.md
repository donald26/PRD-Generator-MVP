# User Stories

**Total Stories**: 12
**Total Story Points**: 58
**By Epic**: EP-001: 8 stories | EP-002: 3 stories | EP-003: 1 stories
**By Priority**: P0: 9 | P1: 2 | P2: 1

This document defines user stories organized by epic and feature. Each story includes Gherkin-style acceptance criteria, story point estimates, and implementation notes.

---

## Epic EP-001: Underwriting

### Feature F-001: AI Application Pre-screening

#### US-001: Loan Officer Reviews AI Pre-screening Results

**Story ID**: US-001
**Feature**: F-001 (AI Application Pre-screening)
**Epic**: EP-001 (Underwriting)
**Priority**: P0
**Story Points**: 5
**Persona**: Loan Officer

**User Story**
As a Loan Officer,
I want to view AI pre-screening results for submitted applications,
So that I can quickly identify which applications require immediate attention versus those ready for processing.

**Acceptance Criteria**
- [ ] Given a new loan application submitted, When the AI pre-screening completes, Then the loan officer sees results within 30 seconds
- [ ] Given pre-screening results displayed, When reviewing the recommendation, Then the confidence score and top 3 risk factors are clearly visible
- [ ] Given a pre-screened application, When viewing the details, Then missing documents are highlighted with specific requests
- [ ] Given multiple applications in the queue, When filtering by AI recommendation, Then applications can be sorted by approve/reject/review status

**Technical Notes**
- API endpoint: GET /api/v1/applications/{id}/prescreening
- Real-time notifications via WebSocket when pre-screening completes
- UI component: ApplicationPreScreeningCard with status badges
- Cache pre-screening results for 24 hours

**Dependencies**
- None

**Definition of Done**
- [ ] Code complete and reviewed
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Acceptance criteria validated

---

#### US-002: AI Agent Identifies Missing Documents

**Story ID**: US-002
**Feature**: F-001 (AI Application Pre-screening)
**Epic**: EP-001 (Underwriting)
**Priority**: P0
**Story Points**: 3
**Persona**: Loan Officer

**User Story**
As a Loan Officer,
I want the AI to automatically identify missing required documents,
So that I can request them from applicants before starting manual review.

**Acceptance Criteria**
- [ ] Given an incomplete application, When AI pre-screening runs, Then all missing required documents are listed
- [ ] Given missing documents identified, When generating request email, Then pre-filled email template includes specific document names
- [ ] Given document requirements vary by loan type, When analyzing applications, Then AI applies correct document checklist (SME vs. retail)
- [ ] Given previously requested documents, When re-screening, Then AI tracks which documents are still pending

**Technical Notes**
- Document requirements configured per loan type in database table: loan_type_requirements
- Email template service: EmailTemplateService.generateMissingDocsRequest()
- Document tracking stored in application_documents table with status enum

**Dependencies**
- US-001 (must have pre-screening results first)

**Definition of Done**
- [ ] Code complete and reviewed
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Acceptance criteria validated

---

### Feature F-002: Automated Document Verification

#### US-003: System Extracts Data from Uploaded Documents

**Story ID**: US-003
**Feature**: F-002 (Automated Document Verification)
**Epic**: EP-001 (Underwriting)
**Priority**: P0
**Story Points**: 8
**Persona**: Underwriter

**User Story**
As an Underwriter,
I want the system to automatically extract key data from uploaded documents,
So that I don't have to manually type information from bank statements and tax forms.

**Acceptance Criteria**
- [ ] Given a PDF bank statement uploaded, When OCR processing completes, Then account balance and transaction history are extracted with 98% accuracy
- [ ] Given a tax return (1040 form) uploaded, When processing completes, Then AGI, filing status, and W2 income are extracted
- [ ] Given an image file (JPG/PNG) uploaded, When processing runs, Then text is extracted with comparable accuracy to PDF
- [ ] Given extraction errors detected, When accuracy is below threshold, Then document is flagged for manual review with specific error locations
- [ ] Given extracted data, When displaying to underwriter, Then confidence scores show reliability of each extracted field

**Technical Notes**
- OCR engine: AWS Textract or Google Cloud Vision API
- Document parser service: DocumentParserService with strategy pattern for different document types
- Extracted data stored in structured_document_data table (JSONB column)
- Background job processing via Celery/RabbitMQ for async document processing

**Dependencies**
- None (foundational feature)

**Definition of Done**
- [ ] Code complete and reviewed
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing with sample documents
- [ ] Documentation updated
- [ ] Acceptance criteria validated
- [ ] OCR accuracy benchmark tests pass

---

#### US-004: Cross-document Data Validation

**Story ID**: US-004
**Feature**: F-002 (Automated Document Verification)
**Epic**: EP-001 (Underwriting)
**Priority**: P0
**Story Points**: 5
**Persona**: Underwriter

**User Story**
As an Underwriter,
I want the system to cross-check data across multiple documents,
So that inconsistencies are automatically flagged before I review the application.

**Acceptance Criteria**
- [ ] Given income stated on application, When compared to W2/tax return, Then discrepancies >10% are flagged
- [ ] Given applicant name on different documents, When validating, Then spelling variations are detected but not flagged as errors
- [ ] Given bank account balance on statement, When compared to assets declared, Then shortfalls are highlighted
- [ ] Given validation rules configured, When running cross-checks, Then custom rules per loan type are applied
- [ ] Given inconsistencies found, When displaying to underwriter, Then specific documents and fields are cited

**Technical Notes**
- Validation rules engine: BusinessRulesEngine with configurable rule definitions
- Fuzzy matching for name variations using Levenshtein distance
- Validation results stored with links to specific document sections
- API endpoint: POST /api/v1/applications/{id}/validate-documents

**Dependencies**
- US-003 (requires extracted document data)

**Definition of Done**
- [ ] Code complete and reviewed
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Acceptance criteria validated

---

### Feature F-003: Risk Assessment Engine

#### US-005: Generate Real-time Risk Score

**Story ID**: US-005
**Feature**: F-003 (Risk Assessment Engine)
**Epic**: EP-001 (Underwriting)
**Priority**: P0
**Story Points**: 8
**Persona**: Underwriter

**User Story**
As an Underwriter,
I want to see a real-time risk score with contributing factors,
So that I can make informed decisions about loan approval.

**Acceptance Criteria**
- [ ] Given all required data available, When requesting risk score, Then calculation completes in under 5 seconds
- [ ] Given risk score calculated, When displaying to underwriter, Then confidence interval (e.g., 650-720) is shown
- [ ] Given contributing factors, When reviewing risk breakdown, Then top 5 factors are ranked by impact with percentage contribution
- [ ] Given risk model version, When scoring application, Then model version is logged for audit trail
- [ ] Given historical data, When model predictions compared, Then accuracy metrics are tracked and reported monthly

**Technical Notes**
- ML model: XGBoost or LightGBM hosted on ML inference service
- Model features: credit score, DTI ratio, employment history, industry risk, loan amount
- Feature store for real-time feature retrieval
- Model monitoring: track prediction distribution and feature drift
- API endpoint: POST /api/v1/applications/{id}/risk-score

**Dependencies**
- US-004 (requires validated document data)
- Credit bureau integration (external)

**Definition of Done**
- [ ] Code complete and reviewed
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Model performance tests meet accuracy thresholds
- [ ] Documentation updated
- [ ] Acceptance criteria validated

---

#### US-006: Configure Risk Policies per Lender

**Story ID**: US-006
**Feature**: F-003 (Risk Assessment Engine)
**Epic**: EP-001 (Underwriting)
**Priority**: P1
**Story Points**: 5
**Persona**: Risk Manager

**User Story**
As a Risk Manager,
I want to configure custom risk policies for my organization,
So that risk assessment aligns with our specific risk appetite and lending criteria.

**Acceptance Criteria**
- [ ] Given policy configuration UI, When setting risk thresholds, Then min/max credit score and DTI ratio can be defined per loan type
- [ ] Given policy rules defined, When saving configuration, Then validation ensures rules are logically consistent
- [ ] Given multiple lenders in system, When scoring applications, Then correct lender-specific policy is applied
- [ ] Given policy changes, When updating configuration, Then changes take effect for new applications only (not retroactive)
- [ ] Given audit requirements, When viewing policy history, Then all past policy versions are retained with timestamps

**Technical Notes**
- Policy configuration stored in lender_risk_policies table with versioning
- Policy UI: RiskPolicyConfigurationForm with rule builder interface
- Policy validation service: PolicyValidator.validateRuleConsistency()
- Feature flags to enable/disable policies per lender

**Dependencies**
- US-005 (requires risk scoring engine)

**Definition of Done**
- [ ] Code complete and reviewed
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Acceptance criteria validated

---

### Feature F-004: Human-in-the-Loop Decision Workflow

#### US-007: Route Applications Based on Risk

**Story ID**: US-007
**Feature**: F-004 (Human-in-the-Loop Decision Workflow)
**Epic**: EP-001 (Underwriting)
**Priority**: P0
**Story Points**: 5
**Persona**: Underwriter

**User Story**
As an Underwriter,
I want applications automatically routed to my queue based on risk level,
So that I focus on reviewing applications that match my expertise and authority level.

**Acceptance Criteria**
- [ ] Given risk score calculated, When routing application, Then low-risk (<600 score) goes to junior underwriters
- [ ] Given high-risk application (>750 score), When routing, Then application assigned to senior underwriters only
- [ ] Given underwriter capacity, When routing decisions, Then workload is balanced across available underwriters
- [ ] Given urgent applications (VIP customers), When prioritizing queue, Then priority applications appear at top
- [ ] Given underwriter on vacation/leave, When routing, Then applications are redistributed to active team members

**Technical Notes**
- Routing rules engine: ApplicationRoutingService with configurable rules
- Queue management: Redis-based priority queue with workload tracking
- Underwriter capacity tracked in real-time based on open assignments
- API endpoint: POST /api/v1/applications/{id}/route
- Notifications: Send email/Slack when new application assigned

**Dependencies**
- US-005 (requires risk scores for routing logic)

**Definition of Done**
- [ ] Code complete and reviewed
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Acceptance criteria validated

---

#### US-008: Override AI Recommendations with Documented Reasoning

**Story ID**: US-008
**Feature**: F-004 (Human-in-the-Loop Decision Workflow)
**Epic**: EP-001 (Underwriting)
**Priority**: P0
**Story Points**: 3
**Persona**: Underwriter

**User Story**
As an Underwriter,
I want to override AI recommendations and document my reasoning,
So that I can exercise professional judgment when AI recommendations don't align with my assessment.

**Acceptance Criteria**
- [ ] Given AI recommendation displayed, When overriding decision, Then underwriter must select override reason from predefined list
- [ ] Given override reason selected, When finalizing decision, Then free-text justification field is required (min 50 characters)
- [ ] Given override submitted, When saving decision, Then original AI recommendation and override are both logged
- [ ] Given supervisor review required, When override on high-value loan, Then approval workflow is triggered
- [ ] Given override trends, When analyzing monthly, Then underwriters with high override rates are flagged for training

**Technical Notes**
- Override reasons enum: insufficient_income, credit_history_concerns, industry_risk, incomplete_documentation, other
- Decision audit trail stored in decisions table with AI_recommendation and final_decision columns
- Approval workflow: ApprovalWorkflowService with supervisor notification
- Analytics dashboard: track override rates per underwriter

**Dependencies**
- US-007 (requires applications routed to underwriters)

**Definition of Done**
- [ ] Code complete and reviewed
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Acceptance criteria validated

---

## Epic EP-002: Operations

### Feature F-005: LOS System Integration

#### US-009: Sync Application Data from LOS

**Story ID**: US-009
**Feature**: F-005 (LOS System Integration)
**Epic**: EP-002 (Operations)
**Priority**: P0
**Story Points**: 8
**Persona**: System Administrator

**User Story**
As a System Administrator,
I want application data to automatically sync from our LOS platform,
So that underwriters have access to the latest application information without manual data entry.

**Acceptance Criteria**
- [ ] Given new application created in LOS, When sync runs, Then application appears in underwriting system within 5 minutes
- [ ] Given application updated in LOS, When change detected, Then updates are synced incrementally (not full refresh)
- [ ] Given sync failure occurs, When error is detected, Then retry logic attempts up to 3 times with exponential backoff
- [ ] Given data schema mismatch, When mapping fields, Then unmapped fields are logged as warnings (not errors)
- [ ] Given sync process running, When monitoring status, Then real-time sync dashboard shows success/failure rates

**Technical Notes**
- Integration adapters per LOS platform: EncompassAdapter, ByteAdapter, CalyxAdapter
- Webhook listeners for real-time LOS events
- Fallback: scheduled polling every 5 minutes if webhooks unavailable
- Data mapping configuration in los_field_mappings table
- Sync monitoring dashboard: /admin/los-sync-status

**Dependencies**
- None (foundational integration)

**Definition of Done**
- [ ] Code complete and reviewed
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests with LOS sandbox environments passing
- [ ] Documentation updated
- [ ] Acceptance criteria validated
- [ ] Performance test: 1000 applications sync within 10 minutes

---

### Feature F-006: Data Management and Security

#### US-010: Encrypt Sensitive Application Data

**Story ID**: US-010
**Feature**: F-006 (Data Management and Security)
**Epic**: EP-002 (Operations)
**Priority**: P0
**Story Points**: 5
**Persona**: Security Officer

**User Story**
As a Security Officer,
I want all sensitive application data encrypted at rest and in transit,
So that we comply with data protection regulations and prevent unauthorized access.

**Acceptance Criteria**
- [ ] Given sensitive fields (SSN, bank account), When storing in database, Then data is encrypted using AES-256
- [ ] Given API communication, When transmitting data, Then TLS 1.3 is enforced for all connections
- [ ] Given encryption keys, When rotating keys, Then automated key rotation occurs quarterly without service interruption
- [ ] Given data at rest, When accessing encrypted fields, Then decryption is transparent to application code
- [ ] Given compliance audit, When generating encryption report, Then all encrypted fields and key versions are documented

**Technical Notes**
- Database: PostgreSQL with pgcrypto extension for column-level encryption
- Key management: AWS KMS or HashiCorp Vault for key storage
- Encrypted fields: ssn, account_number, routing_number, tax_id
- API gateway enforces TLS 1.3 minimum
- Encryption monitoring: track decryption failures and key usage

**Dependencies**
- US-009 (requires data to be stored before encryption)

**Definition of Done**
- [ ] Code complete and reviewed
- [ ] Unit tests passing (>80% coverage)
- [ ] Security scan passing (no high/critical vulnerabilities)
- [ ] Penetration test completed
- [ ] Documentation updated
- [ ] Acceptance criteria validated

---

### Feature F-007: Operational Monitoring Dashboard

#### US-011: View Real-time Application Metrics

**Story ID**: US-011
**Feature**: F-007 (Operational Monitoring Dashboard)
**Epic**: EP-002 (Operations)
**Priority**: P1
**Story Points**: 5
**Persona**: Operations Manager

**User Story**
As an Operations Manager,
I want to view real-time metrics on application volume and processing times,
So that I can identify bottlenecks and optimize team resource allocation.

**Acceptance Criteria**
- [ ] Given dashboard accessed, When viewing metrics, Then data refreshes every 60 seconds automatically
- [ ] Given application volume metrics, When viewing trends, Then hourly/daily/weekly volume charts are displayed
- [ ] Given processing time metrics, When analyzing performance, Then average time-to-decision per application type is shown
- [ ] Given SLA thresholds configured, When metrics exceed thresholds, Then red/yellow/green status indicators update
- [ ] Given historical data, When comparing periods, Then 30/60/90 day trend lines are overlaid

**Technical Notes**
- Metrics aggregation: ClickHouse or TimescaleDB for time-series data
- Real-time updates: WebSocket connection for dashboard push updates
- Dashboard components: React with Recharts for visualization
- Metrics API: GET /api/v1/metrics/applications?period=daily
- Caching: Redis for 60-second metric cache

**Dependencies**
- US-007 (requires workflow data to track processing times)

**Definition of Done**
- [ ] Code complete and reviewed
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Acceptance criteria validated
- [ ] Performance test: dashboard loads within 2 seconds with 100K records

---

## Epic EP-003: Governance

### Feature F-008: Audit Trail and Compliance Reporting

#### US-012: Generate Compliance Report for Regulatory Audit

**Story ID**: US-012
**Feature**: F-008 (Audit Trail and Compliance Reporting)
**Epic**: EP-003 (Governance)
**Priority**: P1
**Story Points**: 5
**Persona**: Compliance Officer

**User Story**
As a Compliance Officer,
I want to generate comprehensive compliance reports on-demand,
So that I can provide auditors with complete decision history and model governance documentation.

**Acceptance Criteria**
- [ ] Given date range selected, When generating report, Then all decisions within period are included with full audit trail
- [ ] Given decision reconstructed, When viewing details, Then AI inputs, model outputs, and human overrides are all visible
- [ ] Given bias monitoring required, When running report, Then protected attribute analysis shows no discriminatory patterns
- [ ] Given report requested, When generating output, Then PDF report is ready within 1 hour for up to 10K decisions
- [ ] Given audit trail integrity, When validating logs, Then cryptographic hashes prove no tampering occurred

**Technical Notes**
- Report generator: ReportGeneratorService with PDF export using WeasyPrint
- Audit trail storage: append-only audit_trail table with hash chain verification
- Bias monitoring: monthly batch job analyzing decisions by protected attributes
- Report templates stored in compliance_report_templates table
- Background job for large reports: Celery task with email notification when complete

**Dependencies**
- US-005 (requires risk scores and model data)
- US-008 (requires decision data with overrides)

**Definition of Done**
- [ ] Code complete and reviewed
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Acceptance criteria validated
- [ ] Compliance team sign-off on report format
