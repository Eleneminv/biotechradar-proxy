from flask import Flask, request, Response
from flask_cors import CORS
import requests
import json
from datetime import datetime, timedelta
from os import environ

app = Flask(__name__)
CORS(app)

CLINICAL_TRIALS_API = "https://clinicaltrials.gov/api/query/study_fields"

# ------------------------------
# Fetch trials from ClinicalTrials.gov
# ------------------------------
def fetch_trials(phase_filter=["Phase 2", "Phase 3"], days_ahead=180, max_records=50):
    today = datetime.today().date()
    end_date = today + timedelta(days=days_ahead)

    expr = f"AREA[Phase]({' OR '.join(phase_filter)}) AND NOT OVERALL_STATUS:Recruiting"

    params = {
        "expr": expr,
        "fields": "NCTId,Condition,Phase,BriefTitle,LeadSponsorName,PrimaryCompletionDate,OverallStatus",
        "min_rnk": 1,
        "max_rnk": max_records,
        "fmt": "json"
    }

    try:
        r = requests.get(CLINICAL_TRIALS_API, params=params, timeout=15)
        r.raise_for_status()
    except requests.RequestException as e:
        return {"error": str(e)}

    data = r.json()
    trials_list = []
    for study in data.get("StudyFieldsResponse", {}).get("StudyFields", []):
        trials_list.append({
            "NCTId": study["NCTId"][0] if study["NCTId"] else None,
            "Condition": ", ".join(study["Condition"]) if study["Condition"] else None,
            "Phase": ", ".join(study["Phase"]) if study["Phase"] else None,
            "Title": study["BriefTitle"][0] if study["BriefTitle"] else None,
            "Sponsor": study["LeadSponsorName"][0] if study["LeadSponsorName"] else None,
            "PrimaryCompletionDate": study["PrimaryCompletionDate"][0] if study["PrimaryCompletionDate"] else None,
            "Status": study["OverallStatus"][0] if study["OverallStatus"] else None
        })

    return trials_list


# ------------------------------
# API route: /trials
# ------------------------------
@app.route('/trials', methods=['GET'])
def get_trials():
    phase_param = request.args.get("phase", "Phase 2,Phase 3")
    days_ahead = int(request.args.get("days_ahead", 180))
    max_results = int(request.args.get("max_results", 50))

    phase_filter = []
    for p in phase_param.split(","):
        p = p.strip()
        if not p.lower().startswith("phase"):
            p = f"Phase {p}"
        phase_filter.append(p)

    try:
        records = fetch_trials(
            phase_filter=phase_filter,
            days_ahead=days_ahead,
            max_records=max_results
        )
        return Response(
            json.dumps({
                "status": "success",
                "requested_phase": phase_filter,
                "days_ahead": days_ahead,
                "max_results": max_results,
                "data": records
            }, indent=2),
            mimetype="application/json"
        )
    except Exception as e:
        return Response(json.dumps({"status": "error", "message": str(e)}), mimetype="application/json", status=500)


# ------------------------------
# OpenAPI Specification for ChatGPT Actions
# ------------------------------
@app.route("/openapi.json", methods=["GET"])
def openapi_spec():
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Biotech Clinical Trials API",
            "version": "1.0.0",
            "description": "Fetch ClinicalTrials.gov data filtered by phase, date, and number of results."
        },
        "servers": [
            {
                "url": "https://biotechradar-proxy.onrender.com"
            }
        ],
        "paths": {
            "/trials": {
                "get": {
                    "summary": "Get clinical trials",
                    "parameters": [
                        {
                            "name": "phase",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": "Clinical trial phase (e.g., Phase 2, Phase 3)"
                        },
                        {
                            "name": "days_ahead",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer"},
                            "description": "Days ahead from today to include in the search"
                        },
                        {
                            "name": "max_results",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer"},
                            "description": "Max number of results to return"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "A list of clinical trials",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    return Response(json.dumps(spec, indent=2, sort_keys=False), mimetype="application/json")


# ------------------------------
# Entry point
# ------------------------------
if __name__ == "__main__":
    port = int(environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
