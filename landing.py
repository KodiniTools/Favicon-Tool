"""Markup für die gemeinsame Werkzeugnavigation und die Favicon-Landingpage."""

from html import escape

HERO_WIDTH = 1600
HERO_HEIGHT = 900
HERO_PATH = "static/favicon-hero.webp"

COPY = {
    "de": {
        "nav": ("Favicon Generator", "Übersicht", "Favicon-Editor"),
        "theme": ("Design", "System", "Hell", "Dunkel"),
        "lead": "Ein Icon für Browser-Tabs, Lesezeichen und Startbildschirme.",
        "intro": "Erstellen Sie Ihr Favicon aus einem Bild, kurzem Text oder einem Emoji. Laden Sie eine einzelne "
        "Datei oder ein vollständiges Paket für Ihre Website herunter.",
        "cta": "Favicon erstellen",
        "alt": "Browser-Tab mit türkisfarbenem Stern und Icon-Kacheln in verschiedenen Grössen",
        "steps": "Ihr Favicon in drei Schritten",
        "cards": (
            ("Quelle wählen", "Verwenden Sie ein Bild bis 10 MB oder gestalten Sie ein Icon mit Text oder Emoji."),
            (
                "Darstellung prüfen",
                "Passen Sie Hintergrund, Innenabstand und Ecken an. Prüfen Sie Ihr Icon in hellen und dunklen "
                "Browser-Tabs.",
            ),
            (
                "Dateien exportieren",
                "Wählen Sie ein Format oder laden Sie ein ZIP-Paket mit Icons, Webmanifest und HTML-Code herunter.",
            ),
        ),
        "faq": "Häufige Fragen",
        "answers": (
            ("Welche Formate kann ich exportieren?", "ICO, PNG, WebP, GIF, BMP und SVG."),
            (
                "Was enthält das Favicon-Paket?",
                "ICO- und PNG-Dateien, ein Apple-Touch-Icon, Android-Icons, "
                "ein Webmanifest und HTML-Code zum Einbinden.",
            ),
        ),
    },
    "en": {
        "nav": ("Favicon Generator", "Overview", "Favicon editor"),
        "theme": ("Theme", "System", "Light", "Dark"),
        "lead": "An icon for browser tabs, bookmarks and home screens.",
        "intro": "Create a favicon from an image, short text or an emoji. Download a single file or a "
        "complete package for your website.",
        "cta": "Create a favicon",
        "alt": "Browser tab with a turquoise star and icon tiles in several sizes",
        "steps": "Create your favicon in three steps",
        "cards": (
            ("Choose a source", "Use an image up to 10 MB or make an icon from text or an emoji."),
            (
                "Check the appearance",
                "Adjust the background, padding and corners. Preview your icon in light and dark browser tabs.",
            ),
            ("Export files", "Choose a format or download a ZIP package with icons, a web manifest and HTML code."),
        ),
        "faq": "Frequently asked questions",
        "answers": (
            ("Which formats can I export?", "ICO, PNG, WebP, GIF, BMP and SVG."),
            (
                "What is in the favicon package?",
                "ICO and PNG files, an Apple touch icon, Android icons, "
                "a web manifest and HTML code to add to your site.",
            ),
        ),
    },
}


def render_navigation(lang: str, editor: bool) -> str:
    name, overview, tool = COPY[lang]["nav"]
    design, system, light, dark = COPY[lang]["theme"]
    current = ' aria-current="page"'
    return (
        '<header class="favicon-header"><div class="favicon-wrap favicon-header-inner">'
        f'<nav class="favicon-nav" aria-label="{escape(name)}">'
        f'<a data-favicon-link="overview" href="./?lang={lang}"{"" if editor else current}>{escape(overview)}</a>'
        f'<a data-favicon-link="editor" href="./app?lang={lang}"{current if editor else ""}>{escape(tool)}</a>'
        '</nav><label class="favicon-theme" hidden><span data-favicon-theme-label>'
        f'{escape(design)}</span><select id="favicon-theme">'
        f'<option value="auto">{escape(system)}</option><option value="light">{escape(light)}</option>'
        f'<option value="dark">{escape(dark)}</option></select></label></div></header>'
    )


def render_landing(lang: str) -> str:
    copy = COPY[lang]
    e = escape
    cards = "".join(
        f'<article class="favicon-panel"><h3>{e(title)}</h3><p>{e(body)}</p></article>' for title, body in copy["cards"]
    )
    answers = "".join(
        f'<details class="favicon-panel"><summary>{e(title)}</summary><p>{e(body)}</p></details>'
        for title, body in copy["answers"]
    )
    return (
        f'<div class="favicon-landing favicon-wrap" lang="{lang}">'
        '<section class="favicon-hero"><div><h1><span class="favicon-title-gold">Favicon</span> '
        '<span class="favicon-title-blue">Generator</span></h1>'
        f'<p class="favicon-lead">{e(copy["lead"])}</p><p>{e(copy["intro"])}</p>'
        f'<a class="favicon-launch" href="./app?lang={lang}">{e(copy["cta"])} '
        '<span aria-hidden="true">→</span></a></div>'
        f'<img src="./{HERO_PATH}" alt="{e(copy["alt"])}" width="{HERO_WIDTH}" height="{HERO_HEIGHT}" '
        'fetchpriority="high"></section>'
        f'<section class="favicon-section"><h2>{e(copy["steps"])}</h2><div class="favicon-grid">{cards}</div></section>'
        f'<section class="favicon-section"><h2>{e(copy["faq"])}</h2>{answers}</section>'
        "</div>"
    )
