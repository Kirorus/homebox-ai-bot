"""
AI service for image analysis and item recognition
"""

import asyncio
import base64
import json
import logging
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI

from models.item import ItemAnalysis
from models.location import Location, LocationManager
from config.settings import AISettings

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-powered image analysis"""
    
    def __init__(self, settings: AISettings):
        self.settings = settings
        self.client = AsyncOpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url
        )
    
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 string"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _build_locations_text(self, location_manager: LocationManager) -> str:
        """Build locations text for AI prompt"""
        locations_text = ""
        for loc in location_manager.locations:
            if loc.description:
                locations_text += f"- {loc.name}: {loc.description}\n"
            else:
                locations_text += f"- {loc.name}\n"
        return locations_text
    
    def _build_prompt(self, location_manager: LocationManager, lang: str, caption: Optional[str] = None) -> str:
        """Build AI prompt for image analysis"""
        locations_text = self._build_locations_text(location_manager)
        
        # Add caption information if available
        caption_info = ""
        if caption and caption.strip():
            if lang == 'en':
                caption_info = f"\n\nAdditional information from the photo description: \"{caption}\"\nUse this information to help identify the item more accurately."
            elif lang == 'de':
                caption_info = f"\n\nZusätzliche Informationen aus der Fotobeschreibung: \"{caption}\"\nVerwenden Sie diese Informationen, um den Gegenstand genauer zu identifizieren."
            elif lang == 'fr':
                caption_info = f"\n\nInformations supplémentaires de la description de la photo : \"{caption}\"\nUtilisez ces informations pour identifier l'objet plus précisément."
            elif lang == 'es':
                caption_info = f"\n\nInformación adicional de la descripción de la foto: \"{caption}\"\nUse esta información para identificar el objeto con mayor precisión."
            else:  # ru and fallback
                caption_info = f"\n\nДополнительная информация из описания фото: \"{caption}\"\nИспользуй эту информацию для более точного определения предмета."
        
        # Define prompts for each language
        prompts = {
            'en': f"""You are an expert at identifying household items and organizing them. Analyze this image carefully and provide:

1. **Item Name**: A concise, descriptive name (max 50 chars). Be specific about brand, model, or type when visible.
2. **Description**: A detailed description (max 200 chars) including material, color, condition, and any distinguishing features.
3. **Storage Location**: Choose the most appropriate location from the available options based on the item's typical use, storage requirements, and the location descriptions provided.

**Analysis Guidelines:**
- Look for brand names, model numbers, or text on the item
- Consider the item's size, material, and typical usage
- Think about where this item would logically be stored in a home
- If it's a tool, consider the workspace; if it's clothing, consider the wardrobe area
- For electronics, consider tech storage areas
- **Pay special attention to location descriptions** - they contain important details about what types of items should be stored there
- Match the item's purpose and characteristics with the most suitable location description

**Available Locations (with descriptions):**
{locations_text}{caption_info}

**Important:** Respond ONLY with valid JSON in this exact format:
{{
    "name": "specific item name",
    "description": "detailed description with material, color, condition",
    "suggested_location": "exact location name from the list above"
}}""",
            
            'de': f"""Sie sind ein Experte für die Identifizierung von Haushaltsgegenständen und deren Organisation. Analysieren Sie dieses Bild sorgfältig und geben Sie folgendes an:

1. **Gegenstandsname**: Ein prägnanter, beschreibender Name (max. 50 Zeichen). Seien Sie spezifisch bezüglich Marke, Modell oder Typ, wenn sichtbar.
2. **Beschreibung**: Eine detaillierte Beschreibung (max. 200 Zeichen) einschließlich Material, Farbe, Zustand und besonderen Merkmalen.
3. **Lagerort**: Wählen Sie den am besten geeigneten Ort aus den verfügbaren Optionen basierend auf der typischen Verwendung des Gegenstands, den Lageranforderungen und den bereitgestellten Ortsbeschreibungen.

**Analyse-Richtlinien:**
- Suchen Sie nach Markennamen, Modellnummern oder Text auf dem Gegenstand
- Berücksichtigen Sie die Größe, das Material und die typische Verwendung des Gegenstands
- Denken Sie darüber nach, wo dieser Gegenstand logisch in einem Haus gelagert werden würde
- Wenn es ein Werkzeug ist, denken Sie an den Arbeitsbereich; wenn es Kleidung ist, denken Sie an den Kleiderschrank
- Für Elektronik berücksichtigen Sie Technik-Lagerbereiche
- **Achten Sie besonders auf Ortsbeschreibungen** - sie enthalten wichtige Details darüber, welche Arten von Gegenständen dort gelagert werden sollten
- Passen Sie den Zweck und die Eigenschaften des Gegenstands an die am besten geeignete Ortsbeschreibung an

**Verfügbare Orte (mit Beschreibungen):**
{locations_text}{caption_info}

**Wichtig:** Antworten Sie NUR mit gültigem JSON in diesem exakten Format:
{{
    "name": "spezifischer Gegenstandsname",
    "description": "detaillierte Beschreibung mit Material, Farbe, Zustand",
    "suggested_location": "genauer Ortsname aus der obigen Liste"
}}""",
            
            'fr': f"""Vous êtes un expert en identification d'articles ménagers et en organisation. Analysez attentivement cette image et fournissez :

1. **Nom de l'article** : Un nom concis et descriptif (max 50 caractères). Soyez spécifique concernant la marque, le modèle ou le type quand c'est visible.
2. **Description** : Une description détaillée (max 200 caractères) incluant le matériau, la couleur, l'état et les caractéristiques distinctives.
3. **Emplacement de stockage** : Choisissez l'emplacement le plus approprié parmi les options disponibles basées sur l'utilisation typique de l'article, les exigences de stockage et les descriptions d'emplacements fournies.

**Directives d'analyse :**
- Recherchez les noms de marque, numéros de modèle ou texte sur l'article
- Considérez la taille, le matériau et l'utilisation typique de l'article
- Pensez à l'endroit où cet article serait logiquement stocké dans une maison
- Si c'est un outil, considérez l'espace de travail ; si c'est un vêtement, considérez l'armoire
- Pour l'électronique, considérez les zones de stockage technologique
- **Portez une attention particulière aux descriptions d'emplacements** - elles contiennent des détails importants sur les types d'articles qui devraient y être stockés
- Faites correspondre le but et les caractéristiques de l'article avec la description d'emplacement la plus appropriée

**Emplacements disponibles (avec descriptions) :**
{locations_text}{caption_info}

**Important :** Répondez UNIQUEMENT avec du JSON valide dans ce format exact :
{{
    "name": "nom spécifique de l'article",
    "description": "description détaillée avec matériau, couleur, état",
    "suggested_location": "nom exact de l'emplacement de la liste ci-dessus"
}}""",
            
            'es': f"""Eres un experto en identificación de artículos del hogar y organización. Analiza cuidadosamente esta imagen y proporciona:

1. **Nombre del artículo**: Un nombre conciso y descriptivo (máx. 50 caracteres). Sé específico sobre la marca, modelo o tipo cuando sea visible.
2. **Descripción**: Una descripción detallada (máx. 200 caracteres) incluyendo material, color, condición y características distintivas.
3. **Ubicación de almacenamiento**: Elige la ubicación más apropiada de las opciones disponibles basada en el uso típico del artículo, requisitos de almacenamiento y las descripciones de ubicación proporcionadas.

**Pautas de análisis:**
- Busca nombres de marca, números de modelo o texto en el artículo
- Considera el tamaño, material y uso típico del artículo
- Piensa dónde se almacenaría lógicamente este artículo en una casa
- Si es una herramienta, considera el espacio de trabajo; si es ropa, considera el armario
- Para electrónicos, considera áreas de almacenamiento tecnológico
- **Presta especial atención a las descripciones de ubicación** - contienen detalles importantes sobre qué tipos de artículos deberían almacenarse allí
- Haz coincidir el propósito y características del artículo con la descripción de ubicación más adecuada

**Ubicaciones disponibles (con descripciones):**
{locations_text}{caption_info}

**Importante:** Responde SOLO con JSON válido en este formato exacto:
{{
    "name": "nombre específico del artículo",
    "description": "descripción detallada con material, color, condición",
    "suggested_location": "nombre exacto de la ubicación de la lista anterior"
}}""",
            
            'ru': f"""Ты эксперт по определению предметов домашнего обихода и их организации. Внимательно проанализируй это изображение и предоставь:

1. **Название предмета**: Краткое, описательное название (до 50 символов). Будь конкретным в отношении бренда, модели или типа, когда это видно.
2. **Описание**: Подробное описание (до 200 символов), включающее материал, цвет, состояние и отличительные особенности.
3. **Место хранения**: Выбери наиболее подходящее место из доступных вариантов, основываясь на типичном использовании предмета, требованиях к хранению и описаниях локаций.

**Рекомендации по анализу:**
- Ищи названия брендов, модели или текст на предмете
- Учитывай размер, материал и типичное использование предмета
- Думай о том, где логично хранить этот предмет в доме
- Если это инструмент, подумай о рабочем пространстве; если одежда - о гардеробе
- Для электроники рассмотри области хранения техники
- **Особое внимание удели описаниям локаций** - они содержат важную информацию о том, какие предметы там должны храниться
- Сопоставь назначение и характеристики предмета с наиболее подходящим описанием локации

**Доступные локации (с описаниями):**
{locations_text}{caption_info}

**Важно:** Отвечай ТОЛЬКО валидным JSON в точном формате:
{{
    "name": "конкретное название предмета",
    "description": "подробное описание с материалом, цветом, состоянием",
    "suggested_location": "точное название локации из списка выше"
}}"""
        }
        
        # Return the appropriate prompt or fallback to Russian
        return prompts.get(lang, prompts['ru'])
    
    async def analyze_image(
        self,
        image_path: str,
        location_manager: LocationManager,
        lang: str = 'ru',
        model: Optional[str] = None,
        caption: Optional[str] = None
    ) -> ItemAnalysis:
        """Analyze image and return item analysis"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            base64_image = self.encode_image(image_path)
            prompt = self._build_prompt(location_manager, lang, caption)
            
            # Use selected model or default
            selected_model = model or self.settings.default_model
            logger.info(f"Analyzing image with model: {selected_model}")
            
            response = await self.client.chat.completions.create(
                model=selected_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # Find suggested location
            suggested_location = location_manager.find_best_match(result.get('suggested_location', ''))
            
            analysis = ItemAnalysis(
                name=result.get('name', 'Unknown item'),
                description=result.get('description', 'No description'),
                suggested_location=suggested_location.name if suggested_location else location_manager.locations[0].name,
                model_used=selected_model,
                processing_time=processing_time
            )
            
            logger.info(f"Image analysis successful: {analysis}")
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in image analysis: {e}")
            error_messages = {
                'en': ("Unknown item", "Failed to parse response"),
                'de': ("Unbekannter Gegenstand", "Fehler beim Parsen der Antwort"),
                'fr': ("Article inconnu", "Échec de l'analyse de la réponse"),
                'es': ("Artículo desconocido", "Error al analizar la respuesta"),
                'ru': ("Неизвестный предмет", "Ошибка обработки ответа")
            }
            name, desc = error_messages.get(lang, error_messages['ru'])
            return ItemAnalysis(
                name=name,
                description=desc,
                suggested_location=location_manager.locations[0].name if location_manager.locations else "Unknown"
            )
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            error_messages = {
                'en': ("Unknown item", "Failed to recognize"),
                'de': ("Unbekannter Gegenstand", "Erkennung fehlgeschlagen"),
                'fr': ("Article inconnu", "Échec de la reconnaissance"),
                'es': ("Artículo desconocido", "Reconocimiento fallido"),
                'ru': ("Неизвестный предмет", "Не удалось распознать")
            }
            name, desc = error_messages.get(lang, error_messages['ru'])
            return ItemAnalysis(
                name=name,
                description=desc,
                suggested_location=location_manager.locations[0].name if location_manager.locations else "Unknown"
            )
