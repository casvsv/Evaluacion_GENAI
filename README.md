Análisis de la Seguridad de Código Fuente Desarrollado con Asistencia GenAI

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![OWASP](https://img.shields.io/badge/OWASP-Top_10:_2025-red.svg)
![CVSS](https://img.shields.io/badge/CVSS-v4.0-purple.svg)

Este repositorio contiene los artefactos de software generados y auditados como parte del Trabajo de Fin de Máster (TFM) del Máster Universitario en Ciberseguridad de la Universidad Internacional de La Rioja (UNIR).
El proyecto evalúa empíricamente la seguridad por defecto del código generado por tres de los Modelos de Lenguaje Grande (LLMs) más extendidos de la industria bajo condiciones zero-shot.
⚠️ Advertencia de Seguridad
> **¡ATENCIÓN!** El código fuente contenido en las carpetas `ChatGPT/`, `Claude/` y `Gemini/` fue generado por Inteligencia Artificial y **contiene vulnerabilidades críticas intencionales y no parcheadas** (como Inyección SQL, IDOR, RCE por subida de archivos y configuraciones inseguras).
>
> Este repositorio tiene fines estrictamente académicos y de investigación. **BAJO NINGUNA CIRCUNSTANCIA** este código debe ser utilizado, copiado o desplegado en entornos de producción.
🗂 Estructura del Repositorio
El repositorio está organizado por modelo de Inteligencia Artificial evaluado. Dentro de cada modelo, se encuentran los tres escenarios funcionales (módulos) desarrollados mediante el micro-framework Flask:
```text
📦 TFM-GenAI-Security-Audit
 ┣ 📂 ChatGPT (GPT-4o)
 ┃ ┣ 📂 1_Modulo_Auth       # Autenticación, registro y recuperación de sesión
 ┃ ┣ 📂 2_API_CRUD          # API REST transaccional para gestión de empleados
 ┃ ┗ 📂 3_File_Upload       # Módulo de carga y procesamiento de archivos
 ┣ 📂 Claude (3.5 Sonnet)
 ┃ ┣ 📂 1_Modulo_Auth
 ┃ ┣ 📂 2_API_CRUD
 ┃ ┗ 📂 3_File_Upload
 ┣ 📂 Gemini (3.1 Pro)
 ┃ ┣ 📂 1_Modulo_Auth
 ┃ ┣ 📂 2_API_CRUD
 ┃ ┗ 📂 3_File_Upload
 ┣ 📂 Guia_Mitigacion_PoC   # (Opcional) Fragmentos de código fortificado
 ┣ 📜 requirements.txt      # Dependencias globales del proyecto
 ┗ 📜 README.md
```
🔬 Metodología de Auditoría
Cada módulo en este repositorio fue sometido a un análisis de seguridad tridimensional:
Análisis Estático (SAST): Ejecutado con Semgrep para detectar malas prácticas sintácticas, secretos embebidos y flujos de datos contaminados.
Análisis Dinámico (DAST): Ejecutado con OWASP ZAP sobre los entornos Flask locales para validar cabeceras de seguridad, inyecciones y fallos de configuración.
Pruebas de Penetración Manuales: Auditoría de lógica de negocio para identificar fallos arquitectónicos (IDOR, BOLA y bypass de autenticación) que evaden el escaneo automatizado.
Los hallazgos fueron clasificados taxonómicamente mediante el OWASP Top 10:2025 y CWE, y puntuados utilizando el sistema CVSS v4.0.
🚀 Despliegue Local (Entorno de Laboratorio)
Si desea levantar alguno de los módulos para replicar la auditoría, se recomienda encarecidamente hacerlo dentro de un entorno virtual aislado (`venv`).
Clonar el repositorio:
```bash
   git clone https://github.com/tu-usuario/TFM-GenAI-Security-Audit.git
   cd TFM-GenAI-Security-Audit
   ```
Crear y activar el entorno virtual:
```bash
   python -m venv venv
   # En Windows: venv\Scripts\activate
   # En Linux/Mac: source venv/bin/activate
   ```
Instalar las dependencias requeridas:
```bash
   pip install -r requirements.txt
   ```
Navegar al módulo deseado e iniciar el servidor Flask:
```bash
   cd Gemini/2_API_CRUD
   python app.py
   ```
👥 Autores y Equipo de Investigación

Trabajo de investigación empírica desarrollado por:
César Augusto Salazar Valdez — Auditoría y análisis de Gemini
Jonathan Gonzalo Diaz Angulo — Auditoría y análisis de ChatGPT
Oscar Dario Lopez Jimenez — Auditoría y análisis de Claude
Universidad Internacional de La Rioja (UNIR) — 2026.
