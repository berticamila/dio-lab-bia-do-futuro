import json
import re
import pandas as pd
from openai import OpenAI
from config import OPENAI_API_KEY
from prompts import get_system_prompt

client = OpenAI(api_key=OPENAI_API_KEY)

# =============================
# CLASSIFICADOR DE INTENÇÃO
# =============================
def classificar_intencao(pergunta: str):
    pergunta = pergunta.lower()
    tem_valor = bool(re.search(r'\d+|mil|cem|duzentos|trezentos', pergunta))

    if any(p in pergunta for p in ["informação"]):
        if not any(p in pergunta for p in ["investir", "simular", "quanto dá", "valor final", "aplicar", "quanto rende"]):
            return "informacao_produto"

    if tem_valor and any(p in pergunta for p in ["investir", "aplicar", "mais", "aporte"]):
        return "simulacao"

    if tem_valor:
        return "simulacao"

    if any(p in pergunta for p in ["simular", "rendimento", "quanto rende", "montante", "valor final", "aporte"]):
        return "simulacao"

    if any(p in pergunta for p in ["mes", "meses", "ano", "anos"]):
        return "simulacao"

    elif any(p in pergunta for p in ["gasto", "despesa", "gastei", "gastos"]):
        return "analise_gastos"

    elif any(p in pergunta for p in ["investimento", "recomenda"]):
        return "recomendacao"

    return "fallback"

# =============================
# CRITÉRIO DE ORDENAÇÃO
# =============================
def definir_criterio_ordenacao(pergunta: str):
    pergunta = pergunta.lower()
    if any(p in pergunta for p in ["rentabilidade", "rendimento", "rende mais", "lucro"]):
        return "rentabilidade"
    elif any(p in pergunta for p in ["total", "montante", "final"]):
        return "montante"
    elif any(p in pergunta for p in ["risco", "seguro"]):
        return "risco"
    return "montante"

def texto_para_numero_avancado(texto: str):
    texto = texto.replace("um mil", "mil")
    texto = texto.lower()
    texto = texto.replace(" e ", " ")
    texto = texto.replace("reais", "").replace("r$", "").strip()

    unidades = {
        "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "tres": 3,
        "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9
    }
    dezenas = {
        "dez": 10, "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50,
        "sessenta": 60, "setenta": 70, "oitenta": 80, "noventa": 90
    }
    centenas = {
        "cem": 100, "cento": 100, "duzentos": 200, "trezentos": 300,
        "quatrocentos": 400, "quinhentos": 500, "seiscentos": 600,
        "setecentos": 700, "oitocentos": 800, "novecentos": 900
    }

    match_k = re.search(r'(\d+(?:[.,]\d+)?)\s*k', texto)
    if match_k:
        return float(match_k.group(1).replace(',', '.')) * 1000

    if "mil" in texto:
        total = 0
        partes = texto.split("mil")
        antes = partes[0].strip()
        depois = partes[1].strip() if len(partes) > 1 else ""

        if antes == "" or not any(p in antes.split() for p in unidades):
            total += 1000
        else:
            for palavra, valor in unidades.items():
                if palavra in antes.split():
                    total += valor * 1000

        if depois:
            palavras_depois = depois.split()
            for palavra in palavras_depois:
                if palavra in centenas:
                    total += centenas[palavra]
                elif palavra in dezenas:
                    total += dezenas[palavra]
                elif palavra in unidades:
                    total += unidades[palavra]

        return float(total)

    match_num = re.search(r'(\d+(?:[.,]\d{3})*(?:[.,]\d{2})?)', texto)
    if match_num:
        valor_str = match_num.group(1).replace('.', '').replace(',', '.')
        return float(valor_str)

    for palavra, valor in centenas.items():
        if palavra in texto.split():
            return float(valor)
    for palavra, valor in dezenas.items():
        if palavra in texto.split():
            return float(valor)
    for palavra, valor in unidades.items():
        if palavra in texto.split():
            return float(valor)

    return None

# =============================
# EXTRAIR PARÂMETROS DA PERGUNTA
# =============================
def extrair_parametros_simulacao(pergunta: str):
    pergunta = pergunta.lower()
    valor = None
    meses = None
    aporte_mensal = None

    match_valor = re.search(r'(?:investimento de|investir|aplicar)\s+([\w\d.,]+)', pergunta)
    if match_valor:
        valor = texto_para_numero_avancado(match_valor.group(1))
        tem_tempo = any(p in pergunta for p in ["mes", "meses", "ano", "anos"])
        if tem_tempo and valor is not None and valor <= 29:
            valor = None

    if valor is None and "aporte" not in pergunta:
        valor_temp = texto_para_numero_avancado(pergunta)
        tem_tempo = any(p in pergunta for p in ["mes", "meses", "ano", "anos"])
        # Ignora números pequenos que provavelmente indicam tempo (ex: "um ano" → 1)
        if tem_tempo and valor_temp is not None and valor_temp <= 29:
            valor_temp = None
        valor = valor_temp

    # APORTE MENSAL (múltiplos padrões)
    match_aporte1 = re.search(r'aporte\s+mensal\s+de\s+([\w\d.,]+)', pergunta)
    match_aporte2 = re.search(r'aporte\s+de\s+([\w\d.,]+)', pergunta)
    match_aporte3 = re.search(r'(\d+|cem|duzentos|trezentos|quatrocentos|quinhentos|[a-zA-Z]+)\s+(?:por mês|por mes|mensal|todo mês|ao mês)', pergunta)

    if match_aporte1:
        aporte_mensal = texto_para_numero_avancado(match_aporte1.group(1))
    elif match_aporte2:
        aporte_mensal = texto_para_numero_avancado(match_aporte2.group(1))
    elif match_aporte3:
        aporte_mensal = texto_para_numero_avancado(match_aporte3.group(1))

    # MESES
    meses_match = re.search(r'(\d+)\s*(meses|mês)', pergunta)
    anos_match = re.search(r'(\d+)\s*(anos|ano)', pergunta)
    if meses_match:
        meses = int(meses_match.group(1))
    elif anos_match:
        meses = int(anos_match.group(1)) * 12

    if meses is None:
        if "um ano" in pergunta:
            meses = 12
        elif "um mês" in pergunta:
            meses = 1

    return valor, meses, aporte_mensal

# =============================
# DEFINIR DEFAULTS INTELIGENTES
# =============================
def definir_parametros_default(perfil, valor, meses):
    if valor is None:
        patrimonio = perfil.get("patrimonio_total", 0)
        valor = patrimonio * 0.3
    if meses is None:
        objetivo = perfil.get("objetivo_principal", "").lower()
        if "reserva" in objetivo:
            meses = 6
        elif "curto" in objetivo:
            meses = 12
        else:
            meses = 12
    return valor, meses

# =============================
# INFORMAÇÃO DE INVESTIMENTOS
# =============================
def responder_informacao_produto(pergunta, produtos):
    produto = detectar_produto_especifico(pergunta, produtos)
    if produto:
        return f"""
📊 Produto: {produto['nome']}

💰 Rentabilidade: {produto['rentabilidade']}
⚠️ Risco: {produto['risco']}
💵 Aporte mínimo: R$ {produto['aporte_minimo']:.2f}

📌 Indicado para: {produto['indicado_para']}
"""
    else:
        return "Não encontrei esse produto. Pode reformular?"

# =============================
# ANÁLISE DE GASTOS
# =============================
def analisar_gastos(transacoes: pd.DataFrame):
    saidas = transacoes[transacoes["tipo"] == "saida"]
    entradas = transacoes[transacoes["tipo"] == "entrada"]
    total_gastos = saidas["valor"].sum()
    total_receitas = entradas["valor"].sum()
    saldo = total_receitas - total_gastos
    por_categoria = saidas.groupby("categoria")["valor"].sum().sort_values(ascending=False)
    maior_categoria = por_categoria.idxmax()
    maior_valor = por_categoria.max()

    resposta = f"""
📊 **Resumo financeiro:**

💰 Receita total: R$ {total_receitas:.2f}
💸 Total gasto: R$ {total_gastos:.2f}
💼 Saldo do período: R$ {saldo:.2f}

🏷️ Categoria com maior gasto: **{maior_categoria}** (R$ {maior_valor:.2f})

📌 **Detalhamento dos gastos por categoria:**
"""
    for cat, val in por_categoria.items():
        resposta += f"\n- {cat}: R$ {val:.2f}"
    return resposta

# =============================
# RECOMENDAÇÃO DE INVESTIMENTOS
# =============================
def recomendar_investimentos(perfil, produtos):
    perfil_risco = perfil.get("perfil", "").lower()
    recomendados = []
    for p in produtos:
        if perfil_risco == "conservador" and p["risco"] == "baixo":
            recomendados.append(p)
        elif perfil_risco == "moderado" and p["risco"] in ["baixo", "medio"]:
            recomendados.append(p)
        elif perfil_risco == "arrojado":
            recomendados.append(p)

    resposta = "💡 **Sugestões de investimentos para seu perfil:**\n"
    for p in recomendados:
        resposta += f"\n- {p['nome']} ({p['rentabilidade']})"
    return resposta

def detectar_produto_especifico(pergunta: str, produtos: list):
    pergunta_lower = pergunta.lower().replace(",", " ").replace("/", " ")
    aliases = {
        "lci": "LCI/LCA", "lca": "LCI/LCA", "LCI": "LCI/LCA", "LCA": "LCI/LCA",
        "cdb": "CDB Liquidez Diária", "tesouro selic": "Tesouro Selic",
        "tesouro": "Tesouro Selic", "selic": "Tesouro Selic",
        "fundo multimercado": "Fundo Multimercado", "multimercado": "Fundo Multimercado",
        "fundo de ações": "Fundo de Ações", "acoes": "Fundo de Ações", "ações": "Fundo de Ações"
    }
    for alias, nome_real in aliases.items():
        if re.search(rf'\b{alias}\b', pergunta_lower):
            return next((p for p in produtos if nome_real.lower() in p["nome"].lower()), None)
    for produto in produtos:
        nome = produto["nome"].lower()
        if nome in pergunta_lower:
            return produto
        for palavra in nome.split():
            if len(palavra) >= 3 and re.search(rf'\b{palavra}\b', pergunta_lower):
                return produto
    return None

# =============================
# SIMULAÇÃO DE INVESTIMENTO
# =============================
def simular_investimento(valor_inicial, taxa_mensal, meses, aporte_mensal=0):

    montante = valor_inicial
    total_aportado = valor_inicial
    for _ in range(meses):
        montante = montante * (1 + taxa_mensal) + aporte_mensal
        total_aportado += aporte_mensal
    rendimento = montante - total_aportado
    return {
        "montante": montante,
        "total_aportado": total_aportado,
        "rendimento": rendimento
    }

def executar_simulacao(pergunta, perfil, produtos, produto_contexto=None, valor_contexto=None, aporte_contexto=None, meses_contexto=None):
    
    valor = None
    meses = None

    valor_extraido, meses_extraido, aporte_mensal = extrair_parametros_simulacao(pergunta)

    continuidade = any(p in pergunta.lower() for p in ["e se", "e", "agora", "mais", "com isso"])
    indica_aporte = any(p in pergunta.lower() for p in ["aporte", "por mês", "por mes", "mensal", "todo mês", "todo mes"])

    if valor_extraido is not None and not indica_aporte:
        valor = valor_extraido
    elif continuidade and valor_contexto is not None:
        valor = valor_contexto
    elif valor_contexto is not None and not indica_aporte:
        valor = valor_contexto
    else:
        valor, _ = definir_parametros_default(perfil, None, None)

    if aporte_mensal is not None:
        aporte = aporte_mensal
    elif aporte_contexto is not None:
        aporte = aporte_contexto
    else:
        aporte = 0

    meses = meses_extraido if meses_extraido is not None else meses_contexto

    if valor is None and valor_contexto is None:
        valor, _ = definir_parametros_default(perfil, valor, meses)
    if meses is None:
        _, meses = definir_parametros_default(perfil, valor, meses)

    produto_especifico = detectar_produto_especifico(pergunta, produtos)

    if produto_especifico is None and produto_contexto:
        produto_especifico = next((p for p in produtos if produto_contexto.lower() in p["nome"].lower()), None)

    if produto_especifico:
        produtos_filtrados = [produto_especifico]
    elif produto_contexto:
        produtos_filtrados = [p for p in produtos if produto_contexto.lower() in p["nome"].lower()]
    else:
        produtos_filtrados = produtos

    criterio = definir_criterio_ordenacao(pergunta)
    resultados = []

    for p in produtos_filtrados:
        taxa = p.get("taxa_simulada_mes", 0)
        resultado = simular_investimento(valor, taxa, meses, aporte)
        resultados.append({
            "nome": p["nome"],
            "montante": resultado["montante"],
            "total_aportado": resultado["total_aportado"],
            "rendimento": resultado["rendimento"],
            "rentabilidade": (resultado["rendimento"] / resultado["total_aportado"] if resultado["total_aportado"] > 0 else 0),
            "risco": p.get("risco", "medio")
        })

    resposta = f"📈 Simulação de rendimento em {meses} meses:\n"
    resposta += f"\n💰 Valor inicial: R$ {valor:.2f}"
    resposta += f"\n💸 Aporte mensal: R$ {aporte:.2f}\n"

    if len(resultados) == 1:
        r = resultados[0]
        resposta += f"\n📊 Produto: {r['nome']}"
        resposta += f"\n- Rentabilidade: {r['rentabilidade']*100:.2f}%"
        resposta += f"\n- Rendimento: R$ {r['rendimento']:.2f}"
        resposta += f"\n- Montante final: R$ {r['montante']:.2f}"
    else:
        if criterio == "rentabilidade":
            resultados.sort(key=lambda x: x["rentabilidade"], reverse=True)
            resposta += "\n\n🏆 Ranking por rentabilidade:\n"
        elif criterio == "montante":
            resultados.sort(key=lambda x: x["montante"], reverse=True)
            resposta += "\n\n🏆 Ranking por valor final:\n"
        elif criterio == "risco":
            ordem_risco = {"baixo": 1, "medio": 2, "alto": 3}
            resultados.sort(key=lambda x: ordem_risco.get(x["risco"], 2))
            resposta += "\n\n🛡️ Ranking por risco (menor → maior):\n"

        for i, r in enumerate(resultados, start=1):
            resposta += f"\n{i}º {r['nome']}"
            resposta += f"\n- Rentabilidade: {r['rentabilidade']*100:.2f}%"
            resposta += f"\n- Rendimento: R$ {r['rendimento']:.2f}"
            resposta += f"\n- Montante final: R$ {r['montante']:.2f}\n"
        melhor = resultados[0]
        resposta += f"\n🏅 Melhor opção: {melhor['nome']}"

    resposta += "\n\n⚠️ Valores simulados são estimativas ilustrativas. Lembre-se que na maioria dos investimentos incidem IR (Imposto de Renda) e taxa de custódia (espécie de aluguel pelo armazenamento dos ativos), o que pode impactar a rentabilidade do investimento."

    return {
        "resposta": resposta,
        "valor": valor,
        "meses": meses,
        "aporte": aporte,
        "produto": produto_especifico["nome"] if produto_especifico else None
    }

# =============================
# MELHORAR RESPOSTA COM LLM
# =============================
def melhorar_resposta_com_llm(texto, perfil, produtos=None):
    resposta = texto
    prompt = f"""
Você é o FinAssist, um agente financeiro inteligente, consultivo e educativo.

Seu objetivo é ajudar o cliente a entender sua situação financeira, melhorar seus hábitos e tomar decisões seguras relacionadas ao controle de gastos e ao planejamento financeiro.

Você deve utilizar exclusivamente as informações fornecidas sobre o cliente(transações, perfil e histórico).

REGRAS IMPORTANTES:
- Preserve **rigorosamente** todos os números, valores e unidades de tempo da resposta original.
- **NUNCA** adicione "ao ano", "ao mês", "após X meses" se não estiver no original.
- Responda em PT-BR e use R$
- **Sempre use "R$" (com cifrão) antes de qualquer valor monetário. Exemplo: "R$ 500,00".**
- Use ponto para separar milhares e vírgula para decimais (padrão brasileiro).
- Não invente dados, produtos ou informações do cliente.
- Não faça promessas de rentabilidade
- Você só pode mencionar produtos que estão na lista abaixo
- Sempre considere o perfil do cliente antes de sugerir investimentos
- Não crie, invente ou generalize produtos
- Mantenha o tom levemente informal, mas profissional, conforme os exemplos de interação fornecidos.

**EXEMPLOS DE TOM:**
- Confirmação: "Entendi! Vou analisar seus dados e te trazer uma simulação personalizada."
- Explicação: "Notei que seu maior gasto é com moradia, representando uma parcela importante do orçamento."
- Encerramento: "Se precisar de mais detalhes ou quiser explorar outras opções, estou aqui para ajudar!"


PERFIL:
{json.dumps(perfil, indent=2, ensure_ascii=False)}

PRODUTOS DISPONÍVEIS:
{json.dumps(produtos, indent=2, ensure_ascii=False) if produtos else "Não informado"}

RESPOSTA ORIGINAL:
{texto}

Reescreva a resposta original seguindo **estritamente** as regras acima, melhorando a clareza e fluidez sem alterar o conteúdo.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você formata respostas financeiras mantendo rigorosamente 'R$' antes de valores."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        resposta = response.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Erro na melhoria com LLM: {e}. Usando resposta original.")

    resposta =  re.sub(r'\bR\s+(?=\d)', 'R$ ', resposta)
    
    return resposta

# =============================
# FALLBACK COM LLM
# =============================
def responder_com_llm(pergunta, perfil, transacoes, produtos, historico):

    contexto = get_system_prompt(
        perfil=perfil,
        transacoes=transacoes.tail(10).to_dict(orient="records"),
        produtos=produtos,
        historico=historico.tail(5).to_string(index=False)
    )

    try:    
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": contexto},
                {"role": "user", "content": pergunta}
            ],
            temperature=0.0
        )
        resposta = response.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Erro na melhoria com LLM: {e}. Usando resposta original.")

    resposta =  re.sub(r'\bR\s+(?=\d)', 'R$ ', resposta)
    
    return resposta

# =============================
# FUNÇÃO PRINCIPAL
# =============================
def gerar_resposta(pergunta, transacoes, perfil, produtos, historico, mensagens, produto_contexto=None, valor_contexto=None, aporte_contexto=None, meses_contexto=None):
    
    intencao = classificar_intencao(pergunta)

    print("INTENÇÃO DETECTADA:", intencao)

    if intencao == "analise_gastos":
        resposta = analisar_gastos(transacoes)
        return melhorar_resposta_com_llm(resposta, perfil)
    
    elif intencao == "informacao_produto":
        return responder_informacao_produto(pergunta, produtos)

    elif intencao == "recomendacao":
        resposta = recomendar_investimentos(perfil, produtos)
        return melhorar_resposta_com_llm(resposta, perfil, produtos)
    
    elif intencao == "simulacao":
        resultado = executar_simulacao(
            pergunta, perfil, produtos,
            produto_contexto, valor_contexto, aporte_contexto, meses_contexto
        )
        resposta_melhorada = melhorar_resposta_com_llm(resultado["resposta"], perfil, produtos)
        return {
            "resposta": resposta_melhorada,
            "valor": resultado["valor"],
            "meses": resultado["meses"],
            "aporte": resultado["aporte"],
            "produto": resultado["produto"]
        }

    else:
        return responder_com_llm(pergunta, perfil, transacoes, produtos, historico)