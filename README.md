   # ConciliaSII

   PoC de SDLC AI-native: una app que concilia el Registro de Compras del SII contra el libro de compras de un ERP.

   Estado: en construcción.

Stack: Python + Streamlit

## Documentación

- [PRD](docs/PRD.md): problema, alcance, requisitos y reglas de negocio.
- [Historias de usuario](docs/historias.md): 15 historias con criterios de aceptación.
- [Arquitectura](docs/arquitectura.md): diseño, flujo, modelo de datos y capas de entrega.
- [ADRs](docs/adr/README.md): decisiones de arquitectura.

## Cómo contribuir

¿Quieres aportar a ConciliaSII? ¡Bienvenido/a! Al estar en construcción, toda ayuda suma. Sigue estos pasos:

1. Haz un *fork* del repositorio y clónalo en tu máquina:
   ```bash
   git clone https://github.com/<tu-usuario>/conciliasii.git
   cd conciliasii
   ```
2. Crea una rama descriptiva para tu aporte:
   ```bash
   git checkout -b mi-aporte
   ```
3. Prepara el entorno (Python + Streamlit) e instala las dependencias cuando existan:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # en Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. Realiza tus cambios con *commits* claros y pequeños. Si corresponde, ejecuta la app con `streamlit run app.py` para verificar que todo funciona.
5. Si modificas el flujo de trabajo, registra una entrada en `Bitacora.md` siguiendo el formato existente.
6. Sube tu rama y abre un *pull request* describiendo el cambio y su motivación:
   ```bash
   git push -u origin mi-aporte
   ```

Para dudas o propuestas más grandes, abre primero un *issue* para conversarlo.