import logging
import json
import os
from azure.functions import HttpRequest, HttpResponse, SendGridMessage
import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.function_name(name="EventGridWebhook")
@app.route(route="eventgridwebhook", methods=["POST"])
@app.sendgrid_output(arg_name="message", api_key=os.environ.get('SENDGRIDAPIKEY'),
                     from_email="trogadog@gmail.com", to_emails=["trogadog@gmail.com"])
def main(req: HttpRequest) -> func.Out[SendGridMessage]:
    try:
        events = req.get_json()
    except Exception:
        logging.exception("Invalid JSON")
        return HttpResponse("Invalid JSON", status_code=400)

    for event in events:
        # Event Grid subscription validation
        if event.get('eventType') == "Microsoft.EventGrid.SubscriptionValidationEvent":
            code = event.get("data", {}).get("validationCode")
            logging.info(f"processing event code: {code}")
            return HttpResponse(
                body=json.dumps({'validationResponse': code}),
                mimetype="application/json",
                status_code=200
            )

        # Event with subject, send email
        if event.get("subject"):
            message = SendGridMessage(
                subject=f"alert triggered - {event['subject']}",
                content=[{
                    "type": "text/plain",
                    "value": json.dumps(events, indent=2)
                }]
            )
            # Return both HTTP response and email
            return func.Out(message), HttpResponse(
                body=json.dumps({'subject': event["subject"]}),
                mimetype="application/json",
                status_code=200
            )

    # Default (no events matched)
    return HttpResponse("No actionable event", status_code=200)
