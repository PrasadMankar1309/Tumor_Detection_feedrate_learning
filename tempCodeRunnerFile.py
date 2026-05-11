from flask import Flask, render_template, request
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np
import os

app = Flask(__name__)

# Load the trained VGG16 model
MODEL_PATH = "brain_tumor_detection_vgg16_model.h5"
model = load_model(MODEL_PATH)

# Folder to save uploaded files
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Class names (adjust if you used more categories)
class_names = ['pituitary', 'glioma', 'notumor', 'meningioma']

@app.route("/", methods=["GET", "POST"])
def upload_predict():
    if request.method == "POST":
        # Check if a file was uploaded
        if "file" not in request.files:
            return render_template("index.html", result="No file uploaded")
        file = request.files["file"]

        if file.filename == "":
            return render_template("index.html", result="No file selected")

        try:
            # Save uploaded file
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)

            # Load and preprocess image
            img = image.load_img(filepath, target_size=(224, 224))
            img_array = image.img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0) / 255.0

            # Predict tumor type
            prediction = model.predict(img_array)
            predicted_class = class_names[np.argmax(prediction)]
            confidence = round(np.max(prediction) * 100, 2)

            return render_template(
                "index.html",
                result=f"Predicted Tumor: {predicted_class}",
                confidence=confidence,
                file_path=filepath
            )

        except Exception as e:
            return render_template("index.html", result=f"Could not process the image: {e}")

    return render_template("index.html", result=None)

if __name__ == "__main__":
    app.run(debug=True)
