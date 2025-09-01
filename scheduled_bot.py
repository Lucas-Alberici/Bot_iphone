name: Rodar Bot iPhone agendado

on:
  schedule:
    - cron: '0 09,21 * * *' # Executa todo dia às 12:00 e 21:00 UTC (ajuste o horário!)
  workflow_dispatch: # permite rodar manualmente também

jobs:
  run-bot:
    runs-on: ubuntu-latest

    steps:
      - name: Baixar código
        uses: actions/checkout@v3

      - name: Configurar Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Instalar dependências
        run: |
          python -m pip install --upgrade pip
          pip install python-telegram-bot

      - name: Rodar o bot
        env:
          TOKEN: ${{ secrets.TOKEN }}
        run: |
          python iphone_bot2.py
