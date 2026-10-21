# Instalación

Requiere Python >=3.13. Para instalar la distribución publicada en PyPI:

```bash
pip install radiankore
# O para añadirla a un proyecto con uv:
uv add radiankore
```

Para contribuir desde una copia del repositorio, usa [uv](https://docs.astral.sh/uv/):

```bash
uv sync --locked
```

`.python-version` selecciona Python 3.13. `uv.lock` fija dependencias de ejecución
y desarrollo. Consérvalo en Git; `--locked` detecta divergencias con el manifiesto.

La firma utiliza `cryptography`, `lxml` y `xmlsec`; el transporte utiliza HTTPX.
`lxml` y `xmlsec` deben usar versiones compatibles de `libxml2`. Si no hay wheels
compatibles, instala las dependencias nativas y compila ambos contra las mismas
bibliotecas, como hace CI. En Debian/Ubuntu:

```bash
sudo apt-get install build-essential pkg-config libxml2-dev libxslt1-dev libxmlsec1-dev libxmlsec1-openssl
uv sync --locked --no-binary-package lxml --no-binary-package xmlsec
```
