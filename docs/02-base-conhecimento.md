# Base de Conhecimento

## Dados Utilizados

Descreva se usou os arquivos da pasta `data`, por exemplo:

| Arquivo | Formato | Utilização no Agente |
|---------|---------|---------------------|
| `historico_atendimento.csv` | CSV | As últimas 5 interações são incluídas no prompt de fallback (responder_com_llm) para manter a continuidade da conversa e evitar repetições. |
| `perfil_investidor.json` | JSON | Fornece o perfil do cliente (nome, idade, renda, patrimônio, objetivo, perfil de risco, metas etc). Usado para personalizar recomendações, definir parâmetros padrão de simulação - default - (ex.: 30% do patrimônio como valor inicial) e orientar a seleção de produtos. |
| `produtos_financeiros.json` | JSON | Lista os produtos disponíveis com nome, categoria, risco, rentabilidade, taxa simulada mensal (taxa_simulada_mes), aporte mínimo e indicação. Essencial para simulações, recomendações e detecção de produto específico. |
| `transacoes.csv` | CSV | Contém entradas e saídas financeiras do cliente. Usado na função analisar_gastos para calcular totais, saldo e categoria de maior gasto. Também incluído no contexto do fallback para consultas genéricas. |

---

## Adaptações nos Dados

> Você modificou ou expandiu os dados mockados? Descreva aqui.

Modifiquei o arquivo produtos_financeiros.json adicionando a taxa simulada mensal (taxa_simulada_mes) para quando realizar cálculos de provável rentabilidade de investimentos (juros compostos), ou seja, a simulação (função simular_investimento) do possível motante gerado a partir de determinado tipo de investimento, baseado no tempo e no valor aplicado.

---

## Estratégia de Integração

### Como os dados são carregados?
> No arquivo app.py, a função carregar_dados() é decorada com @st.cache_data, executada uma vez por sessão e assim os dados são então passados como argumentos para a função gerar_resposta (e subsequentemente para executar_simulacao, analisar_gastos, etc.) em cada interação do usuário.

### Como os dados são usados no prompt?
> Os dados vão no system prompt? São consultados dinamicamente?
Os dados são utilizados de duas formas distintas:

Determinística (sem LLM)

Funções como executar_simulacao e analisar_gastos acessam diretamente os DataFrames e dicionários para calcular resultados.

A resposta é gerada programaticamente (string formatada) e depois, opcionalmente, refinada pelo LLM via melhorar_resposta_com_llm. Nesse refinamento, apenas o texto da resposta original é passado, juntamente com o perfil e a lista de produtos (para evitar alucinações).

Fallback com LLM (responder_com_llm)

Quando a pergunta não se encaixa nas intenções mapeadas, o LLM é acionado.

O system prompt é construído pela função get_system_prompt (definida em prompts.py), que injeta todos os dados disponíveis: perfil completo, últimas transações, lista de produtos e as últimas interações do histórico.

Isso permite que o modelo responda perguntas abertas com base no contexto real do cliente, mantendo a consistência e evitando alucinações.

---

## Exemplo de Contexto Montado

> Mostre um exemplo de como os dados são formatados para o agente.
Quando uma pergunta não cai no fallback a e estrutura do contexto enviado para a função melhorar_resposta_com_llm:

Você é o FinAssist, um agente financeiro inteligente, consultivo e educativo.
...


PERFIL:
{
  "nome": "João Silva",
  "idade": 34,
  "profissao": "Analista de Sistemas",
  "renda_mensal": 5000.0,
  "patrimonio_total": 10000.0,
  "objetivo_principal": "Construir reserva de emergência",
  "horizonte_tempo": "curto",
  "perfil": "moderado",
  "nao_aceita_risco_alto": true
}

PRODUTOS DISPONÍVEIS:
[
  {
    "nome": "Tesouro Selic",
    "categoria": "renda_fixa",
    "risco": "baixo",
    "rentabilidade": "100% da Selic",
    "taxa_simulada_mes": 0.0115,
    "aporte_minimo": 30.0,
    "indicado_para": "Reserva de emergência e iniciantes"
  },
  {
    "nome": "CDB Liquidez Diária",
    ...
  }
]

RESPOSTA ORIGINAL:
📈 Simulação de rendimento em 6 meses:

💰 Valor inicial: R$ 1.000,00
💸 Aporte mensal: R$ 0,00

📊 Produto: Tesouro Selic

- Rentabilidade: 7,10%
- Rendimento: R$ 71,01
- Montante final: R$ 1.071,01

⚠️  Valores simulados são estimativas ilustrativas. Lembre-se que na maioria dos investimentos incidem IR (Imposto de Renda) e taxa de custódia (espécie de aluguel pelo armazenamento dos ativos), o que pode impactar a rentabilidade do investimento.


Quando uma pergunta cai no fallback, o prompt de sistema enviado ao LLM contém um bloco como este (gerado por get_system_prompt):

Você é o FinAssist, um agente financeiro inteligente, consultivo e educativo.
...


DADOS DO CLIENTE:

PERFIL:
{
  "nome": "João Silva",
  "idade": 34,
  "profissao": "Analista de Sistemas",
  "renda_mensal": 5000.0,
  "patrimonio_total": 10000.0,
  "objetivo_principal": "Construir reserva de emergência",
  "horizonte_tempo": "curto",
  "perfil": "moderado",
  "nao_aceita_risco_alto": true
}

TRANSAÇÕES RECENTES:
[{'data': '2025-10-20', 'descricao': 'Academia', 'categoria': 'saude', 'valor': 99.0, 'tipo': 'saida'},
 {'data': '2025-10-15', 'descricao': 'Conta de Luz', 'categoria': 'moradia', 'valor': 180.0, 'tipo': 'saida'},
 {'data': '2025-10-12', 'descricao': 'Uber', 'categoria': 'transporte', 'valor': 45.0, 'tipo': 'saida'},
 {'data': '2025-10-10', 'descricao': 'Restaurante', 'categoria': 'alimentacao', 'valor': 120.0, 'tipo': 'saida'},
 {'data': '2025-10-07', 'descricao': 'Farmácia', 'categoria': 'saude', 'valor': 89.0, 'tipo': 'saida'}]

PRODUTOS DISPONÍVEIS:
[{"nome": "Tesouro Selic", "categoria": "renda_fixa", "risco": "baixo", "rentabilidade": "100% da Selic", "taxa_simulada_mes": 0.0115, ...}, ...]

HISTÓRICO:
      data       canal     tema          resumo                                       resolvido
2025-10-25  email   Atualização cadastral   Cliente atualizou e-mail e telefone     sim

...
