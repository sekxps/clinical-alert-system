import logging
from datetime import datetime
import requests
from config import MORPROMT_CLIENT_KEY, MORPROMT_SECRET_KEY

logger = logging.getLogger(__name__)

MORPROMT_API_URL = "https://morpromt2f.moph.go.th/api/notify/send"

def _build_patient_body(alert_data: dict) -> list:
    metadata = alert_data.get('metadata', {})
    
    visit_id = str(alert_data.get('visit_id', ''))
    patient_id = str(metadata.get('hn', '-'))
    patient_name = str(metadata.get('patient_name', '-'))
    dept_name = str(metadata.get('department_name', 'ไม่ระบุ'))
    vsttime = str(metadata.get('vsttime', '-'))
    vstdate = alert_data.get('timestamp', datetime.now()).strftime('%Y-%m-%d')
    full_date = f"{vstdate} {vsttime}"

    return [
        {
            "type": "text",
            "text": patient_name,
            "weight": "bold",
            "size": "xl",
            "color": "#000000",
            "wrap": True,
            "margin": "md"
        },
        {
            "type": "text",
            "text": f"HN: {patient_id}   |   VN: {visit_id}",
            "size": "sm",
            "color": "#8c8c8c",
            "margin": "sm"
        },
        {"type": "separator", "margin": "lg"},
        {
            "type": "box", "layout": "horizontal", "margin": "md",
            "contents": [
                {"type": "text", "text": "📍 แผนก", "size": "sm", "color": "#8c8c8c", "flex": 1},
                {"type": "text", "text": dept_name, "size": "sm", "color": "#000000", "flex": 3, "wrap": True},
            ],
        },
        {
            "type": "box", "layout": "horizontal", "margin": "sm",
            "contents": [
                {"type": "text", "text": "⏰ เวลา", "size": "sm", "color": "#8c8c8c", "flex": 1},
                {"type": "text", "text": full_date, "size": "sm", "color": "#000000", "flex": 3},
            ],
        },
    ]

def _build_risk_details_section(detail_str: str) -> list:
    section = [
        {"type": "separator", "margin": "lg"},
        {
            "type": "text", "text": "⚠️ ข้อบ่งชี้ / อาการทางคลินิก",
            "weight": "bold", "size": "sm", "margin": "md", "color": "#d4380d",
        },
    ]
    risk_details = [d.strip() for d in detail_str.split('|') if d.strip()]
    for detail in risk_details:
        section.append({
            "type": "text", "text": f"• {detail}",
            "size": "sm", "color": "#595959", "wrap": True, "margin": "sm",
        })
    return section

def _send_via_morpromt(flex_message: dict, visit_number: str, label: str) -> None:
    if not MORPROMT_CLIENT_KEY or not MORPROMT_SECRET_KEY:
        logger.warning(f"Morpromt keys missing. Skipped sending {label} for Visit {visit_number}")
        return

    headers = {
        "client-key": MORPROMT_CLIENT_KEY,
        "secret-key": MORPROMT_SECRET_KEY,
        "Content-Type": "application/json",
    }
    payload = {"messages": [flex_message]}

    try:
        response = requests.post(MORPROMT_API_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully sent {label} for Visit Number {visit_number}")
    except Exception as e:
        logger.error(f"Failed to send {label} for Visit {visit_number}: {e}")

def print_alert(alert_data):
    """Print formatted alert to console."""
    ts = alert_data.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
    ct = alert_data.get('change_type', '')

    if ct == 'HIGH_TO_NOT':
        header_text = "✅ [CANCEL ALERT] Target conditions resolved"
    elif ct == 'NOT_TO_HIGH':
        header_text = "🚨 [NEW ALERT] Risk detected"
    else:
        header_text = "🚨 CLINICAL ALERT"

    metadata = alert_data.get('metadata', {})
    patient_info = ""
    if metadata:
        patient_info = f" | HN: {metadata.get('hn', '-')} | Name: {metadata.get('patient_name', '-')} | Time: {metadata.get('vsttime', '-')}"

    print("\n" + "="*60)
    print(f"{header_text} | {ts}")
    print(f"   Visit ID:  {alert_data.get('visit_id')} {patient_info}")
    print(f"   Criteria:  {alert_data.get('criteria_name')}")
    print(f"   Category:  {alert_data.get('category')}")
    print(f"   Severity:  {alert_data.get('severity').upper()}")
    print("-" * 60)
    print(f"   Detail:    {alert_data.get('detail')}")
    print("="*60 + "\n")

def send_line(alert_data: dict) -> None:
    """Send LINE Flex Message via Morpromt."""
    change_type = alert_data.get('change_type', '')
    metadata = alert_data.get('metadata', {})
    visit_id = str(alert_data.get('visit_id', ''))
    patient_name = str(metadata.get('patient_name', '-'))
    criteria_name = alert_data.get('criteria_name', 'Clinical Alert')

    if change_type == "NOT_TO_HIGH":
        header_text = criteria_name
        sub_text = "🚨 พบผู้ป่วยเข้าเกณฑ์ / ความเสี่ยงใหม่"
        header_color = "#cf1322"  # Deep Red
        alt_text = f"🚨 {criteria_name}: {patient_name}"
    elif change_type == "HIGH_TO_NOT":
        header_text = criteria_name
        sub_text = "🟢 ผู้ป่วยไม่อยู่ในกลุ่มเสี่ยงแล้ว (ข้อมูลถูกแก้ไข)"
        header_color = "#389e0d"  # Forest Green
        alt_text = f"🟢 พ้นกลุ่มเสี่ยง: {patient_name}"
    else:
        return

    body_contents = _build_patient_body(alert_data)

    detail_str = alert_data.get('detail')
    if detail_str and change_type != "HIGH_TO_NOT":
        body_contents.extend(_build_risk_details_section(detail_str))

    flex_message = {
        "type": "flex",
        "altText": alt_text,
        "contents": {
            "type": "bubble",
            "header": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "text", "text": header_text, "weight": "bold", "size": "lg", "color": "#ffffff", "wrap": True},
                    {"type": "text", "text": sub_text, "color": "#ffffff", "size": "sm", "wrap": True},
                ],
                "backgroundColor": header_color,
            },
            "body": {
                "type": "box", "layout": "vertical",
                "contents": body_contents,
            },
        },
    }

    _send_via_morpromt(flex_message, visit_id, f"LINE alert ({change_type})")

def fire_alert(alert_data):
    """Main entry point for firing an alert across all channels."""
    print_alert(alert_data)
    send_line(alert_data)
