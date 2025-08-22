import os
import cv2
import face_recognition
import pickle

ENCODINGS_FILE = "encodings.pkl"

# Encode and Save Faces 
def create_encodings(dataset_dir="records_data", encodings_file=ENCODINGS_FILE):
    known_encodings = []
    known_names = []

    for root, _, files in os.walk(dataset_dir):
        for file in files:
            if file.lower().endswith((".jpg", ".jpeg", ".png")):
                path = os.path.join(root, file)
                person_name = os.path.splitext(file)[0]
                parts = os.path.normpath(path).split(os.sep)
                identity = "/".join(parts[1:])  

                img = face_recognition.load_image_file(path)
                encodings = face_recognition.face_encodings(img)

                if encodings:
                    known_encodings.append(encodings[0])
                    known_names.append(identity)
                    print(f"[INFO] Encoded: {identity}")
                else:
                    print(f"[WARNING] No face found in {path}")

    # Save encodings to file
    with open(encodings_file, "wb") as f:
        pickle.dump((known_encodings, known_names), f)
    print(f"[INFO] Encodings saved to {encodings_file}")


# Load Encodings (fast) 
def load_encodings(encodings_file=ENCODINGS_FILE):
    if not os.path.exists(encodings_file):
        print("[INFO] No encodings found, creating them...")
        create_encodings()
    with open(encodings_file, "rb") as f:
        return pickle.load(f)


#  Real-time Recognition 
def recognize_from_camera(known_encodings, known_names):
    cap = cv2.VideoCapture(0)
    print("[INFO] Starting camera... Press 'q' to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Resize for speed
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # Detect faces
        face_locations = face_recognition.face_locations(rgb_small)
        face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

        for face_encoding, face_loc in zip(face_encodings, face_locations):
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.5)
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)

            name = "Unknown"
            if matches:
                best_match_index = face_distances.argmin()
                if matches[best_match_index]:
                    name = known_names[best_match_index]

            # Scale back
            top, right, bottom, left = [v * 4 for v in face_loc]

            # Draw
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(frame, name, (left, top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Face Recognition", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    known_encodings, known_names = load_encodings()
    recognize_from_camera(known_encodings, known_names)
