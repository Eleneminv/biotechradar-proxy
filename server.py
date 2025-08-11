from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
from os import environ

app = Flask(__name__)
CORS(app)

CLINICAL_TRIALS_API = "https://clinicaltrials.gov/api/query/study_fields"

def fetch_trials(phase_filter=["Phase 2", "Phase 3"], days_ahead=180, max_records=50):
    today = datetime.today().date()
    end_date = today + timedelta(days=days_ahead)

    expr = f"AREA[Phase]({' OR '.join(phase_filter)}) AND NOT Recruiting[OVERALL_STATUS]"
    params = {
        "expr": expr,
        "fields": "NCTId,Condition,Phase,BriefTitle,LeadSponsorName,PrimaryCompletionDate,OverallStatus",
        "min_rnk": 1,
        "max_rnk": max_records,
        "fmt": "json"
    }

    r = requests.get(CLINICAL_TRIALS_API, params=params)
    if r.status_code != 200:
        return []

    data = r.json()
    trials_list = []
    for study in data.get("StudyFieldsResponse", {}).get("StudyFields", []):
        try:
            trials_list.append({
                "NCTId": study["NCTId"][0] if study["NCTId"] else None,
                "Condition": ", ".join(study["Condition"]) if study["Condition"] else None,
                "Phase": ", ".join(study["Phase"]) if study["Phase"] else None,
                "Title": study["BriefTitle"][0] if study["BriefTitle"] else None,
                "Sponsor": study["LeadSponsorName"][0] if study["LeadSponsorName"] else None,
                "PrimaryCompletionDate": study["PrimaryCompletionDate"][0] if study["PrimaryCompletionDate"] else None,
                "Status": study["OverallStatus"][0] if study["OverallStatus"] else None
            })
        except Exception:
            continue

    return trials_list

@app.route("/trials", methods=["GET"])
def get_trials():
    phase = request.args.get("phase", "Phase 3")
    days_ahead = int(request.args.get("days_ahead", 180))
    max_results = int(request.args.get("max_results", 50))

    trials = fetch_trials([phase], days_ahead, max_results)
    return jsonify(trials)

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
