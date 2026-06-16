"""Small display helpers for Spanish dashboard labels."""

from __future__ import annotations

import pandas as pd


VALUE_TRANSLATIONS = {
    "Panama City": "Ciudad de Panamá",
    "panama city": "Ciudad de Panamá",
    "General": "Variada",
    "Contemporanea": "Contemporánea",
    "Latinoamericana, Contemporanea, Panameña": "Latinoamericana, Contemporánea, Panameña",
    "restaurantguru": "RestaurantGuru",
    "degusta": "Degusta",
    "english": "Inglés",
    "spanish": "Español",
    "mixed": "Mixto",
    "en": "Inglés",
    "es": "Español",
    "positive": "positivo",
    "negative": "negativo",
    "neutral": "neutral",
}


COLUMN_LABELS = {
    "restaurant_id": "ID",
    "restaurant_name": "Restaurante",
    "category": "Categoría",
    "location": "Ubicación",
    "price_range": "Rango de precio",
    "overall_rating": "Calificación general",
    "food_rating": "Calificación de comida",
    "service_rating": "Calificación de servicio",
    "ambiance_rating": "Calificación de ambiente",
    "review_text": "Reseña",
    "review_date": "Fecha de reseña",
    "reviewer_name": "Autor",
    "source": "Fuente",
    "review_language": "Idioma",
    "word_count": "Cantidad de palabras",
    "char_count": "Cantidad de caracteres",
    "avg_word_length": "Longitud promedio de palabra",
    "cluster": "Grupo",
}


def translate_value(value):
    """Translate common data values without changing source data."""
    if pd.isna(value):
        return value
    return VALUE_TRANSLATIONS.get(str(value), value)


def translate_series(series: pd.Series) -> pd.Series:
    """Translate known values in a pandas Series for display controls."""
    return series.map(translate_value)


def translate_review_text(text):
    """Translate known English reviews and common metadata into Spanish."""
    if pd.isna(text):
        return text

    text = str(text)
    exact_translations = {
        "The food and service were really good. Staff were very friendly and welcoming. Will definitely come again. Thank you. Price per person PAB 1520 Food 5 Service 5 Atmosphere 5":
            "La comida y el servicio fueron muy buenos. El personal fue amable y atento. Definitivamente volvería. Precio por persona: PAB 15-20. Comida 5, servicio 5, ambiente 5.",
        "Muy bueno Food 4 Service 5 Atmosphere 5":
            "Muy bueno. Comida 4, servicio 5, ambiente 5.",
        "Great service! Jose did an amazing job! Meal type Other Price per person PAB 1520 Food 5 Service 5 Atmosphere 5":
            "Excelente servicio. José hizo un trabajo increíble. Tipo de comida: otro. Precio por persona: PAB 15-20. Comida 5, servicio 5, ambiente 5.",
        "My waiters name was Christopher and he gave great customer service, and the food was great, was happy to enjoy Applebees while visiting here in Panama. Meal type Dinner Food 5 Service 5 Atmosphere 5":
            "Mi mesero se llamaba Christopher y brindó un excelente servicio al cliente. La comida estuvo muy buena y fue agradable disfrutar Applebee's durante la visita a Panamá. Tipo de comida: cena. Comida 5, servicio 5, ambiente 5.",
        "All good. Maria and Andrea were very nice Meal type Dinner Food 5 Service 4 Atmosphere 5":
            "Todo bien. María y Andrea fueron muy amables. Tipo de comida: cena. Comida 5, servicio 4, ambiente 5.",
    }
    if text in exact_translations:
        return exact_translations[text]

    prefix_translations = [
        (
            "The food and service were really good",
            "La comida y el servicio fueron muy buenos. El personal fue muy amable y acogedor. Definitivamente volvería. Gracias. Precio por persona: PAB 15-20. Comida 5, servicio 5, ambiente 5. Platos recomendados: Sugoi Roll y gyosas. Opciones vegetarianas: buena opción. Restricciones alimentarias: bueno."
        ),
        (
            "Salsipuedes Restaurant After a long humid day",
            "Salsipuedes Restaurant. Después de un día largo y húmedo en el bosque, pasamos por este hotel y decidimos entrar. La ubicación y el montaje son preciosos, y los meseros están bien entrenados y son educados. Como detalle curioso, cobran el agua que colocan en la mesa. El bartender sabe muy bien lo que hace: cada cóctel que probamos estaba delicioso y bien balanceado. El menú del chef se veía fantástico, con mucha variedad y color. Recibimos chips de plátano y pan panameño caliente de cortesía para empezar. El ceviche de salmón fue colorido, ácido, graso, crujiente y suave; tocaba todas las notas y fue un plato excelente. El curry afrocaribeño tenía arroz con coco muy bien sazonado y una presentación tradicional en hoja de plátano, aunque algunos vegetales y el pollo pudieron estar mejor. La causa con camarones estuvo muy bien presentada y delicada. Comida 4, servicio 4, ambiente 4. Tipo de comida: almuerzo. Precio por persona: PAB 45-50."
        ),
        (
            "Kaandela Restaurant is an absolute gem",
            "Kaandela Restaurant es una joya en el centro histórico de Panamá. Está ubicado en el corazón de la ciudad, a pocos minutos de la catedral, rodeado de arquitectura impresionante y vistas que crean un ambiente memorable. Luis Afu, gerente del restaurante, explicó con mucho detalle la preparación de los platos y las opciones de maridaje. El personal fue fantástico: cálido, atento y muy conocedor. También tuvimos la oportunidad de conocer y agradecer personalmente al chef José Aparicio. Cada plato estaba lleno de sabor, muy bien presentado y con una ejecución excelente. Definitivamente volvería para seguir disfrutando su comida, cultura y energía. Muy recomendado."
        ),
        (
            "What a great experience Aya la Vida was",
            "Qué gran experiencia fue Aya la Vida. Fuimos por recomendación de amigos y salimos muy contentos. El restaurante es amplio, con mesas de distintos tamaños para grupos. La noche que fuimos había música en vivo, lo que hizo la visita aún más divertida. La comida tradicional panameña estuvo deliciosa. Algunas traducciones literales de los platos pueden confundir, pero la ropa vieja estuvo muy buena. Las bebidas también estuvieron bien y los precios fueron razonables. Recomendaría reservar, especialmente para grupos de más de cuatro personas. Tipo de comida: cena. Precio por persona: PAB 40-45. Comida 5, servicio 5, ambiente 5."
        ),
        (
            "the lady at the reception was quite rude",
            "La persona de recepción fue bastante descortés e insistió en que dejáramos más propina, aunque no estábamos satisfechos con la experiencia. Íbamos vestidos de manera casual y nos sentaron al fondo, detrás de una pared, cerca del baño y la cocina, aunque el restaurante estaba casi vacío. Había música en vivo, pero no podíamos ver nada desde donde estábamos. La comida fue regular y el arroz llegó muy poco cocido. Considerando la calidad, nos pareció caro. Tipo de comida: cena. Precio por persona: PAB 20-25. Comida 2, servicio 2, ambiente 5."
        ),
        (
            "We went to Aya La Vida as a group of four",
            "Fuimos a Aya La Vida en un grupo de cuatro y la experiencia fue sobresaliente de principio a fin. Pedimos tres entradas, tres platos fuertes y tres postres; todo estuvo excelente, sin puntos débiles. Cada plato tenía mucho sabor, buena presentación y se sentía preparado con orgullo. Lo que elevó la noche fue Sonny, nuestro mesero: amable, profesional, eficiente y muy acertado con sus recomendaciones. Preparó el steak tartare en la mesa y luego hizo el flambeado de ron para el postre, con mucha energía y buena presentación. La combinación de buena comida, servicio cálido, música en vivo y ambiente panameño hizo que la noche fuera especial. Felicitaciones al equipo de Aya La Vida, especialmente a Sonny. Definitivamente volveremos. Tipo de comida: cena. Precio por persona: PAB 30-35. Comida 5, servicio 5, ambiente 5."
        ),
    ]
    for prefix, translation in prefix_translations:
        if text.startswith(prefix):
            return translation

    replacements = {
        "Meal type": "Tipo de comida",
        "Price per person": "Precio por persona",
        "Food": "Comida",
        "Service": "Servicio",
        "Atmosphere": "Ambiente",
        "Recommended dishes": "Platos recomendados",
        "Vegetarian options": "Opciones vegetarianas",
        "Dietary restrictions": "Restricciones alimentarias",
        "Dinner": "cena",
        "Lunch": "almuerzo",
        "Other": "otro",
        "Good choice": "buena opción",
        "Good": "bueno",
        "pet friendly": "apto para mascotas",
        "Pet friendly": "Apto para mascotas",
        "slices": "porciones",
        "Slices": "Porciones",
        "slice": "porción",
        "Slice": "Porción",
        "rolls": "rollos",
        "Rolls": "Rollos",
        "lunch": "almuerzo",
        "Lunch": "Almuerzo",
        "brunch": "brunch",
        "deliveries": "entregas a domicilio",
        "full recomendado": "muy recomendado",
        "NY style": "estilo Nueva York",
        "NY stule": "estilo Nueva York",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def translate_dashboard_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Translate visible dataframe content used by the dashboard."""
    display_df = df.copy()
    if "review_text" in display_df.columns:
        display_df["review_text"] = display_df["review_text"].map(translate_review_text)
    for col in display_df.select_dtypes(include="object").columns:
        if col != "review_text":
            display_df[col] = translate_series(display_df[col])
    return display_df


def translate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Return a display copy with known values and column labels in Spanish."""
    display_df = df.copy()
    for column in display_df.columns:
        if display_df[column].dtype == "object":
            display_df[column] = translate_series(display_df[column])
    return display_df.rename(columns={k: v for k, v in COLUMN_LABELS.items() if k in display_df.columns})
