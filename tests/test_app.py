"""Abre o app.py sem navegador: pega erros de sintaxe e de execução da tela que os outros testes não cobrem."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from feedback_radar import config

APP = Path(__file__).parents[1] / "app.py"


def test_app_compila():
    # O AppTest não acusa erro de sintaxe, então compilamos o arquivo antes
    compile(APP.read_text(encoding="utf-8"), str(APP), "exec")


def test_app_abre_sem_erro(monkeypatch):
    monkeypatch.setattr(config, "LOGIN_DESATIVADO", True)
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not app.exception, [e.value for e in app.exception]
