import cv2


def get_img_xy(img_path):
    """read image and print the x,y of the mouse click in the terminal"""
    img = cv2.imread(img_path)
    print(f"image shape: {img.shape}")
    cv2.imshow("image", img)

    def mouse_click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            print(f"x: {x}, y: {y}")

    cv2.setMouseCallback("image", mouse_click)

    cv2.waitKey(0)
    cv2.destroyAllWindows()


img_path = (
    "/home/dhl/Documents/short_whisper/year_progress/static_files/20240626-145623.jpg"
)

get_img_xy(img_path)
