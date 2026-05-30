# LumenAI CAPA Workflow Demo Script

## Demo Title
LumenAI CAPA Workflow: From Audit Signal to Corrective and Preventive Action

## Demo Objective
Demonstrate how LumenAI converts high-value audit signals into structured CAPA records with owner, risk level, due date, corrective action, preventive action, and governance visibility.

## Opening Statement
This module demonstrates LumenAI's Corrective and Preventive Action workflow. It shows how audit signals and quality events can be converted into accountable CAPA records for operational follow-up and leadership oversight.

## Demo Flow

### 1. Start at the Main LumenAI App
Open:

https://lumen-ai-1.onrender.com

Show the main dashboard and point out the CAPA Workflow panel.

### 2. Review CAPA Health Status
Show the CAPA Workflow panel displaying:
- Health: HEALTHY
- Total CAPAs
- Open CAPAs
- High-Risk CAPAs
- Closed CAPAs

Explain:
The CAPA panel is connected to a production backend endpoint and gives leaders visibility into CAPA status and risk.

### 3. Create a CAPA from an Audit Signal
Click:

Create CAPA from Audit Signal

Explain:
This simulates a high-value audit signal being converted into a formal CAPA record.

### 4. Review the Created CAPA
Show the latest CAPA record, including:
- Title
- Risk Level
- Owner
- Due Date
- Source
- Status
- Corrective Action
- Preventive Action

Explain:
The workflow provides a structured way to capture immediate containment, corrective action, preventive action, and governance ownership.

### 5. Validate Backend Endpoint
Open or reference:

https://lumen-ai-53u4.onrender.com/api/capa/health

Expected:
- status: healthy
- module: capa_workflow
- version: 1.0.0

### 6. Validate CAPA List Endpoint
Open or reference:

https://lumen-ai-53u4.onrender.com/api/capa?limit=10

Expected:
- status: success
- module: capa_workflow
- total_returned >= 1
- summary.open >= 1
- summary.high_risk >= 1

## Closing Statement
The CAPA Workflow demonstrates that LumenAI can move beyond detection and reporting into accountable quality governance. It connects audit signals to corrective and preventive action, creating a clear pathway from quality evidence to operational improvement.

## Final Demo Message
LumenAI is building an enterprise quality intelligence platform that connects inspection evidence, audit signals, CAPA workflows, governance visibility, and executive reporting.
