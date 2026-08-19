# 📘 MangaSearch

Centralizador de pesquisa e comparação de preços para mangás físicos.

## 👥 Integrantes do Grupo

Alessandra Leite
Guilherme Caíque Rikaczewski
Maria Eduarda Senff de Souza

## 📌 Resumo da Automação Proposta

O MangaSearch é uma plataforma web que centraliza a pesquisa de mangás físicos disponíveis em diferentes lojas e marketplaces. O sistema automatiza a coleta de dados de múltiplas fontes — sites de venda, aplicativos de usados e scanlators — eliminando a necessidade do usuário visitar vários sites manualmente para encontrar um título.

**Problema:** Não existem plataformas centralizadas para aquisição de mangás físicos, tornando a pesquisa extensa, trabalhosa e frustrante.

**Solução:** Uma interface web onde o usuário busca pelo nome do mangá e o servidor realiza a varredura automatizada de anúncios e preços, retornando ofertas organizadas, filtráveis e ordenáveis em um só lugar.

### Funcionalidades previstas

*   🔍 Pesquisa de mangás por nome
*   🏷️ Catalogação por categoria (online / usado / novo)
*   💰 Comparação de preços e média de valores
*   ⭐ Avaliação do vendedor
*   🔗 Redirecionamento direto para o anúncio
*   📖 Link para leitura online (quando disponível)

## 🛠️ Tecnologias e Ferramentas Utilizadas

| Camada | Tecnologia |
| :--- | :--- |
| Back-end | Python + Flask |
| Automação/Web Scraping | Selenium / Playwright |
| Front-end | JavaScript + React |
| Versionamento | Git / GitHub |
| Prototipação | Figma |

## ⚙️ Instruções de Instalação, Dependências e Execução

### 📋 Pré-requisitos

Python 3.10+
Node.js 18+
npm ou yarn
Git
Navegador Chrome/Chromium (para o Selenium/Playwright)

### 📦 Clonando o repositório

```bash
git clone https://github.com/seu-usuario/mangasearch.git
cd mangasearch
```

### 🐍 Back-end (Flask)

1.  Acesse a pasta do backend:
    ```bash
    cd backend
    ```

2.  Crie e ative o ambiente virtual:
    ```bash
    # Linux/macOS
    python -m venv venv
    source venv/bin/activate

    # Windows
    python -m venv venv
    venv\Scripts\activate
    ```

3.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```

4.  Execute o servidor:
    ```bash
    uvicorn backend.src.main:app --reload
    ```

### 🌐 Front-end (React)

1.  Acesse a pasta do frontend:
    ```bash
    cd frontend
    ```

2.  Instale as dependências:
    ```bash
    npm install
    ```

3.  Execute em modo de desenvolvimento:
    ```bash
    npm start
    ```

### 🧪 Executando os testes de scraping

```bash
cd backend
python -m pytest tests/
```