# FinAssist – Assistente Financeiro Inteligente

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat&logo=python)
![OpenAI](https://img.shields.io/badge/OpenAI-gpt--4o--mini-74aa9c?style=flat&logo=openai)

O **FinAssist** é um assistente financeiro conversacional que ajuda clientes a entender sua situação financeira, controlar gastos e tomar decisões de investimento personalizadas. Utilizando dados mockados (perfil, transações, produtos financeiros) e inteligência artificial, o agente fornece respostas contextualizadas, seguras e educativas.

Desenvolvido como projeto final do Lab de Agentes Financeiros com IA Generativa — DIO + Bradesco ("BIA do Futuro").

---

## 📌 Funcionalidades

- **Análise de Gastos** – Identifica a categoria com maior despesa e apresenta um resumo financeiro detalhado.
- **Recomendação de Investimentos** – Sugere produtos alinhados ao perfil de risco do cliente (conservador, moderado, arrojado).
- **Simulação de Rentabilidade** – Calcula o rendimento estimado com juros compostos, considerando valor inicial, aporte mensal e prazo.
- **Informações de Produtos** – Exibe detalhes de produtos financeiros como rentabilidade, risco e aporte mínimo.
- **Interação por Voz (Streamlit)** – Permite captura e transcrição de áudio para consultas sem digitação.
- **Fallback Inteligente** – Para perguntas fora do escopo, o LLM responde com base no perfil e histórico do cliente, mantendo a conversa fluida.

---

## 🧩 Arquitetura Resumida

A aplicação segue uma arquitetura híbrida:

1. **Interface Streamlit** (`app.py`) – Gerencia o chat, estado da sessão e entrada de texto/áudio.
2. **Backend Determinístico** (`agente.py`) – Classifica a intenção, extrai parâmetros e realiza cálculos exatos.
3. **Base de Conhecimento** – Arquivos JSON/CSV com dados do cliente e produtos financeiros.
4. **LLM (OpenAI)** – Usado para:
   - Polir respostas geradas pelo backend (preservando números e unidades).
   - Responder perguntas não mapeadas (fallback), com contexto enriquecido.

O fluxo completo está documentado em [`docs/01-documentacao-agente.md`](docs/01-documentacao-agente.md).

---

## 🚀 Pré-requisitos

- Python 3.10 ou superior
- Conta na [OpenAI](https://platform.openai.com/) com acesso à API
- Chave de API da OpenAI (`OPENAI_API_KEY`)
- Ambiente virtual

---

## ⚙️ Instalação e Configuração

### 1. Clone o repositório
```bash
git clone https://github.com/berticamila/dio-lab-bia-do-futuro.git

```
### 2. Crie e ative um ambiente virtual
```bash
python -m venv venv
```
# Windows
```bash
venv\Scripts\activate
```
# macOS/Linux
```bash
source venv/bin/activate
```
### 3. Instale as dependências

```bash
pip install -r requirements.txt
```
### 4. Configure as variáveis de ambiente

Crie um arquivo .env na raiz do projeto com o seguinte conteúdo:

```bash
OPENAI_API_KEY=sua-chave-da-openai-aqui
```
## ▶️ Como Executar:

Com o ambiente virtual ativado e as dependências instaladas, execute:
```bash
streamlit run src/app.py
```
A interface será aberta no seu navegador padrão (geralmente http://localhost:8501).

## 🛡️ Segurança e Anti-Alucinação

O agente só responde com base nos dados fornecidos (perfil, transações, produtos).

Não inventa valores, produtos ou prazos.

A validação ocorre em duas camadas:

Determinística – Cálculos realizados exclusivamente sobre a base de conhecimento.

Prompt Restritivo – O LLM recebe instruções para não alterar números nem adicionar periodicidade indevida.

Quando os dados são insuficientes, o agente informa claramente a limitação.

## 📄 Licença

Este projeto é parte de um desafio educacional da DIO e não possui uma licença comercial definida. Sinta-se livre para estudar e adaptar conforme necessário.


## Evidência de Execução

![FinAssist Interface](assets/Captura%20de%20tela%20-%20FinAssist.png)