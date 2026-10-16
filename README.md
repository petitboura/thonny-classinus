# thonny-classinus

Thonny plugin that adds a Classinus panel to the right of the editor.

Step 1: sign in to your Classinus account (through the browser), then type a
question in the panel and the answer appears as it is written.

Step 2: two buttons, "Send my code" (the open file, the selected part, the last
error and the program output) and "Explain this error". Nothing is sent without
a click from the student. The code is added to the message sent to Classinus;
the maximum sizes are in `defauts.json` (`max_code`, `max_sortie`).

The Thonny-specific instructions (where Classinus is, what the buttons do, how to
answer: plain text, Python code in a python block) are no longer in the plugin:
the server adds them itself (file `core/consignes_thonny.txt` of the backend) when
the plugin declares itself as a Thonny client. The plugin only sends `client` and
the names of its buttons in the student's language (`libelles_client`). Editing
that server file changes how Classinus behaves in Thonny.

Step 3: under each code block of the answer, "Copy", "Insert" (the student
confirms, then Ctrl+Z undoes it) and "New tab" (the code opens in an unsaved tab).
Running the script stays with Thonny's green button.

Panel buttons: "Send my code", "Fix my code", "Explain this error", "Explain my
selection" (sends only the selected part), "New conversation" (clears the
discussion). If the student is stepping through the debugger, the line they are
on is sent with the code.

Display: the student's question on the right, the answer on the left. The code
colors are those of Thonny's theme, and the backgrounds follow its light or dark
theme. Links like `[text](https://...)` are clickable, the real site is shown
next to the text and a confirmation window announces it before opening the
browser (http and https only). A "line 7" mention in an answer is clickable and
highlights that line in the editor.

Addresses (Classinus server, sign-in service) are never written in the code: they
come from `defauts.json`, from Thonny's Classinus settings page, or from the
environment variables `CLASSINUS_BACKEND_URL` and `CLASSINUS_SUPABASE_URL`.

Step 5: answer length (short, medium, long) and model choice when the agent offers
one, the same choices as the website. "Attach a file" button (photo 5 MB max,
document 15 MB max, 5 files): sent to the server when you press Send
(`pieces_jointes.py`). Each conversation in the panel has its own identifier and
its messages chain into the same thread of the website history
(`conversation.py`).

Tables: a Markdown table in the answer is shown as a real aligned table
(`tableaux.py`), with a horizontal scroll bar if the panel is too narrow. The
server's Thonny instructions allow tables.

Buttons at the bottom and top of the panel: "Attach a file" (on its own line,
full text) and "Settings" (answer length, effort, teaching mode, resource modes,
as on the website). The "Model" button is at the top of the panel, with the same
rules as the website: it only appears if the server offers models, the list is
grouped by provider, and there is no "Auto" mode. The active model is the
student's last choice if it is still offered, otherwise DeepSeek Flash
(`modele_par_defaut` in `defauts.json`). Provider icons are the real logos
(`logos_data.py`, free library `@lobehub/icons-static-svg`, MIT license), the
"Auto" icon is drawn by the plugin (`icones.py`). The teaching mode and the
resource modes are saved on the server for the current conversation
(`parametres_conversation.py`), as on the website.

Quoted lines: when the answer quotes lines of the code that was sent ("line 7",
"lines 3 to 5"), they are highlighted on their own in the editor at the end of the
answer, without moving the cursor or the text, and only if the open file is still
exactly the one the student sent (`editeur.surligner_lignes_citees`). In the
panel, "line N" stays clickable and shows in yellow.

Classinus files and pages: a link that points to a file served by Classinus
(server or storage) never shows the raw address. It is announced as "(Classinus)"
and opens the "Classinus file" window (`fichier_classinus.py`): open in Thonny
(text and code, new unsaved tab), save to the computer, open in the browser (PDFs
and images). The offered types are in `defauts.json` (`extensions_texte`,
`extensions_navigateur`, `taille_max_texte`), and the recognized addresses come
from the settings (`backend_url`, `supabase_url`, `site_url`). A link to a page of
the Classinus website opens in the browser with the usual confirmation window,
which announces "Classinus".

Updates: Thonny does not warn when a plugin has a new version, so the plugin does
it itself (`mise_a_jour.py`). At startup, it asks PyPI in a separate thread
(address and interval in `defauts.json`: `mise_a_jour_url`,
`mise_a_jour_intervalle_heures`, 24 h by default) and shows a banner at the top of
the panel if a newer version exists. The banner closes with "Close" and does not
come back for that version; an even newer version makes it reappear. Offline, or
on an unexpected answer, nothing is shown. Only versions already installed with
this feature can use it: it does not exist in versions published before it.

Languages: each language is a file in the `thonnycontrib/classinus/langues/`
folder (`fr.py`, `en.py`) with `NOM` and `TEXTES`. Every visible text goes through
`t("key")` and exists in all languages, never in just one. To add a language: copy
`en.py` to `<code>.py` (for example `ar.py`), change `NOM`, translate the values
without touching the keys or the `%s`. The language is discovered automatically
("auto" setting, or its code in Tools > Options > Classinus). The test
`python -m unittest discover tests` fails if a key is missing in a language, if a
text is empty, if the `%s` differ, or if the code calls a key that does not exist.
