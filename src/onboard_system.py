"""Orchestration : attente → calibration → fonctionnement, ou défaut explicite."""

import asyncio
from . import config as reglage
from .compat import ticks_ms, ticks_diff, sleep_ms
from .functions import get_functions as get
from .functions.determine_actions import risque_dessalement, mesure_perimee
from .functions.do_actions import (
    AlerteSonore, set_alerte_dessalement, update_alerte_sonore, arreter_sorties,
)


class OnBoardSystem:
    """Coordonne des pilotes réels ou simulés avec les mêmes décisions."""

    def __init__(
        self, capteurs: object, sortie: object, meteo: object = None,
        config: object = reglage, horloge: object = ticks_ms,
    ) -> None:
        """Prépare les composants, les états et les références."""
        risque_dessalement(0, False, config.SEUIL_ACTIVATION, config.SEUIL_ARRET)
        if not 0 < config.ALPHA <= 1 or config.PERIODE_MS <= 0:
            raise ValueError('Filtre ou période invalide')
        if config.CALIBRATION_ECHANTILLONS < 2 or config.ANTI_REBOND_MS < 0:
            raise ValueError('Calibration ou anti-rebond invalide')
        self.capteurs = capteurs
        self.config = config
        self.horloge = horloge
        self.meteo = meteo
        self.alerte = AlerteSonore(sortie, config.BIP_ON_MS, config.BIP_OFF_MS,
                                   config.FREQUENCE_HZ)
        self.etat = 'attente'
        self.erreur = None
        self.offset_bome = None
        self.mesures = None
        self.inclinaison_filtree = None
        self.risque = False
        self.cache_meteo = None
        self.meteo_ms = None
        self.erreur_meteo = None
        self._pret = False
        self._brut = False
        self._stable = False
        self._changement_ms = horloge()
        self._calibration = []

    def _defaut(self, message: str) -> None:
        """Signale le défaut et exige un nouvel appui pour reprendre."""
        self.etat = 'defaut'
        self.erreur = message
        self.offset_bome = None
        self.inclinaison_filtree = None
        self._calibration = []
        self.risque = False
        # Au prototype, même son pour risque et défaut ; la console les distingue.
        set_alerte_dessalement(True, self.alerte)

    def initialize(self) -> None:
        """Initialise les capteurs, sinon mémorise un défaut matériel."""
        self._pret = False
        try:
            self.capteurs.initialize()
            self._pret = True
            self.etat = 'attente'
            self.erreur = None
            self.offset_bome = None
            self.mesures = None
            self.inclinaison_filtree = None
            self.risque = False
            set_alerte_dessalement(False, self.alerte)
        except (OSError, ValueError) as erreur:
            self._defaut(str(erreur))

    def calibrate(self) -> None:
        """Demande plusieurs mesures stables avec la bôme dans l'axe."""
        if self.etat == 'fonctionnement' and self.risque:
            return  # Ne pas interrompre une alerte pour refaire le zéro.
        if not self._pret:
            self.initialize()
        if self._pret:
            self.etat = 'calibration'
            self._calibration = []
            self.offset_bome = None
            self.erreur = None
            self.risque = False
            set_alerte_dessalement(False, self.alerte)

    def update_button(self, appuye: bool, maintenant_ms: int) -> None:
        """Déclenche une seule calibration par appui stabilisé."""
        if appuye != self._brut:
            self._brut = appuye
            self._changement_ms = maintenant_ms
        if ticks_diff(maintenant_ms, self._changement_ms) >= self.config.ANTI_REBOND_MS:
            if self._stable != self._brut:
                self._stable = self._brut
                if self._stable:
                    self.calibrate()

    def _calibration_step(self, cap_bateau: float, cap_bome: float) -> None:
        """Valide la stabilité angulaire avant d'enregistrer le zéro."""
        delta = get.get_bome_angle(cap_bateau, cap_bome, 0)
        if self._calibration:
            delta = self._calibration[0] + get.get_bome_angle(
                self._calibration[0], delta, 0)
        self._calibration.append(delta)
        if max(self._calibration) - min(self._calibration) > self.config.CALIBRATION_ECART_MAX_DEG:
            raise ValueError('Bôme instable : la maintenir dans l’axe puis réappuyer')
        if len(self._calibration) >= self.config.CALIBRATION_ECHANTILLONS:
            self.offset_bome = sum(self._calibration) / len(self._calibration)
            self.etat = 'fonctionnement'
            self._calibration = []

    def step(self, maintenant_ms: int) -> None:
        """Exécute un cycle acquisition, décision et commande des sorties."""
        try:
            self.update_button(get.get_bouton_data(self.capteurs), maintenant_ms)
            if self._pret:
                debut = self.horloge()
                self.capteurs.refresh()
                bateau = get.get_boussole_bateau_data(self.capteurs)
                bome = get.get_boussole_bome_data(self.capteurs)
                acceleration = get.get_accelerometre_data(self.capteurs)
                cap_bateau = get.get_bateau_cap(bateau)
                cap_bome = get.get_bome_cap(bome)
                inclinaison = get.get_inclinaison(acceleration)
                if mesure_perimee(debut, self.horloge(), self.config.AGE_MESURE_MAX_MS):
                    raise OSError('Acquisition trop lente : mesures périmées')
                # Lisser le plus court écart évite une discontinuité à ±180°.
                if self.inclinaison_filtree is None:
                    self.inclinaison_filtree = inclinaison
                else:
                    ecart = get.get_bome_angle(self.inclinaison_filtree, inclinaison, 0)
                    self.inclinaison_filtree = (
                        get.filtrer_passe_bas(self.inclinaison_filtree + ecart,
                                              self.inclinaison_filtree, self.config.ALPHA)
                        + 180) % 360 - 180
                if self.etat == 'calibration':
                    if abs(inclinaison) > self.config.CALIBRATION_GITE_MAX_DEG:
                        raise ValueError('Zéro refusé : vérifier la gîte et les axes du capteur')
                    self._calibration_step(cap_bateau, cap_bome)
                self.mesures = {'mesure_ms': debut, 'cap_deg': cap_bateau,
                                'gite_deg': self.inclinaison_filtree,
                                'bome_deg': None if self.offset_bome is None else
                                get.get_bome_angle(cap_bateau, cap_bome, self.offset_bome)}
                if self.etat == 'fonctionnement':
                    self.risque = risque_dessalement(
                        self.inclinaison_filtree, self.risque,
                        self.config.SEUIL_ACTIVATION, self.config.SEUIL_ARRET)
                    set_alerte_dessalement(self.risque, self.alerte)
        except (OSError, ValueError) as erreur:
            self._defaut(str(erreur))
        update_alerte_sonore(self.horloge(), self.alerte)

    async def update_weather(self) -> None:
        """Actualise le cache sans effacer la dernière météo en cas d'erreur."""
        from .weather import connecter_wifi
        try:
            if not self.config.SIMULATION:
                await connecter_wifi(self.config.METEO_TIMEOUT_MS)
            donnees = await get.get_meteo_data(
                self.config.LATITUDE, self.config.LONGITUDE,
                self.config.METEO_TIMEOUT_MS, self.meteo)
            self.cache_meteo = donnees
            self.meteo_ms = self.horloge()
            self.erreur_meteo = None
        except Exception as erreur:
            self.erreur_meteo = str(erreur)

    async def _weather_loop(self) -> None:
        """Planifie les mises à jour météo à cadence lente."""
        while True:
            await self.update_weather()
            await sleep_ms(self.config.METEO_PERIODE_MS)

    def snapshot(self) -> dict:
        """Expose l'état et la fraîcheur des mesures et de la météo."""
        maintenant = self.horloge()
        return {'etat': self.etat, 'erreur': self.erreur,
                'mesures': None if self.mesures is None else self.mesures.copy(),
                'mesures_valides': self.etat == 'fonctionnement' and self.mesures is not None
                and not mesure_perimee(self.mesures['mesure_ms'], maintenant,
                                       self.config.AGE_MESURE_MAX_MS),
                'risque': self.risque, 'son': self.alerte.son,
                'meteo': None if self.cache_meteo is None else self.cache_meteo.copy(),
                'meteo_perimee': self.meteo_ms is None or mesure_perimee(
                    self.meteo_ms, maintenant, self.config.METEO_AGE_MAX_MS),
                'erreur_meteo': self.erreur_meteo}

    async def run(self, duree_ms: int = None, observer: object = None) -> None:
        """Lance le système et garantit l'arrêt des sorties à la sortie."""
        tache_meteo = None
        debut = self.horloge()
        derniere_publication = None
        try:
            self.initialize()
            if self.config.METEO_ACTIVE and self.meteo is not None:
                tache_meteo = asyncio.create_task(self._weather_loop())
            while duree_ms is None or ticks_diff(self.horloge(), debut) < duree_ms:
                cycle = self.horloge()
                self.step(cycle)
                if observer is not None and (derniere_publication is None or
                        ticks_diff(cycle, derniere_publication) >= 250):
                    observer(self.snapshot())
                    derniere_publication = cycle
                await sleep_ms(max(1, self.config.PERIODE_MS - ticks_diff(self.horloge(), cycle)))
        finally:
            if tache_meteo is not None:
                tache_meteo.cancel()
                try:
                    await tache_meteo
                except asyncio.CancelledError:
                    pass
            arreter_sorties(self.alerte)
