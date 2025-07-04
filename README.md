Project Overview
FoodFlow AI is a university project developed by the ARMADA team at NHL Stenden University to create an automated food inventory management system. Designed for households and small businesses, it uses a Raspberry Pi, PIR motion sensor, and camera to track fridge contents, leveraging AI for image recognition. The system reduces food waste by providing real-time inventory updates and expiration alerts through a user-friendly web interface. This project showcases our skills in hardware integration, AI, backend development, and frontend design.
Key Features:

Motion-triggered image capture to monitor fridge contents.
AI-based item recognition using the Qwen model.
MongoDB database for storing inventory data.
Web interface for managing inventory and viewing recipe suggestions.
Open-source and customizable to support sustainability goals.

Team Members:

Alexia (5587832): Webpage design and project video.
Rafael (5492181): Database management.
Matin (5362962): Documentation.
Adriana (5572185): API key acquisition and documentation.
Diogo (5548772): Raspberry Pi integration, database integration, coding, 3D printing, presentations, documentation.
Andrei (5464234): Project video.

Repository: https://github.com/Diogo-Alves04/Armada
Prerequisites

Hardware:
Raspberry Pi Pico (or Raspberry Pi 4)
PIR Motion Sensor (HC-SR501)
8MP Camera Module (CSI interface)
5V 3A power adapter


Software:
Python 3.8+
Required Python packages: flask, pymongo, flask-cors, picamera2, requests
MongoDB Atlas account for cloud database
Nebius API key for Qwen AI model


Operating System: Raspberry Pi OS (Linux-based)

Setup Instructions

Hardware Setup:

Connect the PIR sensor to GPIO 17 (Pin 11), 5V (Pin 2/4), and GND (Pin 6).
Attach the camera module to the Raspberry Pi’s CSI interface.
Power the Raspberry Pi using a 5V 3A USB-C adapter.


Clone the Repository:
git clone git@github.com:Diogo-Alves04/FoodFlow.git
cd FoodFlow


Install Software Dependencies:
sudo apt update && sudo apt upgrade -y
sudo apt install git python3-pip -y
pip install flask pymongo flask-cors picamera2 requests


Configure Environment Variables:

Set the MongoDB connection string:export MONGODB_URI="mongodb+srv://<username>:<password>@cluster0.mongodb.net/foodDB"


Set the Nebius API key:export NEBIUS_API_KEY="<your-nebius-api-key>"




Run the Application:
python app.py


Access the System:

Open a web browser and go to http://<Raspberry_Pi_IP>:5000 to view the inventory interface.



How to Use

Automated Inventory Tracking:

When the fridge door opens, the PIR sensor triggers the camera to capture an image.
The Qwen AI model analyzes the image to identify food items and quantities.
Results are stored in MongoDB and displayed on the web interface.


Web Interface:

View the inventory list, including item names, quantities, and expiration dates.
Search or sort items by name or expiration date.
Manually add, edit, or delete items using the interface.
Receive notifications for items nearing expiration.


Recipe Suggestions:

The system suggests recipes based on inventory, prioritizing items close to expiration.


API Endpoints:

GET /api/items: Fetch all inventory items.
POST /api/items: Add a new item manually.
DELETE /api/items/<id>: Delete an item.
POST /photo_handler: Process a photo for AI analysis.



Project Structure
FoodFlow/
app.py              # Flask backend and API logic
Photo_handler.py    # Handles camera capture and photo processing
static/
 styles.css      # Styling for the web interface
 script.js       # JavaScript for frontend functionality
index.html          # Web interface HTML
Uploads/            # Stores uploaded images
results/            # Stores AI analysis results
README.md           # Project documentation

Testing and Validation
The system has been rigorously tested:

Hardware: PIR sensor and camera functionality verified.
AI: Achieves 60–80% accuracy, with manual correction for low-confidence predictions.
API and Database: 100% pass rate for CRUD operations.
Frontend: Supports 50 concurrent users with <200ms response times.
Coverage: 92% test coverage across components.

See the portfolio for detailed test scripts and results.
Contributing
This is a university project, but we welcome feedback and contributions:

Fork the repository.
Create a feature branch (git checkout -b feature/your-feature-name).
Commit your changes (git commit -m "Describe your changes").
Push to the branch (git push origin feature/your-feature-name).
Submit a pull request with a clear description of your changes.

Contact
For inquiries, contact Diogo Alves via GitHub or email at diogo.carvalho.candeias@student.nhlstenden.com. For academic purposes, refer to the project portfolio for detailed documentation.
