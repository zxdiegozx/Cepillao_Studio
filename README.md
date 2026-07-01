# 🍦 Cepillao' Studio

> Motor científico de formulación de helados y gelato con interfaz web en tiempo real.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35-FF4B4B?logo=streamlit&logoColor=white)
![Railway](https://img.shields.io/badge/Deploy-Railway-0B0D0E?logo=railway&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ¿Qué es?

Cepillao' Studio es una aplicación web para formular helados y gelatos con rigor técnico. Ingresás los ingredientes, y el motor calcula en tiempo real la composición fisicoquímica completa: sólidos totales, grasa, MSNF, actividad de agua, crioscopía y poder anticongelante, generando diagnósticos automáticos y recomendaciones de estabilizantes según el tipo de producto y la máquina usada.

Diseñado para heladerías artesanales y desarrollo de recetas que necesitan resultados reales, no aproximaciones.

---

## Funcionalidades

| Módulo | Descripción |
|--------|-------------|
| **Formulador** | Composición en tiempo real: ST, grasa, MSNF, azúcares, POD, PAC, crioscopía (Raoult), Aw (Ross 1975) |
| **Radar de parámetros** | Visualización inmediata del balance de la mezcla |
| **Diagnósticos** | Alertas automáticas con recomendaciones por tipo de producto y máquina |
| **Restricciones** | 13 reglas declarativas: incompatibilidades de estabilizantes, cotas de edulcorantes, contradicciones de tipo de producto y requisitos de proceso |
| **Estabilizantes** | Sugerencias de dosificación basadas en la composición calculada |
| **Ticket de producción** | Resumen imprimible con instrucciones paso a paso |
| **Escalado** | Multiplicador de receta de ×0.25 a ×20 |
| **Costos** | Precio por pote y por litro calculados automáticamente |
| **Ninja Creami** | Soporte nativo con overrun empírico real (~10%) y cálculo de potes |
| **Base de datos** | ~130 ingredientes precargados, recetas guardadas en SQLite local |
| **Interfaz responsive** | Optimizada para móvil: filas de ingredientes horizontales, grids adaptativos, touch targets 44px+ |

---

## Inicio rápido

### Requisitos

- Python 3.11 o superior

### Instalación local

```bash
git clone https://github.com/zxdiegozx/Cepillao_Studio.git
cd Cepillao_Studio

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

La app abre en `http://localhost:8501`.

---

## Despliegue en Railway

El repositorio está listo para Railway con zero-config:

1. Crear proyecto en [railway.app](https://railway.app) y conectar este repositorio
2. Railway detecta el `Procfile` automáticamente y usa Nixpacks como builder
3. Agregar un **Volume** montado en `/data` para persistir la base de datos entre deploys — Railway inyecta `RAILWAY_VOLUME_MOUNT_PATH` automáticamente

Sin el volumen, la DB se resetea en cada redeploy. Con el volumen, los datos sobreviven indefinidamente.

---

## Estructura del proyecto

```
Cepillao_Studio/
│
├── app.py                      # Bootstrap: setup, CSS, tabs, llamada a ui/
├── calculator.py               # Facade pública del motor
├── constants.py                # Constantes y configuración global
├── database.py                 # ORM SQLite + seed de ~130 ingredientes + db_health()
├── restricciones.py            # Capa de restricciones: 13 reglas declarativas de formulación
│
├── engine/                     # Motor de cálculo (puro Python, sin Streamlit)
│   ├── __init__.py             # API pública re-exportada
│   ├── calc_core.py            # Cálculo lineal de ingredientes
│   ├── calc_cryoscopy.py       # Crioscopía — modelo Raoult simplificado
│   ├── calc_nutrition.py       # Nutrición y overrun — factores Atwater
│   ├── diagnostics.py          # Rangos objetivo y diagnósticos por combo
│   └── ticket.py               # Generador de ticket de producción ASCII
│
├── ui/                         # Capa de interfaz modular (Streamlit)
│   ├── __init__.py             # Re-exporta render_* de cada tab
│   ├── components.py           # Helpers compartidos: barras, radar, callbacks
│   ├── tab_formulador.py       # Tab 1 — Formulador + panel de análisis
│   ├── tab_recetas.py          # Tab 2 — Mis Recetas
│   ├── tab_bases.py            # Tab 3 — Bases de Helado
│   ├── tab_ingredientes.py     # Tab 4 — Gestión de ingredientes
│   └── tab_config.py           # Tab 5 — Configuración de rangos
│
├── tests/
│   └── test_formulador_state.py  # 36 tests de session_state del formulador
├── test_calculator.py            # Suite de tests unitarios del motor
│
├── .streamlit/
│   ├── config.toml             # Configuración Streamlit (headless, CORS, WebSocket)
│   └── custom.css              # Estilos dark mode + responsive móvil
│
├── requirements.txt
├── Procfile                    # Comando de inicio para Railway
└── railway.json                # Configuración del builder y restart policy
```

---

## Ciencia del motor

El motor implementa modelos fisicoquímicos estándar de la industria heladera:

- **Crioscopía**: descenso crioscópico por ley de Raoult simplificada (`ΔT = −1.86 × PAC_mol / kg_agua`)
- **Actividad de agua**: modelo de Ross (1975) — producto de las Aw individuales
- **Calorías**: factores Atwater modificados (grasa 9.0, proteína 3.5, azúcares 4.0, fibra 2.5, alcohol 7.0)
- **Overrun**: cálculo diferencial de masa antes/después del mantecado; overrun fijo mecánico para Ninja Creami

Documentación completa de fórmulas y referencias en [CALCULATOR_SCIENCE.md](CALCULATOR_SCIENCE.md).

---

## Tests

```bash
# Motor de cálculo
python -m pytest test_calculator.py -v

# Session state del formulador (36 tests)
python -m pytest tests/test_formulador_state.py -v
```

`test_calculator.py` cubre: cálculo lineal, totales, porcentajes, diagnósticos, crioscopía, actividad de agua, nutrición, overrun y detección de alcohol.

`tests/test_formulador_state.py` cubre: `callback_add_row` con state nulo/corrupto, `callback_clear_all`, `_collect_lines` con valores extremos, `_load_recipe_into_state` e invariantes del formulador.

---

## Stack

| Capa | Tecnología |
|------|-----------|
| UI web | Streamlit 1.35 |
| Visualización | Plotly 5.22 |
| Tablas | Pandas 2.2 |
| Base de datos | SQLite (stdlib) |
| Deploy | Railway · Nixpacks |

---

## Licencia

MIT © 2026 Diego Bracamonte
