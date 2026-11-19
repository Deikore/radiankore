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
bibliotecas, como hace CI. En Ubuntu 24.04 y las versiones de Debian que ofrecen
el paquete `libxmlsec1-openssl`:

```bash
sudo apt-get install build-essential pkg-config libxml2-dev libxslt1-dev libxmlsec1-dev libxmlsec1-openssl
uv sync --locked --no-binary-package lxml --no-binary-package xmlsec
```

En Ubuntu 26.04 el backend OpenSSL de XMLSec se denomina
`libxmlsec1-openssl1`. CI fija explícitamente la imagen `ubuntu-26.04` y usa:

```bash
sudo apt-get update
sudo apt-get install -y build-essential pkg-config libxml2-dev libxslt1-dev libxmlsec1-dev libxmlsec1-openssl1
uv sync --locked --no-binary-package lxml --no-binary-package xmlsec
```

El nombre del paquete nativo depende de la distribución; no cambia las
dependencias Python ni la necesidad de compilar `lxml` y `xmlsec` contra una
versión compatible de `libxml2`. Read the Docs conserva su entorno Ubuntu 24.04.
