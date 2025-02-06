# Import des bibliothèques nécessaires
import websocket
import json
import threading
import os
import stat
import signal
import time
from services.stream_capture import get_audio_stream

class TranscriptionSession:
    """Classe gérant une session de transcription"""
    def __init__(self):
        # Initialisation des attributs de la session
        self.stop_event = threading.Event()  # Event pour arrêter la transcription
        self.is_user_interrupt = False       # Flag pour l'interruption utilisateur
        self.final_events_received = threading.Event()  # Event pour les événements finaux
        self.ws = None                      # Connection WebSocket
        self.shutdown_in_progress = False    # Flag pour l'arrêt en cours
        self.start_time = time.time()       # Timestamp de début
        self.session_id = None              # ID unique de la session

    def stop_recording(self):
        """Envoie le message de fin d'enregistrement via WebSocket."""
        try:
            if self.ws and self.ws.sock:
                # Calcul de la durée d'enregistrement
                recording_duration = time.time() - self.start_time

                # Préparation du message de fin
                end_message = {
                    "session_id": self.session_id,
                    "type": "end_recording",
                    "data": {
                        "recording_duration": recording_duration
                    }
                }

                self.ws.send(json.dumps(end_message))
                print("Signal d'arrêt d'enregistrement envoyé avec succès")
                return True
        except Exception as e:
            print(f"Erreur lors de l'envoi du signal d'arrêt: {e}")
            return False

    def graceful_shutdown(self):
        """Gère l'arrêt propre de la session de transcription"""
        if self.shutdown_in_progress:
            return

        self.shutdown_in_progress = True
        print("\nArrêt demandé. Finalisation en cours...")
        self.is_user_interrupt = True

        if self.stop_recording():
            print("Attente des événements finaux (30 secondes max)...")
            events_received = self.final_events_received.wait(timeout=30)

            if not events_received:
                print("Timeout: Les événements finaux n'ont pas été reçus")
            else:
                print("Événements finaux reçus avec succès")

        self.stop_event.set()

def format_duration(seconds):
    """Formate les secondes en format minutes:secondes.millisecondes."""
    minutes = int(seconds // 60)
    sec = seconds % 60
    return f"{minutes:02}:{sec:06.3f}"

def make_writable(path):
    """Rend un fichier ou dossier modifiable en ajoutant les permissions d'écriture."""
    current = stat.S_IMODE(os.lstat(path).st_mode)
    os.chmod(path, current | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)

def start_transcription(api_key, websocket_url, url, session_id):
    """Initialise la connexion WebSocket et démarre la transcription.
    
    Args:
        api_key (str): Clé API pour l'authentification
        websocket_url (str): URL du serveur WebSocket
        url (str): URL du flux audio à transcrire
        session_id (str): Identifiant unique de la session
    """
    # Création d'une nouvelle session
    session = TranscriptionSession()
    session.session_id = session_id

    # Handler pour le signal SIGINT (Ctrl+C)
    def signal_handler(signum, frame):
        session.graceful_shutdown()

    # Installation du handler
    signal.signal(signal.SIGINT, signal_handler)

    # Configuration des dossiers de travail
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    session_dir = os.path.join(data_dir, f"session_{session_id}")
    
    try:
        # Création du dossier de session avec les permissions appropriées
        os.makedirs(session_dir, mode=0o777, exist_ok=True)
        make_writable(session_dir)
        os.chdir(session_dir)
    except PermissionError:
        print(f"\nErreur: Impossible de créer le dossier {session_dir}")
        print("Sauvegarde dans le dossier data à la place.")
        session_dir = data_dir

    print(f"\nID de session: {session_id}")
    print(f"Dossier de sauvegarde: {os.path.abspath(session_dir)}")

    def on_message(ws, message):
        """Callback pour gérer les messages reçus du WebSocket."""
        try:
            response = json.loads(message)

            # Vérification si l'arrêt est en cours
            if session.shutdown_in_progress:
                if response.get("type") == "post_final_transcript":
                    session.final_events_received.set()
                    if session.ws and session.ws.sock:
                        session.ws.close()
                return

            # Gestion des transcriptions en temps réel
            if response.get("type") == "transcript" and response["data"].get("is_final"):
                start = format_duration(response["data"]["utterance"]["start"])
                end = format_duration(response["data"]["utterance"]["end"])
                text = response["data"]["utterance"]["text"].strip()
                print(f"{start} --> {end} | {text}")

                # Sauvegarde dans le fichier de transcription en cours
                filename = f"transcript_{session_id}_ongoing.txt"
                with open(filename, "a", encoding="utf-8") as f:
                    f.write(f"{start} --> {end} | {text}\n")
                make_writable(filename)

            # Gestion de l'analyse des sentiments
            elif response.get("type") == "sentiment_analysis":
                results = response["data"].get("results", [])
                for result in results:
                    sentiment = result.get("sentiment", "").upper()
                    start = format_duration(result.get("start", 0))
                    end = format_duration(result.get("end", 0))
                    text = result.get("text", "").strip()
                    emotion = result.get("emotion", "")

                    print(f"\nSENTIMENT: {sentiment} | EMOTION: {emotion}")
                    print(f"Timing: {start} --> {end}")
                    print(f"Texte: {text}\n")

                    # Sauvegarde des analyses de sentiment
                    filename = f"sentiments_{session_id}.txt"
                    with open(filename, "a", encoding="utf-8") as f:
                        f.write(f"SENTIMENT: {sentiment} | EMOTION: {emotion}\n")
                        f.write(f"Timing: {start} --> {end}\n")
                        f.write(f"Texte: {text}\n\n")
                    make_writable(filename)

            # Gestion de la transcription finale
            elif response.get("type") == "post_final_transcript":
                print("\n################ Fin de la session ################\n")
                print(json.dumps(response, indent=2, ensure_ascii=False))

                # Sauvegarde de la transcription finale
                filename = f"transcript_{session_id}_final.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(response, f, ensure_ascii=False, indent=2)
                make_writable(filename)
                session.final_events_received.set()
                if session.shutdown_in_progress and session.ws and session.ws.sock:
                    session.ws.close()

        except Exception as e:
            if not session.shutdown_in_progress:
                print(f"Erreur lors du traitement du message: {e}")

    def on_error(ws, error):
        """Callback pour gérer les erreurs WebSocket"""
        if not session.shutdown_in_progress:
            print(f"Erreur de connexion: {error}")

    def on_close(ws, close_status_code, close_msg):
        """Callback pour gérer la fermeture de la connexion WebSocket"""
        if not session.shutdown_in_progress:
            print("Connexion perdue")

    def send_audio(ws, url):
        """Capture et envoie l'audio du flux en continu.
        
        Args:
            ws (WebSocket): Instance WebSocket
            url (str): URL du flux audio
        """
        stream = get_audio_stream(url)
        print("Démarrage de la transcription...")

        try:
            # Sauvegarde du flux audio
            filename = f"audio_{session_id}.wav"
            with open(filename, "wb") as audio_file:
                while not session.stop_event.is_set():
                    chunk = stream.read(4096)
                    if not chunk:
                        break
                    if not session.stop_event.is_set():
                        try:
                            ws.send(chunk, websocket.ABNF.OPCODE_BINARY)
                            audio_file.write(chunk)
                        except websocket.WebSocketConnectionClosedException:
                            if not session.shutdown_in_progress:
                                print("Connexion perdue")
                            break
                        except Exception as e:
                            if not session.shutdown_in_progress:
                                print(f"Erreur d'envoi audio: {e}")
                            break
            make_writable(filename)
        finally:
            try:
                stream.close()
            except:
                pass

    # Initialisation de la connexion WebSocket
    ws = websocket.WebSocketApp(
        websocket_url,
        header={"Authorization": f"Bearer {api_key}"},
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    session.ws = ws

    # Démarrage du thread d'envoi audio
    audio_thread = threading.Thread(target=send_audio, args=(ws, url))
    audio_thread.daemon = True
    audio_thread.start()

    try:
        # Démarrage de la boucle WebSocket
        ws.run_forever()
    finally:
        # Nettoyage final
        if not session.stop_event.is_set():
            session.stop_event.set()
        
        if audio_thread.is_alive():
            audio_thread.join(timeout=2)
        
        if session_dir != data_dir:
            os.chdir(data_dir)
        
        # Affichage du chemin relatif des fichiers sauvegardés
        relative_path = os.path.relpath(session_dir, os.path.dirname(os.path.dirname(__file__)))
        print(f"\nFichiers sauvegardés dans: {relative_path}/")