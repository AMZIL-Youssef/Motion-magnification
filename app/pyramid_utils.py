import cv2
import numpy as np

def build_gaussian_pyramid(image, levels):
    """Builds a Gaussian pyramid for an image."""
    pyramid = [image]
    for _ in range(levels - 1):
        image = cv2.pyrDown(image)
        pyramid.append(image)
    return pyramid

def build_laplacian_pyramid(image, levels):
    """Builds a Laplacian pyramid for an image."""
    gaussian_pyramid = build_gaussian_pyramid(image, levels)
    laplacian_pyramid = []
    for i in range(levels - 1):
        upsampled = cv2.pyrUp(gaussian_pyramid[i+1], dstsize=(gaussian_pyramid[i].shape[1], gaussian_pyramid[i].shape[0]))
        laplacian = cv2.subtract(gaussian_pyramid[i], upsampled)
        laplacian_pyramid.append(laplacian)
    # Add the smallest Gaussian level as the last level of the Laplacian pyramid
    laplacian_pyramid.append(gaussian_pyramid[-1])
    return laplacian_pyramid

def reconstruct_from_laplacian_pyramid(pyramid):
    """Reconstructs the original image from its Laplacian pyramid."""
    image = pyramid[-1]
    for i in range(len(pyramid) - 2, -1, -1):
        upsampled = cv2.pyrUp(image, dstsize=(pyramid[i].shape[1], pyramid[i].shape[0]))
        
        # S'assurer que les deux tableaux ont le même type de données (float32) avant l'addition
        term1 = upsampled.astype(np.float32)
        term2 = pyramid[i].astype(np.float32)
        image = cv2.add(term1, term2)
        
    return image