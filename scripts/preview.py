"""Render the template with fake data -- no API keys, no network calls to Anthropic."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import limits, render  # noqa: E402

SAMPLE = {
    "title": "How mRNA vaccines are made",
    "hook": "From a digital gene sequence to a filled vial, in five industrial stages.",
    "field": "biotech",
    "steps": [
        {"n": 1, "label": "Sequence the target", "icon": "dna",
         "text": "Pathogen genome is read; the spike protein region is selected."},
        {"n": 2, "label": "Build the DNA template", "icon": "database",
         "text": "A synthetic plasmid is grown in E. coli, then cut linear."},
        {"n": 3, "label": "Transcribe to mRNA", "icon": "tank",
         "text": "Enzymes copy the DNA into mRNA in a 30-litre bioreactor."},
        {"n": 4, "label": "Wrap in lipids", "icon": "molecule",
         "text": "Nanoparticles encase the strand so human cells absorb it."},
        {"n": 5, "label": "Fill and finish", "icon": "syringe",
         "text": "Sterile filtration, vialing, cold-chain release testing."},
    ],
    "body": (
        "A vaccine that used to take a decade now takes about a year, and almost none of that "
        "time is spent growing anything.\n\n"
        "It starts with a file. Once a pathogen's genome is sequenced, researchers pick the "
        "region coding for the surface protein the immune system should learn to recognise. "
        "Nothing biological has been touched yet -- this stage happens entirely in software.\n\n"
        "That sequence is then written into a circular DNA plasmid, grown to volume inside "
        "E. coli, harvested and cut into a linear template. This is the only step that still "
        "depends on living cells, and it is the usual bottleneck.\n\n"
        "The template goes into a bioreactor where enzymes transcribe it into mRNA. A single "
        "30-litre run can yield enough material for millions of doses, which is why capacity "
        "scales so differently from egg-grown flu vaccine.\n\n"
        "Naked mRNA would be destroyed in the bloodstream within minutes, so it is wrapped in "
        "lipid nanoparticles -- four lipids mixed with the strand in a microfluidic device. "
        "Getting that ratio right, not the mRNA itself, is the part most competitors struggle "
        "to copy.\n\n"
        "Finally the batch is sterile-filtered, filled into vials and held for release testing. "
        "The open problem is temperature: the lipid shell is why early formulations needed "
        "-70C storage, and stabilising it at fridge temperature is where most current work sits."
    ),
    "x_text": "mRNA vaccines start as a text file. Genome sequenced, spike region picked in "
              "software, then plasmid, bioreactor, lipid shell, vial. The hard part isn't the "
              "mRNA -- it's the four lipids wrapped around it.",
    "hashtags": ["#biotech", "#mrna", "#vaccines", "#science", "#process", "#biology", "#pharma"],
    "sources": ["https://example.org/mrna"],
    "stats": [
        {"value": "30 L", "label": "one reactor run covers millions of doses"},
        {"value": "-70C", "label": "storage the first lipid formulations needed"},
        {"value": "~1 yr", "label": "down from a decade for a conventional vaccine"},
    ],
    "quote": {"text": "The mRNA is the easy part. The delivery system is the hard part.",
              "who": "Drew Weissman, University of Pennsylvania"},
    "art": "a laboratory bioreactor vessel with coiled tubing and floating molecule shapes",
}


def placeholder_art() -> bytes:
    """Stand-in for the generated illustration, so the layout can be checked with no API key."""
    from playwright.sync_api import sync_playwright
    svg = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 400' width='400' height='400'>
      <circle cx='200' cy='200' r='150' fill='#0284C7' opacity='.14'/>
      <rect x='140' y='96' width='120' height='210' rx='46' fill='#0284C7'/>
      <rect x='140' y='210' width='120' height='96' rx='30' fill='#0369A1'/>
      <rect x='176' y='60' width='48' height='44' rx='12' fill='#F97316'/>
      <circle cx='200' cy='170' r='30' fill='#FFF' opacity='.9'/>
      <circle cx='96' cy='140' r='26' fill='#F97316'/>
      <circle cx='312' cy='260' r='34' fill='#F97316' opacity='.85'/>
      <circle cx='320' cy='120' r='16' fill='#0284C7'/>
      <path d='M78 300h244' stroke='#0284C7' stroke-width='12' stroke-linecap='round' fill='none'/>
    </svg>"""
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 400, "height": 400}, device_scale_factor=2)
        pg.set_content(f"<style>html,body{{margin:0;background:transparent}}</style>{svg}")
        png = pg.screenshot(type="png", omit_background=True)
        b.close()
    return png

if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "out", "preview.jpg")
    print(render.render(SAMPLE, out, handle="@yourhandle", art=placeholder_art()))
    caps = {
        "facebook": limits.for_facebook(f"{SAMPLE['title']}\n\n{SAMPLE['body']}", SAMPLE["hashtags"]),
        "instagram": limits.for_instagram(f"{SAMPLE['title']}\n\n{SAMPLE['body']}", SAMPLE["hashtags"]),
        "x": limits.for_x(SAMPLE["x_text"]),
    }
    print(json.dumps({k: len(v) for k, v in caps.items()}, indent=2))
    print("x weighted:", limits.x_weight(caps["x"]))
