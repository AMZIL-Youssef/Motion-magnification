import cv2
import numpy as np
import scipy.signal as signal
from pyramid_utils import build_laplacian_pyramid, reconstruct_from_laplacian_pyramid
import os

def load_video(video_filename, max_frames=None):
    """Loads a video and returns its frames and metadata, optionally limiting the number of frames."""
    cap = cv2.VideoCapture(video_filename)
    if not cap.isOpened():
        raise IOError(f"Cannot open video file: {video_filename}")
    
    frame_count_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    frames = []
    frames_read = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Convert frame to float32 for processing
        frames.append(frame.astype(np.float32) / 255.0)
        frames_read += 1
        
        # Stop if max_frames limit is reached
        if max_frames is not None and frames_read >= max_frames:
            print(f"\nReached max_frames limit ({max_frames}).")
            break
            
    cap.release()
    
    if not frames:
        raise ValueError(f"Could not read any frames from video: {video_filename}")
        
    print(f"Loaded video: {video_filename} ({len(frames)} frames out of {frame_count_total}, {width}x{height} @ {fps:.2f} FPS)")
    return frames, fps, width, height

def save_video(frames, fps, width, height, output_filename):
    """Saves frames as a video file."""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Or use 'XVID' or other codecs
    out = cv2.VideoWriter(output_filename, fourcc, fps, (width, height))
    
    if not out.isOpened():
        print(f"Error: Could not open video writer for {output_filename}")
        return
        
    print(f"Saving video to {output_filename}...")
    for frame in frames:
        # Denormalize and convert back to uint8
        frame = np.clip(frame * 255.0, 0, 255).astype(np.uint8)
        out.write(frame)
        
    out.release()
    print("Video saved successfully.")

def temporal_bandpass_filter(data, fps, low_freq, high_freq, axis=0):
    """Applies a temporal bandpass filter to the data along the specified axis."""
    print(f"Applying temporal filter ({low_freq:.2f}Hz - {high_freq:.2f}Hz)...", end=' ')
    fft_data = np.fft.fft(data, axis=axis)
    frequencies = np.fft.fftfreq(data.shape[axis], d=1.0/fps)
    
    # Create frequency mask
    mask = (np.abs(frequencies) >= low_freq) & (np.abs(frequencies) <= high_freq)
    
    # Apply mask
    fft_data_filtered = fft_data.copy()
    # Zero out frequencies outside the passband
    # Corrected logic: Apply mask to keep frequencies *within* the band
    fft_data_filtered[~mask] = 0 
    
    # Inverse FFT
    filtered_data = np.fft.ifft(fft_data_filtered, axis=axis)
    print("Filter applied.")
    return filtered_data.real # Return the real part

def eulerian_magnification(video_filename, output_dir, pyramid_levels, low_freq, high_freq, amplification_factor, max_frames=None):
    """Performs Eulerian Video Magnification, optionally limiting the number of frames processed."""
    
    # 1. Load Video (with frame limit)
    try:
        frames, fps, width, height = load_video(video_filename, max_frames=max_frames)
    except (IOError, ValueError) as e:
        print(f"Error loading video: {e}")
        return None # Return None on failure

    num_frames = len(frames)
    if num_frames == 0:
        print("No frames loaded, cannot proceed.")
        return None
        
    print(f"Processing {num_frames} frames...")

    # 2. Build Laplacian Pyramid for each frame and store temporally
    print(f"Building Laplacian pyramids (levels={pyramid_levels})...")
    pyramid_video_t = None
    try:
        for i, frame in enumerate(frames):
            lap_pyramid = build_laplacian_pyramid(frame, pyramid_levels)
            if i == 0:
                # Initialize storage for temporal filtering based on first frame's pyramid structure
                pyramid_video_t = [np.zeros((num_frames,) + level.shape, dtype=np.float32) for level in lap_pyramid]
            
            # Store the current frame's pyramid levels in the temporal structure
            for level_idx, level_data in enumerate(lap_pyramid):
                # Ensure consistent shapes
                if level_data.shape == pyramid_video_t[level_idx][i].shape:
                    pyramid_video_t[level_idx][i] = level_data
                else:
                    # Handle shape mismatch - resize might be better than skipping
                    print(f"Warning: Shape mismatch at frame {i}, level {level_idx}. Resizing to {pyramid_video_t[level_idx][i].shape[1::-1]}.")
                    resized_level = cv2.resize(level_data, pyramid_video_t[level_idx][i].shape[1::-1], interpolation=cv2.INTER_LINEAR)
                    if len(resized_level.shape) < len(pyramid_video_t[level_idx][i].shape):
                         resized_level = resized_level[..., np.newaxis]
                    pyramid_video_t[level_idx][i] = resized_level

            print(f"  Frame {i+1}/{num_frames} pyramid built.", end='\r')
        print("\nLaplacian pyramids built for all frames.")
    except MemoryError:
        print("\nError: MemoryError encountered during pyramid building. Try reducing levels or resolution.")
        return None
    except Exception as e:
        print(f"\nAn unexpected error occurred during pyramid building: {e}")
        return None

    # 3. Apply Temporal Filtering to each level
    filtered_pyramid_video_t = []
    try:
        for level_idx, level_video in enumerate(pyramid_video_t):
            # Skip filtering the lowest level (Gaussian remnant) and very small levels
            if level_idx < pyramid_levels -1 and min(level_video.shape[1:3]) > 4: # Heuristic threshold
                print(f"Filtering pyramid level {level_idx+1}/{pyramid_levels}...")
                filtered_level = temporal_bandpass_filter(level_video, fps, low_freq, high_freq, axis=0)
                filtered_pyramid_video_t.append(filtered_level)
            else:
                print(f"Skipping filtering for level {level_idx+1}/{pyramid_levels} (lowest or too small).")
                filtered_pyramid_video_t.append(np.zeros_like(level_video))
    except MemoryError:
        print("\nError: MemoryError encountered during temporal filtering. Try reducing frames, levels, or resolution.")
        return None
    except Exception as e:
        print(f"\nAn unexpected error occurred during temporal filtering: {e}")
        return None

    # 4. Amplify Filtered Signals
    print(f"Amplifying filtered signals (factor={amplification_factor})...")
    amplified_pyramid_video_t = [level * amplification_factor for level in filtered_pyramid_video_t]
    
    # 5. Reconstruct Video
    print("Reconstructing video frames...")
    output_frames = []
    try:
        for i in range(num_frames):
            current_frame_pyramid = []
            for level_idx in range(pyramid_levels):
                # Add amplified signal back to the original pyramid level for this frame
                original_level = pyramid_video_t[level_idx][i]
                amplified_signal = amplified_pyramid_video_t[level_idx][i]
                
                current_frame_pyramid.append(original_level + amplified_signal)
                
            reconstructed_frame = reconstruct_from_laplacian_pyramid(current_frame_pyramid)
            output_frames.append(reconstructed_frame)
            print(f"  Frame {i+1}/{num_frames} reconstructed.", end='\r')
        print("\nVideo reconstruction complete.")
    except MemoryError:
        print("\nError: MemoryError encountered during reconstruction.")
        return None
    except Exception as e:
        print(f"\nAn unexpected error occurred during reconstruction: {e}")
        return None
        
    # 6. Save Output Video
    # Include frame count in filename if limited
    frame_limit_str = f"_frames{max_frames}" if max_frames else ""
    output_filename = os.path.join(output_dir, f"evm_output_levels{pyramid_levels}_f{low_freq:.2f}-{high_freq:.2f}_amp{amplification_factor}{frame_limit_str}.mp4")
    save_video(output_frames, fps, width, height, output_filename)

    print("Eulerian Magnification processing finished.")
    return output_filename