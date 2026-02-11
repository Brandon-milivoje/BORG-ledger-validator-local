import streamlit as st
import json
import re
from datetime import datetime

st.set_page_config(page_title="Borg Ledger Validator", layout="wide")
st.title("📑 Bloomberg Ledger Log Validator")
st.caption("Paste your raw log string below to verify environment and data integrity.")

raw_input = st.text_area("Paste Log Entry Here:", height=200)

if raw_input:
    try:
        json_match = re.search(r'(\{.*\})', raw_input)
        if json_match:
            full_data = json.loads(json_match.group(1))
            data_sec = full_data.get('data', {})
            objects = data_sec.get('objects', [])
            job_props = data_sec.get('jobProperties', {})
            job_meta = data_sec.get('jobMetadata', {})

            for i, obj in enumerate(objects):
                obj_meta = obj.get('objectMetadata', {})
                content_meta = obj.get('objectContent', [{}])[0].get('contentMetadata', {})
                
                # Env Logic
                is_borg = obj_meta.get('isBorgTest')
                send_borg = obj_meta.get('sendToBorg')
                
                # --- UI DISPLAY ---
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader(f"Critical Confirmations (Object {i+1})")
                    # Displaying as a clean table in the browser
                    check_data = [
                        {"Field": "isBorgTest", "Value": is_borg, "Status": "✅"},
                        {"Field": "sendToBorg", "Value": send_borg, "Status": "✅" if send_borg == "YES" else "⚠️"},
                        {"Field": "wireId", "Value": obj_meta.get("wireId"), "Status": "✅" if obj_meta.get("wireId")=="778" else "ℹ️"},
                        {"Field": "tickerValue", "Value": obj_meta.get("tickerValue"), "Status": "👀"},
                        {"Field": "scalingFactor", "Value": obj_meta.get("scalingFactor"), "Status": "👀"},
                        {"Field": "releaseDate", "Value": obj_meta.get("releaseDate"), "Status": "✅" if obj_meta.get("releaseDate")=="NO RELEASE DATE" else "⚠️"}
                    ]
                    st.table(check_data)

                with col2:
                    st.subheader("Job Descriptives")
                    st.info(f"**Environment:** {'DEV/TEST' if is_borg == 'YES' else 'PRODUCTION'}")
                    st.write(f"**Job Name:** {job_props.get('jobName')}")
                    st.write(f"**Source URL:** {content_meta.get('sourceUrl')}")
                    st.write(f"**Wire/Class:** {obj_meta.get('wireId')} / {obj_meta.get('class')}")

                # Alert Logic
                if is_borg == "YES" and send_borg == "NO":
                    st.error("🚨 ALERT: isBorgTest is YES but sendToBorg is NO!")
        else:
            st.error("Could not find JSON in the input.")
    except Exception as e:
        st.error(f"Parsing error: {e}")
