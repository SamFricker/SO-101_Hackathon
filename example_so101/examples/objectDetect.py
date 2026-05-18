import cv2
import numpy as np

# USB camera index
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("Could not open camera")
    exit()

while True:

    ret, frame = cap.read()

    if not ret:
        break

    # Resize for consistency
    frame = cv2.resize(frame, (640, 480))

    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Blur slightly to reduce noise
    blurred = cv2.GaussianBlur(gray, (5,5), 0)

    # Threshold dark objects
    _, mask = cv2.threshold(
        blurred,
        60,      # threshold value
        255,
        cv2.THRESH_BINARY_INV
    )

    # Morphological cleanup
    kernel = np.ones((5,5), np.uint8)

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        kernel
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel
    )

    # Find contours
    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if contours:

        # Largest contour assumed sock
        largest = max(contours, key=cv2.contourArea)

        area = cv2.contourArea(largest)

        # Ignore tiny noise
        if area > 5000:

            x, y, w, h = cv2.boundingRect(largest)

            center_x = x + w // 2
            center_y = y + h // 2

            # Draw contour
            cv2.drawContours(
                frame,
                [largest],
                -1,
                (0,255,0),
                2
            )

            # Bounding box
            cv2.rectangle(
                frame,
                (x,y),
                (x+w,y+h),
                (255,0,0),
                2
            )

            # Center point
            cv2.circle(
                frame,
                (center_x, center_y),
                6,
                (0,0,255),
                -1
            )

            # Label
            cv2.putText(
                frame,
                f"Sock: ({center_x}, {center_y})",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0,255,0),
                2
            )

            print(f"Sock detected at: {center_x}, {center_y}")

    # Show windows
    cv2.imshow("Sock Detection", frame)
    cv2.imshow("Mask", mask)

    # Quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()