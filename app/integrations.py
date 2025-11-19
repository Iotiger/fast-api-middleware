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
    extract_flight_numbers,
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
    
    # Print detailed request information
    _log_webhook_request(request, webhook_data)
    
    # Process booking data if it contains booking information
    if "booking" in webhook_data:
        try:
            print("Processing booking data...")
            
            booking_data = webhook_data["booking"]
            
            # Check if this is a round trip booking
            if is_round_trip(booking_data):
                return await _process_round_trip_booking(booking_data)
            else:
                return await _process_single_trip_booking(booking_data)
                
        except Exception as e:
            print(f"Error processing booking: {str(e)}")
            return {
                "message": "Booking received but processing failed", 
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    else:
        print("No booking data found in webhook")
        return {"message": "Webhook received but no booking data found", "timestamp": datetime.now().isoformat()}


async def _process_round_trip_booking(booking_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a round trip booking (requires 2 webhook requests)
    """
    order_id = get_order_display_id(booking_data)
    print(f"ROUND TRIP: Processing booking for order {order_id}")
    
    # Clean up old bookings first
    cleanup_old_bookings()
    
    # Check if we already have a booking for this order
    if has_round_trip_booking(order_id):
        print(f"ROUND TRIP: Found existing booking for order {order_id}, combining flights")
        
        # Get the existing booking data
        existing_booking_info = get_round_trip_booking(order_id)
        if not existing_booking_info:
            # This shouldn't happen, but handle it gracefully
            print(f"ERROR: Booking for order {order_id} not found in storage")
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
        print("ROUND TRIP: Data transformation completed")
        print(f"ROUND TRIP: Transformed data: {json.dumps(transformed_data, indent=2)}")
        
        # Send to MakerSuite API
        print("ROUND TRIP: Sending to MakerSuite API...")
        api_result = await send_to_makersuite_api(transformed_data)
        
        # Clean up the stored booking
        remove_round_trip_booking(order_id)
        
        if api_result["success"]:
            print("ROUND TRIP: Successfully sent to MakerSuite API")
            return {
                "message": "Round trip booking processed and sent to MakerSuite successfully!", 
                "timestamp": datetime.now().isoformat(),
                "makersuite_response": api_result["response"]
            }
        else:
            print(f"ROUND TRIP: Failed to send to MakerSuite API: {api_result['error']}")
            return {
                "message": "Round trip booking received but failed to send to MakerSuite", 
                "timestamp": datetime.now().isoformat(),
                "error": api_result["error"]
            }
    else:
        print(f"ROUND TRIP: First booking for order {order_id}, storing for later")
        
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
    print("SINGLE TRIP: Processing single trip booking")
    
    # Get flight identifiers from API
    depart_flights = await get_flight_identifiers_from_api(booking_data)
    
    # Transform the booking data
    transformed_data = transform_booking_data(booking_data, depart_flights=depart_flights)
    print("SINGLE TRIP: Data transformation completed")
    print(f"SINGLE TRIP: Transformed data: {json.dumps(transformed_data, indent=2)}")
    
    # Send to MakerSuite API
    print("SINGLE TRIP: Sending to MakerSuite API...")
    api_result = await send_to_makersuite_api(transformed_data)
    
    if api_result["success"]:
        print("SINGLE TRIP: Successfully sent to MakerSuite API")
        return {
            "message": "Single trip booking processed and sent to MakerSuite successfully!", 
            "timestamp": datetime.now().isoformat(),
            "makersuite_response": api_result["response"]
        }
    else:
        print(f"SINGLE TRIP: Failed to send to MakerSuite API: {api_result['error']}")
        return {
            "message": "Single trip booking received but failed to send to MakerSuite", 
            "timestamp": datetime.now().isoformat(),
            "error": api_result["error"]
        }


def _log_webhook_request(request: Request, webhook_data: Dict[str, Any]):
    """
    Log webhook request details
    """
    print("\n" + "="*80)
    print(f"WEBHOOK REQUEST RECEIVED")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Client IP: {request.client.host if request.client else 'unknown'}")
    print(f"URL: {request.url}")
    print(f"Headers:")
    for key, value in request.headers.items():
        print(f"   {key}: {value}")
    print(f"Request Body:")
    print(json.dumps(webhook_data, indent=2))
    print("="*80)
    print()
