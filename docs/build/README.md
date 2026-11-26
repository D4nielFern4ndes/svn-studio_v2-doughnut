# Construction du guide PDF

Le texte du guide est dans `docs/guide_methodologique.md`. Le PDF
`docs/guide_methodologique.pdf` est généré à partir de ce fichier ; ne le modifiez pas à la main.

```
python -m pip install markdown weasyprint   # une fois
python docs/build/build_guide.py            # .md -> PDF
```

- `guide.css` : mise en page et couleurs (palette UTT, variables en haut du fichier).
- `img/` : copies d'écran de l'application, placées après les titres « Étape 1 » à « Étape 7 » et
  « Outil » (liste `FIGURES` dans `build_guide.py`).
- Quand l'interface change, régénérez les copies d'écran puis le PDF :

```
python -m pip install playwright && python -m playwright install chromium   # une fois
python docs/build/capture_screenshots.py
python docs/build/build_guide.py
```
