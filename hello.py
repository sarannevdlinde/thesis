import os
import json
import asyncio
import websockets
from gtts import gTTS
import dotenv
from quart import Quart, request, render_template, make_response
import pandas as pd

# Websocket URL to connect to Lizz server
ws_url = 'ws://ws.lizz.health:5556/?type=TABLET&id=dded0926-34fd-4bf1-9254-d03ef5078c70'

# Message list
messages = [
    "Het is tijd om je medicijnen in te nemen",
    "Het is tijd om te lunchen",
    "Het is tijd om te bewegen!",
    "Het is tijd om de woonkamer op te ruimen"
]

# Generate audio files for messages
for i, text in enumerate(messages):
    tts = gTTS(text=text, lang='nl')
    audio_file = f"static/output_{i}.mp3"
    tts.save(audio_file)

app = Quart(__name__)

# Load environment variables
dotenv_file = './example.env'
dotenv.load_dotenv(dotenv_file)

# Initialize dataframe for messages
messages_df = pd.DataFrame(columns=['message', 'received_time', 'display_time', 'duration'])


# Get tablet ID from environment variables
def _get_tablet_id():
    try:
        return os.getenv("TABLET_ID")
    except Exception as e:
        print("[ERROR] No stored tablet ID found, requesting a new one.")
        return ""

# Save tablet ID to .env file
def _save_tablet_id(tablet_id: str):
    dotenv.set_key(dotenv_file, "TABLET_ID", tablet_id)


# WebSocket handler to connect Lizz server as a tablet
async def connect_to_socket_as_tablet():
    iot_id = _get_tablet_id()
    async with websockets.connect(ws_url) as websocket:
        if not iot_id:
            connect_msg = await websocket.recv()
            data = json.loads(connect_msg)
            if data["type"] == "connected":
                iot_id = data["client"]["id"]
                _save_tablet_id(iot_id)

        # Continuously receive messages from server
        while True:
            msg = await websocket.recv()
            print("Message received: ", msg)
            messages_df.loc[len(messages_df)] = [msg, pd.Timestamp.now(), None, None]
            print(messages_df)


# Quart routes
@app.before_serving
async def startup():
    app.add_background_task(connect_to_socket_as_tablet)

# Handle POST requests for button interactions
@app.route('/post_data', methods=['POST'])
async def buttonHandler():
    data = await request.get_json()
    print(f"Received POST request with data: {data}")
    return "Received POST request", 200

# Return messages as JSON
@app.route('/get_messages', methods=['GET'])
async def get_messages():
    sorted_messages = messages_df.sort_values(by='received_time', ascending=False)
    return sorted_messages.to_json(), 200

# Serve the home page
@app.route("/", methods=["GET"])
async def home():
    return await render_template("index.html")

# Run Quart app
if __name__ == "__main__":
    app.run(debug=True)
