FROM python:3.12-slim


WORKDIR /code


COPY ./requirements.txt /code/requirements.txt


RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt


# Bing, Enjoei e OLX leem páginas montadas por JavaScript e precisam de um
# navegador de verdade. O pip instala só a biblioteca do Playwright; o binário
# do Chromium vem deste passo, e o `--with-deps` traz as bibliotecas de sistema
# que a imagem slim não tem.
#
# Sem isto as três fontes levantam PlaywrightIndisponivel e a busca responde
# apenas com Estante Virtual e MangaDex — foi o que aconteceu em produção.
RUN playwright install --with-deps chromium


COPY ./backend/src /code/backend/src

CMD ["uvicorn", "backend.src.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]