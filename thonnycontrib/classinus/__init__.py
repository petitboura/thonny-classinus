"""classinus : Classinus dans un panneau de Thonny."""

from thonny import get_workbench

from . import reglages
from .textes import definir_langue, t


def load_plugin():
    from . import contexte
    from .panneau import VueClassinus
    from .reglages_ui import PageReglages

    wb = get_workbench()
    reglages.declarer_defauts()
    definir_langue(reglages.lire("langue"), wb.get_option("general.language") or "")
    contexte.installer()
    wb.add_view(VueClassinus, t("titre_panneau"), "ne", visible_by_default=True)
    wb.add_configuration_page("classinus", t("titre_reglages"), PageReglages, 80)
