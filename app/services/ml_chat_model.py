import math
from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class MLChatModel:
    """Simple TF-IDF retrieval model to keep conversational context."""

    def __init__(self):
        self.examples = [
            ("hola", "Hola, soy tu asistente de estacionamiento. Puedo ver disponibilidad o predecir lugares."),
            ("buenas", "Hola, dime el área y te digo si hay espacio."),
            ("disponible area norte",
             "Puedo consultar áreas con lugares libres, dime el nombre exacto del área."),
            ("hay lugares en estacionamiento norte",
             "¿Quieres que revise Estacionamiento Norte ahora mismo?"),
            ("prediccion 15:00 estacionamiento norte",
             "Dime el área y la hora; estimo la probabilidad de lugar libre."),
            ("estara lleno a las 7",
             "Puedo estimar ocupación futura; indica el área y la hora."),
            ("sin lugar", "Si no hay lugar en un área, puedo sugerir otra con más espacios libres."),
            ("otra area", "Puedo listar las 3 áreas con más lugares libres ahora mismo."),
            ("gracias", "Con gusto. ¿Necesitas algo más?"),
            ("adios", "Hasta luego. Estoy aquí si necesitas otra consulta."),
        ]
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), analyzer="char", min_df=1)
        self._fit()

    def _fit(self):
        corpus = [q for q, _ in self.examples]
        self.tfidf = self.vectorizer.fit_transform(corpus)

    def respond(self, message: str, history_lines: List[str]) -> str:
        msg = message.lower()
        if not msg.strip():
            return "No entendí tu mensaje. Pregunta por disponibilidad o predicción de lugares."

        # Combine message with brief history to bias similarity.
        history_hint = " ".join(history_lines[-4:]) if history_lines else ""
        query = f"{msg} {history_hint}".strip()

        q_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self.tfidf).flatten()
        best_idx = sims.argmax()
        best_score = sims[best_idx] if sims.size else 0.0

        if math.isnan(best_score) or best_score < 0.10:
            return "Puedo ayudarte a revisar disponibilidad o predecir lugares. Indica el área y, si quieres, la hora."

        _, reply = self.examples[best_idx]
        return reply


_ml_instance: MLChatModel | None = None


def get_ml_chat_model() -> MLChatModel:
    global _ml_instance
    if _ml_instance is None:
        _ml_instance = MLChatModel()
    return _ml_instance
