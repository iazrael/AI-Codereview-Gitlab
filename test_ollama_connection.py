import ollama

def check_ollama_connection():
    try:
        client = ollama.Client(
            # host="http://127.0.0.1:11434",
            host="http://192.168.200.34:11434",
        )
        # Attempt to list models to check connectivity
        response = client.list()
        print(response)
        
        print("✅ Successfully connected to Ollama.")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to Ollama: {e}")
        print("Please ensure Ollama is running and accessible. You can download it from https://ollama.com/download")
        return False

if __name__ == "__main__":
    check_ollama_connection()
