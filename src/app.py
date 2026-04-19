import streamlit as st
import pandas as pd
import json
import re
from agente import gerar_resposta, detectar_produto_especifico, texto_para_numero_avancado
from config import OPENAI_API_KEY
from openai import OpenAI
from streamlit_mic_recorder import mic_recorder
import tempfile

client = OpenAI(api_key=OPENAI_API_KEY)

st.set_page_config(page_title="FinAssist", page_icon="💰")
st.title("💰 FinAssist - Assistente Financeiro Inteligente")

@st.cache_data
def carregar_dados():
    transacoes = pd.read_csv("data/transacoes.csv")
    with open("data/perfil_investidor.json", "r", encoding="utf-8") as f:
        perfil = json.load(f)
    with open("data/produtos_financeiros.json", "r", encoding="utf-8") as f:
        produtos = json.load(f)
    historico = pd.read_csv("data/historico_atendimento.csv")
    return transacoes, perfil, produtos, historico

transacoes, perfil, produtos, historico = carregar_dados()

if "mensagens" not in st.session_state:
    st.session_state.mensagens = []
if "produto_atual" not in st.session_state:
    st.session_state.produto_atual = None
if "valor_atual" not in st.session_state:
    st.session_state["valor_atual"] = None
if "meses_atual" not in st.session_state:
    st.session_state["meses_atual"] = None
if "aporte_mensal" not in st.session_state:
    st.session_state["aporte_mensal"] = 0
if "transcricao_audio" not in st.session_state:
    st.session_state.transcricao_audio = None
if "recorder_key" not in st.session_state:
    st.session_state.recorder_key = 0

for msg in st.session_state.mensagens:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

container = st.container()
with container:
    col1, col2 = st.columns([8, 1])
    with col1:
        user_input = st.chat_input("Digite sua pergunta...")
    with col2:
        audio = mic_recorder(
            start_prompt="🎙️",
            stop_prompt="⏹️",
            key=f"recorder_{st.session_state.recorder_key}"
        )

def processar_pergunta(pergunta):
    #Função unificada para processar a pergunta (texto ou áudio)
    
    st.session_state.mensagens.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    # --- Extração de valor numérico ---
    valor_detectado = texto_para_numero_avancado(pergunta)
    tem_tempo = any(p in pergunta.lower() for p in ["mes", "meses", "ano", "anos"])
    if tem_tempo and valor_detectado is not None and valor_detectado <= 29:
        valor_detectado = None

    # --- Classificação do tipo de valor ---
    pergunta_lower = pergunta.lower()
    tipo_valor = None
    marcadores_tempo = ["mês", "mes", "mensal", "ano", "semana"]

    if ("aporte mensal" in pergunta_lower or
        re.search(r'(\d+|cem|duzentos|trezentos|[a-zA-Z]+)\s+(por mês|por mes|mensal|todo mês|ao mês)', pergunta_lower)):
        tipo_valor = "aporte"
    elif "mais" in pergunta_lower and not any(p in pergunta_lower for p in marcadores_tempo):
        tipo_valor = "incremento"
    elif re.search(r'aporte\s+(?:de\s+)?([\w\d.,]+)', pergunta_lower) and not any(p in pergunta_lower for p in marcadores_tempo):
        if st.session_state.get("valor_atual") is not None:
            tipo_valor = "incremento"
        else:
            tipo_valor = "inicial"
    elif any(p in pergunta_lower for p in ["investir", "investimento", "aplicar", "simular", "rendimento de"]):
        tipo_valor = "inicial"
    elif valor_detectado is not None:
        tipo_valor = "inicial"

    # --- Atualização de estado ---
    if tipo_valor == "aporte":
        if valor_detectado is not None:
            st.session_state["aporte_mensal"] = valor_detectado
    elif tipo_valor == "incremento":
        if valor_detectado is not None and st.session_state.get("valor_atual") is not None:
            st.session_state["valor_atual"] += valor_detectado
        elif valor_detectado is not None:
            st.session_state["valor_atual"] = valor_detectado
    elif tipo_valor == "inicial":
        if valor_detectado is not None:
            st.session_state["valor_atual"] = valor_detectado

    if valor_detectado is not None and tipo_valor != "aporte" and st.session_state.get("valor_atual") is None:
        st.session_state["valor_atual"] = valor_detectado

    # --- Detecção de meses ---
    if "um ano" in pergunta.lower():
        st.session_state["meses_atual"] = 12
    elif "um mês" in pergunta.lower() or "um mes" in pergunta.lower():
        st.session_state["meses_atual"] = 1
    else:
        match_meses = re.search(r'(\d+)\s*(meses|mês)', pergunta)
        match_anos = re.search(r'(\d+)\s*(anos|ano)', pergunta)
        if match_meses:
            st.session_state["meses_atual"] = int(match_meses.group(1))
        elif match_anos:
            st.session_state["meses_atual"] = int(match_anos.group(1)) * 12

    # --- Detecção de produto e reset de aporte ---
    produto = detectar_produto_especifico(pergunta, produtos)
    produto_anterior = st.session_state.get("produto_atual")
    if produto:
        if produto["nome"] != produto_anterior:
            if not re.search(r'aporte|por mês|mensal|todo mês|ao mês', pergunta.lower()):
                st.session_state["aporte_mensal"] = 0
        st.session_state["produto_atual"] = produto["nome"]

    # --- Chamada ao agente ---
    resultado = gerar_resposta(
        pergunta=pergunta,
        transacoes=transacoes,
        perfil=perfil,
        produtos=produtos,
        historico=historico,
        mensagens=st.session_state.mensagens,
        produto_contexto=st.session_state.get("produto_atual"),
        valor_contexto=st.session_state.get("valor_atual"),
        aporte_contexto=st.session_state.get("aporte_mensal"),
        meses_contexto=st.session_state.get("meses_atual")
    )

    # --- Processamento da resposta ---
    if isinstance(resultado, dict):
        resposta = resultado["resposta"]
        st.session_state["valor_atual"] = resultado.get("valor")
        st.session_state["meses_atual"] = resultado.get("meses")
        st.session_state["aporte_mensal"] = resultado.get("aporte", 0)
        if resultado.get("produto"):
            st.session_state["produto_atual"] = resultado["produto"]
    else:
        resposta = resultado

    # Escape do cifrão e correção de "R "
    resposta = re.sub(r'(?<!\\)\$', r'\\$', resposta)
    resposta = re.sub(r'\bR\s+(?=\d)', 'R$ ', resposta)

    st.session_state.mensagens.append({"role": "assistant", "content": resposta})
    with st.chat_message("assistant"):
        st.markdown(resposta)

# =============================
# TEXTO DIGITADO
# =============================
if user_input:
    processar_pergunta(user_input)

# =============================
# ÁUDIO → TRANSCRIÇÃO AUTOMÁTICA
# =============================
if audio and not st.session_state.get("transcricao_audio"):
    audio_bytes = audio["bytes"]
    st.session_state.audio_bytes = audio_bytes
    st.caption("🎙️ Áudio capturado")
    st.audio(audio_bytes, format="audio/wav")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        caminho_audio = tmp.name

    with st.spinner("⏳ Transcrevendo áudio..."):
        with open(caminho_audio, "rb") as f:
            transcricao = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
    st.session_state.transcricao_audio = transcricao.text

# =============================
# CONFIRMAÇÃO DA TRANSCRIÇÃO
# =============================
if st.session_state.get("transcricao_audio"):
    st.markdown("### 📝 O que você disse:")
    st.info(st.session_state.transcricao_audio)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Enviar"):
            pergunta = st.session_state.transcricao_audio
            processar_pergunta(pergunta)
            st.session_state.transcricao_audio = None
            st.session_state.audio_bytes = None
            st.session_state.recorder_key += 1
            st.rerun()

    with col2:
        if st.button("🔁 Regravar"):
            st.session_state.transcricao_audio = None
            st.session_state.audio_bytes = None
            st.session_state.recorder_key += 1
            st.rerun()