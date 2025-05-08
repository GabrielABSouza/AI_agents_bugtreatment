import os
import psycopg2
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()
DB_URL = os.getenv("NEON_DB_URL")

if not DB_URL:
    print("ERRO: A variável NEON_DB_URL não foi carregada corretamente. Verifique seu .env!")
else:
    print("Conectando ao banco de dados em:", DB_URL)

# Testando conexão
try:
    conn = psycopg2.connect(DB_URL)
    print("✅ Conexão bem-sucedida ao banco de dados!")
    conn.close()
except Exception as e:
    print("❌ Erro ao conectar ao banco:", e)
