import importlib
import os
from dotenv import load_dotenv
import subprocess

load_dotenv()

if __name__ == "__main__":
    try:
        cmd = ["python", "pubmed/pubmed_data.py"]
        subprocess.run(cmd, check=True)
        print("Successfully generated pubmed.jsonl.")
    except subprocess.CalledProcessError:
        print("Script execution failed.")
    except FileNotFoundError:
        print("Python interpreter or the script was not found.")

    host = os.environ.get("HOST", "localhost")
    port = int(os.environ.get("PORT", 8000))

    print("now realtime rag ")
    app_api = importlib.import_module("api.ragapp")
    print("realtime rag_api will run")
    app_api.run(host=host, port=port)
