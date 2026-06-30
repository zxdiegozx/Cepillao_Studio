# engine/ — Motor de Cálculo Científico

Este paquete contiene toda la lógica fisicoquímica de Cepillao' Studio.  
No tiene dependencias de UI, base de datos ni estado — es Python puro y testeable en aislamiento.

---

## Módulos

| Archivo | Responsabilidad |
|---------|----------------|
| `calc_core.py` | Cálculo lineal de composición (ST, MSNF, POD, PAC, Aw) |
| `calc_cryoscopy.py` | Descenso crioscópico — modelo de Raoult simplificado |
| `calc_nutrition.py` | Calorías (Atwater), edulcorantes, proteínas, overrun |
| `diagnostics.py` | Rangos objetivo por tipo de producto y máquina; diagnósticos priorizados |
| `ticket.py` | Generador de ticket de producción (texto estructurado, sin UI) |
| `__init__.py` | Re-exporta la API pública; único punto de importación externo |

---

## 1. Modelo de composición lineal

**Archivo:** `calc_core.py`

La mezcla de helado se modela como una superposición lineal de ingredientes. Cada ingrediente aporta una fracción de cada componente según su ficha técnica:

```
masa_componente_i = masa_ingrediente × fracción_componente / 100
```

Los componentes rastreados son:

| Variable | Descripción |
|----------|-------------|
| `fat` | Grasa total |
| `msnf` | Sólidos no grasos de la leche (MSNF / SNL) |
| `sugars` | Azúcares disponibles (incluyendo sustitutos con azúcar base) |
| `other_st` | Otros sólidos: fibra, cacao, almidón, proteínas no lácteas |
| `water` | Agua libre |
| `st` | Sólidos Totales = fat + msnf + sugars + other_st |
| `pod` | Poder Dulzorante acumulado (adimensional, referencia sacarosa = 1.0) |
| `pac` | Poder Anticongelante acumulado (adimensional, referencia sacarosa = 1.0) |

**POD y PAC** se acumulan como `Σ (gramos_i × factor_i)` — los factores están expresados por gramo de ingrediente (no por 100 g), por lo que el resultado es un número adimensional que representa el efecto total de toda la mezcla relativo a la sacarosa pura.

**Costo** se calcula como `Σ (gramos_i / 1000) × precio_por_kg_i`.

---

## 2. Fracciones del MSNF

La leche contiene sólidos no grasos cuya composición es relativamente constante entre variedades. El motor usa las fracciones estándar de **Walstra (2005)**:

| Componente | Fracción del MSNF |
|------------|-------------------|
| Lactosa | 55 % |
| Sales minerales | 8 % |
| Proteínas | ~35 % (Goff & Hartel 2013) |

Estas fracciones se usan en dos modelos: Aw (Ross) y cálculo de proteína láctea.

---

## 3. Actividad de Agua — ecuación de Ross (1975)

**Archivo:** `calc_core.py` → `calc_water_activity()`

La actividad de agua (Aw) se estima con la ecuación de Ross, que aproxima Aw como la fracción molar del solvente (agua) en la solución:

```
Aw ≈ n_agua / (n_agua + n_solutos)
```

donde los moles de cada especie se calculan con sus masas molares:

```
n_agua    = water_g / 18.015          # PM agua
n_azúcar  = sugars_g / 270.0          # PM promedio ponderado: sacarosa (342) + monos (180)
n_lactosa = (msnf_g × 0.55) / 342.0  # 55% del MSNF es lactosa (Walstra 2005)
n_sal     = (msnf_g × 0.08) / 58.44 × 2   # NaCl disocia en 2 iones → ×2
```

**Supuestos del modelo:**
- La grasa no se disuelve en agua → no contribuye a los moles de soluto
- Las proteínas, por su alto peso molecular, tienen una contribución molar despreciable
- El PM de 270 g/mol es un promedio ponderado empírico entre sacarosa (342) y monosacáridos como dextrosa/fructosa (180)

**Precisión:** ±0.01–0.02 unidades de Aw. Suficiente para evaluación de riesgo microbiológico relativo.

**Interpretación de riesgo:**

| Aw | Riesgo microbiológico |
|----|----------------------|
| < 0.85 | Bajo — crecimiento inhibido en congelado |
| 0.85–0.91 | Medio — levaduras osmófilas posibles en descongelación parcial |
| > 0.91 | Alto (normal en bases lácteas) — controlar pasteurización |

**Referencia:** Ross, E.W. (1975). *Relation of water activity to some conventional moisture contents in dry foods*. Journal of Food Science.

---

## 4. Validación Brix

**Archivo:** `calc_core.py` → `validate_brix()`

El refractómetro mide el índice de refracción de la mezcla, que es proporcional a los sólidos disueltos. En helado, los azúcares fermentables y la lactosa del MSNF son los principales contribuyentes:

```
Brix_calculado_base   = (azúcares_g / masa_total_g) × 100
Brix_calculado_con_MSNF = (azúcares_g + msnf_g × 0.55) / masa_total_g × 100
delta = Brix_medido − Brix_calculado_con_MSNF
```

El factor `0.55` proviene de la fracción de lactosa del MSNF (Walstra 2005). Los refractómetros digitales auto-compensan temperatura a 20°C.

**Umbral de proceso:** ±2 °Brix es el estándar industrial de control de recetas. Un delta positivo indica azúcares no declarados (fruta más madura, ingrediente con mayor contenido real) o un error de pesaje. Un delta negativo sugiere dilución, fermentación inicial o error de medición.

---

## 5. Crioscopía — modelo de Raoult simplificado

**Archivo:** `calc_cryoscopy.py` → `calc_cryoscopy()`

El descenso del punto de congelación de una solución diluida sigue la **ley de Raoult** para propiedades coligativas:

```
ΔT = −Kf × m
```

donde:
- `Kf = 1.86 °C·kg/mol` — constante crioscópica del agua (propiedad física del solvente)
- `m` — molalidad (moles de soluto por kg de solvente)

La molalidad se calcula normalizando el PAC acumulado respecto a la masa molar de la sacarosa, usando la sacarosa como molécula de referencia para expresar todos los azúcares en equivalentes crioscópicos:

```
PAC_moles = PAC_total / 342.3    # M_sacarosa = 342.3 g/mol
m = PAC_moles / (water_g / 1000) # molalidad real
ΔT = −1.86 × m
```

**Por qué PAC y no azúcares directamente:** El PAC es el "poder anticongelante" de cada edulcorante relativo a la sacarosa. Usar PAC en lugar de gramos brutos de azúcar permite integrar el efecto real de distintos edulcorantes (dextrosa con PAC=1.9, trehalosa con PAC=0.7, eritritol con PAC=1.3, etc.) en un único número que respeta su verdadera contribución crioscópica por mol.

**Zonas de comportamiento (física de cristalización del hielo):**

| ΔT (°C) | Zona | Consecuencia |
|---------|------|-------------|
| > −1.0 | `muy_bajo` | Base acuosa — cristales grandes, textura icy inevitable |
| −1.0 a −1.8 | `bajo` | Granuloso probable |
| −1.8 a −4.0 | `optimo` | Zona ideal para Creami y mantecadora |
| −4.0 a −6.0 | `alto` | Exceso leve — puede quedar blando |
| < −6.0 | `muy_alto` | Exceso severo o alcohol masivo |

> **Nota crítica de interpretación:** ΔT es la temperatura de *inicio* de congelación (primer cristal de hielo), no la temperatura a la que el helado solidifica completamente. Un ΔT de −2/−3°C es correcto y esperado — el helado congela a −18°C porque la congelación es un proceso progresivo: a medida que se forman cristales, la concentración de solutos en el agua remanente aumenta, deprimiendo aún más el punto de congelación hasta que el sistema alcanza el estado vítreo.

**Referencia:** Walstra, P. (2005). *Physical Chemistry of Foods*. CRC Press.

---

## 6. Calorías — factores de Atwater modificados

**Archivo:** `calc_nutrition.py` → `calc_calories()`

El valor energético se estima con los factores de conversión de Atwater, con la versión para proteína láctea adoptada por FAO/WHO (2003):

| Macronutriente | Factor (kcal/g) | Nota |
|----------------|----------------|------|
| Grasa | 9.0 | Estándar universal |
| Proteína láctea | **3.5** | FAO/WHO 2003 — no el 4.0 genérico |
| Azúcares disponibles | 4.0 | |
| Otros sólidos (fibra, cacao, almidón resistente) | 2.5 | |
| Alcohol (etanol) | 7.0 | |

La proteína se estima como el 35% del MSNF (Goff & Hartel 2013), ya que las fichas técnicas de los ingredientes no siempre declaran proteína por separado.

**Corrección para zero-calorie:** Los ingredientes marcados como `zero_calorie=1` en la base de datos (eritritol, alulosa, stevia) tienen su fracción de azúcares descontada del cálculo, ya que sus azúcares base no son metabólicamente disponibles como la sacarosa. Sin esta corrección, la alulosa se contaría como 4 kcal/g cuando en realidad aporta ~0.4 kcal/g.

**Corrección por alcohol:** Si se detectan ingredientes alcohólicos (licores, extractos), sus gramos de etanol se suman con el factor 7.0. Las fracciones de etanol por tipo de ingrediente están tabuladas en `constants.py` → `ALCOHOL_ETHANOL_FRACTION`.

**Referencias:**
- FAO/WHO (2003). *Food Energy: Methods of Analysis and Conversion Factors*.
- Goff, H.D. & Hartel, R.W. (2013). *Ice Cream* (7th ed.). Springer.

---

## 7. Overrun y rendimiento por máquina

**Archivo:** `calc_nutrition.py` → `overrun_calc()`

El **overrun** es el porcentaje de incremento de volumen por incorporación de aire durante el mantecado:

```
overrun = (volumen_final − volumen_base) / volumen_base × 100
```

La densidad del helado con overrun se deriva directamente:

```
densidad (g/mL) = 1 / (1 + overrun_factor)
```

Ejemplos:
- 0% overrun → 1.00 g/mL (mezcla base sin aire)
- 50% overrun → 0.67 g/mL (Ninja Creami Deluxe típico)
- 100% overrun → 0.50 g/mL (límite industrial premium)

**Ninja Creami — overrun mecánico fijo:** La máquina tritura el bloque congelado e incorpora aire de forma mecánica, sin control por parte del formulador. Los overruns aproximados son:
- Deluxe: ~50% (capacidad del pote: 640 g)
- Standard: ~40% (capacidad del pote: 430 g)

La masa base para un pote Creami es fija → el formulador no controla litros producidos sino el llenado del pote.

**Mantecadora — overrun configurable:**
```
liters_producidos = (base_g / 1000) × (1 + overrun_pct / 100)
base_necesaria_g  = target_liters × 1000 / (1 + overrun_pct / 100)
```

---

## 8. Análisis de edulcorantes

**Archivo:** `calc_nutrition.py` → `analyze_sweeteners()`

Cada edulcorante tiene un perfil tabulado con cinco propiedades:

```python
# (POD, PAC, kcal/g, descripción_sabor, perfil_dulzor)
'dextrosa':  (0.75, 1.90, 4.0, 'Frescor suave positivo en boca fría', 'inmediato')
'eritritol': (0.65, 1.30, 0.2, 'Efecto frescor/mentolado — limitar a 1.5%', 'inmediato')
'trehalosa': (0.45, 0.70, 4.0, 'Muy suave, casi neutro, crioprotector', 'lento')
'alulosa':   (0.70, 1.80, 0.4, 'El más parecido al azúcar, sin retrogusto', 'inmediato')
```

El análisis desglosa la contribución porcentual de cada edulcorante al POD total y al PAC total, permitiendo identificar cuál edulcorante "mueve" más la crioscopía o el dulzor.

**Advertencias automáticas por umbral:**
- **Eritritol > 1.5% de la mezcla:** efecto mentolado/frescor pronunciado en boca fría
- **Stevia > 0.3 g/kg:** retrogusto amargo potencial
- **Fructosa > 8% de la mezcla:** puede resultar empalagosa

---

## 9. Análisis proteico

**Archivo:** `calc_nutrition.py` → `analyze_protein()`

El motor identifica fuentes proteicas por coincidencia de nombres y asigna perfiles funcionales definidos en `constants.py` → `PROTEIN_PROFILES`. Cada perfil declara:

| Campo | Descripción |
|-------|-------------|
| `protein_fraction` | Fracción proteica sobre el total del ingrediente o sobre su MSNF |
| `protein_in_total` | `True` si la fracción es sobre el total; `False` si es sobre MSNF |
| `capacidad_espuma` | Score 1–5 de capacidad espumante (relevante para overrun) |
| `capacidad_gel` | Score 1–5 de capacidad gelificante (relevante para textura) |
| `t_desnaturaliz_c` | Temperatura de desnaturalización (°C) — alerta si < 75°C |
| `tipo` | Clasificación: `'suero'`, `'caseína'`, `'vegetal'`, `'lácteo_mixto'`, etc. |

Si no hay perfil específico para un ingrediente, se aplica el **fallback** de 36% del MSNF como estimación de proteína láctea genérica.

**Claims nutricionales** (umbrales en `PROTEIN_CLAIM_THRESHOLDS`):
- "Fuente de proteína" si ≥ X g/100g
- "Alto en proteína" si ≥ Y g/100g

---

## 10. Sistema de diagnósticos

**Archivo:** `diagnostics.py` → `calc_derived()`

Los diagnósticos se generan por comparación directa entre el valor calculado y el rango objetivo, usando tres niveles de prioridad:

| Prioridad | Significado |
|-----------|-------------|
| `critical` | Defecto irreversible o imposibilidad técnica |
| `important` | Problema probable de textura o seguridad |
| `adjustable` | Ajuste de optimización — no es urgente |

**Rangos objetivo por tipo de producto y máquina** (`get_targets()`):

Los rangos difieren según dos ejes: el tipo de producto (Helado/Gelato, Sorbete, Vegano, Frozen, Ligero) y la máquina (Creami vs. Mantecadora). Las diferencias clave son:

- **Mantecadora:** exige ST más alto (34–42% vs. 28–38%), MSNF más alto (6–11%), PAC más alto (150–320 vs. 120–260) porque el proceso de mantecado requiere una mezcla más concentrada para desarrollar cremosidad
- **Creami:** tolera ST más bajo porque la trituración mecánica compensa parcialmente la estructura de sólidos; el límite de MSNF es crítico (11%) para evitar arenado por recristalización de lactosa

**Ratio ST/Agua** es una métrica derivada que integra ambos parámetros:

```
ratio_ST_agua = ST_pct / water_pct
```

Un ratio bajo indica demasiada agua libre relativa a los sólidos → cristales grandes. Un ratio alto indica sobreconcentración → textura pastosa, overrun difícil.

---

## 11. Recomendaciones de estabilizantes

**Archivo:** `diagnostics.py` → `recommend_stabilizers()`

El sistema detecta deficiencias en la composición y propone estabilizantes de forma genérica (familia, no marca comercial). Las reglas de activación son:

| Condición | Recomendación |
|-----------|--------------|
| Agua libre > 62% sin espesante | CMC o Xantana (base láctea) / Guar o Tara (sorbete) |
| ST < mínimo sin ser sorbete | Fibra soluble o Inulina |
| Carragenina + fruta ácida sin Xantana | Sustituir carragenina (se degrada con pH < 4.5) |
| Grasa > 4% sin emulsionante | Lecitina de girasol / soja / yema |
| Creami sin crioprotector | Trehalosa o dextrosa |
| ST alto + agua baja sin problemas | Confirmación "sin espesante adicional necesario" |

Cada recomendación incluye dosis por kg de mezcla y por la receta actual, alternativas y advertencias de incompatibilidades (ej: CMC + Natulac + fruta ácida → triple gelificación).

---

## API pública

Todas las funciones públicas se re-exportan desde `__init__.py`. El único punto de entrada externo es:

```python
from engine import (
    calc_line, calc_totals, calc_percentages,
    validate_brix, calc_water_activity,
    calc_cryoscopy,
    calc_calories, analyze_sweeteners, analyze_protein, overrun_calc,
    calc_derived, get_targets, recommend_stabilizers,
    format_production_ticket,
)
```

O simplemente:

```python
from calculator import *   # facade en calculator.py
```

---

## Constantes moleculares

| Constante | Valor | Fuente |
|-----------|-------|--------|
| Kf (agua) | 1.86 °C·kg/mol | Propiedad física del agua pura |
| PM sacarosa | 342.3 g/mol | |
| PM agua | 18.015 g/mol | |
| PM azúcares (promedio) | 270.0 g/mol | Promedio ponderado sacarosa/monos |
| PM lactosa | 342.0 g/mol | |
| PM NaCl | 58.44 g/mol | |
| Fracción lactosa en MSNF | 0.55 | Walstra (2005) |
| Fracción sales en MSNF | 0.08 | Walstra (2005) |
| Fracción proteína en MSNF | 0.35 | Goff & Hartel (2013) |

---

## Referencias bibliográficas

- **Walstra, P. (2005).** *Physical Chemistry of Foods.* CRC Press. — Composición del MSNF, propiedades del agua en sistemas lácteos.
- **Goff, H.D. & Hartel, R.W. (2013).** *Ice Cream* (7th ed.). Springer. — Estructura del helado, fracciones proteicas, overrun, tecnología de mantecado.
- **FAO/WHO (2003).** *Food Energy: Methods of Analysis and Conversion Factors.* FAO Food and Nutrition Paper 77. — Factor Atwater 3.5 kcal/g para proteína láctea.
- **Ross, E.W. (1975).** *Relation of water activity to some conventional moisture contents in dry foods.* Journal of Food Science, 40(5). — Modelo de actividad de agua por fracción molar.
- **Raoult, F.M. (1882).** Ley de propiedades coligativas — base teórica del descenso crioscópico. Kf del agua: dato físico estándar.
