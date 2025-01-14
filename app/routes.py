from flask import Blueprint, request, jsonify, render_template, current_app, redirect, url_for
import os
from .utils import extract_text_from_pdf, analyze_cv_text, generate_questions, calculate_score, calculate_score_based_on_answers
from bson.objectid import ObjectId
from openai import OpenAI

UPLOAD_FOLDER = "uploads/"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

routes = Blueprint("routes", __name__)
# Definir las inteligencias y sus preguntas asociadas
INTELLIGENCES = {
    "Comunicativa": [9, 10, 17, 22, 30],
    "Razonamiento Matemático": [5, 7, 15, 20, 25],
    "Visual Semiótica": [1, 11, 14, 23, 27],
    "Motriz": [8, 16, 19, 21, 29],
    "Rítmica": [3, 4, 13, 24, 28],
    "Autoconocimiento": [2, 6, 26, 31, 33],
    "Social": [12, 18, 32, 34, 35]
}

# Definir las competencias y subcompetencias para Habilidades Blandas
SOFT_SKILLS_COMPETENCIES = {
    "Cognitiva": ["Pensamiento analítico", "Respuesta ante los problemas", "Iniciativa"],
    "Afectiva": ["Autodominio", "Afrontamiento al estrés"],
    "Social": ["Socialización", "Contribución"],
    "Moral": ["Principios", "Compromiso"],
    "Directriz": ["Liderazgo", "Trabajo colaborativo"],
    "Gestión": ["Programación y orden", "Capacidad didáctica"],
    "Alto potencial": ["Orientación al éxito", "Empuje"]
}

# Definir los rangos para cada subcompetencia en Habilidades Blandas
# Estos rangos deben ajustarse según la documentación específica
SOFT_SKILLS_RANGES = {
    "Pensamiento analítico": {"Muy Bajo": (24, 78), "Bajo": (79, 85), "Medio": (86, 105), "Alto": (106, 115), "Muy Alto": (116, 120)},
    "Respuesta ante los problemas": {"Muy Bajo": (24, 78), "Bajo": (79, 85), "Medio": (86, 105), "Alto": (106, 115), "Muy Alto": (116, 120)},
    "Iniciativa": {"Muy Bajo": (24, 78), "Bajo": (79, 85), "Medio": (86, 105), "Alto": (106, 115), "Muy Alto": (116, 120)},
    "Autodominio": {"Muy Bajo": (24, 78), "Bajo": (79, 85), "Medio": (86, 105), "Alto": (106, 115), "Muy Alto": (116, 120)},
    "Afrontamiento al estrés": {"Muy Bajo": (24, 78), "Bajo": (79, 85), "Medio": (86, 105), "Alto": (106, 115), "Muy Alto": (116, 120)},
    "Socialización": {"Muy Bajo": (24, 78), "Bajo": (79, 85), "Medio": (86, 105), "Alto": (106, 115), "Muy Alto": (116, 120)},
    "Contribución": {"Muy Bajo": (24, 78), "Bajo": (79, 85), "Medio": (86, 105), "Alto": (106, 115), "Muy Alto": (116, 120)},
    "Principios": {"Muy Bajo": (24, 78), "Bajo": (79, 85), "Medio": (86, 105), "Alto": (106, 115), "Muy Alto": (116, 120)},
    "Compromiso": {"Muy Bajo": (24, 78), "Bajo": (79, 85), "Medio": (86, 105), "Alto": (106, 115), "Muy Alto": (116, 120)},
    "Liderazgo": {"Muy Bajo": (24, 78), "Bajo": (79, 85), "Medio": (86, 105), "Alto": (106, 115), "Muy Alto": (116, 120)},
    "Trabajo colaborativo": {"Muy Bajo": (24, 78), "Bajo": (79, 85), "Medio": (86, 105), "Alto": (106, 115), "Muy Alto": (116, 120)},
    "Programación y orden": {"Muy Bajo": (24, 78), "Bajo": (79, 85), "Medio": (86, 105), "Alto": (106, 115), "Muy Alto": (116, 120)},
    "Capacidad didáctica": {"Muy Bajo": (24, 78), "Bajo": (79, 85), "Medio": (86, 105), "Alto": (106, 115), "Muy Alto": (116, 120)},
    "Orientación al éxito": {"Muy Bajo": (24, 78), "Bajo": (79, 85), "Medio": (86, 105), "Alto": (106, 115), "Muy Alto": (116, 120)},
    "Empuje": {"Muy Bajo": (24, 78), "Bajo": (79, 85), "Medio": (86, 105), "Alto": (106, 115), "Muy Alto": (116, 120)}
}
@routes.route("/")
def index():
    return render_template("index.html")

@routes.route("/upload_cv", methods=["POST", "GET"])
def upload_cv():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            return jsonify({"error": "No file uploaded or selected"}), 400

        if not file.filename.lower().endswith(".pdf"):
            return jsonify({"error": "Only PDF files are allowed"}), 400

        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        # Extraer texto del CV
        text = extract_text_from_pdf(file_path)
        analysis = analyze_cv_text(text)
        skills = [skill.strip() for skill in analysis.split(",")]
        questions = generate_questions(skills)
        score = calculate_score(skills)

        user_data = {
            "name": request.form.get("name", "Anonymous"),
            "cv_path": file_path,
            "analysis": analysis,
            "questions": questions,
            "score": score,
        }
        user_id = current_app.mongo.db.users.insert_one(user_data).inserted_id

        # >>> En lugar de devolver JSON, redirigimos a soft_skills_questionnaire:
        return redirect(url_for("routes.multiple_intelligences_questionnaire", user_id=user_id))

    return render_template("upload.html")

@routes.route("/questions/<user_id>")
def questions(user_id):
    user_data = current_app.mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user_data:
        return jsonify({"error": "User not found"}), 404

    return render_template("questions.html", questions=user_data["questions"])

@routes.route("/score/<user_id>")
def score(user_id):
    user_data = current_app.mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user_data:
        return jsonify({"error": "User not found"}), 404

    return render_template(
        "score.html",
        score=user_data["score"],
        skills=[skill.strip() for skill in user_data["analysis"].split(",")],
        questions=user_data["questions"]
    )

@routes.route("/answer_questions/<user_id>")
def answer_questions(user_id):
    user_data = current_app.mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user_data:
        return jsonify({"error": "User not found"}), 404

    return render_template(
        "answer_questions.html",
        user_id=user_id,
        questions=user_data["questions"]
    )

@routes.route("/submit_answers/<user_id>", methods=["POST"])
def submit_answers(user_id):
    answers = request.form.getlist("answers")
    user_data = current_app.mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user_data:
        return jsonify({"error": "User not found"}), 404

    # Recuperar puntaje inicial del CV
    initial_score = user_data.get("score", 0)

    # Calcular puntaje basado en las respuestas
    questions = user_data["questions"]
    response_score, explanations = calculate_score_based_on_answers(questions, answers)

    # Combinar ambos puntajes
    total_score = initial_score + response_score
    total_score = min(total_score, 100)  # Escalar a un máximo de 100

    # Generar una explicación detallada usando GPT
    client = OpenAI(api_key=current_app.config["OPENAI_API_KEY"])
    messages = [
        {"role": "system", "content": "Eres un experto en evaluación de habilidades."},
        {
            "role": "user",
            "content": (
                f"Basándote en estos datos:\n"
                f"- Puntaje inicial basado en el CV: {initial_score}\n"
                f"- Puntaje basado en respuestas: {response_score}\n"
                f"- Total: {total_score}\n"
                f"Explicaciones individuales:\n{chr(10).join(explanations)}\n"
                "Genera una explicación clara y concisa con un máximo de 3 puntos clave para destacar las fortalezas del candidato."
            )
        }
    ]

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=300,
        temperature=0.7
    )
    detailed_explanation = completion.choices[0].message.content.strip()

    # Actualizar la base de datos con el nuevo puntaje y explicación
    current_app.mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "answers": answers,
                "score": total_score,
                "response_score": response_score,
                "initial_score": initial_score,
                "explanations": explanations,
                "detailed_explanation": detailed_explanation,
            }
        }
    )

    return redirect(url_for("routes.dashboard", user_id=user_id))


@routes.route("/dashboard/<user_id>", methods=["GET"])
def dashboard(user_id):
    user_data = current_app.mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user_data:
        return jsonify({"error": "User not found"}), 404

    # Información existente
    total_score = user_data.get("score", 0)
    initial_score = user_data.get("initial_score", 0)
    response_score = user_data.get("response_score", 0)
    detailed_explanation = user_data.get("detailed_explanation", "Explicación no disponible.")

    # Evaluación de Inteligencias Múltiples
    multiple_intelligences_answers = user_data.get("multiple_intelligences_answers", [])
    intelligences_scores = {}
    for intelligence, questions in INTELLIGENCES.items():
        score = 0
        for q_num in questions:
            if q_num <= len(multiple_intelligences_answers):
                if multiple_intelligences_answers[q_num - 1] == "true":
                    score += 1
        if score >= 4:
            level = "Nivel Alto"
        elif score == 3:
            level = "Nivel Medio"
        else:
            level = "Nivel Bajo"
        intelligences_scores[intelligence] = {"score": score, "level": level}

    # Evaluación de Habilidades Blandas
    soft_skills_answers = user_data.get("soft_skills_answers", [])
    # Asumiendo que soft_skills_answers es una lista de respuestas ordenadas de 1 a 80
    # Mapeamos cada respuesta a su valor numérico (1-5)
    soft_skills_scores = {comp: {sub: 0 for sub in subs} for comp, subs in SOFT_SKILLS_COMPETENCIES.items()}

    # Crear una lista ordenada de subcompetencias
    subcompetencies = []
    for comp, subs in SOFT_SKILLS_COMPETENCIES.items():
        for sub in subs:
            subcompetencies.append((comp, sub))

    # Asumimos que las preguntas 1-80 están distribuidas en el orden de subcompetencies
    for i, (comp, sub) in enumerate(subcompetencies):
        if i < len(soft_skills_answers):
            try:
                answer = int(soft_skills_answers[i])
                if 1 <= answer <=5:
                    points = answer
                else:
                    points = 0  # En caso de respuestas no válidas
            except ValueError:
                points = 0  # En caso de respuestas no válidas
            soft_skills_scores[comp][sub] += points

    # Clasificación de cada subcompetencia
    soft_skills_classification = {comp: {} for comp in SOFT_SKILLS_COMPETENCIES.keys()}
    for comp, subs in SOFT_SKILLS_COMPETENCIES.items():
        for sub in subs:
            score = soft_skills_scores[comp][sub]
            classification = "No definido"
            ranges = SOFT_SKILLS_RANGES.get(sub, {})
            for level, (low, high) in ranges.items():
                if low <= score <= high:
                    classification = level
                    break
            soft_skills_classification[comp][sub] = {"score": score, "classification": classification}

    return render_template(
        "dashboard.html",
        user_id=user_id,
        total_score=total_score,
        initial_score=initial_score,
        response_score=response_score,
        detailed_explanation=detailed_explanation,
        intelligences_scores=intelligences_scores,
        soft_skills_scores=soft_skills_scores,
        soft_skills_classification=soft_skills_classification
    )

@routes.route("/process_cv", methods=["POST"])
def process_cv():
    try:
        file = request.files.get("file")
        name = request.form.get("name")
        if not file or not name:
            return jsonify({"error": "Name and file are required"}), 400

        if not file.filename.lower().endswith(".pdf"):
            return jsonify({"error": "Only PDF files are allowed"}), 400

        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        text = extract_text_from_pdf(file_path)
        analysis = analyze_cv_text(text)
        skills = [skill.strip() for skill in analysis.split(",")]
        questions = generate_questions(skills)
        score = calculate_score(skills)

        user_data = {
            "name": name,
            "cv_path": file_path,
            "analysis": analysis,
            "questions": questions,
            "score": score,
        }
        user_id = current_app.mongo.db.users.insert_one(user_data).inserted_id

        return redirect(url_for("routes.multiple_intelligences_questionnaire", user_id=user_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@routes.route("/soft_skills_questionnaire/<user_id>", methods=["GET", "POST"])
def soft_skills_questionnaire(user_id):
    user_data = current_app.mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user_data:
        return jsonify({"error": "Usuario no encontrado"}), 404

    if request.method == "POST":
        # Recoger las respuestas individuales de las 80 preguntas
        answers = []
        for i in range(1, 81):
            answer = request.form.get(f"soft{i}")
            if not answer:
                return jsonify({"error": f"Pregunta {i} no ha sido respondida."}), 400
            answers.append(answer)

        # Guardar las respuestas en la base de datos
        current_app.mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"soft_skills_answers": answers}}
        )

        # Redirigir a la siguiente etapa o dashboard
        return redirect(url_for("routes.answer_questions", user_id=user_id))

    # Si es GET, renderizar la plantilla
    # Asegúrate de pasar las preguntas al template
    soft_questions = [
        "Ante la adversidad se me facilita analizar las situaciones.",
        "Me gusta resolver problemas.",
        "Adopto una actitud constructiva.",
        "Pierdo el control cuando los demás no hacen lo que quiero.",
        "Tomo buenas decisiones cuando estoy estresado(a).",
        "Se me facilita iniciar una conversación.",
        "Regularmente colaboro con las personas que necesitan ayuda.",
        "Expongo mis ideas de forma clara.",
        "He tenido problemas con la ley.",
        "Cuando me comprometo a realizar algo lo cumplo.",
        "Me gusta investigar e innovar nuevas soluciones.",
        "Me entusiasma la idea de emprender actividades nuevas.",
        "Me entusiasma crear cosas originales.",
        "Tengo facilidad para convencer a mis compañeros(as) de que mis ideas son mejores.",
        "Propongo estrategias al equipo para resolver dificultades.",
        "Me gusta participar en mis equipos de trabajo.",
        "Planifico con anticipación mis actividades.",
        "Me siento capaz de aprender cosas nuevas.",
        "Doy mi máximo esfuerzo.",
        "Cuando trabajo en equipo propongo nuevas ideas.",
        "Soy capaz de analizar diferentes propuestas antes de tomar una decisión.",
        "Me gusta investigar y obtener ideas para la resolución de problemas.",
        "Identifico oportunidades en situaciones complicadas que otros no aprecian.",
        "Cuando me enojo reacciono de forma violenta.",
        "En momentos de estrés me mantengo amable.",
        "Se me facilita interactuar con otras personas.",
        "Disfruto ayudar a mis compañeros(as) en clase.",
        "Comunico mis emociones de forma espontánea, sin dificultad.",
        "Respeto las normas y reglamentos de la escuela.",
        "Mis compañeros(as) me consideran una persona confiable y responsable.",
        "Me abro a nuevas ideas y experiencias.",
        "Cuando me propongo realizar algo no paro hasta conseguirlo.",
        "Planteo soluciones originales a los problemas que se me presentan.",
        "Hago cambiar de opinión a mis compañeros(as) con facilidad.",
        "Me gusta tomar la iniciativa para emprender nuevas acciones.",
        "Fomento la motivación de mis compañeros(as) creando un ambiente agradable de trabajo.",
        "Organizo mis actividades anticipadamente.",
        "Aplico fácilmente mis conocimientos en situaciones nuevas.",
        "Me gusta resolver problemas difíciles.",
        "Elaboro por iniciativa propia nuevas actividades y proyectos.",
        "Cuando se me presenta una dificultad soy capaz de analizar sus diferentes aspectos.",
        "Analizo las causas de los problemas detenidamente.",
        "Preveo los problemas y planteo soluciones de forma anticipada.",
        "Cuando me molesto alzo la voz.",
        "Cuando estoy presionado(a) me cuesta trabajo resolver problemas.",
        "Se me facilita hacer amigos(as).",
        "Me siento capaz de ayudar a mis compañeros(as) y al mismo tiempo realizar mis propias actividades.",
        "Cuando transmito una idea verifico que me hayan comprendido.",
        "Me gusta respetar las normas escolares.",
        "Mis profesores(as) consideran que soy una persona responsable.",
        "Soy una persona flexible que me adapto a las diferentes situaciones que se me presentan.",
        "Me gusta asumir riesgos cuando mis profesores(as) me piden realizar nuevas actividades.",
        "Manejo los materiales de forma creativa.",
        "Se me facilita convencer a las y los demás con argumentos sólidos.",
        "Me gusta ser líder.",
        "Me siento apreciado(a) cuando trabajo en equipo.",
        "Administro mi tiempo en función de prioridades.",
        "Aplico el conocimiento en situaciones nuevas.",
        "Alcanzo mis objetivos.",
        "Busco nuevas formas de hacer las cosas.",
        "Cuando tengo un problema puedo encontrar soluciones inmediatas.",
        "Cuando se me presenta un problema selecciono la información importante, invierto tiempo y esfuerzo hasta solucionarlo.",
        "Cuando trabajo en equipo, puedo anticipar los problemas y propongo soluciones.",
        "Digo cosas de las que después me arrepiento.",
        "Cuando se me presenta una crisis soy capaz de mantener la calma.",
        "Mis compañeros(as) opinan que soy sociable.",
        "Me gusta el trabajo colaborativo.",
        "Me es fácil comunicarme con mis compañeros(as).",
        "Mi conducta y actitud son transparentes.",
        "Me resulta fácil asumir las consecuencias de mis actos.",
        "Cumplo con mis actividades escolares, aunque me cueste trabajo.",
        "Aun cuando me cueste trabajo realizar alguna actividad, la concluyo.",
        "Utilizo mi creatividad para inventar cosas originales.",
        "Convenzo a mis compañeros(as) fácilmente de que tengo la razón.",
        "Mis compañeros(as) confían en mi opinión para tomar decisiones.",
        "Mis compañeros(as) se sienten a gusto trabajando conmigo.",
        "Soy una persona organizada.",
        "Aprendo de nuevas experiencias con facilidad.",
        "Trabajo por lograr la excelencia en todo lo que hago.",
        "Busco oportunidades de mejora sin que me lo sugieran.",
        "Me es fácil identificar las causas de una situación complicada.",
        "Tengo la costumbre de analizar las ventajas y desventajas de las posibles soluciones a un problema.",
        "Veo los problemas como oportunidades.",
        "Pierdo los estribos y me dan ganas de tirar y romper cosas cuando me molesto.",
        "Cuando estoy estresado(a) me cuesta trabajo conciliar el sueño.",
        "Con frecuencia hago amigos(as) en la escuela.",
        "Mis compañeros(as) consideran que soy una persona colaborativa.",
        "Me es fácil comunicarme con mis profesores(as).",
        "Realizo mis actos de forma correcta y adecuada.",
        "Me comprometo con mis compañeros(as) cuando trabajo en equipo.",
        "Me adapto a nuevas situaciones.",
        "Me esfuerzo para concluir las actividades y trabajos escolares.",
        "Con los materiales de que dispongo elaboro objetos creativos.",
        "Influyo en las ideas de mis compañeros(as).",
        "Cuando trabajo en equipo con frecuencia asumo el liderazgo.",
        "Acepto los acuerdos de mi equipo de trabajo.",
        "Organizo mis actividades antes de empezar un proyecto.",
        "Aprendo de mis equivocaciones.",
        "Cuando trabajo en equipo me gusta realizar las actividades más complejas.",
        "Planteo propuestas para la solución de problemas."
    ]
    return render_template("soft_skills_questionnaire.html", user_id=user_id, soft_questions=soft_questions)


@routes.route("/multiple_intelligences_questionnaire/<user_id>", methods=["GET", "POST"])
def multiple_intelligences_questionnaire(user_id):
    user_data = current_app.mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user_data:
        return jsonify({"error": "User not found"}), 404

    if request.method == "POST":
        # Obtener todas las claves que empiezan con 'q' y siguen con un número
        form_keys = request.form.keys()
        q_keys = [key for key in form_keys if key.startswith('q') and key[1:].isdigit()]
        total_intelligence_questions = len(q_keys)

        answers = []
        for i in range(1, total_intelligence_questions + 1):
            answer = request.form.get(f"q{i}")
            if not answer:
                return jsonify({"error": f"Pregunta {i} no ha sido respondida."}), 400
            answers.append(answer)

        # Guardar las respuestas en la base de datos
        current_app.mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"multiple_intelligences_answers": answers}}
        )

        # Redirigir al siguiente cuestionario o al dashboard
        return redirect(url_for("routes.soft_skills_questionnaire", user_id=user_id))

    # Si es GET, renderizar la plantilla con las preguntas correspondientes
    questions = [
        "Si me preguntan cómo llegar a una ubicación, prefiero hacer un croquis que explicarlo verbalmente.",
        "Cuando me siento molesto(a) o feliz, sé exactamente el motivo.",
        "Canto, toco o alguna vez he tocado algún instrumento musical.",
        "La música me ayuda a identificar mis emociones.",
        "Tengo facilidad para hacer cálculos aritméticos de forma mental y con rapidez.",
        "Prefiero realizar operaciones matemáticas empleando la calculadora que mentalmente.",
        "Se me facilita aprender actividades físicas que requieren destreza como andar en patineta, bicicleta, etc.",
        "Expreso lo que pienso con facilidad cuando platico con mis compañeros(as).",
        "Gozo cuando participo en una buena conversación.",
        "Tengo buen sentido de orientación espacial (norte, sur, este, oeste).",
        "Disfruto reunir a mis amigos(as) en fiestas y eventos.",
        "Necesito escuchar música para sentirme bien.",
        "Se me facilita entender instructivos y diagramas.",
        "Me gustan los juegos de destreza, crucigramas y videojuegos.",
        "Se me facilita realizar trabajos de construcción como maquetas, esculturas, etc.",
        "Tengo talento para identificar el significado de las palabras.",
        "Tengo facilidad para girar mentalmente un objeto.",
        "Hay canciones o música que me recuerdan acontecimientos importantes de mi vida.",
        "Me gusta trabajar con cálculos, números y figuras geométricas.",
        "Disfruto del silencio porque me permite meditar sobre cómo me siento.",
        "Mirar construcciones nuevas me da una sensación de bienestar.",
        "Me gusta tomar nota en mis clases.",
        "Regularmente identifico las señales y expresiones de mi rostro.",
        "Reconozco fácilmente los estados de ánimo de mis compañeros(as).",
        "Soy capaz de identificar mis sentimientos y emociones.",
        "Me doy cuenta fácilmente de lo que piensan mis compañeros(as) de mí."
    ]
    return render_template("multiple_intelligences_questionnaire.html", user_id=user_id, questions=questions)
