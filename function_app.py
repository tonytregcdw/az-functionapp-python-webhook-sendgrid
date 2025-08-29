import azure.functions as func
import logging
import json
import os
import sendgrid
from sendgrid.helpers.mail import Mail

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="eventgridwebhooksendgrid")
def eventgridwebhooksendgrid(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        # Get the request body
        req_body = req.get_json()
        if not req_body:
            return func.HttpResponse("Invalid request body", status_code=400)
        
        # EventGrid always sends arrays, but handle single events too
        events = req_body if isinstance(req_body, list) else [req_body]
        
        # Process each event
        for event in events:
            # Check if this is an EventGrid subscription validation event
            if event.get('eventType') == 'Microsoft.EventGrid.SubscriptionValidationEvent':
                # Handle webhook validation
                validation_code = event.get('data', {}).get('validationCode')
                if validation_code:
                    validation_response = {
                        "validationResponse": validation_code
                    }
                    logging.info(f'EventGrid webhook validation successful: {validation_code}')
                    return func.HttpResponse(
                        json.dumps(validation_response),
                        status_code=200,
                        headers={'Content-Type': 'application/json'}
                    )
                else:
                    return func.HttpResponse("Missing validation code", status_code=400)
            else:
                # Send email for non-validation events
                email_result = send_email_via_sendgrid(event)
                if email_result.status_code != 200:
                    return email_result
        
        return func.HttpResponse("Processed event(s) successfully", status_code=200)
        
    except ValueError as e:
        logging.error(f'Error parsing JSON: {str(e)}')
        return func.HttpResponse("Invalid JSON in request body", status_code=400)
    except Exception as e:
        logging.error(f'Unexpected error: {str(e)}')
        return func.HttpResponse(f"Internal server error: {str(e)}", status_code=500)


def send_email_via_sendgrid(event_data):
    """Send email via SendGrid using event data"""
    try:
        # Get environment variables
        api_key = os.environ.get('SENDGRID_API_KEY')
        from_address = os.environ.get('FROM_ADDRESS')
        to_address = os.environ.get('TO_ADDRESS')
        
        if not all([api_key, from_address, to_address]):
            missing_vars = []
            if not api_key:
                missing_vars.append('SENDGRID_API_KEY')
            if not from_address:
                missing_vars.append('FROM_ADDRESS')
            if not to_address:
                missing_vars.append('TO_ADDRESS')
            
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logging.error(error_msg)
            return func.HttpResponse(error_msg, status_code=500)
        
        # Extract subject from event data
        subject = event_data.get('subject', 'EventGrid Notification')
        
        # Use the entire request body as email content
        email_content = json.dumps(event_data, indent=2)
        
        # Create SendGrid message
        message = Mail(
            from_email=from_address,
            to_emails=to_address,
            subject=subject,
            plain_text_content=email_content
        )
        
        # Send email
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        response = sg.send(message)
        
        logging.info(f'Email sent successfully. Status code: {response.status_code}')
        return func.HttpResponse(
            f"Email sent successfully. Status: {response.status_code}",
            status_code=200
        )
        
    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        logging.error(error_msg)
        return func.HttpResponse(error_msg, status_code=500)


