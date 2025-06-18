from picamera2 import Picamera2
import requests
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def take_and_send_photo(handler_url):
    """Capture and send photo to the handler server"""
    try:
        # Initialize camera
        picam2 = Picamera2()

        # Camera configuration
        config = picam2.create_still_configuration()
        picam2.configure(config)

        # Start camera and capture photo
        picam2.start()
        logging.info("Camera warming up...")
        time.sleep(2)  # Allow for exposure adjustment

        photo_path = '/home/armada/Desktop/work#/Test/uploads/photo.jpg'
        picam2.capture_file(photo_path)
        picam2.stop()
        logging.info(f"Photo captured and saved to {photo_path}")

        # Send to photo handler
        with open(photo_path, 'rb') as photo_file:
            files = {'photo': photo_file}
            response = requests.post(handler_url, files=files)

        if response.status_code == 200:
            logging.info("Photo sent successfully")
            logging.info(f"Server response: {response.json()}")
        else:
            logging.error(f"Server error: {response.status_code} - {response.text}")

    except Exception as e:
        logging.error(f"Error in photo capture/transmission: {str(e)}")
    
    finally:
        if 'picam2' in locals():
            picam2.close()

if __name__ == '__main__':
    # Replace with your server URL
    PHOTO_HANDLER_URL = "http://141.252.216.152:5000/photo_handler"
    take_and_send_photo(PHOTO_HANDLER_URL)
