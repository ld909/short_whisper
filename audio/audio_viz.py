import pygame
import numpy as np
import librosa
import math
import sys
import os  # For checking file existence

# --- Configuration ---
SCREEN_WIDTH = 900
SCREEN_HEIGHT = 250  # Adjusted for a horizontal bar layout as in the reference
FPS = 60

# Bar settings
NUM_BARS = 50  # 柱子总量从75减少到50
MAX_BAR_HEIGHT = (
    SCREEN_HEIGHT * 0.8
)  # Max height a bar can reach (80% of screen height)
BAR_COLOR = (255, 255, 255)  # White
BACKGROUND_COLOR = (30, 30, 35)  # Dark, slightly bluish gray
BAR_WIDTH_RATIO = 0.6  # 柱子粗细比例从0.7降低到0.6
BAR_SPACING_RATIO = 1.0 - BAR_WIDTH_RATIO  # 间隙比例相应增加到0.4
BAR_MIN_HEIGHT = 2  # Minimum visible height for a bar
BAR_SMOOTHING_FACTOR = 0.08  # Smoothing for bar height changes (0-1, lower is smoother)
Y_BASELINE_OFFSET = SCREEN_HEIGHT * 0.05  # Small offset from the bottom

# Audio processing settings
N_FFT = 2048
HOP_LENGTH = 512


# --- Helper Functions ---
def preprocess_audio(audio_path):
    """Loads and preprocesses the audio file (MP3 or WAV)."""
    if not os.path.exists(audio_path):
        print(f"Error: Audio file not found at '{audio_path}'")
        return None, 0, 0
    try:
        y, sr = librosa.load(audio_path, sr=None)
    except Exception as e:
        print(f"Error loading audio file '{audio_path}': {e}")
        return None, 0, 0

    stft_result = librosa.stft(y, n_fft=N_FFT, hop_length=HOP_LENGTH)
    magnitudes = np.abs(stft_result)
    db_magnitudes = librosa.amplitude_to_db(magnitudes, ref=np.max, top_db=80.0)
    normalized_magnitudes = (db_magnitudes + 80.0) / 80.0
    normalized_magnitudes = np.clip(normalized_magnitudes, 0, 1)

    num_freq_bins = normalized_magnitudes.shape[0]

    # Select frequency bins for the visual bars
    # Using linspace to get a spread across available frequencies
    # We take a portion of the frequency spectrum, often lower/mid frequencies are more visually active
    # For NUM_BARS, we select NUM_BARS points from the lower ~70% of frequencies.
    # Adjust the `num_freq_bins * 0.7` part if you want to include higher frequencies.
    if num_freq_bins > NUM_BARS:
        # Take roughly log-spaced bins, or more bins from lower frequencies
        # A simple approach is linear spacing on a subset of bins
        # indices = np.linspace(0, num_freq_bins * 0.7, NUM_BARS, dtype=int) # Focus on lower-mid
        indices = np.unique(
            np.logspace(
                np.log10(1), np.log10(num_freq_bins * 0.6), NUM_BARS, base=10, dtype=int
            ).clip(0, num_freq_bins - 1)
        )
        if len(indices) < NUM_BARS:  # Fallback if logspace gives too few unique bins
            indices = np.linspace(0, num_freq_bins * 0.7, NUM_BARS, dtype=int)

    else:  # Fewer available bins than desired bars
        indices = np.arange(num_freq_bins)

    processed_magnitudes = normalized_magnitudes[indices, :]

    # Ensure we have exactly NUM_BARS, pad if necessary
    if processed_magnitudes.shape[0] < NUM_BARS:
        padding_needed = NUM_BARS - processed_magnitudes.shape[0]
        # Pad by repeating last rows or adding zeros
        # For simplicity, pad with zeros (less visually distracting than repeating)
        padding = np.zeros((padding_needed, processed_magnitudes.shape[1]))
        processed_magnitudes = np.vstack((processed_magnitudes, padding))
    elif (
        processed_magnitudes.shape[0] > NUM_BARS
    ):  # Should not happen if indices selection is correct
        processed_magnitudes = processed_magnitudes[:NUM_BARS, :]

    return processed_magnitudes, sr, HOP_LENGTH


# --- Pygame Setup ---
pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Minimalist Audio Visualizer")
clock = pygame.time.Clock()

# --- Load and Prepare Audio ---
audio_file_path = (
    "./suon_music.mp3"  # <--- IMPORTANT: Change this to your MP3 or WAV file
)
# Example:
# audio_file_path = 'audio/my_track.wav'

audio_features, sample_rate, hop_length = preprocess_audio(audio_file_path)

if audio_features is None:
    print(f"Exiting due to audio processing error.")
    pygame.quit()
    sys.exit()

num_frames = audio_features.shape[1]
time_per_frame_ms = (hop_length / sample_rate) * 1000

# --- Play Audio ---
if os.path.exists(audio_file_path):
    try:
        pygame.mixer.music.load(audio_file_path)
        pygame.mixer.music.play(0)
    except pygame.error as e:
        print(f"Error playing audio with pygame.mixer: {e}")
        pygame.quit()
        sys.exit()
else:
    # This case should be caught by preprocess_audio, but as a safeguard
    print(f"Audio file '{audio_file_path}' not found. Cannot play.")
    pygame.quit()
    sys.exit()


# --- Main Loop Variables ---
running = True
current_bar_heights_normalized = np.zeros(
    NUM_BARS
)  # Store normalized heights for smoothing

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    # --- Get Current Audio Position ---
    current_time_ms = pygame.mixer.music.get_pos()
    if (
        current_time_ms == -1 and not pygame.mixer.music.get_busy()
    ):  # Song finished or error
        # Option: loop, fade out, or just stop updating
        target_heights_normalized = np.zeros(NUM_BARS)  # Fade out bars
    else:
        current_frame_index = int(current_time_ms / time_per_frame_ms)
        if current_frame_index >= num_frames:
            current_frame_index = num_frames - 1
            if not pygame.mixer.music.get_busy():
                target_heights_normalized = np.zeros(NUM_BARS)
            else:
                target_heights_normalized = audio_features[:, current_frame_index]
        elif current_frame_index < 0:
            target_heights_normalized = np.zeros(NUM_BARS)
        else:
            target_heights_normalized = audio_features[:, current_frame_index]

    # Apply smoothing to normalized heights
    current_bar_heights_normalized = (
        current_bar_heights_normalized * (1 - BAR_SMOOTHING_FACTOR)
        + target_heights_normalized * BAR_SMOOTHING_FACTOR
    )

    # --- Drawing ---
    screen.fill(BACKGROUND_COLOR)

    bar_total_width_px = SCREEN_WIDTH / NUM_BARS
    actual_bar_width_px = bar_total_width_px * BAR_WIDTH_RATIO
    spacing_px = bar_total_width_px * BAR_SPACING_RATIO / 2  # Half spacing on each side

    y_baseline = SCREEN_HEIGHT - Y_BASELINE_OFFSET

    for i in range(NUM_BARS):
        # Scale normalized height to screen height
        bar_pixel_height = current_bar_heights_normalized[i] * MAX_BAR_HEIGHT
        bar_pixel_height = max(
            BAR_MIN_HEIGHT, bar_pixel_height
        )  # Ensure minimum visible height

        # Center bars with spacing
        bar_x = i * bar_total_width_px + spacing_px
        bar_y = y_baseline - bar_pixel_height

        pygame.draw.rect(
            screen, BAR_COLOR, (bar_x, bar_y, actual_bar_width_px, bar_pixel_height)
        )

    pygame.display.flip()
    clock.tick(FPS)

# --- Cleanup ---
pygame.mixer.music.stop()
pygame.quit()
sys.exit()
