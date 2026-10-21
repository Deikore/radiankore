# Mantener la documentación

El sitio usa Sphinx, Markdown mediante MyST y el tema Furo. Las dependencias de
compilación están fijadas en `docs/requirements.txt`, separadas de las dependencias
de ejecución de la librería. La configuración lee la versión de `pyproject.toml`
sin importar `radiankore`: no requiere certificados, DIAN ni bibliotecas de firma.

## Compilar localmente

Desde la raíz del repositorio:

```bash
uv run --no-project --with-requirements docs/requirements.txt sphinx-build -W --keep-going -b html docs docs/_build/html
```

Abre `docs/_build/html/index.html` para revisar la navegación, los ejemplos y los
enlaces. `-W` trata los avisos como errores; CI usa el mismo comando. El contenido
original en `docs/references/` está excluido del sitio, con enlaces al repositorio
para consultar esas fuentes sin copiar sus documentos al HTML generado.

## Activar Read the Docs

1. Accede a [Read the Docs](https://readthedocs.org/) con la cuenta que administrará
   el proyecto y conecta GitHub.
2. Importa `Deikore/radiankore` y usa `radiankore` como slug, si está disponible.
3. Mantén `.readthedocs.yaml` como archivo de configuración y selecciona español
   como idioma del proyecto. Activa la rama predeterminada como `latest`.
4. Ejecuta el primer build y verifica `https://radiankore.readthedocs.io/`.
5. Activa las etiquetas que quieras publicar como documentación versionada.

El registro y la vinculación de la cuenta se realizan en Read the Docs; los archivos
del repositorio no crean automáticamente un proyecto remoto. Si eliges otro slug,
actualiza los enlaces y badges del README, `project.urls.Documentation` y el valor
predeterminado de `html_baseurl` en `docs/conf.py`.

Los badges consultan los servicios reales: CI, Read the Docs y PyPI. Pueden mostrar
estado desconocido hasta que el proyecto tenga su primer build o publicación; no
contienen resultados de pruebas ni porcentajes de cobertura fijados manualmente.

Consulta la [configuración oficial de Read the Docs](https://docs.readthedocs.com/platform/stable/config-file/v2.html)
para las opciones del entorno y la [guía de Markdown de Sphinx](https://www.sphinx-doc.org/en/master/usage/markdown.html)
para ampliar el contenido.
