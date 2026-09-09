"""AI-content disclosure. Required by art. 50 AI Act and by YouTube/Meta policy.

Ported from ShortFactory. Not cosmetic: every caption and the YouTube status flag carry it.
Do not add a code path that publishes without it.
"""

# Long form, appended after the body and before hashtags.
CAPTION = "Made with AI: illustration and video generated, narration synthetic."

# Short form for X, where every character costs.
X_TAG = "(AI-generated)"


def youtube_status(privacy: str) -> dict:
    return {
        "privacyStatus": privacy,
        "selfDeclaredMadeForKids": False,
        # YouTube's altered-or-synthetic-content declaration.
        "containsSyntheticMedia": True,
    }
