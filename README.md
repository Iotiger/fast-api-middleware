# FareHarbor to MakerSuite Booking Integration

A FastAPI project that receives booking webhook data from FareHarbor, transforms it, and forwards it to the MakerSuite API for flight bookings.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python main.py
```

The API will be available at:
- Local HTTP: `http://localhost:8000`
- Local HTTPS: `https://localhost:8000`
- External HTTP: `http://95.217.102.140:8000`
- External HTTPS: `https://95.217.102.140:8000` (your current IP)

## External Access

To access from other computers on the network:

1. **Find your IP address**: Run `ipconfig` in Command Prompt
2. **Access via IP**: Use `http://YOUR_IP:8000` instead of localhost
3. **Windows Firewall**: You may need to allow Python through Windows Firewall
4. **Test connection**: Run `python test_connection.py` to verify accessibility

## Project Structure

```
├── app/
│   ├── __init__.py          # App package
│   ├── models.py            # Pydantic models
│   ├── webhooks.py          # Webhook handlers
│   └── integrations.py      # Integration routes
├── main.py                  # FastAPI application
├── requirements.txt         # Dependencies
└── test_connection.py      # Connection tester
```

## Endpoints

- `GET /` - API root with endpoint information
- `POST /integrations/fareharbor/webhooks/bookings` - Receives FareHarbor booking webhooks and forwards to MakerSuite API

## Booking Data Transformation

The webhook endpoint automatically:

1. **Receives** FareHarbor booking data
2. **Transforms** the data to MakerSuite API format
3. **Forwards** the transformed data to MakerSuite API
4. **Returns** success/failure status

### Data Transformation Flow

**Input (FareHarbor):**
```json
{
  "booking": {
    "availability": {"item": {"pk": 80038}},
    "customers": [{"custom_field_values": [...]}],
    "contact": {"email": "...", "phone": "..."},
    "custom_field_values": [...]
  }
}
```

**Output (MakerSuite):**
```json
{
  "DepartFlights": [80038],
  "ReturnFlights": [],
  "Passengers": [{
    "FirstName": "sadf",
    "LastName": "asdf",
    "DateOfBirth": "2000-11-11",
    "Gender": "M",
    "Email": "f.qvarnstrom8@gmail.com",
    "Phone": "3534524323",
    "DocumentNumber": "sdfasfdsa",
    "DocumentExpiry": "2028-11-11",
    "DocumentType": "P",
    "DocumentCountry": "United States",
    "Weight": 165,
    "BahamasStay": "BSStay",
    "AddressStreet": "sadf",
    "AddressCity": "asdf2",
    "AddressState": "asdf3",
    "AddressZIPCode": ""
  }],
  "IsDepartFirstClass": false,
  "IsReturnFirstClass": false
}
```

## Data Models

### WebhookData (Basic)
```json
{
  "data": {
    "booking_id": "string",
    "customer_name": "string",
    "email": "string",
    "phone": "string (optional)",
    "booking_date": "string",
    "tour_name": "string",
    "participants": "number",
    "total_amount": "number",
    "status": "string",
    "payment_method": "string (optional)",
    "special_requests": "string (optional)",
    "emergency_contact": "object (optional)",
    "tour_details": "object (optional)",
    "payment_info": "object (optional)"
  }
}
```

### FareHarborWebhook (Detailed)
```json
{
  "data": {
    "booking_id": "string",
    "customer_name": "string", 
    "email": "string",
    "phone": "string (optional)",
    "booking_date": "string",
    "tour_name": "string",
    "participants": "number",
    "total_amount": "number",
    "status": "string",
    "payment_method": "string (optional)",
    "special_requests": "string (optional)",
    "emergency_contact": "object (optional)",
    "tour_details": "object (optional)",
    "payment_info": "object (optional)"
  },
  "event_type": "string (optional)",
  "timestamp": "string (optional)",
  "source": "string (optional)"
}
```

## HTTPS Setup

The server automatically detects SSL certificates and runs with HTTPS if available:

1. **Generate SSL certificates:**
   ```bash
   python generate_ssl.py
   ```

2. **Start server with HTTPS:**
   ```bash
   python main.py
   ```

3. **Test HTTPS endpoints:**
   ```bash
   python test_connection.py
   ```

## Testing

### Test Data Transformation
```bash
python test_booking_transformation.py
```

### Test Country Conversion
```bash
python test_country_conversion.py
```

### Test API Integration
```bash
python test_connection.py
```

## Configuration

### MakerSuite API Settings
- **API URL**: `https://testapi.makerssuite.com/api/Book/CreateBooking`
- **API Key**: `AD3236C8-E7E8-4D81-A73A-E389F4ADE35B`
- **Headers**: `ApiKey` for authentication

### Field Mapping

| FareHarbor Field | MakerSuite Field | Transformation |
|------------------|------------------|----------------|
| `availability.item.pk` | `DepartFlights[0]` | Direct mapping |
| `customers[].custom_field_values` | `Passengers[]` | Complex mapping |
| `contact.email` | `Passengers[].Email` | Direct mapping |
| `contact.phone` | `Passengers[].Phone` | Direct mapping |
| Date formats | Date formats | MM/DD/YYYY → YYYY-MM-DD |
| Gender display | Gender code | "Male" → "M", "Female" → "F" |
| Country names | ISO3 codes | "United States" → "USA" |

## Usage

Send a POST request to `/integrations/fareharbor/webhooks/bookings` with FareHarbor booking data. The system will:

1. **Log** the incoming webhook data
2. **Transform** the data to MakerSuite format
3. **Send** to MakerSuite API
4. **Return** success/failure status

**HTTPS URLs:**
- `https://95.217.102.140:8000/integrations/fareharbor/webhooks/bookings`

## API Documentation

Once the server is running, you can access:
- Interactive API docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`
