from camera_scout import CameraResearcher


def main():
    Resercher = CameraResearcher(visualize=False)

    if cam := Resercher.get_camera("cam"):
        print(f"Using camera: {cam['name']}")
        print(f"Resolution: {cam['cam_param']['width']}x{cam['cam_param']['height']}")

    if cam := Resercher.get_camera("termal"):
        print(f"Using camera: {cam['name']}")
        print(f"Resolution: {cam['cam_param']['width']}x{cam['cam_param']['height']}")


if __name__ == "__main__":
    main()
