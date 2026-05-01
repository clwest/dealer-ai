# dealer_ai/views.py

import uuid
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import ChatSession, ChatMessage, CustomerLead
from .services.chat_engine import build_chat_response


@api_view(["POST"])
def start_chat(request):
    session = ChatSession.objects.create(
        session_key=str(uuid.uuid4())
    )

    return Response({
        "session_id": session.id,
        "session_key": session.session_key,
        "message": "Chat started."
    })


@api_view(["POST"])
def send_chat_message(request):
    session_id = request.data.get("session_id")
    message = request.data.get("message")

    if not session_id or not message:
        return Response(
            {"error": "session_id and message are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    session = ChatSession.objects.get(id=session_id)

    ChatMessage.objects.create(
        session=session,
        role="user",
        content=message,
    )

    result = build_chat_response(session, message)

    ChatMessage.objects.create(
        session=session,
        role="assistant",
        content=result["reply"],
        metadata={"vehicles": result["vehicles"]},
    )

    return Response(result)


@api_view(["POST"])
def create_lead(request):
    lead = CustomerLead.objects.create(
        session_id=request.data.get("session_id"),
        name=request.data.get("name", ""),
        phone=request.data.get("phone", ""),
        email=request.data.get("email", ""),
        vehicle_interest=request.data.get("vehicle_interest", ""),
        target_monthly_payment=request.data.get("target_monthly_payment") or None,
        down_payment=request.data.get("down_payment") or None,
        trade_in=request.data.get("trade_in", False),
        credit_range=request.data.get("credit_range", ""),
        urgency=request.data.get("urgency", ""),
        conversation_summary=request.data.get("conversation_summary", ""),
    )

    return Response({
        "lead_id": lead.id,
        "message": "Lead created."
    })