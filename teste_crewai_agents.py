from crewai import Agent, Task, Crew
from langgraph.graph import StateGraph
import os
import psycopg2
import pinecone
import matplotlib.pyplot as plt
import networkx as nx
from dotenv import load_dotenv
from openai import OpenAI
import logging
from pydantic import BaseModel

# Configuração de logs para visualizar todo o processamento
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Definir esquema de estado para o LangGraph
class BugState(BaseModel):
    bug: dict
    componente: str = None
    severidade: str = None
    analise_tecnica: str = None
    resolucao: str = None
    documentacao: str = None

# Carregar variáveis do .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
NEON_DB_URL = os.getenv("NEON_DB_URL")

# Inicializar OpenAI clients
client_agents = OpenAI(api_key=OPENAI_API_KEY)
client_manager = OpenAI(api_key=OPENAI_API_KEY)

# Criar agentes e suas respectivas tasks
AG1 = Agent(
    name="Classificador de Componente",
    role="Classificação de bugs por componente afetado",
    goal="Classificar corretamente os bugs nos componentes adequados do sistema.",
    backstory="Especialista em triagem de bugs para componentes Frontend, Backend, Database, DevOps, Security ou Integration.",
    llm=client_agents,
    model="gpt-4o"
)
Task_AG1 = Task(
    description="Classificar o bug pelo componente afetado.",
    agent=AG1
)

AG2 = Agent(
    name="Classificador de Severidade",
    role="Classificação de bugs por severidade",
    goal="Definir a severidade dos bugs e incidentes.",
    backstory="Avaliador da severidade de bugs como Crítico, Grave ou Menor.",
    llm=client_agents,
    model="gpt-4o"
)
Task_AG2 = Task(
    description="Definir a severidade do bug.",
    agent=AG2
)

AG3 = Agent(
    name="Analista Técnico de Bugs",
    role="Análise técnica de bugs e incidentes",
    goal="Fornecer uma análise técnica detalhada com possíveis causas e soluções.",
    backstory="Engenheiro de software especializado em debugging e resolução de problemas técnicos.",
    llm=client_agents,
    model="gpt-4o"
)
Task_AG3 = Task(
    description="Analisar tecnicamente o bug e sugerir possíveis causas e soluções.",
    agent=AG3
)

AG4 = Agent(
    name="Gerenciador de Resolução",
    role="Gerenciamento do fluxo de resolução de bugs",
    goal="Coordenar a resolução de bugs e atribuir a desenvolvedores apropriados.",
    backstory="Tech Lead responsável por garantir que bugs sejam resolvidos eficientemente.",
    llm=client_agents,
    model="gpt-4o"
)
Task_AG4 = Task(
    description="Coordenar a resolução do bug e atribuir a desenvolvedores apropriados.",
    agent=AG4
)

AG5 = Agent(
    name="Documentador de Bugs",
    role="Documentação completa de bugs e soluções",
    goal="Criar documentação detalhada para cada bug e sua resolução.",
    backstory="Especialista em documentação técnica e gestão de conhecimento.",
    llm=client_agents,
    model="gpt-4o"
)
Task_AG5 = Task(
    description="Criar documentação completa do bug e sua solução.",
    agent=AG5
)

# Criando o Grafo de Processamento com LangGraph
graph = StateGraph(state_schema=BugState)

def executar_task(task, state):
    # Criar um texto enriquecido com todas as informações disponíveis sobre o bug
    texto_completo = f"Bug: {state.bug['descricao']}\n"
    if 'passos_reproducao' in state.bug and state.bug['passos_reproducao']:
        texto_completo += f"Passos para reprodução: {state.bug['passos_reproducao']}\n"
    if 'versao_sistema' in state.bug and state.bug['versao_sistema']:
        texto_completo += f"Versão: {state.bug['versao_sistema']}\n"
    if 'ambiente' in state.bug and state.bug['ambiente']:
        texto_completo += f"Ambiente: {state.bug['ambiente']}\n"
    
    # Adicionar informações de estados anteriores se disponíveis
    if state.componente:
        texto_completo += f"Componente classificado: {state.componente}\n"
    if state.severidade:
        texto_completo += f"Severidade classificada: {state.severidade}\n"
    if state.analise_tecnica:
        texto_completo += f"Análise técnica: {state.analise_tecnica}\n"
    if state.resolucao:
        texto_completo += f"Plano de resolução: {state.resolucao}\n"
        
    return task.execute(inputs={"input": texto_completo})

graph.add_node("classificacao_componente_node", lambda state: executar_task(Task_AG1, state))
graph.add_node("classificacao_severidade_node", lambda state: executar_task(Task_AG2, state))
graph.add_node("analise_tecnica_node", lambda state: executar_task(Task_AG3, state))
graph.add_node("gerenciamento_resolucao_node", lambda state: executar_task(Task_AG4, state))
graph.add_node("documentacao_bug_node", lambda state: executar_task(Task_AG5, state))

graph.add_edge("classificacao_componente_node", "classificacao_severidade_node")
graph.add_edge("classificacao_severidade_node", "analise_tecnica_node")
graph.add_edge("analise_tecnica_node", "gerenciamento_resolucao_node")
graph.add_edge("gerenciamento_resolucao_node", "documentacao_bug_node")

graph.set_entry_point("classificacao_componente_node")

compiled_graph = graph.compile()

# Conectar ao NeonDB para buscar bugs
conn = psycopg2.connect(NEON_DB_URL)
cur = conn.cursor()
cur.execute("SELECT id, descricao, passos_reproducao, versao_sistema, ambiente FROM bugs WHERE status = 'Aberto';")
bugs = cur.fetchall()
cur.close()
conn.close()

# Criar equipe
crew = Crew(
    name="Equipe de Processamento de Bugs",
    tasks=[Task_AG1, Task_AG2, Task_AG3, Task_AG4, Task_AG5],
    llm=client_manager,
    process="sequential"
)

# Executar fluxo
for bug in bugs:
    bug_data = BugState(bug={
        "descricao": bug[1],
        "passos_reproducao": bug[2] if bug[2] else "",
        "versao_sistema": bug[3] if bug[3] else "",
        "ambiente": bug[4] if bug[4] else ""
    })
    logger.info("🚀 Iniciando processamento do bug: %s", bug_data)
    resultado = compiled_graph.invoke(bug_data)
    logger.info("✅ Processamento concluído!")
    logger.info("📜 Documentação final do bug: %s", resultado)