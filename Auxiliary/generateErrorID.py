import uuid
from datetime import datetime

def generate_error_id():
    # Generate a unique ID using a combination of timestamp and random number
    error_id = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex[:6]}"
    return error_id