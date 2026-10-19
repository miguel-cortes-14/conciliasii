# ADR-0004 · Ruff como linter y formateador

- **Estado:** Aceptada
- **Fecha:** 2026-10-19

## Contexto

El proyecto se construye con apoyo de IA y necesita una forma rápida y automática de mantener el código consistente y detectar errores comunes, sin configurar varias herramientas.

## Decisión

Usar **ruff** como linter y formateador, configurado en `pyproject.toml`: `line-length = 100`, `target-version = "py311"` y reglas `E`, `F`, `I`, `B`, `UP`. Se instala desde `requirements-dev.txt` junto con `pytest`. Comandos de verificación:

```bash
ruff check .
ruff format --check .
```

## Alternativas consideradas

- **flake8 + isort + black.** Tres herramientas y tres configuraciones para cubrir lo mismo.
- **pylint.** Más completo pero lento y ruidoso para una PoC.
- **Sin linter.** Se pierde un control barato de calidad.

## Consecuencias

- Una sola herramienta, muy rápida y con una configuración mínima.
- Los comandos pueden correr localmente y en una integración continua futura.
- Las reglas son amplias pero no exhaustivas; se pueden ampliar más adelante.
- Ruff 0.16 también formatea los bloques `python` dentro de los `.md`; los ejemplos de código en la documentación deben respetar el formato (`ruff format .` los corrige).
