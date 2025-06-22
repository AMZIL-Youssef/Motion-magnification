import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QSpinBox, QDoubleSpinBox,
    QGroupBox, QProgressBar, QStatusBar, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget

# Importer la fonction EVM
try:
    from evm import eulerian_magnification
    EVM_AVAILABLE = True
except ImportError as e:
    print(f"ERREUR CRITIQUE: Impossible d'importer le backend EVM: {e}")
    EVM_AVAILABLE = False

    def eulerian_magnification(*args, **kwargs):
        raise NotImplementedError("Backend EVM non trouvé. Vérifiez les dépendances (numpy, scipy, opencv-python).")

class ProcessingThread(QThread):
    """Exécute le traitement vidéo dans un thread séparé."""
    finished = Signal(str, str)  # Signaux : output_path, error_message
    status_update = Signal(str)

    def __init__(self, input_file, output_dir, params):
        super().__init__()
        self.input_file = input_file
        self.output_dir = output_dir
        self.params = params

    def run(self):
        try:
            if not EVM_AVAILABLE:
                self.finished.emit(None, "Le backend EVM n'est pas disponible.")
                return

            self.status_update.emit("Démarrage du traitement EVM...")
            
            output_path = eulerian_magnification(
                self.input_file,
                self.output_dir,
                self.params["levels"],
                self.params["low_freq"],
                self.params["high_freq"],
                self.params["alpha"]
            )

            if output_path:
                self.status_update.emit(f"Traitement terminé. Sortie : {output_path}")
                self.finished.emit(output_path, None)
            else:
                self.finished.emit(None, "Le traitement n'a pas pu produire de fichier de sortie.")

        except Exception as e:
            error_msg = f"Erreur durant le traitement : {e}"
            print(error_msg)
            self.status_update.emit(error_msg)
            self.finished.emit(None, error_msg)

class MotionMagnificationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EVM - Motion Magnification")
        self.setGeometry(100, 100, 1200, 700)

        self.input_video_path = None
        self.output_video_path = None
        self.processing_thread = None

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        left_panel = QVBoxLayout()
        main_layout.addLayout(left_panel, 1)

        # Groupe de sélection de fichier
        file_group = QGroupBox("Vidéo d'entrée")
        file_layout = QHBoxLayout()
        self.file_label = QLabel("Aucune vidéo sélectionnée")
        self.file_button = QPushButton("Sélectionner Vidéo")
        self.file_button.clicked.connect(self.select_video_file)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.file_button)
        file_group.setLayout(file_layout)
        left_panel.addWidget(file_group)

        # Groupe des paramètres EVM (maintenant la seule méthode)
        self.evm_params_group = QGroupBox("Paramètres EVM")
        evm_layout = QVBoxLayout()
        self.levels_spin = QSpinBox()
        self.levels_spin.setRange(2, 8); self.levels_spin.setValue(3) # Valeur par défaut plus sûre
        self.low_freq_spin = QDoubleSpinBox()
        self.low_freq_spin.setRange(0.01, 10.0); self.low_freq_spin.setValue(0.83); self.low_freq_spin.setDecimals(2); self.low_freq_spin.setSingleStep(0.1)
        self.high_freq_spin = QDoubleSpinBox()
        self.high_freq_spin.setRange(0.1, 20.0); self.high_freq_spin.setValue(1.0); self.high_freq_spin.setDecimals(2); self.high_freq_spin.setSingleStep(0.1)
        self.alpha_spin = QDoubleSpinBox()
        self.alpha_spin.setRange(1, 500); self.alpha_spin.setValue(50); self.alpha_spin.setDecimals(1); self.alpha_spin.setSingleStep(10)
        evm_layout.addWidget(QLabel("Niveaux de la pyramide :"))
        evm_layout.addWidget(self.levels_spin)
        evm_layout.addWidget(QLabel("Fréquence de coupure basse (Hz) :"))
        evm_layout.addWidget(self.low_freq_spin)
        evm_layout.addWidget(QLabel("Fréquence de coupure haute (Hz) :"))
        evm_layout.addWidget(self.high_freq_spin)
        evm_layout.addWidget(QLabel("Facteur d'amplification (alpha) :"))
        evm_layout.addWidget(self.alpha_spin)
        self.evm_params_group.setLayout(evm_layout)
        left_panel.addWidget(self.evm_params_group)

        # Bouton de traitement
        self.process_button = QPushButton("Traiter la Vidéo")
        self.process_button.clicked.connect(self.start_processing)
        self.process_button.setEnabled(False)
        left_panel.addWidget(self.process_button)

        # Replay Vidéo Originale Bouton
        self.replay_Originale_button = QPushButton("Replay Vidéo Originale")
        self.replay_Originale_button.clicked.connect(self.replay_Originale_video)
        self.replay_Originale_button.setEnabled(False)
        #left_panel.addWidget(self.replay_Originale_button)

        # Replay Vidéo Magnifiée Bouton
        self.replay_button = QPushButton("Replay Vidéo Magnifiée")
        self.replay_button.clicked.connect(self.replay_video)
        self.replay_button.setEnabled(False)
        left_panel.addWidget(self.replay_button)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_panel.addWidget(self.progress_bar)

        left_panel.addStretch()

        right_panel = QVBoxLayout()
        main_layout.addLayout(right_panel, 3)

        video_layout = QHBoxLayout()
        
        original_video_group = QGroupBox("Vidéo Originale")
        original_video_layout = QVBoxLayout()
        self.original_video_widget = QVideoWidget()
        self.original_player = QMediaPlayer()
        self.original_player.setVideoOutput(self.original_video_widget)
        original_video_layout.addWidget(self.original_video_widget)
        original_video_group.setLayout(original_video_layout)
        video_layout.addWidget(original_video_group)

        magnified_video_group = QGroupBox("Vidéo Magnifiée")
        magnified_video_layout = QVBoxLayout()
        self.magnified_video_widget = QVideoWidget()
        self.magnified_player = QMediaPlayer()
        self.magnified_player.setVideoOutput(self.magnified_video_widget)
        magnified_video_layout.addWidget(self.magnified_video_widget)
        magnified_video_group.setLayout(magnified_video_layout)
        video_layout.addWidget(magnified_video_group)

        right_panel.addLayout(video_layout)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Prêt. Sélectionnez un fichier vidéo.")

    def select_video_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Vidéos (*.mp4 *.avi *.mov *.mkv)")
        file_dialog.setViewMode(QFileDialog.Detail)
        if file_dialog.exec():
            filenames = file_dialog.selectedFiles()
            if filenames:
                self.input_video_path = filenames[0]
                self.file_label.setText(os.path.basename(self.input_video_path))
                self.status_bar.showMessage(f"Vidéo sélectionnée : {self.input_video_path}")
                self.process_button.setEnabled(True)
                self.original_player.setSource(QUrl.fromLocalFile(self.input_video_path))
                self.original_player.play()
                self.replay_Originale_button.setEnabled(True)
                self.magnified_player.setSource(QUrl())
                self.output_video_path = None

    def start_processing(self):
        self.replay_Originale_button.setEnabled(False)
        self.replay_button.setEnabled(False)
        if not self.input_video_path:
            QMessageBox.warning(self, "Attention", "Veuillez d'abord sélectionner une vidéo.")
            return

        if self.processing_thread and self.processing_thread.isRunning():
            QMessageBox.warning(self, "Attention", "Un traitement est déjà en cours.")
            return

        params = {
            "levels": self.levels_spin.value(),
            "low_freq": self.low_freq_spin.value(),
            "high_freq": self.high_freq_spin.value(),
            "alpha": self.alpha_spin.value()
        }

        # S'assure que le répertoire de résultats existe
        output_dir = os.path.join(os.path.dirname(__file__), "../results")
        os.makedirs(output_dir, exist_ok=True)

        self.process_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_bar.showMessage("Traitement en cours...")

        self.processing_thread = ProcessingThread(self.input_video_path, output_dir, params)
        self.processing_thread.status_update.connect(self.status_bar.showMessage)
        self.processing_thread.finished.connect(self.on_processing_finished)
        self.processing_thread.start()

    def on_processing_finished(self, output_path, error_message):
        self.process_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)

        if error_message:
            QMessageBox.critical(self, "Erreur de Traitement", error_message)
            self.status_bar.showMessage(f"Le traitement a échoué : {error_message}")
        elif output_path:
            self.output_video_path = output_path
            self.status_bar.showMessage(f"Traitement terminé. Sortie : {output_path}")
            self.magnified_player.setSource(QUrl.fromLocalFile(self.output_video_path))
            self.magnified_player.play()
            self.replay_button.setEnabled(True)
            self.replay_Originale_button.setEnabled(True)
        else:
            self.status_bar.showMessage("Le traitement s'est terminé, mais aucun fichier n'a été généré.")
    
    def replay_Originale_video(self):
        self.original_player.setPosition(0)
        self.original_player.play()

    def replay_video(self):
        self.replay_Originale_video()
        self.magnified_player.setPosition(0)
        self.magnified_player.play()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MotionMagnificationApp()
    window.show()
    sys.exit(app.exec())