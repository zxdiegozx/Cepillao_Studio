"""
restricciones.py — Capa de restricciones de formulación de helado.

Complementa a engine/diagnostics.py (que valida rangos numéricos) con
reglas que detectan incompatibilidades entre ingredientes, contradicciones
de tipo de producto y requisitos de proceso no garantizados.

API pública:
    verificar(lines_with_ings, totals, pct, product_type, machine) → list[dict]

Cada violación es un dict con:
    tipo        — 'incompatibilidad' | 'cota_superior' | 'contexto' | 'proceso'
    severidad   — 'critico' | 'importante' | 'ajustable'
    key         — str identificador único
    titulo      — str descripción corta
    detalle     — str explicación y corrección sugerida
    ingredientes — list[str] ingredientes involucrados
"""

from constants import (
    PRODUCT_SORBETE, PRODUCT_GRANITA, PRODUCT_VEGANO,
    PRODUCT_FROZEN, PRODUCT_LIGERO,
    MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD,
)


# ─────────────────────────────────────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────────────────────────────────────

def verificar(
    lines_with_ings: list,
    totals: dict | None = None,
    pct: dict | None = None,
    product_type: str = "Helado/Gelato",
    machine: str = "Ninja Creami Deluxe",
) -> list[dict]:
    """
    Evalúa la formulación contra todas las restricciones registradas.
    Retorna lista de violaciones; lista vacía = sin problemas detectados.
    """
    if not lines_with_ings:
        return []

    vista = _build_vista(lines_with_ings, totals or {}, pct or {})
    violaciones = []

    for regla in _REGLAS:
        resultado = regla(vista, product_type, machine)
        if resultado:
            if isinstance(resultado, list):
                violaciones.extend(resultado)
            else:
                violaciones.append(resultado)

    # Orden: crítico primero
    _orden = {'critico': 0, 'importante': 1, 'ajustable': 2}
    violaciones.sort(key=lambda v: _orden.get(v['severidad'], 9))
    return violaciones


# ─────────────────────────────────────────────────────────────────────────────
# VISTA NORMALIZADA
# ─────────────────────────────────────────────────────────────────────────────

def _build_vista(lines_with_ings: list, totals: dict, pct: dict) -> dict:
    nombres, categorias = [], []
    gramos: dict = {}
    total_g = totals.get('grams', 0) or sum(
        float(g) for _, g, _ in lines_with_ings if g
    )

    for ing, grams, _ in lines_with_ings:
        if not ing or not grams:
            continue
        g = float(grams)
        n = ing.get('name', '').lower().strip()
        c = ing.get('category', '').lower().strip()
        nombres.append(n)
        categorias.append(c)
        gramos[n] = gramos.get(n, 0) + g

    def pct_ing(nombre: str) -> float:
        return gramos.get(nombre, 0) / total_g * 100 if total_g else 0

    return {
        'nombres':    nombres,
        'categorias': categorias,
        'gramos':     gramos,
        'total_g':    total_g,
        'pct_ing':    pct_ing,
        'totals':     totals,
        'pct':        pct,
    }


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE BÚSQUEDA
# ─────────────────────────────────────────────────────────────────────────────

def _buscar(*claves):
    """Retorna función que filtra una lista de strings buscando cualquier clave."""
    def _check(lst: list) -> list:
        return [s for s in lst if any(k in s for k in claves)]
    return _check


_es_carragenina = _buscar('natulac', 'carrageen', 'carragenina', 'kappa', 'iota')
_es_cmc         = _buscar('cmc', 'carboximetil')
_es_pectina     = _buscar('pectina', 'pectin')
_es_guar        = _buscar('guar')
_es_lbg         = _buscar('algarroba', 'lbg', 'locust bean', 'garrofin')
_es_xantana     = _buscar('xantana', 'xanthan')
_es_goma_guar_lbg = _buscar('guar', 'algarroba', 'lbg', 'locust bean', 'garrofin')

_es_goma_espesante = _buscar(
    'cmc', 'carboximetil', 'xantana', 'xanthan', 'guar',
    'pectina', 'pectin', 'natulac', 'carrageen', 'carragenina',
    'algarroba', 'lbg', 'locust bean', 'konjac', 'agar',
    'goma arábiga', 'goma tara', 'goma ghatti',
)

_es_fruta_acida = _buscar(
    'limón', 'lemon', 'lima', 'lime',
    'maracuyá', 'passion', 'fruta de la pasión',
    'piña', 'pineapple', 'tamarindo',
    'naranja', 'mandarina', 'pomelo', 'grapefruit',
    'kiwi', 'fresa', 'frambuesa', 'mora', 'arándano',
    'cereza ácida', 'hibisco',
)

_es_huevo = _buscar(
    'yema', 'huevo', 'egg', 'clara', 'albumina', 'albúmina', 'ovoproduct',
)

_es_yogur = _buscar(
    'yogur', 'yogurt', 'kefir', 'kéfir', 'cultivo', 'ferment', 'probiótic',
)

_KEYWORDS_LACTEO_NOMBRE = (
    'leche entera', 'leche semi', 'leche descremada',
    'crema de leche', 'crema líquida', 'nata ', 'nata,',
    'mantequilla', 'suero de leche', 'whey', 'wpc', 'wpi',
    'caseína', 'caseina', 'mpc', 'queso', 'ricotta',
)


def _nombres_lacteos(nombres: list, categorias: list) -> list:
    """Ingredientes con categoría láctea o nombre claramente lácteo."""
    encontrados = []
    for nom, cat in zip(nombres, categorias):
        if 'lácteo' in cat or 'lacteo' in cat:
            if nom not in encontrados:
                encontrados.append(nom)
        elif any(k in nom for k in _KEYWORDS_LACTEO_NOMBRE):
            if nom not in encontrados:
                encontrados.append(nom)
    return encontrados


def _violacion(tipo, severidad, key, titulo, detalle, ingredientes=None):
    return {
        'tipo':         tipo,
        'severidad':    severidad,
        'key':          key,
        'titulo':       titulo,
        'detalle':      detalle,
        'ingredientes': ingredientes or [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# REGLAS
# ─────────────────────────────────────────────────────────────────────────────

def _r_cmc_carragenina(v, product_type, machine):
    """CMC + Natulac/carragenina → doble red hidrofílica, textura gomosa."""
    cmcs  = _es_cmc(v['nombres'])
    carrs = _es_carragenina(v['nombres'])
    if cmcs and carrs:
        return _violacion(
            'incompatibilidad', 'importante', 'cmc_carragenina',
            "CMC + Carragenina — doble red espesante",
            "Ambos son hidrocoloides fuertes que forman redes independientes. "
            "La superposición produce una textura excesivamente elástica y gomosa "
            "difícil de corregir una vez gelificada. Usa solo uno: CMC para proceso "
            "frío (hidrata sin calentar) o carragenina kappa para proceso caliente "
            "(requiere ≥ 70 °C). Si necesitas los dos efectos, prefiere "
            "Xantana + CMC (sinérgicos, sin doble gelificación).",
            cmcs + carrs,
        )


def _r_carragenina_fruta_acida(v, product_type, machine):
    """Natulac/carragenina + fruta ácida → hidrólisis ácida e irreversible."""
    carrs  = _es_carragenina(v['nombres'])
    frutas = _es_fruta_acida(v['nombres'])
    if carrs and frutas:
        xantana = _es_xantana(v['nombres'])
        aviso_extra = "" if not xantana else " (la Xantana detectada puede mitigar el efecto, pero no elimina el riesgo)"
        return _violacion(
            'incompatibilidad', 'importante', 'carragenina_acida',
            "Carragenina + fruta ácida — riesgo de hidrólisis",
            f"La carragenina se degrada irreversiblemente a pH < 4.5. "
            f"Las frutas ácidas detectadas pueden llevar la mezcla a pH 3.0–4.0, "
            f"causando sinéresis (agua separada) y pérdida total de cuerpo{aviso_extra}. "
            "Alternativas estables en ácido: Goma Xantana (pH 2–8, 0.3–0.5 g/kg) "
            "o Pectina LM con calcio (1–2 g/kg).",
            carrs + frutas,
        )


def _r_pectina_sin_activacion(v, product_type, machine):
    """Pectina HM en base láctea sin fruta ácida → no gelifica en pH neutro."""
    pectinas = _es_pectina(v['nombres'])
    if not pectinas:
        return None
    lacteos = _nombres_lacteos(v['nombres'], v['categorias'])
    frutas  = _es_fruta_acida(v['nombres'])
    if lacteos and not frutas:
        return _violacion(
            'incompatibilidad', 'ajustable', 'pectina_sin_acido',
            "Pectina en base láctea sin fruta ácida — activación dudosa",
            "La pectina de alta metoxilación (HM) requiere pH < 3.5 para gelificar. "
            "Una base láctea sin fruta ácida tiene pH ≈ 6.5, donde la pectina HM "
            "no forma gel. Si ya usas Pectina LM (baja metoxilación), ignora esta "
            "alerta: la LM gelifica con el Ca²⁺ del MSNF independientemente del pH. "
            "Si no sabes cuál tienes, consulta la ficha del proveedor o añade fruta ácida.",
            pectinas,
        )


def _r_multiples_espesantes(v, product_type, machine):
    """3 o más agentes espesantes distintos → sinergia impredecible."""
    gomas = _es_goma_espesante(v['nombres'])
    if len(gomas) >= 3:
        return _violacion(
            'incompatibilidad', 'importante', 'multiples_espesantes',
            f"{len(gomas)} agentes espesantes simultáneos — sinergia impredecible",
            "Tres o más hidrocoloides crean interacciones cruzadas difíciles de "
            "controlar: la textura puede variar drásticamente con temperatura, "
            "pH o tiempo de maduración. Las combinaciones documentadas y confiables "
            "son de a dos: Guar + LBG (1:1, cremosidad), Xantana + Guar (1:2, cuerpo), "
            "CMC + Xantana (0.5:0.3 g/kg, antirecristalización + cuerpo). "
            "Simplifica a máximo 2 espesantes.",
            gomas,
        )


def _r_eritritol_exceso(v, product_type, machine):
    """Eritritol > 1.5 % del total → efecto frescor/mentolado dominante."""
    eritritol_noms = [n for n in v['nombres'] if 'eritritol' in n]
    if not eritritol_noms:
        return None
    pct_total = sum(v['pct_ing'](n) for n in eritritol_noms)
    if pct_total > 1.5:
        return _violacion(
            'cota_superior', 'importante', 'eritritol_exceso',
            f"Eritritol {pct_total:.1f}% — efecto mentolado sobre umbral (1.5%)",
            f"El eritritol tiene calor de disolución endotérmica alto: sobre el 1.5% "
            f"del total produce un frescor/mentolado que domina el perfil sensorial "
            f"y puede ocultar los sabores del helado. Actual: {pct_total:.1f}%. "
            "Sustituye el exceso por Alulosa (POD=0.70, efecto neutro, sin mentolado) "
            "o Trehalosa (POD=0.45, crioprotector natural).",
            eritritol_noms,
        )


def _r_maltitol_exceso(v, product_type, machine):
    """Maltitol > 12 % → umbral de efecto laxante osmótico documentado."""
    malt = [n for n in v['nombres'] if 'maltitol' in n]
    if not malt:
        return None
    pct_total = sum(v['pct_ing'](n) for n in malt)
    if pct_total > 12.0:
        return _violacion(
            'cota_superior', 'critico', 'maltitol_laxante',
            f"Maltitol {pct_total:.1f}% — umbral laxante superado (> 12%)",
            f"El maltitol no absorbido fermenta en el colon. La dosis individual "
            f"de efecto laxante es ≈ 10–12 g, equivalente a ≈ 80–100 g de helado "
            f"a {pct_total:.1f}% de contenido. Puede causar hinchazón, diarrea osmótica "
            "y calambres. Reduce a < 12% o sustituye parcialmente con Alulosa "
            "(efecto GI mínimo documentado) o Eritritol (≤ 1.5%).",
            malt,
        )


def _r_vegano_con_lacteo(v, product_type, machine):
    """Producto Vegano con ingrediente de categoría o nombre lácteo."""
    if product_type != PRODUCT_VEGANO:
        return None
    lacteos = _nombres_lacteos(v['nombres'], v['categorias'])
    if lacteos:
        return _violacion(
            'contexto', 'critico', 'vegano_con_lacteo',
            "Gelato Vegano contiene ingredientes lácteos",
            "El tipo de producto es 'Gelato Vegano' pero se detectaron ingredientes "
            "de origen animal. Esto invalida la declaración vegana y puede representar "
            "un problema de alérgenos (lácteos). Sustituye por: "
            "leche de coco/avena/almendra, crema de coco, grasa de coco en lugar de "
            "mantequilla, proteína de guisante o arroz en lugar de WPC/WPI.",
            lacteos[:6],
        )


def _r_sorbete_con_grasa(v, product_type, machine):
    """Sorbete/Granita con grasa > 2% → pierde definición técnica de sorbete."""
    if product_type not in (PRODUCT_SORBETE, PRODUCT_GRANITA):
        return None
    fat_pct = v['pct'].get('fat_pct', 0)
    if fat_pct > 2.0:
        return _violacion(
            'contexto', 'importante', 'sorbete_grasa',
            f"Sorbete con {fat_pct:.1f}% grasa — fuera de definición",
            f"La definición estándar de sorbete es ≤ 2% de grasa total. "
            f"Grasa actual: {fat_pct:.1f}%. Si la grasa viene de leche de coco, "
            "considera cambiar el tipo a 'Gelato Vegano'. Si viene de lácteos, "
            "considera 'Helado/Gelato'. Un sorbete real debe ser a base de fruta "
            "con agua/azúcar y sin grasas significativas.",
        )


def _r_ligero_grasa_alta(v, product_type, machine):
    """Helado Ligero con grasa > 6% → no cumple criterio FAO/Codex light."""
    if product_type != PRODUCT_LIGERO:
        return None
    fat_pct = v['pct'].get('fat_pct', 0)
    if fat_pct > 6.0:
        return _violacion(
            'contexto', 'importante', 'ligero_grasa_alta',
            f"Helado Ligero con {fat_pct:.1f}% grasa — supera límite light",
            "El criterio FAO/Codex para helado 'light' es ≤ 3 g de grasa por "
            "100 g de producto (o al menos 50% menos que el estándar equivalente). "
            f"Grasa actual: {fat_pct:.1f}% — supera incluso el rango objetivo "
            "de 2–6% para Helado Ligero. Reduce crema o mantequilla y reemplaza "
            "con leche entera o leche descremada.",
        )


def _r_frozen_sin_yogur(v, product_type, machine):
    """Frozen Yogurt sin yogurt ni cultivos → nombre de producto incorrecto."""
    if product_type != PRODUCT_FROZEN:
        return None
    yogures = _es_yogur(v['nombres'])
    if not yogures:
        return _violacion(
            'contexto', 'ajustable', 'frozen_sin_yogur',
            "Frozen Yogurt sin yogurt ni cultivos detectados",
            "El tipo declarado es 'Frozen Yogurt' pero no se detectó yogurt, "
            "kefir ni cultivos vivos. Sin yogurt, el producto es técnicamente "
            "un helado ligero o sorbete lácteo. Añade yogur natural entero o "
            "descremado (al menos 15–20% de la mezcla base) para obtener el perfil "
            "ácido característico, los probióticos y la denominación correcta.",
        )


def _r_huevo_sin_pasteurizar(v, product_type, machine):
    """Yema/huevo en receta → pasteurización obligatoria por Salmonella."""
    huevos = _es_huevo(v['nombres'])
    if huevos:
        return _violacion(
            'proceso', 'critico', 'huevo_pasteurizacion',
            "Huevo en receta — pasteurización obligatoria",
            "Yema, clara o huevo entero crudos son vector potencial de Salmonella "
            "enteritidis. La pasteurización es obligatoria antes de congelar: "
            "68 °C durante 15 segundos (yema) o 63 °C × 30 min (baño María). "
            "Nota técnica: la clara desnaturaliza desde 60 °C — un leve espesado "
            "en la base es normal y aceptable. "
            "Alternativa segura y lista: yema pasteurizada comercial (líquida o polvo).",
            huevos,
        )


def _r_guar_lbg_en_creami(v, product_type, machine):
    """Guar o LBG en Ninja Creami → no se activan en proceso frío."""
    if machine not in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD):
        return None
    guar_lbg = _es_goma_guar_lbg(v['nombres'])
    if guar_lbg:
        return _violacion(
            'proceso', 'importante', 'guar_lbg_creami',
            f"Goma Guar / LBG en {machine} — no se activan en proceso frío",
            "La Goma Guar y la Goma de Algarroba (LBG) necesitan 80–85 °C para "
            "hidratarse y desplegar su viscosidad. El flujo Ninja Creami congela "
            "directamente sin etapa de pasteurización caliente, por lo que estos "
            "espesantes no alcanzarán su temperatura de activación. Resultado: "
            "espesamiento débil, textura granulosa o sensación de agua libre. "
            "En Creami usa Goma Xantana (hidrata en frío, pH 2–8) o CMC "
            "(también activo en frío, 0.5–1.0 g/kg).",
            guar_lbg,
        )


def _r_alcohol_en_creami(v, product_type, machine):
    """Alcohol con Creami: el proceso mecánico amplifica el efecto ablandador."""
    if machine not in (MACHINE_CREAMI_DELUXE, MACHINE_CREAMI_STANDARD):
        return None
    alc_nombres = [n for n in v['nombres']
                   if any(k in n for k in ('ron', 'vodka', 'whisky', 'whiskey',
                                           'tequila', 'ginebra', 'gin', 'amaretto',
                                           'limoncello', 'baileys', 'kahlú', 'cointreau',
                                           'kirsch', 'sambuca', 'licor', 'alcohol'))]
    if not alc_nombres:
        return None
    # Solo alertar si el diagnóstico de alcohol aún no es crítico
    # (ethanol > 4% ya lo detecta diagnostics.py como CRITICAL)
    eth_pct = sum(
        v['gramos'].get(n, 0) for n in alc_nombres
    ) / v['total_g'] * 100 if v['total_g'] else 0
    if 0 < eth_pct < 4.0:
        return _violacion(
            'proceso', 'ajustable', 'alcohol_creami',
            "Alcohol + Ninja Creami — compensar textura",
            "El alcohol baja el punto de congelación y la Creami procesa la base "
            "a temperatura fija. Con alcohol, la base queda más blanda y el procesado "
            "puede ser irregular. Compensa añadiendo 15–25 g extra de Dextrosa o "
            "Trehalosa para subir los sólidos y contrabalancear el PAC del etanol. "
            "Procesa la base bien congelada (mínimo 24 h a −18 °C).",
            alc_nombres,
        )


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRO DE REGLAS (orden de evaluación)
# ─────────────────────────────────────────────────────────────────────────────

_REGLAS = [
    # Incompatibilidades de estabilizantes
    _r_cmc_carragenina,
    _r_carragenina_fruta_acida,
    _r_pectina_sin_activacion,
    _r_multiples_espesantes,
    # Cotas de edulcorantes
    _r_eritritol_exceso,
    _r_maltitol_exceso,
    # Contradicciones de tipo de producto
    _r_vegano_con_lacteo,
    _r_sorbete_con_grasa,
    _r_ligero_grasa_alta,
    _r_frozen_sin_yogur,
    # Requisitos de proceso
    _r_huevo_sin_pasteurizar,
    _r_guar_lbg_en_creami,
    _r_alcohol_en_creami,
]
