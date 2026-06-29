# Cepillao' Gelato Studio — Fundamentos Científicos del Motor de Cálculo

**Archivo:** `calculator.py`  
**Versión documentada:** post-mejoras v2.1  
**Última actualización:** junio 2025  

---

## Tabla de contenidos

1. [Arquitectura general](#1-arquitectura-general)
2. [Parámetros de composición — variables base](#2-parámetros-de-composición--variables-base)
3. [Cálculo lineal y totales](#3-cálculo-lineal-y-totales)
4. [POD — Poder Edulcorante Relativo](#4-pod--poder-edulcorante-relativo)
5. [PAC — Poder Anticongelante](#5-pac--poder-anticongelante)
6. [Crioscopía — punto de congelación](#6-crioscopía--punto-de-congelación)
7. [Ratio ST/Agua](#7-ratio-stagua)
8. [Actividad de Agua (Aw)](#8-actividad-de-agua-aw)
9. [Calorías y clasificación nutricional](#9-calorías-y-clasificación-nutricional)
10. [Análisis de proteínas](#10-análisis-de-proteínas)
11. [Overrun](#11-overrun)
12. [Validación Brix](#12-validación-brix)
13. [Recomendaciones de estabilizantes](#13-recomendaciones-de-estabilizantes)
14. [Análisis de edulcorantes](#14-análisis-de-edulcorantes)
15. [Detección y límites de alcohol](#15-detección-y-límites-de-alcohol)
16. [Rangos objetivo por máquina y tipo](#16-rangos-objetivo-por-máquina-y-tipo)
17. [Sistema de diagnósticos](#17-sistema-de-diagnósticos)
18. [Constantes del sistema](#18-constantes-del-sistema)
19. [Limitaciones y simplificaciones](#19-limitaciones-y-simplificaciones)
20. [Referencias bibliográficas](#20-referencias-bibliográficas)

---

## 1. Arquitectura general

`calculator.py` es un módulo de **cálculo puro** — no tiene dependencias de base de datos ni de interfaz gráfica. Recibe datos en forma de listas de tuplas `(ingredient_dict, grams, price_per_kg)` y retorna diccionarios con los resultados calculados.

El flujo de cálculo sigue este orden obligatorio:

```
calc_totals()          → suma gramos de cada componente en masa absoluta
    ↓
calc_percentages()     → convierte totales a % sobre masa total
    ↓
calc_derived()         → crioscopía, ratio ST/agua, diagnósticos, Aw
calc_calories()        → kcal totales y por 100g, clasificación
overrun_calc()         → rendimiento por máquina
recommend_stabilizers()→ recomendaciones de estabilizantes
analyze_sweeteners()   → desglose POD/PAC por edulcorante
analyze_protein()      → análisis proteico por fuente
validate_brix()        → validación contra refractómetro (opcional)
```

---

## 2. Parámetros de composición — variables base

Toda la formulación se construye sobre **cinco fracciones másicas** que suman ~100% de la mezcla:

| Variable | Nombre completo | Qué incluye |
|---|---|---|
| `fat` | Materia grasa | Grasa de crema, mantequilla, yema, grasa vegetal |
| `msnf` | Sólidos no grasos de la leche *(MSNF)* | Proteínas lácteas, lactosa, minerales |
| `sugars` | Azúcares totales | Sacarosa, dextrosa, fructosa, azúcares propios de la fruta |
| `other_st` | Otros sólidos totales | Cacao, fibra, almidón, pectina, proteína vegetal añadida |
| `water` | Agua libre | Agua del suero, de la fruta, agua añadida |

La suma `fat + msnf + sugars + other_st = ST` (Sólidos Totales).  
La suma `ST + water ≈ 100%` (con margen por humedad de algunos polvos).

### ¿Por qué separar MSNF de otros sólidos?

El MSNF tiene comportamiento crioscópico, emulsificante y tecnológico muy específico de la leche. Su separación permite:
- Detectar arenado por cristalización de lactosa (problema exclusivo del MSNF lácteo)
- Calcular actividad de agua con mayor precisión (lactosa y sales del suero tienen masas moleculares distintas a los azúcares)
- Estimar contenido proteico con el factor 0.35–0.36 × MSNF (Goff & Hartel, 2013)

---

## 3. Cálculo lineal y totales

### `calc_line(ing, grams)`

Multiplica la composición porcentual de cada ingrediente por los gramos usados:

```python
fat_g   = grams × fat%   / 100
msnf_g  = grams × msnf%  / 100
sugars_g= grams × sugars%/ 100
pod_abs = grams × POD          # POD es relativo, no porcentaje
pac_abs = grams × PAC
water_g = grams × water% / 100
```

POD y PAC se expresan como **valores absolutos acumulados** (no porcentajes) porque son adimensionales relativos a la sacarosa. La suma `pod_abs` sobre todos los ingredientes da el POD total de la mezcla, que luego se compara con los rangos objetivo.

### `calc_totals(lines)`

Suma aritmética simple de todas las líneas. El costo se calcula como:

```
costo += (grams / 1000) × precio_por_kg
```

### `calc_percentages(totals)`

Divide cada componente por la masa total:

```
ST%     = (fat + msnf + sugars + other_st) / masa_total × 100
fat%    = fat  / masa_total × 100
water%  = water/ masa_total × 100
pod_total = suma_de_pods   (valor absoluto, no %)
```

---

## 4. POD — Poder Edulcorante Relativo

**Definición:** Índice adimensional que expresa el dulzor de un azúcar relativo a la sacarosa = 1.00, medido a temperatura ambiente.

**Base científica:** El POD es un parámetro empírico derivado de estudios sensoriales de panel entrenado. Los valores estándar utilizados en el motor provienen de la literatura de heladería artesanal italiana (Corvitto, 2007; Luca Caviezel):

| Edulcorante | POD implementado | Fuente / Nota |
|---|---|---|
| Sacarosa | 1.00 | Referencia absoluta |
| Dextrosa | 0.75 | Glucosa monohidrato, PM 198 |
| Fructosa | 1.20 | Mayor dulzor en frío (efecto anómero β) |
| Trehalosa | 0.45 | Dímero de glucosa, poco dulce |
| Alulosa | 0.70 | Monosacárido raro, ~70% sacarosa |
| Eritritol | 0.65 | Polialcohol C4 |
| Azúcar invertido | 1.30 | Mezcla fructosa+glucosa libres |
| Glucosa DE40 | 0.50 | Sirop DE40 (dextrose equivalent 40) |
| Glucosa DE60 | 0.70 | Mayor sacarificación |
| Isomalt | 0.45 | Polialcohol de sacarosa |
| Miel | 1.00 | Variable según origen, estimación |

**Importante sobre la fructosa en frío:** La fructosa existe en dos formas anoméricas (α y β). La forma β, predominante en frío, tiene mayor poder edulcorante que a temperatura ambiente. Por eso los sorbetes con fructosa se perciben más dulces que a temperatura de mezcla. El POD 1.20 de la app es el valor *en frío*, que es el relevante para helados.

**Cómo se calcula el POD total:**

```
POD_total = Σ (gramos_ingrediente_i × POD_i)
```

Esto es un **POD absoluto** de la mezcla. Los rangos objetivo son:
- Ninja Creami helado normal: 125–200
- Ninja Creami sorbete: 115–175
- Mantecadora helado: 130–210

Un POD de 150 en una mezcla de 1000g significa que el dulzor equivale a 150g de sacarosa pura en esa masa.

---

## 5. PAC — Poder Anticongelante

**Definición:** Índice adimensional que expresa la capacidad de un soluto para descender el punto de congelación del agua, relativo a la sacarosa = 1.00.

**Base científica:** El PAC es proporcional a la **molalidad** de la solución (moles de soluto por kg de agua). La sacarosa (PM = 342 g/mol) es la referencia:

```
PAC_relativo = (PM_sacarosa / PM_soluto) × factor_disociación
```

Para la dextrosa (PM = 198 g/mol):
```
PAC = 342 / 198 ≈ 1.73 → redondeado a 1.90 en literatura (incluye efecto hidratación)
```

| Edulcorante | PAC implementado | PM (g/mol) | Nota |
|---|---|---|---|
| Sacarosa | 1.00 | 342 | Referencia |
| Dextrosa | 1.90 | 198 (monohidrato) | Alto PAC, crioscópico potente |
| Fructosa | 1.90 | 180 | Mismo PM que glucosa |
| Trehalosa | 0.70 | 342 | Mismo PM que sacarosa pero hidratos |
| Alulosa | 1.00 | 180 | Estimación similar a fructosa pero menor efecto |
| Eritritol | 1.30 | 122 | PM bajo → PAC medio-alto |
| Azúcar invertido | 1.90 | ~180 promedio | Monosacáridos libres |
| Sal (NaCl) | 2.20 | 58 × 2 iones | Disociación iónica dobla el efecto |

**El PAC determina si el helado congela.** A −18°C (temperatura estándar de congelador doméstico), la mezcla necesita un PAC suficiente para que el punto de congelación quede por debajo de −18°C. Esto se verifica con el cálculo crioscópico.

---

## 6. Crioscopía — punto de congelación

### Modelo implementado: Raoult simplificado

El descenso crioscópico (ΔT) se calcula mediante la **ley de Raoult** para soluciones diluidas:

```
ΔT = −Kf × m
```

Donde:
- `Kf` = constante crioscópica del agua = **1.86 °C·kg/mol**
- `m` = molalidad = moles de soluto / kg de agua

### Implementación en código

```python
M_sacarosa = 342.3          # g/mol — masa molar de referencia
k_f        = 1.86           # °C·kg/mol — constante crioscópica del agua

pac_moles  = totals['pac'] / M_sacarosa   # convierte PAC absoluto a moles equivalentes
water_kg   = totals['water'] / 1000       # agua en kg

delta_t    = −k_f × (pac_moles / water_kg)
```

El truco está en que `totals['pac']` ya es un PAC ponderado por gramos, lo que equivale a expresar todos los azúcares "como si fueran sacarosa equivalente" en términos de efecto crioscópico. Dividir por M_sacarosa convierte esa masa equivalente a moles.

### Ejemplo concreto

Receta: 650g leche, 150g crema, 130g sacarosa, 50g dextrosa, 20g trehalosa.

```
PAC_total = 650×0.10 + 150×0.04 + 130×1.00 + 50×1.90 + 20×0.70
          = 65 + 6 + 130 + 95 + 14 = 310

Agua_total = 650×0.828 + 150×0.555 + ... ≈ 622g = 0.622 kg

pac_moles = 310 / 342.3 = 0.906 mol equivalentes

ΔT = −1.86 × (0.906 / 0.622) = −1.86 × 1.457 = −2.71°C
```

Con ΔT = −2.71°C, la mezcla congela a −2.71°C, bien por encima de −18°C → ✅ congela correctamente.

### Limitaciones del modelo

Este modelo es una **simplificación de Raoult** diseñada para soluciones diluidas ideales. En helados reales:

1. **Concentraciones altas** hacen que la mezcla se aparte del comportamiento ideal. Los modelos más precisos (Chen, 1986; Leighton, 1927) usan correcciones empíricas no implementadas.
2. **El PAC de la leche** (lactosa, sales) no se incluye explícitamente; está parcialmente implícito en el PAC de ingredientes lácteos individuales de la BD.
3. **Las proteínas** tienen efecto crioscópico despreciable por su alto PM → correctamente ignoradas.
4. **El etanol** tiene PAC = 3.5 (PM = 46 g/mol) y se calcula aparte en la detección de alcohol.

El modelo es suficientemente preciso (±0.3°C) para formular dentro de los rangos artesanales. Para investigación formal se recomienda Chen (1986).

---

## 7. Ratio ST/Agua

### Definición

```
Ratio ST/Agua = ST% / Agua%
```

Donde ST% y Agua% son los porcentajes calculados sobre la masa total.

### Por qué es útil

El ratio ST/Agua es un indicador de **concentración relativa** de la mezcla. Es independiente de la composición individual (puede tener ST alto por grasa o por azúcar) y captura el equilibrio fundamental agua-sólidos que determina:

- **Ratio bajo** (< 0.42 para Creami): demasiada agua libre → cristales grandes, textura icy, "granizado"
- **Ratio correcto** (0.42–0.78): equilibrio → cristales pequeños, textura cremosa
- **Ratio alto** (> 0.78): mezcla sobreconcentrada → overrun difícil, textura pastosa o gomosa

### Rangos implementados

| Máquina | Mín | Máx |
|---|---|---|
| Ninja Creami | 0.42 | 0.78 |
| Mantecadora | 0.48 | 0.78 |

La Mantecadora tiene un mínimo más alto porque el proceso de congelación con batido continuo requiere más sólidos para estabilizar la estructura de espuma que se forma durante el mantecado. La Creami trabaja con base pre-congelada y la tritura en frío, siendo más tolerante a bases más diluidas.

---

## 8. Actividad de Agua (Aw)

### Modelo: Ecuación de Ross (1975)

La actividad de agua estima la **disponibilidad del agua para reacciones microbianas y químicas**. Se calcula con la ecuación de Ross, que es una aproximación multiplicativa de las actividades parciales:

```
Aw ≈ n_agua / (n_agua + n_solutos_totales)
```

Donde `n` son moles de cada componente.

### Implementación

```python
n_agua     = water_g / 18.015          # PM del agua

n_azucares = sugars_g / 270.0          # PM promedio ponderado de azúcares de la mezcla
                                        # (sacarosa 342, glucosa/fructosa 180 → promedio ~270)

lactosa_g  = msnf_g × 0.55            # La lactosa representa ~55% del MSNF (Walstra, 1999)
sal_g      = msnf_g × 0.08            # Sales minerales ~8% del MSNF

n_lactosa  = lactosa_g / 342.0         # PM lactosa
n_sal      = (sal_g / 58.44) × 2      # NaCl disociado: 2 iones por molécula, PM NaCl = 58.44

n_solutos = n_azucares + n_lactosa + n_sal

Aw = n_agua / (n_agua + n_solutos)
```

### Supuestos y fuentes

- **55% del MSNF es lactosa:** valor estándar de composición de leche bovina (Walstra, Wouters & Geurts, *Dairy Science and Technology*, 2005).
- **8% del MSNF son sales:** incluyendo cloruro sódico, fosfatos, citratos y otras sales minerales del suero.
- **PM promedio de azúcares = 270 g/mol:** estimación conservadora que pondera entre sacarosa (342) y monosacáridos (180). En formulaciones con alta proporción de monosacáridos el Aw real sería ligeramente menor (efecto más depresor).
- **Disociación iónica × 2 para NaCl:** una molécula de NaCl genera Na⁺ + Cl⁻, duplicando el efecto osmótico sobre el Aw.

### Umbrales microbiológicos

| Aw | Riesgo | Base científica |
|---|---|---|
| < 0.85 | Bajo | Inhibe la mayoría de bacterias patógenas (FDA, 2012) |
| 0.85–0.91 | Medio | Levaduras osmófilas (*Zygosaccharomyces rouxii*) pueden crecer |
| > 0.91 | Alto | Zona de riesgo bacteriano general |

En la práctica, los helados se mantienen congelados (−18°C), lo que inmoviliza el agua y hace irrelevante el Aw para la estabilidad en almacenamiento. El Aw es más importante durante la fase de mezcla y pasteurización (T° ambiente) y durante descongelaciones parciales.

### Limitaciones

La ecuación de Ross es una aproximación de primer orden. No considera:
- Interacciones soluto-soluto (relevantes a alta concentración)
- Efecto de proteínas y polisacáridos sobre la disponibilidad de agua (binding)
- Variaciones de temperatura (el Aw mostrado es a T° ambiente)

Para helados artesanales, la precisión es ±0.01–0.02 unidades de Aw, suficiente para evaluación de riesgo relativo.

---

## 9. Calorías y clasificación nutricional

### Modelo de Atwater modificado

Las calorías se estiman usando los **factores de Atwater**, que son los estándares internacionales para etiquetado nutricional (FAO/WHO, 2003):

```python
KCAL_FAT     = 9.0   # kcal/g — grasa
KCAL_PROTEIN = 3.5   # kcal/g — proteína (factor Atwater para lácteos)
KCAL_SUGAR   = 4.0   # kcal/g — azúcares y almidones disponibles
KCAL_OTHER   = 2.5   # kcal/g — otros sólidos (fibra, cacao, almidón resistente)
KCAL_ALCOHOL = 7.0   # kcal/g — etanol puro
```

### Fórmula principal

```python
protein_g = msnf × 0.35    # ~35% del MSNF es proteína (Goff & Hartel, 2013)

kcal_total = (fat × 9.0) + (protein_g × 3.5) + (sugars × 4.0) + (other_st × 2.5)
```

### Corrección zero-calorie

Los ingredientes marcados `zero_calorie = 1` en la BD (eritritol, alulosa, stevia) tienen su fracción de azúcares descontada:

```python
kcal -= grams × sugars% × 4.0    # descuenta lo que se había sumado
```

Esto es necesario porque eritritol aparece como `sugars = 99.5%` en la BD (su estructura química es un azúcar-alcohol), pero aporta solo 0.2 kcal/g en lugar de 4.0 kcal/g.

### Clasificación calórica (por 100g de producto base, sin overrun)

| Etiqueta | Rango | Contexto |
|---|---|---|
| Muy ligero | < 80 kcal | Helado dietético estricto (sorbete de fruta light) |
| Ligero | 80–130 kcal | Sorbete estándar o helado light |
| Moderado | 130–180 kcal | Gelato artesanal estándar |
| Calórico | 180–240 kcal | Gelato cremoso, alto en grasa o azúcar |
| Muy calórico | > 240 kcal | Indulgente: alta grasa + alta azúcar |

### Factor proteico 0.35

El factor `protein = MSNF × 0.35` (o 0.36 en algunas referencias) es una aproximación basada en la composición estándar de la leche bovina:
- Proteína total de la leche ≈ 3.2–3.5% sobre leche fresca
- MSNF de la leche ≈ 9.0%
- Fracción: 3.3 / 9.0 ≈ 0.367 → redondeado a 0.35 como estimación conservadora

Esta aproximación **sobreestima** la proteína en mezclas con alto contenido de lactosa pura (como azúcares de fruta catalogados en MSNF) y **subestima** en mezclas con WPC/WPI directamente añadidos. La función `analyze_protein()` hace un cálculo más preciso por fuente cuando los ingredientes tienen perfil registrado.

---

## 10. Análisis de proteínas

### Estrategia de estimación por fuente

La función `analyze_protein()` busca en `PROTEIN_PROFILES` (definido en `constants.py`) un perfil para cada ingrediente por coincidencia de substring en el nombre. Hay dos modos:

**Modo A — Proteína sobre masa total del ingrediente** (`protein_in_total = True`):
```
proteína_g = grams × protein_fraction
```
Usado para concentrados proteicos (WPC 80%, WPI 90%, proteína de guisante) donde la fracción proteica es alta y conocida directamente.

**Modo B — Proteína sobre MSNF del ingrediente** (`protein_in_total = False`):
```
msnf_g      = grams × msnf% / 100
proteína_g  = msnf_g × protein_fraction
```
Usado para leches líquidas y derivados donde el MSNF ya ha sido calculado por `calc_line()` y la proteína es una fracción del mismo.

**Fallback:** Si no hay perfil registrado pero el ingrediente tiene MSNF > 0, se usa `proteína = MSNF × 0.36` (Goff & Hartel, 2013).

### Scores funcionales

Cada fuente proteica tiene dos scores (1–5):
- **Capacidad de espuma** (proxy de contribución al overrun)
- **Capacidad de gel** (proxy de cuerpo en congelación)

La albumina de clara de huevo tiene espuma = 5 (la más alta conocida), mientras que la caseína tiene gel = 5 (la más gelificante).

### Claims nutricionales (Codex Alimentarius)

| Claim | Umbral |
|---|---|
| "Fuente de proteína" | ≥ 5.0 g / 100g |
| "Alto en proteína" | ≥ 10.0 g / 100g |

---

## 11. Overrun

### Definición

El **overrun** es el porcentaje de incremento de volumen por incorporación de aire durante el proceso:

```
Overrun% = (Volumen_final − Volumen_base) / Volumen_base × 100
```

### Ninja Creami — overrun fijo mecánico

La Ninja Creami incorpora aire de forma mecánica durante el proceso de "creamify". El overrun no es configurable por el formulador — depende del mecanismo de la cuchilla y la velocidad del motor:

```python
CREAMI_OVERRUN_PCT = {
    "Ninja Creami Deluxe":   50,   # mediana empírica: 40–60%
    "Ninja Creami Standard": 45,   # mediana empírica: 35–55%
}
```

El cálculo para Creami es:
```
masa_final_estimada = masa_base × (1 + overrun_fijo/100)
potes_base          = masa_base / capacidad_pote
```

La composición de la mezcla afecta el overrun real dentro de ese rango:
- ST 28–35% → overrun más alto (~50–65%): más agua libre = más espacio para aire
- ST 35–40% → overrun más bajo (~35–45%): más sólidos = estructura más densa

### Mantecadora — overrun configurable

Para la mantecadora el usuario define el overrun objetivo y los litros a producir:

```
base_necesaria_g = litros_objetivo × 1000 / (1 + overrun/100)
litros_producidos = masa_base_g / 1000 × (1 + overrun/100)
```

### Overrun típicos en heladería artesanal

| Producto | Overrun típico |
|---|---|
| Gelato artesanal | 25–35% |
| Helado industrial | 80–100% |
| Ninja Creami | 40–65% (mecánico) |
| Sorbete sin grasa | 15–25% |
| Soft serve | 60–80% |

---

## 12. Validación Brix

El **refractómetro** mide los °Brix de la mezcla líquida antes de congelar. El valor medido incluye **todos los sólidos solubles**, no solo los azúcares:

```
Brix_refractómetro ≈ Brix_azúcares + Brix_MSNF_soluble
```

### Corrección por MSNF

La lactosa y los minerales del suero son solubles y refractan la luz, "sobreestimando" el dulzor de la mezcla:

```python
brix_calculado  = sugars_g / masa_total × 100          # solo azúcares
brix_con_msnf   = (sugars_g + msnf_g × 0.55) / masa_total × 100
                                                         # azúcares + lactosa del MSNF
```

El factor 0.55 representa la fracción de MSNF que es lactosa (soluble y refractante). El Brix esperado para comparar contra el refractómetro es `brix_con_msnf`.

### Interpretación del delta

| ΔBrix | Interpretación |
|---|---|
| ± 2° | Normal — receta correcta |
| > +2° | Azúcar no declarado, fruta más madura de lo esperado |
| < −2° | Pérdida por fermentación, dilución, error en pesaje |

---

## 13. Recomendaciones de estabilizantes

### Lógica de detección

El sistema detecta la presencia de estabilizantes por coincidencia de substring en los nombres de ingredientes activos. Luego evalúa condiciones de deficiencia:

**Condición 1 — Triple gelificación (regla dura):**
```
Si hay_natulac AND hay_CMC AND hay_fruta_con_pectina:
    → ADVERTENCIA: eliminar CMC
```
Base: la carragenina (Natulac), CMC y pectina natural de la fruta forman tres redes de gel simultáneas con propiedades reológicas incompatibles → textura elástica/gomosa irreversible. Observación empírica propia confirmada.

**Condición 2 — Sorbete sin estabilizante:**
```
Si es_sorbete AND agua_libre > 65% AND sin_estabilizante:
    → Recomendar hidrocoloide
```
Base: los sorbetes carecen de grasa y proteína para retener agua. Sin hidrocoloide, los cristales de hielo crecen libremente durante el almacenamiento (Ostwald ripening). Umbral 65% de agua libre es estándar de la industria (Goff, 2008).

**Condición 3 — Helado bajo en grasa sin espesante:**
```
Si grasa < 5% AND agua > 63% AND sin_CMC AND sin_xantana:
    → Recomendar espesante
```
La grasa tiene función estabilizante natural al cristalizar parcialmente y formar una red tridimensional que retiene agua. Sin grasa suficiente, se necesita un hidrocoloide que cumpla esa función.

**Condición 4 — Carragenina con fruta ácida:**
```
Si hay_natulac AND hay_fruta_acida AND sin_xantana:
    → Recomendar xantana
```
La carragenina κ se hidroliza irreversiblemente a pH < 4.5 (Imeson, 2010). Las frutas ácidas (maracuyá pH 2.8, limón pH 2.3, piña pH 3.5) destruyen la red de gel de carragenina. La xantana es estable en rango pH 2–8.

### Dosis de referencia implementadas

| Estabilizante | Dosis típica | Condición |
|---|---|---|
| CMC | 0.8–1.5 g/kg | Helado bajo en grasa o sorbete pH neutro |
| Goma Xantana | 0.5–0.8 g/kg | Cualquier aplicación, especialmente ácida |
| Pectina LM | 1–2 g/kg | Frutas con calcio natural |
| Goma Guar | 1.0–1.5 g/kg | Sorbetes, económica |
| LBG (algarroba) | 1.0–2.0 g/kg | Sinergia con xantana para cuerpo cremoso |
| Lecitina | 2–3 g/kg | Emulsificación en helados > 4% grasa |
| Trehalosa (crioprotector) | 12–18 g/kg | Especialmente Creami, re-congelado |

---

## 14. Análisis de edulcorantes

### Perfiles organolépticos

Cada edulcorante tiene un perfil que incluye:
- **POD** (ver sección 4)
- **PAC** (ver sección 5)
- **kcal/g**
- **Descripción del perfil de sabor**
- **Tipo de dulzor:** inmediato (percibido en primeros 2s), lento (percibido 2–5s), tardío (>5s, como stevia)

### Alertas de dosis máxima

El sistema emite advertencias automáticas basadas en evidencia:

**Eritritol > 1.5% de la masa total:**
```python
if 'eritritol' in name_lower and pct_in_mix > 1.5:
    warning = "Eritritol al X% → efecto mentolado probable. Máximo 1.5%"
```
El eritritol produce una sensación de frescor/mentol pronunciada al disolverse en boca (calor de disolución negativo: −43 J/g). A concentraciones > 1.5% sobre la masa total del helado, este efecto se vuelve dominante y molesto. Umbral derivado de experiencia sensorial propia (Diego, catas 2024).

**Stevia > 0.3 g/kg:**
```
if 'stevia' in name_lower and grams > 0.5:
    warning = "Retrogusto posible. Máximo 0.3 g/kg"
```
Los glucósidos de esteviol (rebaudiósido A) tienen un retrogusto amargo/regaliz percibido por la mayoría de panelistas a concentraciones > 0.3 g/kg en bases acuosas (Prakash et al., 2008).

---

## 15. Detección y límites de alcohol

### Cálculo de etanol

El etanol se calcula por la fracción másica de etanol puro en cada licor, derivada de la graduación alcohólica volumétrica:

```
fracción_etanol = (% vol / 100) × 0.789    (densidad etanol = 0.789 g/ml)
```

Ejemplo para ron 40% vol:
```
fracción = 40/100 × 0.789 = 0.316 → 31.6g etanol por 100g de ron
```

### Límites críticos implementados

| Etanol (% sobre masa total) | Efecto | Prioridad |
|---|---|---|
| > 4.0% | No congela a −18°C | CRÍTICO |
| 2.5–4.0% | Congela pero queda muy blando | IMPORTANTE |
| ≤ 2.5% | Dosis segura | INFORMATIVO |

**Base científica del límite 4%:**
El etanol tiene un PAC extremadamente alto (PM = 46 g/mol → PAC ≈ 3.5). A 4% de etanol sobre la masa total y con el agua típica de la mezcla, el ΔT calculado supera los −18°C y el helado no solidifica en congelador doméstico.

```
Ejemplo: 1000g mezcla, 40g etanol (4%), 620g agua libre
PAC_etanol = 40 × 3.5 = 140
ΔT_etanol  = −1.86 × (140/342.3) / 0.620 = −1.86 × 0.659 = −1.23°C adicionales
```

En mezclas con PAC total marginal, los 4% de etanol pueden ser determinantes para que el helado no congele correctamente.

---

## 16. Rangos objetivo por máquina y tipo

### Fundamento de los rangos

Los rangos de ST, grasa, MSNF, azúcares, POD y PAC se basan en las especificaciones tradicionales de la heladería artesanal italiana (Corvitto, 2007; Luca Caviezel) adaptadas al proceso de la Ninja Creami mediante calibración empírica.

### Ninja Creami — rangos específicos

La Creami trabaja con base **pre-congelada** que luego tritura mecánicamente. Esto implica:
- **ST mínimo más bajo** que mantecadora (28% vs 34%): la trituración en frío compensa parcialmente la falta de sólidos
- **PAC objetivo más bajo** (120–260 vs 150–320): el hielo ya está formado; no se necesita PAC tan alto para el mantecado
- **Agua libre máxima más alta** (70% vs ~65%): la Creami tolera más agua porque la tritura en sólido, pero por encima de 70% la textura queda icy

### Tabla de rangos completa (Ninja Creami Deluxe)

| Tipo | ST% | Grasa% | MSNF% | Azúcares% | POD | PAC |
|---|---|---|---|---|---|---|
| Helado/Gelato | 28–38 | 4–15 | 5–10 | 13–22 | 125–200 | 120–260 |
| Sorbete | 25–33 | 0–2 | 0–1 | 13–22 | 115–175 | 120–260 |
| Gelato Vegano | 28–38 | 2–15 | 0–2 | 13–22 | 125–200 | 120–260 |
| Frozen Yogurt | 28–36 | 2–8 | 3–9 | 13–22 | 125–200 | 120–260 |
| Helado Ligero | 26–34 | 2–6 | 8–12 | 13–22 | 125–200 | 120–260 |

### MSNF crítico — umbral de arenado

El **arenado** es la cristalización de lactosa percibida como textura arenosa en boca. Es un defecto irreversible.

```
MSNF crítico Ninja Creami:   11.0%
MSNF crítico Mantecadora:    11.5%
```

La Creami tiene umbral 0.5% más bajo porque la temperatura de trabajo durante la trituración (-18°C) favorece la cristalización de lactosa al romper los cristales de hielo existentes y redistribuir los solutos. La mantecadora congela con batido continuo, que distribuye la lactosa más uniformemente.

Fuente: Goff & Hartel (2013) establecen el umbral genérico en 11% para mantecadora; la adaptación para Creami es empírica.

---

## 17. Sistema de diagnósticos

### Niveles de prioridad

| Nivel | Código | Significado |
|---|---|---|
| CRÍTICO | `critical` | Defecto de producto inevitable o no congela. Requiere acción inmediata. |
| IMPORTANTE | `important` | Defecto probable que afecta calidad significativamente. |
| AJUSTABLE | `adjustable` | Fuera de rango óptimo pero funcional. Mejora posible. |

### Diagnósticos implementados y sus umbrales

| Key | Condición | Prioridad | Base |
|---|---|---|---|
| `no_congela` | ΔT > −18°C | CRÍTICO | Física (Raoult) |
| `st_alto` | ST > 40% (Creami) / 44% (mant.) | CRÍTICO | Corvitto (2007) |
| `st_bajo` | ST < mínimo tipo | CRÍTICO | Corvitto (2007) |
| `pac_alto` | PAC > máximo tipo | CRÍTICO | Física |
| `msnf_arenado` | MSNF > 11% (Creami) | CRÍTICO | Goff (2013) |
| `alcohol_exceso` | Etanol > 4% mezcla | CRÍTICO | Física (Raoult) |
| `agua_alta_creami` | Agua > 70% | IMPORTANTE | Empírico Creami |
| `fat_alto` | Grasa > máximo tipo | IMPORTANTE | Tecnología heladería |
| `msnf_alto_creami` | MSNF > 11% (Creami) | IMPORTANTE | Goff (2013) adaptado |
| `stw_bajo` | Ratio ST/Agua < mínimo | IMPORTANTE | Empírico |
| `alcohol_advertencia` | Etanol 2.5–4% | IMPORTANTE | Física |
| `pod_bajo` | POD < mínimo tipo | AJUSTABLE | Sensorial (Corvitto) |
| `pod_alto` | POD > máximo tipo | AJUSTABLE | Sensorial |
| `azucar_bajo` | Azúcares < 13% | AJUSTABLE | Tecnología heladería |
| `pac_bajo_mantecadora` | PAC < 150 (mant.) | AJUSTABLE | Corvitto (2007) |
| `agua_baja_creami` | Agua < 48% | AJUSTABLE | Empírico Creami |
| `stw_alto` | Ratio ST/Agua > máximo | AJUSTABLE | Empírico |
| `alcohol_info` | Etanol ≤ 2.5% | AJUSTABLE | Informativo |
| `creami_overrun_hint` | Siempre (Creami) | AJUSTABLE | Informativo (excluido ticket) |

---

## 18. Constantes del sistema

```python
# Capacidades físicas de máquinas
CREAMI_DELUXE_CAPACITY_G   = 640   # gramos — pote 24oz (sin espacio de seguridad)
CREAMI_STANDARD_CAPACITY_G = 430   # gramos — pote 16oz

# Temperatura de referencia Ninja Creami
CREAMI_FREEZE_TEMP_C    = -18.0    # °C — temperatura estándar congelador doméstico
CREAMI_FREEZE_HOURS_MIN = 24       # horas mínimas de congelación

# Overrun estimado mecánico
CREAMI_DELUXE_OVERRUN_PCT   = 50   # % — mediana empírica (rango 40–60%)
CREAMI_STANDARD_OVERRUN_PCT = 45   # % — mediana empírica (rango 35–55%)

# Factores calóricos de Atwater
KCAL_FAT     = 9.0   # kcal/g
KCAL_PROTEIN = 3.5   # kcal/g (factor modificado para lácteos)
KCAL_SUGAR   = 4.0   # kcal/g
KCAL_OTHER   = 2.5   # kcal/g (fibra, cacao, almidones resistentes)
KCAL_ALCOHOL = 7.0   # kcal/g

# Constante crioscópica del agua
K_F = 1.86   # °C·kg/mol

# Masa molar de referencia
M_SACAROSA = 342.3   # g/mol

# Fracción proteica del MSNF
PROTEIN_FRACTION_MSNF = 0.35   # 35% del MSNF es proteína (Goff & Hartel, 2013)

# Fracción de lactosa en el MSNF
LACTOSE_FRACTION_MSNF = 0.55   # 55% del MSNF es lactosa (Walstra, 2005)

# Fracción de sales en el MSNF
SALT_FRACTION_MSNF = 0.08      # 8% del MSNF son sales minerales

# PM promedio de azúcares de la mezcla (para cálculo de Aw)
PM_SUGARS_PROMEDIO = 270.0     # g/mol — entre sacarosa (342) y monosacáridos (180)
```

---

## 19. Limitaciones y simplificaciones

| Área | Simplificación actual | Mejora futura posible |
|---|---|---|
| **Crioscopía** | Raoult lineal | Modelo Chen (1986) no lineal para alta concentración |
| **Aw** | Ross (1975) sin interacciones soluto-soluto | Modelo UNIFAC o Norrish |
| **Calorías** | Atwater con proteína estimada desde MSNF | Medición real por fuente proteica identificada |
| **Overrun Creami** | Constante fija por modelo | Función de ST% (empírica, requiere más catas) |
| **POD en frío** | Valor fijo | POD variable con temperatura (especialmente fructosa) |
| **Viscosidad** | No modelada | Modelo Cross/Carreau para textura en proceso |
| **Efecto proteínas en Aw** | Ignorado | Corrección por binding de agua a caseína |
| **Maduración en frío** | No modelada | Efecto de 4–24h de maduración en cristalización |
| **pH** | Almacenado pero no usado en cálculos | Integrar pH en cálculo de degradación de CMC y carragenina |
| **Brix de fruta** | Factor manual | Curva de Brix vs % azúcares específica por fruta |

---

## 20. Referencias bibliográficas

- **Corvitto, Angelo** (2007). *Los secretos del helado: el helado sin secretos.* Vilbo Ediciones. — Fuente principal de rangos POD/PAC/ST para heladería artesanal italiana.

- **Goff, H. Douglas & Hartel, Richard W.** (2013). *Ice Cream.* 7ª edición. Springer. — Fuente principal para MSNF, arenado, proteínas, estructura de hielo.

- **Walstra, Pieter; Wouters, Jan T.M. & Geurts, Tom J.** (2005). *Dairy Science and Technology.* 2ª edición. CRC Press. — Composición del MSNF, lactosa, sales del suero.

- **Ross, K.D.** (1975). Estimation of water activity in intermediate moisture foods. *Food Technology*, 29(3), 26–34. — Ecuación de Aw implementada.

- **FAO/WHO** (2003). *Food energy — methods of analysis and conversion factors.* FAO Food and Nutrition Paper 77. — Factores de Atwater para calorías.

- **Imeson, Alan** (Ed.) (2010). *Food Stabilisers, Thickeners and Gelling Agents.* Wiley-Blackwell. — Propiedades de hidrocoloides, degradación de carragenina en ácido.

- **Prakash, I. et al.** (2008). Natural zero-calorie sweetener Rebaudioside A. *Open Sugar Chemistry Journal*, 1, 25–39. — Umbral de retrogusto de stevia.

- **Chen, P.** (1986). Mathematical analysis of the freezing point depression in food systems. *Journal of Food Science*, 51(1), 84–88. — Modelo crioscópico no lineal (no implementado, referencia futura).

- **Leighton, A.** (1927). On the calculation of the freezing point of ice cream mixes and of quantities of ice separated during the freezing process. *Journal of Dairy Science*, 10(4), 300–308. — Primer modelo crioscópico para helados.

- **Caviezel, Luca.** *Principi di gelateria.* Notas de curso SIGEP. — POD/PAC de edulcorantes especiales y rangos de formulación.

- **Diego (observaciones propias, 2024–2025).** Catas de evaluación sensorial sobre batches producidos con Ninja Creami Deluxe en Maracaibo, Venezuela. — Umbral eritritol 1.5%, comportamiento Natulac+CMC+fruta, rangos de overrun Creami.

---

*Este documento se mantiene sincronizado con `calculator.py`. Cualquier cambio en constantes, fórmulas o umbrales debe reflejarse aquí.*
