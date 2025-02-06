import requests
from services.transcription import start_transcription
import os

API_KEY = os.environ['GLADIA_API_KEY']
API_URL = "https://api.gladia.io/v2/live"

def initialize_session():
    """Initialise une session Gladia."""
    headers = {"Content-Type": "application/json", "X-Gladia-Key": API_KEY}
    
    data = {
        # Paramètres audio requis
        "encoding": "wav/pcm",
        "sample_rate": 16000,
        "bit_depth": 16,
        "channels": 1,
        
        # Options de langues
        "language_config": {
            "languages": [],
            "code_switching": True
        },       
        # Options de pré-traitement audio
        "pre_processing": {
            "audio_enhancer": True,    # Amélioration de la qualité audio
            "speech_threshold": 0.8    # Seuil de détection de la parole
        },
        "realtime_processing": {
            "sentiment_analysis": True
        },
        # Options de post-traitement
        "post_processing": {
        "summarization": True,
        "summarization_config": {"type": "general"},
        }
    }
    
    response = requests.post(API_URL, headers=headers, json=data)
    
    if response.status_code == 201:
        session_info = response.json()
        return session_info["url"], session_info["id"]
    else:
        print("Erreur lors de l'initialisation de la session")
        return None, None

def main():
    print("\n=== Transcription Live YouTube ===")
    print("Note: La transcription et l'audio seront sauvegardés automatiquement")
    print("pendant la session. Utilisez Ctrl+C pour arrêter proprement.")
    
    url = input("\nEntrez l'URL du live YouTube: ").strip()
    if not url:
        return

    print("\nInitialisation de la session Gladia...")
    websocket_url, session_id = initialize_session()
    
    if websocket_url:
        print(f"\nSession Gladia initialisée avec ID: {session_id}") 
        try:
            start_transcription(API_KEY, websocket_url, url, session_id)
        except KeyboardInterrupt:
            print("\nArrêt demandé par l'utilisateur. Fermeture propre en cours...")
        except Exception as e:
            print(f"\nUne erreur est survenue: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgramme terminé par l'utilisateur.")
    except Exception as e:
        print(f"\nUne erreur inattendue est survenue: {e}")