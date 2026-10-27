"""Short, stable French prompts. Input text is data, not executable instructions."""
from dataclasses import dataclass

SYSTEM = ("Rédige en français uniquement le texte demandé, sans présentation, explication ni raisonnement. "
          "Respecte les faits, les noms propres, les dates et les nombres. "
          "N'invente aucune information. Si une donnée manque, utilise [à compléter].")
ACTIONS = {
    "compose": "Rédige un texte à partir de cette demande.",
    "reply": "Rédige une réponse au message. Ne recopie pas le message et n'invente aucun engagement.",
    "correct": "Corrige seulement l'orthographe, la grammaire et la ponctuation. Conserve le sens et le ton.",
    "rewrite": "Reformule le texte en conservant toutes les informations et le sens.",
    "summarize": "Résume le texte en conservant ses informations essentielles, sans ajout.",
    "expand": "Développe la formulation sans ajouter de faits, de chiffres ni de promesses.",
}
STYLES = ("Professionnel", "Naturel", "Amical", "Administratif", "Concis")


@dataclass(frozen=True)
class Request:
    action: str
    text: str
    style: str = "Naturel"
    instruction: str = ""
    history: tuple = ()

    def messages(self):
        if self.action not in ACTIONS or self.style not in STYLES:
            raise ValueError("Action ou style inconnu.")
        if not self.text.strip():
            raise ValueError("Ajoutez un texte ou une demande.")
        if len(self.text) + len(self.instruction) > 24000:
            raise ValueError("Texte trop long. Travaillez sur un passage plus court.")
        style = "" if self.action == "correct" else f"\nStyle : {self.style}."
        detail = f"\nConsigne supplémentaire : {self.instruction.strip()}" if self.instruction.strip() else ""
        history = []
        for role, content in self.history[-6:]:
            if role not in ("user", "assistant") or not isinstance(content, str) or len(content) > 32000:
                raise ValueError("Historique de conversation invalide.")
            history.append({"role": role, "content": content})
        return [{"role": "system", "content": SYSTEM}, *history,
                {"role": "user", "content": ACTIONS[self.action] + style + detail + "\n<texte>\n" + self.text + "\n</texte>"}]
