"""
Main webhook handler for FareHarbor bookings
"""

from fastapi import APIRouter, Request
import json
from datetime import datetime
from typing import Dict, Any

from app.helpers import (
    is_round_trip,
    get_order_display_id,
    get_flight_identifiers_from_api,
    determine_flight_directions
)
from app.storage import (
    cleanup_old_bookings,
    store_round_trip_booking,
    get_round_trip_booking,
    remove_round_trip_booking,
    has_round_trip_booking
)
from app.transform import transform_booking_data
from app.api_client import send_to_makersuite_api
from app.logger import (
    log_info, log_error, log_warning, log_webhook_request,
    save_webhook_request_body
)

router = APIRouter()


@router.post("/bookings")
async def receive_booking_webhook(request: Request):
    """
    Receive booking webhook data from FareHarbor and forward to MakerSuite API
    """
    # Get the raw request body
    body = await request.body()
    
    # Parse JSON
    try:
        webhook_data = json.loads(body)
    except json.JSONDecodeError:
        webhook_data = {"raw_body": body.decode('utf-8')}
    
    # Save webhook request body to JSON file
    save_webhook_request_body(
        webhook_data=webhook_data,
        client_ip=request.client.host if request.client else None,
        url=request.url
    )
    
    # Log webhook request
    _log_webhook_request(request, webhook_data)
    
    # Process booking data if it contains booking information
    if "booking" in webhook_data:
        try:
            log_info("Processing booking data")
            
            booking_data = webhook_data["booking"]
            
            # Check if this is a round trip booking
            if is_round_trip(booking_data):
                return await _process_round_trip_booking(booking_data)
            else:
                return await _process_single_trip_booking(booking_data)
                
        except Exception as e:
            log_error("Error processing booking", str(e), {"webhook_data": webhook_data})
            return {
                "message": "Booking received but processing failed", 
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    else:
        log_warning("No booking data found in webhook", {"webhook_data": webhook_data})
        return {"message": "Webhook received but no booking data found", "timestamp": datetime.now().isoformat()}


async def _process_round_trip_booking(booking_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a round trip booking (requires 2 webhook requests)
    """
    order_id = get_order_display_id(booking_data)
    log_info(f"Processing round trip booking for order {order_id}", {"order_id": order_id})
    
    # Clean up old bookings first
    cleanup_old_bookings()
    
    # Check if we already have a booking for this order
    if has_round_trip_booking(order_id):
        log_info(f"Found existing booking for order {order_id}, combining flights", {"order_id": order_id})
        
        # Get the existing booking data
        existing_booking_info = get_round_trip_booking(order_id)
        if not existing_booking_info:
            log_error(f"Booking for order {order_id} not found in storage", None, {"order_id": order_id})
            return {
                "message": f"Error: Booking for order {order_id} not found",
                "timestamp": datetime.now().isoformat(),
                "error": "Booking storage error"
            }
        
        existing_booking = existing_booking_info["booking_data"]
        
        # Get flight identifiers from API for both bookings to ensure consistency
        existing_flights = await get_flight_identifiers_from_api(existing_booking)
        current_flights = await get_flight_identifiers_from_api(booking_data)
        
        # Determine which is depart and which is return
        depart_flights, return_flights = determine_flight_directions(
            existing_flights, current_flights, existing_booking, booking_data
        )
        
        # Use the first booking's passenger data (they should be the same)
        combined_booking_data = existing_booking
        
        # Transform the combined booking data
        transformed_data = transform_booking_data(combined_booking_data, depart_flights, return_flights)
        log_info("Round trip data transformation completed", {
            "order_id": order_id,
            "depart_flights": depart_flights,
            "return_flights": return_flights,
            "transformed_data": transformed_data
        })
        
        # Send to MakerSuite API
        log_info("Sending round trip booking to MakerSuite API", {"order_id": order_id})
        api_result = await send_to_makersuite_api(transformed_data)
        
        # Clean up the stored booking
        remove_round_trip_booking(order_id)
        
        if api_result["success"]:
            log_info("Round trip booking successfully sent to MakerSuite API", {
                "order_id": order_id,
                "response": api_result.get("response")
            })
            return {
                "message": "Round trip booking processed and sent to MakerSuite successfully!", 
                "timestamp": datetime.now().isoformat(),
                "makersuite_response": api_result["response"]
            }
        else:
            log_error("Failed to send round trip booking to MakerSuite API", api_result.get("error"), {
                "order_id": order_id
            })
            return {
                "message": "Round trip booking received but failed to send to MakerSuite", 
                "timestamp": datetime.now().isoformat(),
                "error": api_result["error"]
            }
    else:
        log_info(f"First booking for order {order_id}, storing for later", {"order_id": order_id})
        
        # Get flight identifiers from API for this booking
        flights = await get_flight_identifiers_from_api(booking_data)
        store_round_trip_booking(order_id, booking_data, flights)
        
        return {
            "message": f"Round trip booking received and stored for order {order_id}. Waiting for second booking.", 
            "timestamp": datetime.now().isoformat()
        }


async def _process_single_trip_booking(booking_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single trip booking (sent immediately)
    """
    log_info("Processing single trip booking")
    
    # Get flight identifiers from API
    depart_flights = await get_flight_identifiers_from_api(booking_data)
    
    # Transform the booking data
    transformed_data = transform_booking_data(booking_data, depart_flights=depart_flights)
    log_info("Single trip data transformation completed", {
        "depart_flights": depart_flights,
        "transformed_data": transformed_data
    })
    
    # Send to MakerSuite API
    log_info("Sending single trip booking to MakerSuite API")
    api_result = await send_to_makersuite_api(transformed_data)
    
    if api_result["success"]:
        log_info("Single trip booking successfully sent to MakerSuite API", {
            "response": api_result.get("response")
        })
        return {
            "message": "Single trip booking processed and sent to MakerSuite successfully!", 
            "timestamp": datetime.now().isoformat(),
            "makersuite_response": api_result["response"]
        }
    else:
        log_error("Failed to send single trip booking to MakerSuite API", api_result.get("error"))
        return {
            "message": "Single trip booking received but failed to send to MakerSuite", 
            "timestamp": datetime.now().isoformat(),
            "error": api_result["error"]
        }


def _log_webhook_request(request: Request, webhook_data: Dict[str, Any]):
    """
    Log webhook request details
    """
    # Also print for console (keep existing behavior)
    print("\n" + "="*80)
    print("WEBHOOK REQUEST RECEIVED")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Client IP: {request.client.host if request.client else 'unknown'}")
    print(f"URL: {request.url}")
    print("Headers:")
    for key, value in request.headers.items():
        print(f"   {key}: {value}")
    print("Request Body:")
    print(json.dumps(webhook_data, indent=2))
    print("="*80)
    print()
    
    # Log to JSON file
    log_webhook_request(
        request_data=webhook_data,
        client_ip=request.client.host if request.client else None,
        url=request.url
    )
