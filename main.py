from camera_scout import CameraResearcher


def main():
    Researcher = CameraResearcher(visualize=False)

    if cam := Researcher.get_camera("cam"):
        print(f"Using camera: {cam['name']}")
        print(f"Resolution: {cam['cam_param']['width']}x{cam['cam_param']['height']}")

    if cam := Researcher.get_camera("termal"):
        print(f"Using camera: {cam['name']}")
        print(f"Resolution: {cam['cam_param']['widqsth']}x{cam['cam_param']['height']}")


if __name__ == "__main__":
    main()
