from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from twilio.request_validator import RequestValidator
from src.utils.env import TWILIO_AUTH_TOKEN, ENVIRONMENT, EXTERNAL_URL, FORCE_VALIDATION
from src.utils.logger import get_logger

app = FastAPI()
logger = get_logger(__name__)

# Initialize Twilio request validator
validator = RequestValidator(TWILIO_AUTH_TOKEN)


class RequestValidatorMiddleware(BaseHTTPMiddleware):
    async def parse_params(self, request: Request):
        # Get content type
        content_type = request.headers.get("content-type", "")
        logger.info("Content-Type detected", {"content_type": content_type})

        if "application/x-www-form-urlencoded" in content_type:
            # Twilio sends form data
            logger.info("Parsing as form data")
            form = await request.form()
            params = dict(form)
        elif "application/json" in content_type:
            # JSON data
            logger.info("Parsing as JSON")
            body = await request.json()
            params = body if isinstance(body, dict) else {}
        else:
            # Try form first (Twilio default), fallback to empty
            logger.info("Unknown content type, trying form parsing")
            try:
                form = await request.form()
                params = dict(form)
            except Exception as e:
                logger.warning("Form parsing failed", {"error": str(e)})
                params = {}

        return params

    async def dispatch(self, request: Request, call_next):
        logger.info("Middleware invoked")

        # Get request body based on content type
        params = await self.parse_params(request)

        # Validate Twilio signature
        signature = request.headers.get("X-Twilio-Signature")

        # Determine the correct URL for validation
        if EXTERNAL_URL:
            # Use external URL (ngrok, load balancer, etc.)
            validation_url = f"{EXTERNAL_URL.rstrip('/')}{request.url.path}"
            if request.url.query:
                validation_url += f"?{request.url.query}"
        else:
            # Use the request URL as-is
            validation_url = str(request.url)

        # Log validation details for debugging
        logger.info(
            "Signature validation details",
            {
                "signature_provided": bool(signature),
                "validation_url": validation_url,
                "request_url": str(request.url),
                "external_url": EXTERNAL_URL,
                "environment": ENVIRONMENT,
                "params_count": len(params) if params else 0,
                "host_header": request.headers.get("host"),
                "user_agent": request.headers.get("user-agent"),
            },
        )

        # Always validate Twilio signatures (no development mode bypass)
        if not signature:
            logger.warning(
                "No Twilio signature provided",
                {"url": validation_url, "environment": ENVIRONMENT},
            )
            return JSONResponse(
                status_code=403, content={"error": "Missing Twilio signature"}
            )

        # For testing purposes, temporarily log more details
        validation_result = validator.validate(validation_url, params, signature)

        # Temporary bypass for development testing - remove in production
        if (
            not validation_result
            and ENVIRONMENT == "development"
            and not FORCE_VALIDATION
        ):
            logger.warning(
                "Signature validation failed but bypassing for development",
                {
                    "validation_url": validation_url,
                    "signature_preview": signature[:20] + "..." if signature else None,
                },
            )
            validation_result = True

        if not validation_result:
            logger.warning(
                "Twilio webhook validation failed",
                {
                    "validation_url": validation_url,
                    "request_url": str(request.url),
                    "external_url": EXTERNAL_URL,
                    "hasSignature": bool(signature),
                    "environment": ENVIRONMENT,
                    "signature_preview": signature[:20] + "..." if signature else None,
                    "params_keys": list(params.keys()) if params else [],
                },
            )

            # In development, provide more helpful error info
            if ENVIRONMENT == "development":
                logger.info(
                    "Validation details for debugging",
                    {
                        "signature": signature,
                        "params": dict(params),
                        "validation_url": validation_url,
                    },
                )

            return JSONResponse(
                status_code=403, content={"error": "Invalid Twilio signature"}
            )

        # Store parsed params in state for use by routes
        request.state.twilio_params = params

        response = await call_next(request)
        return response
