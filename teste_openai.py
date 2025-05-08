import openai
import os
from dotenv import load_dotenv
from pathlib import Path

# Carregar o .env
dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Teste de conexão
try:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.models.list()
    print("✅ Conexão bem-sucedida com OpenAI! Modelos disponíveis:")
    for model in response.data:
        print(f"- {model.id}")
except Exception as e:
    print("❌ Erro ao conectar à OpenAI:", e)
