"""Configuration lue dans les variables d'environnement (aucune clé dans le dépôt)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_URL = "https://s3.amazonaws.com/tripdata/JC-202409-citibike-tripdata.csv.zip"
RAW_DIR = ROOT / "data" / "raw"
RAW_CSV = RAW_DIR / "JC-202409-citibike-tripdata.csv"
CLEAN_CSV = ROOT / "data" / "clean" / "trips_2024_09.csv"
CLEANING_LOG = ROOT / "data" / "cleaning_log.json"
TRACES_DIR = ROOT / "traces"

# "ollama" (par défaut, Qwen3.5-4B en local) ou "openai" (API compatible, ex. Cerebras)
BACKEND = os.environ.get("LLM_BACKEND", "ollama")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("LLM_MODEL", "qwen3.5:4b-q4_K_M")
NUM_CTX = int(os.environ.get("LLM_NUM_CTX", "16384"))
TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.7"))
THINK = os.environ.get("LLM_THINK", "0") == "1"
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.cerebras.ai/v1")
API_KEY_ENV = os.environ.get("LLM_API_KEY_ENV", "CEREBRAS_API_KEY")
