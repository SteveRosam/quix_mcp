import os
import threading
import time
from quixstreams import Application
from datetime import datetime

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

# Global variable for the config ID
current_config_id = 1

# Function to run in a separate thread
def increment_config_id():
    global current_config_id
    while True:
        time.sleep(5)  # Increment every 5 seconds
        current_config_id += 1
        if current_config_id > 10:
            current_config_id = 1
        print(f"Config ID updated to: {current_config_id}")

app = Application(consumer_group="hard-braking-v136543", auto_offset_reset="earliest", use_changelog_topics=False)

input_topic = app.topic(os.environ["input"])
output_topic = app.topic(os.environ["output"])

sdf = app.dataframe(input_topic)

# Filter items out without brake value.
sdf = sdf[sdf.contains("Speed")]

# Calculate hopping window of 1s with 200ms steps.
sdf = sdf.apply(lambda row: float(row["Speed"])) \
        .hopping_window(1000, 200).mean().final() 
        
sdf.print()

# Create nice JSON alert message.
sdf = sdf.apply(lambda row: {
    "Timestamp": str(datetime.fromtimestamp(row["start"]/1000)),
    "Alert": "For last 1 second, average speed was " + str(row["value"]),
    "Speed": row["value"],
    "config_id": current_config_id
})

# Print JSON messages in console.
sdf.print()

# Send the message to the output topic
sdf.to_topic(output_topic)

if __name__ == "__main__":
    # Start the config ID incrementing thread before running the app
    config_thread = threading.Thread(target=increment_config_id, daemon=True)
    config_thread.start()
    
    # Run the application
    app.run()