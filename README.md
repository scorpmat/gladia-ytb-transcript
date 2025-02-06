This project is an example of implementing the Gladia Real-Time V2 API using Python. It enables real-time transcription of audio streams from livestreams or YouTube videos (utilizing the yt-dlp library).

The project is structured into three main files :

- **main.py** : Handles the initialization of the Gladia session and configures various advanced options, such as sentiment analysis.
- **transcription.py** : Manages the WebSocket connection for real-time transcription and the storage of results.
- **stream_capture.py** :  Captures the YouTube audio stream and encoding with ffmpeg

The implementation leverages some of Gladia's key features, such as audio pre-processing (audio enhancer) and real-time sentiment analysis. 
The code is designed to handle errors and interruptions properly while automatically saving transcriptions, sentiment analyses, and audio files separately. 
This project provides a practical illustration of how to integrate and use the Gladia Real-Time V2 API in a concrete use case.
