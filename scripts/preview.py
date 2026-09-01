"""Render the template with fake data -- no API keys, no network calls to Anthropic."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import render  # noqa: E402

SAMPLE = {
    "title": "How mRNA vaccines are made",
    "hook": "From a digital gene sequence to a vial, in five industrial stages.",
    "field": "biotech",
    "steps": [
        {"n": 1, "label": "Sequence the target", "text": "Pathogen genome read, spike protein region selected."},
        {"n": 2, "label": "Build the DNA template", "text": "Synthetic plasmid grown in bacteria, then linearised."},
        {"n": 3, "label": "Transcribe to mRNA", "text": "Enzymes copy DNA into mRNA in a reactor."},
        {"n": 4, "label": "Wrap in lipids", "text": "Nanoparticles encase mRNA so cells absorb it."},
        {"n": 5, "label": "Fill and finish", "text": "Sterile filtration, vialing, cold-chain release testing."},
    ],
    "caption": "Sample caption used only for the offline template preview.",
    "hashtags": ["#biotech", "#mrna", "#process"],
}

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out", "preview.jpg")
    print(render.render(SAMPLE, out, handle="@yourhandle"))
