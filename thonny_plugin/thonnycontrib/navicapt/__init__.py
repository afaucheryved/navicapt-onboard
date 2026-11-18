"""Extension frontend Thonny : observation passive des sorties du programme Pico."""
import logging
import time

logger = logging.getLogger(__name__)


class ConsoleBridge:
    def __init__(self, workbench, window_factory=None):
        self.workbench = workbench
        self.window_factory = window_factory or self._create_window
        self.viewer = None
        self.buffer = ''
        self.discard = False
        self.suppressed = False
        self.state = None
        self.received = None
        for event, handler in [('ProgramOutput', self.on_output),
                               ('CommandAccepted', self.on_command),
                               ('BackendRestart', self.reset),
                               ('BackendTerminated', self.reset)]:
            workbench.bind(event, handler, True)
        workbench.add_command('navicapt_show', 'view', 'NaviCapt — mesures du Pico', self.show)

    def _create_window(self):
        import tkinter as tk
        from .runtime.pico_viewer import PicoViewer
        window = tk.Toplevel(self.workbench)
        viewer = PicoViewer(window, console=True)
        window.protocol('WM_DELETE_WINDOW', self.hide)
        return viewer

    def on_command(self, event):
        command = event.command
        if command.name in ('Run', 'run', 'Debug', 'debug', 'execute_source'):
            self.reset()

    def reset(self, event=None):
        self.buffer = ''
        self.discard = False
        self.suppressed = False
        self.state = None
        self.received = None
        if self.viewer is not None:
            self.viewer.state = None
            self.viewer.received = None
            self.viewer.render()

    def on_output(self, event):
        if getattr(event, 'stream_name', 'stdout') != 'stdout':
            return
        data = getattr(event, 'data', '')
        if not isinstance(data, str):
            return
        # Pas de break/return "break" : la console conserve ses propres sorties.
        pieces = data.split('\n')
        for index, piece in enumerate(pieces):
            if not self.discard:
                self.buffer += piece
                if len(self.buffer) > 16384:
                    self.buffer = ''
                    self.discard = True
            if index < len(pieces) - 1:
                if not self.discard:
                    self._line(self.buffer.rstrip('\r'))
                self.buffer = ''
                self.discard = False

    def _line(self, line):
        if not line.startswith('NAVICAPT '):
            return
        from .runtime.telemetry import decode
        state = decode(line)
        if state is None:
            return
        self.state, self.received = state, time.monotonic()
        if not self.suppressed:
            self.show()

    def show(self):
        self.suppressed = False
        try:
            if self.viewer is None:
                self.viewer = self.window_factory()
            self.viewer.state = self.state
            self.viewer.received = self.received
            self.viewer.render()
            if self.viewer.root.state() == 'withdrawn':
                self.viewer.root.deiconify()
        except Exception:
            # Une défaillance du dessin ne doit pas interrompre le programme ou la console.
            logger.exception('Impossible d’afficher NaviCapt')
            self.suppressed = True

    def hide(self):
        self.suppressed = True
        if self.viewer is not None:
            self.viewer.root.withdraw()


_bridge = None


def load_plugin():
    global _bridge
    if _bridge is None:
        from thonny import get_workbench
        _bridge = ConsoleBridge(get_workbench())
