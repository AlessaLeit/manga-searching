# 📘 MangaSearch

Centralizador de pesquisa e comparação de preços para mangás físicos.

Uma busca só consulta várias lojas em paralelo ao trabalho manual que o usuário
faria site a site, e devolve as ofertas reunidas, ordenadas da mais barata para
a mais cara, com link e capa de cada uma.

## 👥 Integrantes do Grupo

Alessandra Leite
Guilherme Caíque Rikaczewski
Maria Eduarda Senff de Souza

## 📌 O problema

Não existe plataforma centralizada para comprar mangás físicos no Brasil. Quem
procura um volume específico abre Estante Virtual, Amazon, OLX e Enjoei um por
um, compara preços na mão e ainda precisa julgar se o anúncio é novo ou usado.

O MangaSearch automatiza essa varredura: o usuário busca pelo nome, o servidor
consulta as fontes e devolve tudo em um lugar só, filtrável por condição.

## 🔍 Fontes consultadas

Cada site exigiu uma estratégia diferente, conforme o obstáculo encontrado:

| Fonte | Como é lida | O que entrega |
| :--- | :--- | :--- |
| **Estante Virtual** | HTTP + BeautifulSoup | novos e usados, com condição filtrada pela própria loja |
| **MangaDex** | API pública JSON | leitura online (sem preço) |
| **Bing Shopping** | Playwright | ofertas de lojas grandes (Amazon, Magazine Luiza) |
| **Enjoei** | Playwright | anúncios de usados entre pessoas |
| **OLX** | Playwright | classificados, com a condição declarada pelo anunciante |
| **Google Shopping** | Playwright | *desligada* — veja Limitações |

Fonte que falha não derruba a busca: ela é reportada em `fontes_com_falha` e as
demais respondem normalmente.

## 🛠️ Tecnologias

| Camada | Tecnologia |
| :--- | :--- |
| API | Python + FastAPI + Uvicorn |
| Validação | Pydantic v2 |
| Scraping (HTML) | Requests + BeautifulSoup + lxml |
| Scraping (JavaScript) | Playwright (Chromium headless) |
| Testes | pytest |
| Container | Docker + Docker Compose |
| CI | GitHub Actions |
| Versionamento | Git / GitHub |

## ⚙️ Instalação e execução

### Pré-requisitos

- Python 3.12+
- Git

Node.js **não** é necessário: o frontend não vive neste repositório.

### 1. Clonar e entrar no projeto

```bash
git clone https://github.com/AlessaLeit/manga-searching.git
```

```bash
cd manga-searching
```

### 2. Criar o ambiente virtual

```bash
python -m venv .venv
```

Ative — Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Instalar o navegador do Playwright

Necessário para Bing, Enjoei e OLX. Sem ele, essas três fontes reportam falha e
só Estante Virtual e MangaDex respondem.

```bash
python -m playwright install chromium
```

### 5. Configurar o ambiente

```bash
cp .env.example .env
```

### 6. Subir o servidor

> ⚠️ **Rode sempre a partir da raiz do repositório**, não de dentro de
> `backend/`. Os imports do projeto são absolutos (`backend.src.*`); executar de
> outro diretório falha com `ModuleNotFoundError: No module named 'backend'`.

```bash
uvicorn backend.src.main:app --reload
```

A API sobe em <http://127.0.0.1:8000>. A documentação interativa fica em
<http://127.0.0.1:8000/docs> — é a forma mais simples de testar a busca.

## 🔧 Configuração (.env)

| Variável | Padrão | Para que serve |
| :--- | :--- | :--- |
| `BING_SHOPPING_ENABLED` | `1` | Liga a fonte Bing Shopping |
| `ENJOEI_ENABLED` | `1` | Liga a fonte Enjoei |
| `OLX_ENABLED` | `1` | Liga a fonte OLX |
| `GOOGLE_SHOPPING_ENABLED` | `0` | Liga o Google Shopping (hoje bloqueado) |
| `CORS_ORIGINS` | `localhost:5173,3000,8080` | Origens do front autorizadas; `*` libera todas |
| `SEARCH_TIMEOUT_SECONDS` | `45` | Teto da busca inteira antes de responder 504 |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` ou `ERROR` |

As fontes que usam navegador custam segundos por busca. Desligá-las (`=0`)
deixa a resposta mais rápida, com menos ofertas.

## 🔌 API

### `GET /search/`

| Parâmetro | Obrigatório | Descrição |
| :--- | :--- | :--- |
| `search_expression` | sim | Nome do mangá. De 2 a 60 caracteres úteis |
| `filters` | não | `novo`, `usado` ou `online`. Repetível; sem ele, busca todas |

```bash
curl "http://127.0.0.1:8000/search/?search_expression=berserk&filters=usado"
```

Resposta:

```json
{
  "manga": "berserk",
  "total_opcoes": 40,
  "preco_minimo": 16.52,
  "preco_medio": 40.98,
  "fontes_consultadas": ["Estante Virtual", "MangaDex", "Bing Shopping", "Enjoei", "OLX"],
  "fontes_com_falha": [],
  "opcoes": [
    {
      "nome": "Berserk Vol. 1",
      "condicao": "usado",
      "fonte": "Estante Virtual",
      "loja": "Estante Virtual",
      "preco": 32.0,
      "link": "https://www.estantevirtual.com.br/livro/berserk-vol-1-...",
      "imagem": "https://static.estantevirtual.com.br/book/00/...",
      "autor": "Kentaro Miura",
      "ano": 2019,
      "ofertas": 8
    }
  ]
}
```

As opções vêm da mais barata para a mais cara, com as de leitura online por
último (não têm preço). Os campos `preco`, `link`, `imagem`, `autor`, `ano` e
`ofertas` podem vir `null` — cada fonte expõe um conjunto diferente de dados, e
o front precisa tratar ausência em todos eles.

`fonte` e `loja` respondem perguntas diferentes e não devem ser confundidos:

| | `fonte` | `loja` |
| :--- | :--- | :--- |
| Responde | de onde a oferta veio | quem está vendendo |
| Valores | sempre um dos nomes da tabela de fontes | varia muito |
| Exemplo | `"Bing Shopping"` | `"Amazon BR"` |
| Exemplo | `"Enjoei"` | `"panini"` (um vendedor, apesar do nome) |
| Exemplo | `"OLX"` | `"OLX"` (classificado não tem loja) |

Use `fonte` para agrupar, filtrar ou mostrar um selo de origem no card. `loja`
é texto livre vindo do anúncio e serve só para exibir.

### Códigos de resposta

| Código | Quando acontece |
| :--- | :--- |
| `200` | Busca concluída. Inclui o caso de não achar nada (`total_opcoes: 0`) |
| `422` | Entrada inválida: pesquisa curta demais, sem letras, filtro desconhecido |
| `502` | Nenhuma fonte respondeu — problema de conexão com as lojas |
| `504` | A busca passou de `SEARCH_TIMEOUT_SECONDS` |
| `500` | Erro inesperado. O detalhe vai para o log, nunca para a resposta |

Todo erro sai no mesmo formato, com mensagem em português pronta para exibir:

```json
{"detail": "A pesquisa precisa conter letras ou números.", "errors": 1}
```

### `GET /health`

Responde `{"status": "ok"}`. Serve para checar se a API está no ar antes de
culpar a rede.

## 🧪 Testes

Há duas suítes, com propósitos diferentes.

### Suíte padrão (offline)

Da raiz do repositório, com o ambiente ativado:

```bash
pytest
```

São 62 testes que não sobem navegador nem acessam a internet. Rodam em
segundos, não quebram quando uma loja muda de layout, e é esta que o CI executa
a cada push. Protegem a lógica: conversão de preço, relevância, condição,
contrato das fontes, validação e erros da API.

### Teste de fumaça (acessa os sites reais)

```bash
pytest -m fumaca -v
```

Leva cerca de um minuto e responde a pergunta que a suíte offline não alcança:
**as fontes ainda estão trazendo resultado dos sites de verdade?**

A distinção importa. Quando a Enjoei parou de retornar — por uma espera que
exigia visibilidade de um elemento que nunca ficava visível —, os testes
offline seguiram todos verdes, porque a lógica estava correta; a fonte apenas
devolvia lista vazia, sem erro, e ainda aparecia em `fontes_consultadas`. O
teste de fumaça acusa exatamente esse caso.

Ele verifica, por fonte: se ainda vêm resultados, se nome e link estão
preenchidos, se os preços convertem para valores plausíveis e se as capas não
são o placeholder de carregamento. Mais a busca completa ponta a ponta e a
garantia de que busca sem sentido não inventa resultado.

> Falha aqui raramente é bug de lógica — é sinal de que uma fonte precisa de
> conserto. Mas **rode de novo antes de concluir**: os sites limitam acesso
> repetido, e execuções em sequência produzem alarme falso. Por isso este teste
> fica fora do CI.

## 🐳 Docker

```bash
docker compose up --build
```

A API fica em <http://localhost:8000>, lendo as variáveis do `.env`.

> O Dockerfile não instala o Chromium do Playwright. No container, as fontes que
> dependem de navegador (Bing, Enjoei, OLX) reportam falha; Estante Virtual e
> MangaDex seguem funcionando.

## 📁 Estrutura

```
backend/src/
├── main.py              # Aplicação FastAPI, CORS, /health
├── core/
│   ├── errors.py        # Tratadores centralizados (422/500/502/504)
│   └── masks.py         # Normalização da entrada antes da validação
├── routes/search.py     # Endpoint /search/
├── schemas/search.py    # Validação da entrada e formato da resposta
└── scraper/
    ├── scraper.py       # Orquestra as fontes e consolida
    ├── normalizer.py    # Relevância, preço, deduplicação, ordenação
    ├── navegador.py     # Chromium compartilhado pelas fontes com JS
    ├── models.py        # Produto, ResultadoBusca, Condicao
    └── sources/         # Uma fonte por arquivo
backend/tests/           # Testes da rota e das fontes
```

### Adicionar uma fonte nova

Crie um arquivo em `sources/` expondo `NOME` e
`buscar(query, condicoes, limite) -> list[dict]`, e registre-o em `FONTES`
(`sources/__init__.py`). O orquestrador e o normalizador não mudam.

Opcionalmente, a fonte pode expor `habilitado()`, para ser ligada por variável
de ambiente, e `USA_QUERY_LIMPA = True`, para receber o termo digitado pelo
usuário em vez da expressão enriquecida enviada às lojas.

## ⚠️ Limitações conhecidas

- **Google Shopping está bloqueado.** A fonte está implementada e testada, mas o
  Google responde com página de verificação anti-robô (CAPTCHA). Fica desligada
  por padrão e, se ligada, apenas reporta falha. Não há contorno previsto.
- **Não há cache.** Toda busca consulta as lojas de novo, inclusive buscas
  repetidas. Uma busca completa leva de 10 a 15 segundos.
- **As fontes são consultadas em sequência**, não em paralelo: o tempo total é a
  soma delas.
- **O campo `loja` é texto livre** e varia de significado conforme a fonte: o
  site (`"Estante Virtual"`), a loja real (`"Amazon BR"`) ou o apelido do
  vendedor (`"pri"`, no Enjoei). Para saber a origem da oferta use `fonte`,
  que é sempre um dos nomes da tabela de fontes.
- **Alguns links do Bing passam por redirecionador de anúncios**
  (`ad.doubleclick.net`) em vez de apontarem direto para a loja. Eles funcionam,
  mas não são links limpos.
