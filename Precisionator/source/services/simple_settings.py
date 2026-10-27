"""Named choices, translated to motion settings without technical UI controls."""
CHOICES = {
    "size": (
        ("small", "Petite", {"lens_diameter": 180}),
        ("medium", "Moyenne", {"lens_diameter": 300}),
        ("large", "Grande", {"lens_diameter": 440}),
    ),
    "appearance": (
        ("early", "Plus tôt", {"trigger_speed": 650, "activation_delay_ms": 50}),
        ("normal", "Normalement", {"trigger_speed": 450, "activation_delay_ms": 80}),
        ("late", "Plus tard", {"trigger_speed": 250, "activation_delay_ms": 160}),
    ),
    "aim": (
        ("short", "Court", {"idle_delay_ms": 800, "exit_speed": 800}),
        ("comfortable", "Confortable", {"idle_delay_ms": 2000, "exit_speed": 1100}),
        ("long", "Long", {"idle_delay_ms": 4000, "exit_speed": 1600}),
    ),
}


def closest_choice(group, prefs):
    choices = CHOICES[group]
    fields = choices[0][2]
    ranges = {field: max(choice[2][field] for choice in choices) - min(choice[2][field] for choice in choices)
              for field in fields}
    return min(choices, key=lambda choice: sum(abs(getattr(prefs, field) - value) / max(1, ranges[field])
                                               for field, value in choice[2].items()))[0]
