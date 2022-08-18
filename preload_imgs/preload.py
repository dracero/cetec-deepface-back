from deepface import DeepFace
import base64

result = DeepFace.verify(img1_path = "/preload_imgs/img.jpg", img2_path = "/preload_imgs/img.jpg",
				  model_name = "VGG-Face",
				  distance_metric = "cosine",
				  detector_backend = "opencv"
)
