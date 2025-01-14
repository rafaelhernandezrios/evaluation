import PyPDF2
from openai import OpenAI
from flask import current_app

def extract_text_from_pdf(pdf_path):
    """Extrae el texto de un archivo PDF."""
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text.strip()

def analyze_cv_text(text):
    """Analiza el texto del CV usando la nueva API de OpenAI."""
    client = OpenAI(api_key=current_app.config["OPENAI_API_KEY"])
    messages = [
        {"role": "system", "content": "Eres un experto en análisis de currículums."},
        {"role": "user", "content": f"Extrae las habilidades duras y blandas así como la experiencia más relevantes del siguiente texto de un CV:\n\n{text}"}
    ]
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=300,
        temperature=0.7
    )
    return completion.choices[0].message.content.strip()

def generate_questions(skills):
    """
    Genera 3 preguntas de habilidades duras y 2 preguntas de habilidades blandas.
    Asegura que cada pregunta esté relacionada con una habilidad específica.
    """
    # Inicializa el cliente de OpenAI
    client = OpenAI(api_key=current_app.config["OPENAI_API_KEY"])

    # Separar habilidades en duras y blandas
    hard_skills = [skill for skill in skills if skill.lower() in ["python", "machine learning", "data analysis"]]
    soft_skills = [skill for skill in skills if skill.lower() in ["teamwork", "communication"]]

    # Asegurar que haya suficientes habilidades para generar preguntas
    if len(hard_skills) < 3:
        hard_skills.extend(["Python", "Machine Learning", "Data Analysis"][:3 - len(hard_skills)])
    if len(soft_skills) < 2:
        soft_skills.extend(["Teamwork", "Communication"][:2 - len(soft_skills)])

    # Mensajes para el modelo
    hard_skills_messages = "\n".join(
        [f"Genera una pregunta específica para evaluar la habilidad '{skill}'." for skill in hard_skills[:3]]
    )
    soft_skills_messages = "\n".join(
        [f"Genera una pregunta específica para evaluar la habilidad '{skill}'." for skill in soft_skills[:2]]
    )

    prompt = (
        f"A continuación, se proporcionan habilidades duras y blandas. Para cada una, genera una pregunta específica "
        f"que permita evaluarla en una entrevista técnica:\n\n"
        f"Habilidades duras:\n{hard_skills_messages}\n\n"
        f"Habilidades blandas:\n{soft_skills_messages}\n\n"
        f"Proporciona exactamente 5 preguntas numeradas, sin texto adicional, como en el ejemplo:\n"
        f"1. ¿Cómo has utilizado Python en tus proyectos y cuál fue tu contribución principal?\n"
        f"2. ¿Puedes describir un caso en el que aplicaste Machine Learning para resolver un problema complejo?\n"
        f"3. ¿Qué herramientas de análisis de datos prefieres y cómo las utilizas?\n"
        f"4. Describe una ocasión en la que tu habilidad de comunicación ayudó a resolver un conflicto en tu equipo.\n"
        f"5. ¿Cómo manejaste una situación bajo presión en un entorno colaborativo?"
    )

    # Llamar al modelo
    messages = [{"role": "user", "content": prompt}]
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=300,
        temperature=0.7
    )

    # Procesar la salida del modelo
    questions = completion.choices[0].message.content.strip().split("\n")
    questions = [q.strip() for q in questions if q.strip()]  # Limpiar preguntas vacías

    # Validar que el número de preguntas sea correcto
    if len(questions) < 5:
        missing_count = 5 - len(questions)
        for i in range(missing_count):
            questions.append(f"{len(questions) + 1}. Pregunta genérica de ejemplo.")

    return questions[:5]


def calculate_score(skills):
    """
    Calcula una puntuación basada en las habilidades detectadas.
    Asigna pesos a ciertas habilidades clave y maneja habilidades repetidas.
    """
    skill_weights = {
        "Python": 10,
        "Machine Learning": 15,
        "Data Analysis": 12,
        "Teamwork": 8,
        "Communication": 5
    }
    unique_skills = set(skills)  # Elimina duplicados
    total_score = sum(skill_weights.get(skill, 5) for skill in unique_skills)
    return min(total_score, 100)

def calculate_score_based_on_answers(questions, answers):
    """
    Calcula un puntaje basado en las respuestas del usuario y proporciona explicaciones detalladas.
    Ahora admite coincidencias parciales y mejora el manejo de entradas.
    """
    # Define palabras clave para habilidades duras y blandas
    skill_keywords = {
        "hard_skills": {
            "Python": ["programming", "automation", "python", "scripting"],
            "Machine Learning": ["models", "ai", "algorithms", "deep learning"],
            "Data Analysis": ["statistics", "visualization", "pandas", "data analysis"],
        },
        "soft_skills": {
            "Communication": ["teamwork", "collaboration", "clear communication", "listening", "presentation"],
            "Teamwork": ["team", "cooperation", "leadership", "helping"],
        }
    }

    # Define los pesos para cada categoría
    weights = {
        "hard_skills": 15,  # Cada habilidad dura tiene más peso
        "soft_skills": 10,  # Cada habilidad blanda tiene menos peso
    }

    # Puntuación inicial
    total_score = 0
    explanations = []  # Lista para almacenar las explicaciones
    evaluated_skills = set()  # Para evitar contar habilidades duplicadas

    # Califica cada respuesta
    for question, answer in zip(questions, answers):
        answer_lower = answer.lower()  # Convertimos la respuesta a minúsculas para coincidencias flexibles
        for category, skills in skill_keywords.items():
            for skill, keywords in skills.items():
                # Verifica si alguna palabra clave está en la respuesta y si no se ha evaluado ya la habilidad
                if skill not in evaluated_skills and any(keyword in answer_lower for keyword in keywords):
                    weight = weights[category]
                    total_score += weight
                    evaluated_skills.add(skill)  # Marca la habilidad como evaluada
                    explanations.append(
                        f"La respuesta '{answer}' demuestra conocimiento en '{skill}' (+{weight} puntos)."
                    )

    # Escalar el puntaje a 100 si es necesario
    total_score = min(total_score, 100)

    # Agregar una explicación general
    if total_score == 0:
        explanations.append("No se detectaron habilidades relevantes en las respuestas.")
    else:
        explanations.append(f"El puntaje total se calculó como {total_score} sobre 100 basado en habilidades duras y blandas.")

    return total_score, explanations

