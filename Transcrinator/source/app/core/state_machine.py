from enum import Enum


class State(str, Enum):
    IDLE = "Prêt"
    PREPARING = "Préparation…"
    LISTENING = "Écoute…"
    FLUSHING = "Traitement…"
    ERROR = "Erreur"
    CLOSED = "Fermé"


class StateMachine:
    allowed = {
        State.IDLE: {State.PREPARING, State.ERROR, State.CLOSED},
        State.PREPARING: {State.LISTENING, State.IDLE, State.ERROR, State.CLOSED},
        State.LISTENING: {State.FLUSHING, State.ERROR, State.CLOSED},
        State.FLUSHING: {State.IDLE, State.ERROR, State.CLOSED},
        State.ERROR: {State.IDLE, State.PREPARING, State.CLOSED},
        State.CLOSED: set(),
    }

    def __init__(self):
        self.state = State.IDLE

    def transition(self, target: State):
        if target not in self.allowed[self.state]:
            raise RuntimeError(f"Transition interdite : {self.state.name} → {target.name}")
        self.state = target
